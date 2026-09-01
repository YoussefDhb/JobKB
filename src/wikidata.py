"""Wikidata enrichment: anchor KB tech-skills and occupations to stable QIDs in a side table."""

from __future__ import annotations

import csv
import json
import os
import re
import time
import urllib.parse
import urllib.request

from . import config as C
from . import common as K

# Labels per SPARQL query, and labels between snapshot flushes.
_CHUNK = 50


# HTTP (stdlib urllib; polite + resilient + fail-open)
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
        except Exception as e: 
            code = getattr(e, "code", None)
            if code == 429:
                # Throttled (WDQS outage rule caps to ~1 req/min). Wait for the token bucket to refill instead of failing fast 
                if attempt == C.WIKIDATA_MAX_RETRIES - 1:
                    return None
                ra = None
                try:
                    hdrs = getattr(e, "headers", None)
                    ra = int(hdrs.get("Retry-After")) if hdrs and hdrs.get("Retry-After") else None
                except (TypeError, ValueError):
                    ra = None
                wait = min(ra, C.WIKIDATA_THROTTLE_MAX_WAIT) if ra else C.WIKIDATA_THROTTLE_WAIT
                time.sleep(max(wait, C.WIKIDATA_THROTTLE_WAIT))
                continue
            if code and 400 <= code < 500:
                return None  # a real 4xx (bad query) won't improve on retry
            if attempt == C.WIKIDATA_MAX_RETRIES - 1:
                return None
            time.sleep(delay)
            delay *= 2
    return None


# Snapshot
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


# Provided CSV: programming-language synonyms
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


# Candidate selection (reuse the already-built unified concepts)
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


def _domain_candidates():
    """The 10 faceted-taxonomy functional-domain nodes (hierarchy.DOMAINS). Each domain node stores its domain KEY in `it_subtype`"""
    items, probes = [], {}
    for r in K.read_all(C.SKILLS_CSV):
        if r.get("esco_skill_type") != "skill_domain":
            continue
        dom_key = (r.get("it_subtype") or "").strip()
        labels = C.WIKIDATA_DOMAIN_PROBES.get(dom_key)
        if not labels:  # dom_cross / dom_soft: no clean single concept -> intentionally unresolved
            continue
        did = r["entity_id"]
        probes[did] = list(labels)
        for lbl in labels:
            items.append((did, lbl))
    return items, probes


# Batched SPARQL resolution: label-match + class-verification in one query
def _sparql_escape(s: str) -> str:
    return s.replace("\\", "\\\\").replace('"', '\\"').replace("\n", " ").replace("\r", " ")


def _resolve_chunk(items, allow_classes, seed, field_classes=()):
    """items: list of (norm, label)."""
    # Map each query string -> the KB norm it serves (KB label + optional CSV-seed canonical name).
    str2norm = {}
    for norm, label in items:
        str2norm[label] = norm
        if seed is not None and norm in seed and seed[norm].lower() != label.lower():
            str2norm.setdefault(seed[norm], norm)
    values = " ".join(f'"{_sparql_escape(s)}"@en' for s in str2norm)
    deny = " ".join(f"wd:{q}" for q in C.WIKIDATA_DENY_CLASSES)
    # class filter
    branches = []
    if allow_classes:
        allow = " ".join(f"wd:{q}" for q in allow_classes)
        branches.append(f"{{ ?item wdt:P31 ?t. ?t wdt:P279* ?ac. VALUES ?ac {{ {allow} }} }}")
    if field_classes:
        field = " ".join(f"wd:{q}" for q in field_classes)
        branches.append(f"{{ ?item wdt:P31 ?fc. VALUES ?fc {{ {field} }} }}")
    class_filter = " UNION ".join(branches)
    # Lean query: label/alias match + class filter + deny filter + sitelinks.
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
    """Resolve `items` (list of (unified_id, label)) into `snap` in place."""
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


_NONIT_DESC = [re.compile(p, re.I) for p in C.WIKIDATA_NONIT_DESC_PATTERNS]


def _is_nonit_desc(desc: str) -> bool:
    """True if a fetched Wikidata description reads as a non-tech same-name homonym """
    d = (desc or "").strip()
    return bool(d) and any(p.search(d) for p in _NONIT_DESC)


def _relation(match_method: str) -> str:
    """SKOS mapping relation for the side table."""
    return "skos:exactMatch" if (match_method or "").startswith("exact") else "skos:closeMatch"


# Metadata pass: fetch description + aliases (en/fr) for the anchored QIDs, keyed BY QID.
def _fetch_metadata(snap, checkpoint=None) -> int:
    """For every anchored QID lacking metadata, fetch en/fr `schema:description` + `skos:altLabel`. """
    need = {}
    for key, r in snap.items():
        qid = r.get("qid")
        if not qid:
            continue
        if r.get("wd_description") or r.get("wd_aliases_en") or r.get("wd_aliases_fr"):
            continue
        need.setdefault(qid, []).append(key)
    qids = list(need)
    queries = 0
    for i in range(0, len(qids), _CHUNK):
        batch = qids[i:i + _CHUNK]
        values = " ".join(f"wd:{q}" for q in batch)
        query = (
            "SELECT ?item ?d_en ?d_fr "
            '(GROUP_CONCAT(DISTINCT ?ae; separator=" | ") AS ?a_en) '
            '(GROUP_CONCAT(DISTINCT ?af; separator=" | ") AS ?a_fr) WHERE { '
            f"VALUES ?item {{ {values} }} "
            'OPTIONAL { ?item schema:description ?d_en. FILTER(LANG(?d_en)="en") } '
            'OPTIONAL { ?item schema:description ?d_fr. FILTER(LANG(?d_fr)="fr") } '
            'OPTIONAL { ?item skos:altLabel ?ae. FILTER(LANG(?ae)="en") } '
            'OPTIONAL { ?item skos:altLabel ?af. FILTER(LANG(?af)="fr") } '
            "} GROUP BY ?item ?d_en ?d_fr"
        )
        js = _http_get(C.WIKIDATA_SPARQL_URL, {"query": query, "format": "json"})
        queries += 1
        if js is None:
            continue 
        got = {}
        for b in js.get("results", {}).get("bindings", []):
            qid = b["item"]["value"].rsplit("/", 1)[-1]
            got[qid] = {
                "wd_description": b.get("d_en", {}).get("value", "")
                                  or b.get("d_fr", {}).get("value", ""),
                "wd_description_fr": b.get("d_fr", {}).get("value", ""),
                "wd_aliases_en": b.get("a_en", {}).get("value", ""),
                "wd_aliases_fr": b.get("a_fr", {}).get("value", ""),
            }
        for qid in batch:
            m = got.get(qid)
            if not m:
                continue
            for key in need[qid]:
                snap[key]["wd_description"] = m["wd_description"]
                snap[key]["wd_aliases_en"] = m["wd_aliases_en"]
                snap[key]["wd_aliases_fr"] = m["wd_aliases_fr"]
        if checkpoint is not None:
            checkpoint()
    return queries


def run(refresh: bool = False) -> dict:
    """Resolve tech-skills + occupations to Wikidata QIDs; write kb/wikidata_links.csv + snapshot."""
    snap = {} if refresh else _load_snapshot()
    seed = _language_seed()
    skills = _skill_candidates()
    occs = _occupation_candidates()
    dom_items, dom_probes = _domain_candidates()
    print(f"[WIKIDATA] candidates: {len(skills)} tech-skills, {len(occs)} occupations, "
          f"{len(dom_probes)} domains ({len(dom_items)} probes) "
          f"(snapshot has {len(snap)} cached; refresh={refresh}).", flush=True)

    def _checkpoint():
        _save_snapshot(snap)
        anchored = sum(1 for v in snap.values() if v.get("qid"))
        print(f"[WIKIDATA] checkpoint: {len(snap)} labels resolved ({anchored} anchored) "
              f"— snapshot flushed.", flush=True)

    q1 = _resolve(skills, "skill", C.WIKIDATA_SKILL_CLASSES, snap, seed=seed,
                  checkpoint=_checkpoint, field_classes=C.WIKIDATA_SKILL_FIELD_CLASSES)
    q2 = _resolve(occs, "occupation", (), snap, seed=None, checkpoint=_checkpoint,
                  field_classes=C.WIKIDATA_OCC_CLASSES)
    q3 = _resolve(dom_items, "domain", C.WIKIDATA_DOMAIN_CLASSES, snap, seed=None,
                  checkpoint=_checkpoint, field_classes=C.WIKIDATA_DOMAIN_FIELD_CLASSES)
    _save_snapshot(snap)

    # Metadata pass: description + aliases (en/fr) for the anchored QIDs, for in-graph enrichment.
    qm = _fetch_metadata(snap, checkpoint=_checkpoint)
    _save_snapshot(snap)

    # Build the KB side table (only entities that actually resolved to a QID).
    def _row(uid, kind, label, r):
        return {
            "entity_id": uid, "entity_kind": kind, "unified_id": uid,
            "label_en": label, "qid": r["qid"], "relation": _relation(r["match_method"]),
            "wikidata_url": f"https://www.wikidata.org/wiki/{r['qid']}",
            "wd_label": r["wd_label"], "wd_description": r.get("wd_description", ""),
            "wd_aliases_en": r.get("wd_aliases_en", ""), "wd_aliases_fr": r.get("wd_aliases_fr", ""),
            "instance_of": r.get("instance_of", ""),
            "match_method": r["match_method"], "confidence": r["confidence"],
        }

    def _links(items, kind):
        # The non-IT description guard is a homonym filter for concept/tech labels.
        guard = kind != "occupation"
        rows = []
        for uid, label in items:
            r = snap.get((K.normalize_label(label), kind))
            if r and r.get("qid") and not (guard and _is_nonit_desc(r.get("wd_description", ""))):
                rows.append(_row(uid, kind, label, r))
        return rows

    # Domains: one anchor per domain node, choosing the first probe label that resolved to a QID.
    def _domain_links():
        rows = []
        for did, labels in dom_probes.items():
            for label in labels:
                r = snap.get((K.normalize_label(label), "domain"))
                if r and r.get("qid") and not _is_nonit_desc(r.get("wd_description", "")):
                    rows.append(_row(did, "domain", label, r))
                    break
        return rows

    links = _links(skills, "skill") + _links(occs, "occupation") + _domain_links()
    K.write_csv(C.WIKIDATA_LINKS_CSV, C.WIKIDATA_LINKS_FIELDS, links)

    n_skill = sum(1 for l in links if l["entity_kind"] == "skill")
    n_occ = sum(1 for l in links if l["entity_kind"] == "occupation")
    n_dom = sum(1 for l in links if l["entity_kind"] == "domain")
    n_high = sum(1 for l in links if l["confidence"] == "high")
    K.log_provenance("WIKIDATA", [{
        "entity_id": "WIKIDATA", "source": "WIKIDATA", "source_version": "live query.wikidata.org",
        "retrieved_at": K.now_iso(), "retrieval_method": "sparql label-match + class verify + metadata",
        "notes": f"{len(links)} QID anchors ({n_skill} skills, {n_occ} occ, {n_dom} domains, "
                 f"{n_high} high-conf); {q1 + q2 + q3 + qm} SPARQL queries this run",
    }])
    print(f"[WIKIDATA] {len(links)} QID anchors written ({n_skill} skills, {n_occ} occupations, "
          f"{n_dom} domains, {n_high} high-confidence); {q1 + q2 + q3 + qm} SPARQL queries.", flush=True)

    # Weave the anchors into the concept layer (identifiers + descriptions + cleaned aliases).
    integrate()
    return {"anchors": len(links), "skills": n_skill, "occupations": n_occ,
            "domains": n_dom, "high": n_high}


# In-graph integration: join the side table onto the unified concept layer.
def _links_by_uid() -> dict:
    """unified_id -> side-table row (only anchored). Empty dict if the side table is absent."""
    idx = {}
    if os.path.isfile(C.WIKIDATA_LINKS_CSV):
        for r in K.read_all(C.WIKIDATA_LINKS_CSV):
            if r.get("qid"):
                idx[r.get("unified_id") or r.get("entity_id")] = r
    return idx


_PAREN = re.compile(r"\([^)]*\)")


def _clean_aliases(existing_norm, raw):
    """Hygiene-filter Wikidata aliases before merging into a concept's alt_labels"""
    from . import relevance 
    out, out_norm = [], set()
    for a in (p.strip() for p in (raw or "").split(" | ")):
        n = K.normalize_label(a)
        if not a or not n or n in existing_norm or n in out_norm:
            continue
        # a "X (qualifier)" alias that reduces to an existing label is a disambiguation variant.
        stripped = K.normalize_label(_PAREN.sub("", a))
        if stripped and stripped != n and (stripped in existing_norm or stripped in out_norm):
            continue
        if len(a.split()) > C.WIKIDATA_ALIAS_MAX_TOKENS or len(a) > C.WIKIDATA_ALIAS_MAX_CHARS:
            continue
        if relevance.is_structural_noise(a):
            continue
        out.append(a)
        out_norm.add(n)
        if len(out) >= C.WIKIDATA_MAX_ALIASES:
            break
    return out


def enrich_rows(rows, kind):
    """Mutate unified `rows` in place."""
    idx = _links_by_uid()
    for r in rows:
        link = idx.get(r.get("unified_id", ""))
        if not link:
            # Always overwrite from the side table (the source of truth).
            r["wikidata_qid"] = ""
            r["wikidata_url"] = ""
            r["wikidata_description"] = ""
            continue
        r["wikidata_qid"] = link["qid"]
        r["wikidata_url"] = link.get("wikidata_url", "")
        r["wikidata_description"] = link.get("wd_description", "")
        for lang in ("en", "fr"):
            field = f"alt_labels_{lang}"
            existing = [p.strip() for p in (r.get(field) or "").split(" | ") if p.strip()]
            existing_norm = {K.normalize_label(r.get(f"primary_label_{lang}", ""))}
            existing_norm |= {K.normalize_label(x) for x in existing}
            add = _clean_aliases(existing_norm, link.get(f"wd_aliases_{lang}", ""))
            if add:
                r[field] = " | ".join(existing + add)
    return rows


def integrate():
    """Weave the Wikidata side table into the concept layer by re-running the merge stage."""
    if not os.path.isfile(C.WIKIDATA_LINKS_CSV):
        return (0, 0)
    from . import merge
    merge.run()
    occ = K.read_all(C.UNIFIED_OCCUPATIONS_CSV)
    skl = K.read_all(C.UNIFIED_SKILLS_CSV)
    n_occ = sum(1 for r in occ if r.get("wikidata_qid"))
    n_skl = sum(1 for r in skl if r.get("wikidata_qid"))
    print(f"[WIKIDATA] integrated into concept layer: {n_skl} skills + {n_occ} occupations carry a QID.",
          flush=True)
    return (n_skl, n_occ)
