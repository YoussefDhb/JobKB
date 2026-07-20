"""Relevance / noise gate — automatic IT-relevance + noise screening at ingest.

Every pluggable `StructuredSource` (SFIA, CSO, future scraped postings) is screened here
*before* its rows are written, so noise never enters the KB. Two checks per incoming
skill/occupation:

1. **Structural noise** — malformed / fragment / math-notation labels (deterministic).
2. **IT-relevance** — a contrastive embedding test (max cosine to an IT anchor space vs. to a
   non-IT anchor space, using the shared bge-m3 embedder), with the mDeBERTa NLI verifier as a
   backstop. *Lenient / precision-first on blocking*: an item is blocked as non-IT only when the
   embedding says it is far from IT **and** NLI agrees it isn't IT — anything borderline is kept
   and logged. Fail-open: if the models can't load (or TF-IDF fallback), only structural noise is
   blocked (never drop valid data on an infrastructure failure).

Blocked (and near-miss borderline) decisions are logged to `kb/blocked_entities.csv`, keyed by
source (idempotent per re-ingest), so the gate is fully auditable with no human in the loop.

Built-in taxonomies (ESCO/ISCO/ONET/NOC/ROME) bypass this — they are already IT-scoped by
authoritative code filters and do not go through `StructuredSource.ingest`.
"""

from __future__ import annotations

import re

from . import config as C
from . import common as K
from .align import candidates as cand
from .align import verify as _verify

_IT_HYP = "This is a concept in information technology, computing, software or data."

# math/list notation or non-alphanumeric start => malformed CSO-style slug
_JUNK = re.compile(r"[+=]| ,")

_ANCHOR_CACHE = {}          # kind -> (it_matrix, nonit_matrix)


def is_structural_noise(label: str) -> bool:
    """Deterministic junk detector (shared with source-specific cleaners)."""
    label = (label or "").strip()
    if not label or not label[:1].isalnum():
        return True
    return bool(_JUNK.search(label))


def _anchors(kind, embedder):
    """(it_matrix, nonit_matrix) of anchor embeddings for a kind, built once per process."""
    if kind in _ANCHOR_CACHE:
        return _ANCHOR_CACHE[kind]
    it_texts = list(C.REL_IT_SEED)
    if kind == "occupation":
        # authoritative IT-occupation anchors: the ISCO IT groups already in the KB
        try:
            groups = [r for r in K.read_all(C.OCCUPATIONS_CSV)
                      if r.get("occupation_type") == "isco_group"]
            it_texts += [cand.entity_text(g) for g in groups]
        except Exception:
            pass
    it_emb = cand.encode_cached(embedder, it_texts)
    non_emb = cand.encode_cached(embedder, list(C.REL_NONIT_ANCHORS))
    _ANCHOR_CACHE[kind] = (it_emb, non_emb)
    return _ANCHOR_CACHE[kind]


def _screen(rows, kind, embedder, verifier):
    """Return (kept_rows, blocked_entity_ids, log_rows, stats)."""
    stats = {"kept": 0, "malformed": 0, "non_it": 0, "borderline": 0}
    if not rows:
        return rows, set(), [], stats

    labels = [r.get("pref_label_en") or r.get("pref_label_fr") or "" for r in rows]

    # Semantic scoring only in sentence-transformer mode (TF-IDF vectors aren't comparable
    # across separately-fitted calls); otherwise structural-only + keep (fail-open).
    sim_it = sim_non = None
    if embedder.mode == "st":
        import numpy as np
        from sklearn.metrics.pairwise import cosine_similarity
        it_emb, non_emb = _anchors(kind, embedder)
        emb = cand.encode_cached(embedder, [cand.entity_text(r) for r in rows])
        sim_it = cosine_similarity(emb, it_emb).max(axis=1)
        sim_non = cosine_similarity(emb, non_emb).max(axis=1)
        np  # (kept for clarity; numpy used via sklearn output)

    # Pass 1: structural + gather NLI candidates (items clearly closer to a non-IT domain).
    verdict = [None] * len(rows)     # "keep" | "block:malformed" | "nli"
    for i, r in enumerate(rows):
        if is_structural_noise(labels[i]):
            verdict[i] = "block:malformed"
        elif sim_it is None:
            verdict[i] = "keep"                       # fail-open (no embeddings)
        elif sim_non[i] >= C.REL_NONIT_HI and (sim_non[i] - sim_it[i]) >= C.REL_NONIT_MARGIN:
            verdict[i] = "nli"                        # candidate non-IT -> confirm with NLI
        else:
            verdict[i] = "keep"

    # Pass 2: one batched NLI inference for the candidates.
    cand_idx = [i for i, v in enumerate(verdict) if v == "nli"]
    nli_scores = {}
    if cand_idx and verifier.nli_ok:
        texts = [(cand.entity_text(rows[i]), _IT_HYP) for i in cand_idx]
        for i, s in zip(cand_idx, verifier.entail_batch(texts)):
            nli_scores[i] = s

    # Pass 3: finalize.
    kept, blocked_ids, log = [], set(), []

    def _log(r, i, decision, reason):
        log.append({
            "entity_kind": kind, "source": r["source"], "source_id": r.get("source_id", ""),
            "label": labels[i], "decision": decision, "reason": reason,
            "sim_it": "" if sim_it is None else round(float(sim_it[i]), 3),
            "sim_non": "" if sim_non is None else round(float(sim_non[i]), 3),
            "nli": "" if nli_scores.get(i) is None else round(float(nli_scores[i]), 3),
        })

    for i, r in enumerate(rows):
        v = verdict[i]
        if v == "block:malformed":
            blocked_ids.add(r["entity_id"]); stats["malformed"] += 1
            _log(r, i, "block", "malformed"); continue
        if v == "nli":
            s = nli_scores.get(i)
            if s is not None and s < C.REL_NLI_MIN:      # confidently not IT -> block
                blocked_ids.add(r["entity_id"]); stats["non_it"] += 1
                _log(r, i, "block", "non_it"); continue
            stats["borderline"] += 1                      # kept, but a near-miss -> log it
            _log(r, i, "keep", "borderline")
        kept.append(r); stats["kept"] += 1
    return kept, blocked_ids, log, stats


def filter_rows(occ_rows, skill_rows, source):
    """Screen a source's freshly-built rows. Returns (kept_occ, kept_skl, blocked_ids, stats).
    Fail-open on any model/infra error (structural noise still blocked)."""
    if not C.RELEVANCE_GATE_ENABLED:
        return occ_rows, skill_rows, set(), None
    try:
        embedder = cand.get_embedder()
        verifier = _verify.Verifier()
    except Exception:
        # embeddings unavailable -> structural-only screen, no semantic blocking
        embedder = verifier = None

    if embedder is None:
        kept_occ = [r for r in occ_rows if not is_structural_noise(r.get("pref_label_en") or r.get("pref_label_fr") or "")]
        kept_skl = [r for r in skill_rows if not is_structural_noise(r.get("pref_label_en") or r.get("pref_label_fr") or "")]
        blocked = ({r["entity_id"] for r in occ_rows} - {r["entity_id"] for r in kept_occ}) | \
                  ({r["entity_id"] for r in skill_rows} - {r["entity_id"] for r in kept_skl})
        K.replace_source_rows(C.BLOCKED_ENTITIES_CSV, C.BLOCKED_FIELDS, source, [])
        return kept_occ, kept_skl, blocked, {"kept": len(kept_occ) + len(kept_skl),
                                             "malformed": len(blocked), "non_it": 0, "borderline": 0}

    kept_occ, blk_o, log_o, st_o = _screen(occ_rows, "occupation", embedder, verifier)
    kept_skl, blk_s, log_s, st_s = _screen(skill_rows, "skill", embedder, verifier)
    K.replace_source_rows(C.BLOCKED_ENTITIES_CSV, C.BLOCKED_FIELDS, source, log_o + log_s)
    stats = {k: st_o[k] + st_s[k] for k in st_o}
    return kept_occ, kept_skl, blk_o | blk_s, stats
