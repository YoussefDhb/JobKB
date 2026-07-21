"""Wikidata enrichment — anchor KB tech-skills and occupations to stable Wikidata QIDs.

Wikidata is the KB's *connective tissue*: a general-purpose, richly-linked graph with stable QIDs
we can anchor everything else to, giving free entity resolution for technologies, tools and
companies that no occupation taxonomy provides. This module adds a **side table**
(`kb/wikidata_links.csv`) mapping our unified concepts to verified QIDs — it creates **no** nodes
or relations, so the core graph is untouched.

Resolution is a **single batched SPARQL query per ~50 labels** that does label matching *and*
class verification at once (QIDs are never hardcoded from memory — a guessed QID is often a
person/film). A candidate item is accepted only when:
  * our label equals the item's English label (`rdfs:label`, `match_method=exact`) or one of its
    aliases (`skos:altLabel`, `match_method=alias`), AND
  * its instance-of (`P31` then `P279*` closure) lands in a class allowlist — software /
    programming language / library / framework / OS / database / hardware / company for skills;
    profession / occupation for occupations — AND
  * it is NOT a denied class (human / film / album / taxon / video game).
Ties are broken by exact>alias, then by sitelink count (canonical items have more sitelinks).

Batching keeps the whole enrichment to ~110 SPARQL queries (a few minutes) instead of thousands of
per-label API calls, which the Action API rate-limits. Every resolution — including verified
*unresolved* — is snapshotted to `resources/WIKIDATA/retrieved/resolutions.csv`, flushed after each
chunk, so a re-run is fully offline/reproducible and an interruption resumes from the last flush.
A failed query leaves its labels *inconclusive* (not cached) so a transient error never poisons the
snapshot with a false 'unresolved'. All HTTP is polite (descriptive User-Agent, paced, backed-off,
fail-open).

The provided `ESCO_v1.2.1-wikidata.csv` is a noisy export whose QIDs were lost; its one clean
signal — programming-language synonyms — broadens matching for language skills (e.g. `golang`→Go).
"""

from __future__ import annotations

import csv
import json
import os
import time
import urllib.parse
import urllib.request

from . import config as C
from . import common as K

# Labels per SPARQL query, and labels between snapshot flushes (resume granularity).
_CHUNK = 50


# ------------------------------------------------------------------------------------------
# HTTP (stdlib urllib; polite + resilient + fail-open)
# ------------------------------------------------------------------------------------------
def _http_get(url: str, params: dict) -> dict | None:
    """GET a JSON endpoint with retries/backoff. Returns parsed JSON, or None on failure."""
    qs = urllib.parse.urlencode(params)
    full = f"{url}?{qs}"
    delay = 1.0
    for attempt in range(C.WIKIDATA_MAX_RETRIES):
        try:
            req = urllib.request.Request(full, headers={
                "User-Agent": C.WIKIDATA_USER_AGENT,
                "Accept": "application/sparql-results+json,application/json",
            })
            with urllib.request.urlopen(req, timeout=90) as resp:
                data = resp.read().decode("utf-8")
            time.sleep(C.WIKIDATA_RATE_SLEEP)
            return json.loads(data)
        except Exception as e:  # noqa: BLE001 — deliberately broad: HTTP/timeout/JSON all fail-open
            code = getattr(e, "code", None)
            if code and code != 429 and 400 <= code < 500:
                return None  # a real 4xx (bad query) won't improve on retry
            if attempt == C.WIKIDATA_MAX_RETRIES - 1:
                return None
            time.sleep(delay)
            delay *= 2
    return None


# ------------------------------------------------------------------------------------------
# Snapshot (offline-first cache of every resolution, keyed by normalized label + kind)
# ------------------------------------------------------------------------------------------
def _load_snapshot() -> dict:
    snap = {}
    if os.path.isfile(C.WIKIDATA_SNAPSHOT_CSV):
        with open(C.WIKIDATA_SNAPSHOT_CSV, encoding="utf-8", newline="") as f:
            for r in csv.DictReader(f):
                snap[(r["norm_label"], r["entity_kind"])] = r
    return snap


def _save_snapshot(snap: dict) -> None:
    os.makedirs(C.WIKIDATA_RETRIEVED_DIR, exist_ok=True)
    rows = sorted(snap.values(), key=lambda r: (r["entity_kind"], r["norm_label"]))
    with open(C.WIKIDATA_SNAPSHOT_CSV, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=C.WIKIDATA_SNAPSHOT_FIELDS)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in C.WIKIDATA_SNAPSHOT_FIELDS})


# ------------------------------------------------------------------------------------------
# Provided CSV: programming-language synonyms (the one clean signal in the noisy export)
# ------------------------------------------------------------------------------------------
def _language_seed() -> dict:
    """norm(language-or-synonym) -> canonical language name, from the resolved (non-QID) rows."""
    seed = {}
    if not os.path.isfile(C.WIKIDATA_SRC_CSV):
        return seed
    import re
    qid = re.compile(r"^Q\d+$")
    with open(C.WIKIDATA_SRC_CSV, encoding="utf-8-sig", errors="replace", newline="") as f:
        for r in csv.DictReader(f):
            lang = (r.get("languageLabel") or "").strip()
            if not lang or qid.match(lang):
                continue
            seed.setdefault(K.normalize_label(lang), lang)
            for alt in (r.get("languageAltLabel") or "").split(","):
                alt = alt.strip()
                if alt:
                    seed.setdefault(K.normalize_label(alt), lang)
    return seed


# ------------------------------------------------------------------------------------------
# Candidate selection (reuse the already-built unified concepts)
# ------------------------------------------------------------------------------------------
def _skill_candidates():
    out = []
    for r in K.read_all(C.UNIFIED_SKILLS_CSV):
        if r.get("it_subtype") not in C.WIKIDATA_SKILL_SUBDOMAINS:
            continue
        label = (r.get("primary_label_en") or "").strip()
        if label and len(label.split()) <= C.WIKIDATA_SKILL_MAX_TOKENS:
            out.append((r["unified_id"], label))
    return out


def _occupation_candidates():
    out = []
    for r in K.read_all(C.UNIFIED_OCCUPATIONS_CSV):
        label = (r.get("primary_label_en") or "").strip()
        if label:
            out.append((r["unified_id"], label))
    return out


# ------------------------------------------------------------------------------------------
# Batched SPARQL resolution: label-match + class-verification in one query per ~50 labels
# ------------------------------------------------------------------------------------------
def _sparql_escape(s: str) -> str:
    return s.replace("\\", "\\\\").replace('"', '\\"').replace("\n", " ").replace("\r", " ")


def _resolve_chunk(items, allow_classes, seed, field_classes=()):
    """items: list of (norm, label). One SPARQL query resolves all of them. Returns
    (resolved, ok): resolved = {norm: best-resolution-dict}; ok = whether the query succeeded
    (if False, callers keep the labels inconclusive instead of caching a false 'unresolved').

    `allow_classes` are matched by P31/P279* closure (concrete tech / professions); `field_classes`
    (abstract IT fields) by cheap DIRECT P31 — closing over e.g. 'academic discipline' would time
    the query out."""
    # Map each query string -> the KB norm it serves (KB label + optional CSV-seed canonical name).
    str2norm = {}
    for norm, label in items:
        str2norm[label] = norm
        if seed is not None and norm in seed and seed[norm].lower() != label.lower():
            str2norm.setdefault(seed[norm], norm)
    values = " ".join(f'"{_sparql_escape(s)}"@en' for s in str2norm)
    allow = " ".join(f"wd:{q}" for q in allow_classes)
    deny = " ".join(f"wd:{q}" for q in C.WIKIDATA_DENY_CLASSES)
    # class filter: P279* closure for concrete classes, direct P31 for broad field classes.
    class_filter = f"{{ ?item wdt:P31 ?t. ?t wdt:P279* ?ac. VALUES ?ac {{ {allow} }} }}"
    if field_classes:
        field = " ".join(f"wd:{q}" for q in field_classes)
        class_filter += f" UNION {{ ?item wdt:P31 ?fc. VALUES ?fc {{ {field} }} }}"
    # Lean query: label/alias match + class filter + deny filter + sitelinks. (Fetching descriptions
    # here made the query time out, so wd_description is left empty.)
    query = (
        "SELECT ?lbl ?item ?itemLabel ?via (SAMPLE(?slv) AS ?sl) WHERE { "
        f"VALUES ?lbl {{ {values} }} "
        '{ ?item rdfs:label ?lbl. BIND("exact" AS ?via) } '
        'UNION { ?item skos:altLabel ?lbl. BIND("alias" AS ?via) } '
        f"{class_filter} "
        f"FILTER NOT EXISTS {{ ?item wdt:P31 ?dc. VALUES ?dc {{ {deny} }} }} "
        "OPTIONAL { ?item wikibase:sitelinks ?slv. } "
        'SERVICE wikibase:label { bd:serviceParam wikibase:language "en". } } '
        "GROUP BY ?lbl ?item ?itemLabel ?via"
    )
    js = _http_get(C.WIKIDATA_SPARQL_URL, {"query": query, "format": "json"})
    if js is None:
        return {}, False

    # Collect candidates per norm, then pick the best (exact > alias, then sitelinks).
    best = {}  # norm -> (rank_tuple, resolution)
    for b in js.get("results", {}).get("bindings", []):
        s = b.get("lbl", {}).get("value", "")
        norm = str2norm.get(s)
        if norm is None:
            continue
        qid = b["item"]["value"].rsplit("/", 1)[-1]
        via = b.get("via", {}).get("value", "exact")
        wd_label = b.get("itemLabel", {}).get("value", "")
        sl = int(b.get("sl", {}).get("value", "0") or 0)
        rank = (1 if via == "exact" else 0, sl)
        if norm not in best or rank > best[norm][0]:
            best[norm] = (rank, {
                "qid": qid, "wd_label": wd_label, "wd_description": "",
                "match_method": via, "confidence": "high" if via == "exact" else "medium",
            })
    return {norm: res for norm, (_, res) in best.items()}, True


def _resolve(items, kind, allow_classes, snap, seed=None, checkpoint=None, field_classes=()):
    """Resolve `items` (list of (unified_id, label)) into `snap` in place; return network-query
    count. New labels are looked up in ~50-label SPARQL chunks; each chunk flushes a checkpoint."""
    to_fetch = {}  # norm -> representative label (skip anything already snapshotted)
    for _, label in items:
        norm = K.normalize_label(label)
        if (norm, kind) not in snap:
            to_fetch.setdefault(norm, label)
    todo = list(to_fetch.items())

    queries = 0
    for i in range(0, len(todo), _CHUNK):
        sub = todo[i:i + _CHUNK]
        resolved, ok = _resolve_chunk(sub, allow_classes, seed, field_classes)
        queries += 1
        if not ok:
            continue  # query failed -> leave this chunk inconclusive (retried next run)
        for norm, label in sub:
            row = {"norm_label": norm, "entity_kind": kind, "qid": "", "wd_label": "",
                   "wd_description": "", "instance_of": "", "match_method": "", "confidence": ""}
            m = resolved.get(norm)
            if m:
                corrob = "+csv_seed" if (seed is not None and norm in seed) else ""
                row.update({"qid": m["qid"], "wd_label": m["wd_label"],
                            "wd_description": m["wd_description"],
                            "match_method": m["match_method"] + corrob,
                            "confidence": m["confidence"]})
            snap[(norm, kind)] = row
        if checkpoint is not None:
            checkpoint()
    return queries


def run(refresh: bool = False) -> dict:
    """Resolve tech-skills + occupations to Wikidata QIDs; write kb/wikidata_links.csv + snapshot."""
    snap = {} if refresh else _load_snapshot()
    seed = _language_seed()
    skills = _skill_candidates()
    occs = _occupation_candidates()
    print(f"[WIKIDATA] candidates: {len(skills)} tech-skills, {len(occs)} occupations "
          f"(snapshot has {len(snap)} cached; refresh={refresh}).", flush=True)

    def _checkpoint():
        _save_snapshot(snap)
        anchored = sum(1 for v in snap.values() if v.get("qid"))
        print(f"[WIKIDATA] checkpoint: {len(snap)} labels resolved ({anchored} anchored) "
              f"— snapshot flushed.", flush=True)

    q1 = _resolve(skills, "skill", C.WIKIDATA_SKILL_CLASSES, snap, seed=seed,
                  checkpoint=_checkpoint, field_classes=C.WIKIDATA_SKILL_FIELD_CLASSES)
    q2 = _resolve(occs, "occupation", C.WIKIDATA_OCC_CLASSES, snap, seed=None, checkpoint=_checkpoint)
    _save_snapshot(snap)

    # Build the KB side table (only entities that actually resolved to a QID).
    def _links(items, kind):
        rows = []
        for uid, label in items:
            r = snap.get((K.normalize_label(label), kind))
            if r and r.get("qid"):
                rows.append({
                    "entity_id": uid, "entity_kind": kind, "unified_id": uid,
                    "label_en": label, "qid": r["qid"],
                    "wikidata_url": f"https://www.wikidata.org/wiki/{r['qid']}",
                    "wd_label": r["wd_label"], "wd_description": r["wd_description"],
                    "instance_of": r.get("instance_of", ""),
                    "match_method": r["match_method"], "confidence": r["confidence"],
                })
        return rows

    links = _links(skills, "skill") + _links(occs, "occupation")
    K.write_csv(C.WIKIDATA_LINKS_CSV, C.WIKIDATA_LINKS_FIELDS, links)

    n_skill = sum(1 for l in links if l["entity_kind"] == "skill")
    n_occ = sum(1 for l in links if l["entity_kind"] == "occupation")
    n_high = sum(1 for l in links if l["confidence"] == "high")
    K.log_provenance("WIKIDATA", [{
        "entity_id": "WIKIDATA", "source": "WIKIDATA", "source_version": "live query.wikidata.org",
        "retrieved_at": K.now_iso(), "retrieval_method": "sparql label-match + class verify",
        "notes": f"{len(links)} QID anchors ({n_skill} skills, {n_occ} occ, {n_high} high-conf); "
                 f"{q1 + q2} SPARQL queries this run",
    }])
    print(f"[WIKIDATA] {len(links)} QID anchors written ({n_skill} skills, {n_occ} occupations, "
          f"{n_high} high-confidence); {q1 + q2} SPARQL queries.", flush=True)
    return {"anchors": len(links), "skills": n_skill, "occupations": n_occ, "high": n_high}
