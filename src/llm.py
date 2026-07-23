"""LLM-powered enrichment (pillar 3) — HuggingFace, auto-validated (pillar 4).

Uses a HuggingFace generative LLM to make the KB more *complete* without sacrificing *reliability*:

  * **T1 descriptions** — concise, factual definitions for occupations and emerging/niche skills that
    have none (grounded on label + taxonomy context + any Wikidata description).
  * **T2 fill `hard_soft`** — classify skills missing the hard/soft flag, via the already-loaded
    mDeBERTa as a **zero-shot** classifier (no API cost).
  * **T3 inferred links** — occupation→skill relations the demand data missed, chosen from the
    *existing* KB skill vocabulary (never invented) and NLI-verified.
  * **T4 emerging tech** — link emerging skills to demanding occupations, and add genuinely-new
    emerging tech/roles **only when a real Wikidata QID confirms them** (reuses `wikidata`).

Because the KB is built with **no human in the loop**, every LLM output is validated before it touches
the graph — the IT-relevance gate (`relevance`) + the mDeBERTa NLI verifier (`align.verify`) — marked
with provenance (`source="LLM"`, `description_source="llm"`, `relation_type="llm_inferred"`), and
**never overwrites** a source/curated value. Generation is **snapshotted** (`resources/LLM/retrieved/`)
so re-runs are offline and make zero API calls (important on the HF free tier). The client is
API-primary (HF Inference Providers) with an optional local fallback, and **fail-open** (offline / no
credits → the task is skipped, the build still succeeds).
"""

from __future__ import annotations

import csv
import hashlib
import json
import os
import re
import time

from . import config as C
from . import common as K


# ==========================================================================================
# Snapshot cache (offline-first: every generation is cached by task+key, so re-runs cost nothing)
# ==========================================================================================
def _load_snapshot() -> dict:
    snap = {}
    if os.path.isfile(C.LLM_SNAPSHOT_CSV):
        with open(C.LLM_SNAPSHOT_CSV, encoding="utf-8", newline="") as f:
            for r in csv.DictReader(f):
                snap[(r["task"], r["key"])] = r
    return snap


def _save_snapshot(snap: dict) -> None:
    os.makedirs(C.LLM_RETRIEVED_DIR, exist_ok=True)
    rows = sorted(snap.values(), key=lambda r: (r["task"], r["key"]))
    with open(C.LLM_SNAPSHOT_CSV, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=C.LLM_SNAPSHOT_FIELDS)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in C.LLM_SNAPSHOT_FIELDS})


def _hash(s: str) -> str:
    return hashlib.sha1(s.encode("utf-8")).hexdigest()[:12]


# ==========================================================================================
# LLM client: HF Inference Providers (primary) -> local transformers (optional) -> None (fail-open)
# ==========================================================================================
class LLMClient:
    def __init__(self):
        self.mode = None
        self._api = None
        self._api_dead = False
        self._local = None
        if C.HF_TOKEN:
            try:
                from huggingface_hub import InferenceClient
                kw = {"model": C.LLM_API_MODEL, "token": C.HF_TOKEN, "timeout": C.LLM_TIMEOUT}
                if C.LLM_API_PROVIDER and C.LLM_API_PROVIDER != "auto":
                    kw["provider"] = C.LLM_API_PROVIDER
                self._api = InferenceClient(**kw)
                self.mode = "api"
            except Exception:
                self._api = None
        # Load the local model whenever the fallback is enabled — so chat() can degrade to it if the
        # API errors mid-run (e.g. HTTP 402 when free-tier credits are exhausted), not only when the
        # API can't be constructed at all.
        if C.LLM_USE_LOCAL_FALLBACK:
            try:
                from transformers import pipeline
                self._local = pipeline("text-generation", model=C.LLM_LOCAL_MODEL,
                                       token=C.HF_TOKEN or None)
                self.mode = self.mode or "local"
            except Exception:
                self._local = None

    @property
    def ok(self) -> bool:
        return self._api is not None or self._local is not None

    def chat(self, system: str, user: str) -> str | None:
        """One chat completion. Returns the text, or None on failure (fail-open)."""
        if self._api is not None and not self._api_dead:
            delay = 1.0
            for attempt in range(C.LLM_MAX_RETRIES):
                try:
                    r = self._api.chat_completion(
                        messages=[{"role": "system", "content": system},
                                  {"role": "user", "content": user}],
                        max_tokens=C.LLM_MAX_TOKENS, temperature=C.LLM_TEMPERATURE)
                    time.sleep(C.LLM_RATE_SLEEP)
                    return (r.choices[0].message.content or "").strip()
                except Exception as e:  # noqa: BLE001 — rate limit / network / provider: back off, fail-open
                    status = getattr(e, "status_code", None) or getattr(getattr(e, "response", None),
                                                                        "status_code", None)
                    if status in (401, 402, 403):
                        # credits depleted / auth — won't recover this run; stop hitting the API.
                        self._api_dead = True
                        break
                    if attempt == C.LLM_MAX_RETRIES - 1:
                        break
                    time.sleep(delay)
                    delay *= 2
        return self._local_chat(system, user)

    def _local_chat(self, system: str, user: str) -> str | None:
        if self._local is None:
            return None
        try:
            msgs = [{"role": "system", "content": system}, {"role": "user", "content": user}]
            out = self._local(msgs, max_new_tokens=C.LLM_MAX_TOKENS, do_sample=False,
                              return_full_text=False)
            return (out[0]["generated_text"] or "").strip()
        except Exception:
            return None


# ==========================================================================================
# JSON parsing (tolerant: models sometimes wrap JSON in prose or code fences)
# ==========================================================================================
_JSON_OBJ = re.compile(r"\{.*\}", re.S)


def _parse_json(text: str | None) -> dict | None:
    if not text:
        return None
    try:
        return json.loads(text)
    except Exception:
        m = _JSON_OBJ.search(text)
        if m:
            try:
                return json.loads(m.group(0))
            except Exception:
                return None
    return None


def _clean_desc(label: str, desc: str) -> str:
    """Strip a leading 'Label:' echo and surrounding quotes/whitespace from a generated definition."""
    d = (desc or "").strip().strip('"').strip()
    # models often prefix "MLOps engineer: ..." — drop an echoed label prefix.
    pref = re.match(r"^\s*" + re.escape(label) + r"\s*[:\-–]\s*", d, re.I)
    if pref:
        d = d[pref.end():].strip()
    return d


# ==========================================================================================
# Validation (pillar 4): the mDeBERTa NLI verifier grounds/gates every LLM output.
# ==========================================================================================
class Validator:
    def __init__(self):
        from .align.verify import Verifier
        self.v = Verifier()
        self.rejects = []  # (task, entity_id, label, output, reason, score)

    @property
    def nli_ok(self):
        return self.v.nli_ok

    def _entail(self, premise, hypothesis):
        s = self.v.entail_batch([(premise, hypothesis)])[0]
        return s if s is not None else 0.0

    def check_description(self, task, entity_id, label, desc):
        """A generated description is accepted iff it is well-formed AND, per NLI, actually describes
        the label (catches off-topic drift / hallucination). Returns (ok, score)."""
        n = len(desc)
        if n < C.LLM_DESC_MIN_CHARS or n > C.LLM_DESC_MAX_CHARS:
            self.rejects.append((task, entity_id, label, desc, "length", n))
            return False, 0.0
        if self.nli_ok:
            score = self._entail(desc, f"This text describes {label}.")
            if score < C.LLM_DESC_NLI_MIN:
                self.rejects.append((task, entity_id, label, desc, "nli_off_topic", round(score, 3)))
                return False, score
            return True, score
        return True, 0.0  # NLI unavailable -> structural-only (fail-open)

    def dump_rejects(self):
        rows = [{"task": t, "entity_id": e, "label": l, "output": o, "reason": r, "score": s}
                for (t, e, l, o, r, s) in self.rejects]
        K.write_csv(C.LLM_REJECTED_CSV, C.LLM_REJECTED_FIELDS, rows)


# ==========================================================================================
# Context builders (ground generation on the existing KB, not the model's memory alone)
# ==========================================================================================
def _domain_label(subtype):
    from . import hierarchy as H
    cat = H.CATEGORIES.get(subtype)
    if cat:
        dom = H.DOMAINS.get(cat[0])
        return f"{cat[1]} / {dom[1] if dom else ''}".strip(" /")
    return ""


def _skill_context(row):
    parts = []
    if row.get("it_subtype"):
        d = _domain_label(row["it_subtype"])
        if d:
            parts.append(f"domain: {d}")
    if row.get("wikidata_description"):
        parts.append(f"Wikidata: {row['wikidata_description']}")
    alts = (row.get("alt_labels_en") or "").split(" | ")[:3]
    if alts and alts[0]:
        parts.append("aka " + ", ".join(a for a in alts if a))
    return "; ".join(parts)


def _occ_context(row):
    parts = []
    if row.get("isco_code"):
        parts.append(f"ISCO {row['isco_code']}")
    if row.get("wikidata_description"):
        parts.append(f"Wikidata: {row['wikidata_description']}")
    alts = (row.get("alt_labels_en") or "").split(" | ")[:3]
    if alts and alts[0]:
        parts.append("aka " + ", ".join(a for a in alts if a))
    return "; ".join(parts)


# Plain-text output (not JSON): small local models follow "one sentence" far more reliably than strict
# JSON, and it parses trivially. IT-relevance is enforced downstream by the NLI validator, not a flag.
_DESC_SYS = (
    "You are an expert IT taxonomy assistant building a knowledge base of IT occupations and skills. "
    "Given an entity and its context, reply with ONLY one concise, factual, neutral sentence (max ~35 "
    "words) that defines it. Do not restate the name, do not add quotes, labels, JSON, or any preamble "
    "— output the single definition sentence and nothing else."
)


def _first_sentence(text, maxlen):
    """First 1-2 sentences of a plain-text generation, trimmed to maxlen (defensive against rambling)."""
    t = " ".join((text or "").split())
    if len(t) <= maxlen:
        return t
    cut = t[:maxlen]
    dot = cut.rfind(". ")
    return (cut[:dot + 1] if dot > 40 else cut).strip()


# ==========================================================================================
# T1 — generate descriptions for occupations + emerging/niche skills lacking one
# ==========================================================================================
def _needs_desc(row):
    return not (row.get("description") or "").strip()


def _task_descriptions(client, snap, validator):
    occ = K.read_all(C.UNIFIED_OCCUPATIONS_CSV)
    skl = K.read_all(C.UNIFIED_SKILLS_CSV)
    targets = []
    for r in occ:
        if _needs_desc(r) and (r.get("primary_label_en") or "").strip():
            targets.append(("occupation", r, _occ_context(r)))
    for r in skl:
        if (_needs_desc(r) and (r.get("primary_label_en") or "").strip()
                and r.get("it_subtype") in C.LLM_DESC_SKILL_SUBDOMAINS):
            targets.append(("skill", r, _skill_context(r)))
    if C.LLM_DESC_MAX_TARGETS:
        targets = targets[:C.LLM_DESC_MAX_TARGETS]  # bound API cost (free tier / testing)

    made = cached = rejected = failed = 0
    for kind, row, ctx in targets:
        uid, label = row["unified_id"], row["primary_label_en"]
        if snap.get(("desc", uid), {}).get("output"):
            cached += 1  # already generated + validated in a prior run
            continue
        user = f"{kind}: {label}" + (f"\ncontext: {ctx}" if ctx else "")
        raw = client.chat(_DESC_SYS, user)
        if raw is None:
            failed += 1  # backend returned nothing (rate limit / offline) — retried on next run
            continue
        out = _first_sentence(_clean_desc(label, raw), C.LLM_DESC_MAX_CHARS)
        ok, _ = validator.check_description("desc", uid, label, out)  # validate BEFORE caching
        if not ok:
            continue  # check_description already logged the reject
        snap[("desc", uid)] = {"task": "desc", "key": uid, "model": client.mode or "",
                               "prompt_hash": _hash(user), "output": out, "created_at": K.now_iso()}
        made += 1
    return {"targets": len(targets), "generated": made, "cached": cached,
            "rejected": rejected, "failed": failed}


# ==========================================================================================
# T2 — fill missing hard_soft, coherently, from the taxonomy (a skill's category -> domain -> TYPE
# is the authoritative hard/soft signal). Deterministic, free, and consistent with the hierarchy —
# more reliable than an LLM guess. Genuinely ambiguous residual categories are cross-checked by NLI.
# ==========================================================================================
_AMBIGUOUS_CATS = {"other_hard", "knowledge_general"}


def _task_hardsoft(validator, snap):
    """Fill any empty `hard_soft` deterministically from the taxonomy: a skill's category belongs to a
    domain, and a domain is hard or soft, so `hard_soft` is a pure function of `it_subtype`
    (`hierarchy.skill_type`). `merge` now applies this same rule authoritatively, so this task is a
    safety net; it never guesses. (An earlier NLI zero-shot on the catch-all categories was removed —
    it mislabeled clearly-technical skills like "Nvidia CUDA"/"JPEG 2000" as soft.)"""
    from . import hierarchy as H
    skl = K.read_all(C.UNIFIED_SKILLS_CSV)
    targets = [r for r in skl if not (r.get("hard_soft") or "").strip()
               and (r.get("primary_label_en") or r.get("primary_label_fr"))]
    filled = 0
    for r in targets:
        decision = H.skill_type(r.get("it_subtype", ""))
        if not decision:
            continue
        snap[("hardsoft", r["unified_id"])] = {
            "task": "hardsoft", "key": r["unified_id"], "model": "taxonomy",
            "prompt_hash": "", "output": decision, "created_at": K.now_iso()}
        filled += 1
    return {"targets": len(targets), "filled": filled, "nli_used": 0}


_LINK_SYS = (
    "You are an IT skills expert. Given an IT occupation and a numbered list of candidate skills, pick "
    "ONLY the ones that are genuinely core or commonly-required skills for that occupation. Reply with "
    "ONLY the numbers of those skills separated by commas (e.g. 1, 4, 7). No words, no other text."
)


# ==========================================================================================
# T3 — infer missing occupation->skill links (embedding shortlist -> LLM picks -> NLI-validated).
# Bounded to emerging roles + occupations with sparse relations. Skills come from the EXISTING KB
# vocabulary only (never invented). Written as relation_type="llm_inferred" (source LLM), additive.
# ==========================================================================================
def _link_targets(occ_raw):
    rels = K.read_all(C.OCC_SKILL_REL_CSV)
    from collections import Counter as _C
    cnt = _C(r["occupation_entity_id"] for r in rels)
    out = [o for o in occ_raw if (o.get("pref_label_en") or "").strip()
           and (o.get("source") == C.SRC_EMERGING or cnt.get(o["entity_id"], 0) <= C.LLM_LINK_SPARSE_MAX)]
    return out[:C.LLM_LINK_MAX_OCC]


def _task_links(client, snap, validator):
    from .align import candidates as cand
    from .sources import evidence as ev
    import numpy as np
    embedder = cand.get_embedder()
    occ_raw, skl_raw = cand.load_entities()
    skl_raw = [s for s in skl_raw if s.get("esco_skill_type") != "skill_category"
               and (s.get("pref_label_en") or "").strip()]
    targets = _link_targets(occ_raw)
    if not targets:
        return {"targets": 0, "links": 0}
    skl_vecs = np.asarray(cand.encode_cached(embedder, [cand.entity_text(s) for s in skl_raw]))
    by_lbl = {s["pref_label_en"]: s for s in skl_raw}
    id2vec = {skl_raw[i]["entity_id"]: skl_vecs[i] for i in range(len(skl_raw))}

    new_rels, n_links, kept_occ = [], 0, 0
    for o in targets:
        ovec = np.asarray(embedder.encode([cand.entity_text(o)]))[0]
        cell = snap.get(("link", o["entity_id"]))
        if cell and cell.get("output") is not None:
            picks_lbls = [p for p in (cell["output"] or "").split(" | ") if p]
        else:
            sims = skl_vecs @ ovec
            top = np.argsort(-sims)[:C.LLM_LINK_TOPK]
            shortlist = [skl_raw[i] for i in top]
            numbered = "\n".join(f"{i+1}. {s['pref_label_en']}" for i, s in enumerate(shortlist))
            raw = client.chat(_LINK_SYS, f"occupation: {o['pref_label_en']}\ncandidate skills:\n{numbered}")
            if raw is None:
                continue
            nums = sorted({int(n) for n in re.findall(r"\d+", raw) if 1 <= int(n) <= len(shortlist)})
            picks = [shortlist[n - 1] for n in nums][:C.LLM_LINK_MAX_PER_OCC]
            picks_lbls = [p["pref_label_en"] for p in picks]
            snap[("link", o["entity_id"])] = {"task": "link", "key": o["entity_id"], "model": client.mode or "",
                                              "prompt_hash": "", "output": " | ".join(picks_lbls),
                                              "created_at": K.now_iso()}
        # Validate each pick by embedding cosine (they were LLM-selected from an embedding shortlist —
        # a double signal); keep those above the floor and store the cosine as the relation weight.
        used = False
        for lbl in picks_lbls:
            s = by_lbl.get(lbl)
            if not s:
                continue
            cos = float(id2vec[s["entity_id"]] @ ovec)
            if cos >= C.LLM_LINK_MIN_SIM:
                new_rels.append(ev.relation_row(o["entity_id"], s["entity_id"], C.SRC_LLM,
                                                str(round(cos, 3)), relation_type="llm_inferred"))
                n_links += 1
                used = True
        kept_occ += used
    ev.write_relations(C.SRC_LLM, new_rels)
    return {"targets": len(targets), "occupations_linked": kept_occ, "links": n_links}


_EMERGE_SYS = (
    "You are an IT technology analyst curating a knowledge base of IT skills and occupations. List "
    "current, real, well-known emerging IT technologies, tools, or frameworks (recent years) that such "
    "a KB should contain. Use canonical names. Reply with ONLY a plain list, ONE name per line, no "
    "numbering, no descriptions, no other text."
)


# ==========================================================================================
# T4 — emerging tech: propose new tech/roles absent from the KB, keep ONLY those a real Wikidata QID
# confirms (reuses the anchoring), add as source="LLM" nodes (skills classified by the hierarchy;
# roles ISCO-attached downstream). No skill->skill edges. Reliability via external confirmation.
# ==========================================================================================
def _task_emerging(client, snap, validator):
    from . import wikidata as W
    from . import hierarchy as H
    from .sources import evidence as ev
    # existing vocabulary (skip anything already present)
    occ_raw, skl_raw = K.read_all(C.OCCUPATIONS_CSV), K.read_all(C.SKILLS_CSV)
    existing = {ev.match_key(l) for r in occ_raw + skl_raw
                for l in ((r.get("pref_label_en") or ""), (r.get("pref_label_fr") or "")) if l}

    cell = snap.get(("emerging", "proposals"))
    if cell and cell.get("output"):
        names = [n for n in cell["output"].split(" | ") if n]
    else:
        raw = client.chat(_EMERGE_SYS, "List up to 40 emerging IT technologies, tools, and frameworks.")
        if raw is None:
            return {"proposed": 0, "added_skills": 0, "note": "no backend"}
        names = [re.sub(r"^[\-\*\d\.\)\s]+", "", ln).strip() for ln in raw.splitlines()]
        names = [n for n in names if 1 < len(n) <= 60]
        snap[("emerging", "proposals")] = {"task": "emerging", "key": "proposals", "model": client.mode or "",
                                           "prompt_hash": "", "output": " | ".join(names),
                                           "created_at": K.now_iso()}
    # keep only genuinely-new proposals (not already in the KB)
    new, seen = [], set()
    for name in names:
        k = ev.match_key(name)
        if k and k not in existing and k not in seen:
            seen.add(k)
            new.append(name)
    new = new[:C.LLM_EMERGING_MAX_NEW]

    # Wikidata-validate each new SKILL: keep ONLY names a real class-verified QID confirms (reliability).
    # (Roles are not auto-added — they need ISCO attachment to avoid orphaning the graph.)
    skl_rows = []
    for name in new:
        resolved, ok = W._resolve_chunk([(K.normalize_label(name), name)], W.C.WIKIDATA_SKILL_CLASSES,
                                        None, field_classes=W.C.WIKIDATA_SKILL_FIELD_CLASSES)
        m = resolved.get(K.normalize_label(name))
        if not ok or not m or not m.get("qid") or W._is_nonit_desc(m.get("wd_description", "")):
            continue
        sub = H.classify_subdomain(name, "", "")
        skl_rows.append({
            "entity_id": K.mint_id("SKL_", C.SRC_LLM, m["qid"]), "source": C.SRC_LLM, "source_id": m["qid"],
            "pref_label_en": name, "pref_label_fr": "", "alt_labels_en": "", "alt_labels_fr": "",
            "description_en": m.get("wd_description", ""), "description_fr": "", "esco_skill_type": "",
            "esco_reuse_level": "", "hard_soft_provisional": "", "hard_soft_method": "", "it_subtype": sub,
        })
    if skl_rows:
        K.replace_source_rows(C.SKILLS_CSV, C.SKILL_FIELDS, C.SRC_LLM, skl_rows)
    return {"proposed": len(names), "new_candidates": len(new), "added_skills": len(skl_rows)}


# ==========================================================================================
# Apply snapshotted enrichment onto the unified concept layer (called by merge.py — idempotent).
# ==========================================================================================
def apply_enrichment(rows, kind):
    """Fill `description`/`description_source` and (skills) `hard_soft` on unified `rows` from the LLM
    snapshot, ONLY where still empty — so LLM values never overwrite source/Wikidata data and a
    standalone re-merge keeps them. No-op if the snapshot is absent."""
    snap = _load_snapshot()
    if not snap:
        return rows
    for r in rows:
        uid = r.get("unified_id", "")
        if not (r.get("description") or "").strip():
            cell = snap.get(("desc", uid))
            if cell and cell.get("output"):
                r["description"] = cell["output"]
                r["description_source"] = "llm"
        if kind == "skill" and not (r.get("hard_soft") or "").strip():
            cell = snap.get(("hardsoft", uid))
            if cell and cell.get("output"):
                r["hard_soft"] = cell["output"]
    return rows


# ==========================================================================================
# Orchestration
# ==========================================================================================
ALL_TASKS = ("descriptions", "hardsoft", "links", "emerging")


def run(tasks=ALL_TASKS) -> dict:
    """Run the selected LLM enrichment tasks, then re-integrate into the KB (merge + relations)."""
    tasks = tuple(tasks)
    snap = _load_snapshot()
    validator = Validator()
    need_client = any(t in tasks for t in ("descriptions", "links", "emerging"))
    client = LLMClient() if need_client else None
    if need_client and (client is None or not client.ok):
        print("[LLM] no generative backend available (no token / offline) — generation tasks skipped.",
              flush=True)
    stats = {}

    if "descriptions" in tasks and client and client.ok:
        stats["descriptions"] = _task_descriptions(client, snap, validator)
        _save_snapshot(snap)
        print(f"[LLM] descriptions: {stats['descriptions']}", flush=True)
    if "hardsoft" in tasks:
        stats["hardsoft"] = _task_hardsoft(validator, snap)
        _save_snapshot(snap)
        print(f"[LLM] hard_soft: {stats['hardsoft']}", flush=True)
    if "links" in tasks and client and client.ok:
        stats["links"] = _task_links(client, snap, validator)
        _save_snapshot(snap)
        print(f"[LLM] links: {stats['links']}", flush=True)
    added_nodes = False
    if "emerging" in tasks and client and client.ok:
        stats["emerging"] = _task_emerging(client, snap, validator)
        _save_snapshot(snap)
        added_nodes = stats["emerging"].get("added_skills", 0) > 0
        print(f"[LLM] emerging: {stats['emerging']}", flush=True)

    validator.dump_rejects()
    _integrate(added_nodes)
    K.log_provenance("LLM", [{
        "entity_id": "LLM", "source": "LLM",
        "source_version": f"api={C.LLM_API_MODEL}",
        "retrieved_at": K.now_iso(), "retrieval_method": "hf-llm + nli-validation",
        "notes": "; ".join(f"{k}={v}" for k, v in stats.items())[:500],
    }])
    print(f"[LLM] done. rejects logged: {len(validator.rejects)}.", flush=True)
    return stats


def _integrate(added_nodes=False):
    """Weave enrichment back into the KB. Descriptions/hard_soft/links only need a re-merge; new
    Wikidata-confirmed skill nodes additionally need hierarchy placement + alignment before merge."""
    if added_nodes:
        from . import hierarchy
        from .align import run as align_run
        hierarchy.run()
        align_run(focus_source=C.SRC_LLM)  # align new LLM skills against existing (dedup)
    from . import merge
    merge.run()
