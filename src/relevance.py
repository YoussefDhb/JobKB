"""Relevance / noise gate: screens every pluggable StructuredSource at ingest, before rows are written.
Two checks: (1) structural noise (2) IT-relevance via a contrastive bge-m3 test
"""

from __future__ import annotations

import re

from . import config as C
from . import common as K
from .align import candidates as cand
from .align import verify as _verify

_IT_HYP = "This is a concept in information technology, computing, software or data."

# Space-before-comma is the CSO math-list junk signal ("(min ,max ,+)"); a comma normally has
# no leading space in real labels. Deliberately NOT flagging "+" / "." / "#" — they are common in
# genuine tech skills (C++, .NET, C#, X++, NIS+).
_JUNK = re.compile(r" ,")

_ANCHOR_CACHE = {}          # kind -> (it_matrix, nonit_matrix)


def is_structural_noise(label: str) -> bool:
    """True if `label` is a structural junk / malformed string (not a real skill/occupation label)."""
    label = (label or "").strip()
    if not label or not re.search(r"[A-Za-z]", label):
        return True
    if label[0] in "([{":
        return True
    return bool(_JUNK.search(label))


# Soft-branch IT-relevance filter (curated). O*NET "Abilities" and ESCO's broad transversal
# collection dragged psychometric / physical / non-IT-life-skill entries into the soft branch
# (Far Vision, Finger Dexterity, Perceptual Speed, "apply hygiene standards", "maintain physical
# fitness", "foster biodiversity", "participate in civic life", …). These are not IT-workplace soft
# skills. `is_non_it_soft()` (EXACT normalized-label match — substrings are unsafe: they would hit
# real IT skills like "integrated development environment", "Cyber Hygiene", "Physical Layers",
# "healthcare data systems") is applied at the ONET/ESCO ingests to keep them out. Kept deliberately:
# the cognitive/verbal O*NET reasoning abilities (Deductive/Inductive/Mathematical Reasoning, Oral/
# Written Comprehension/Expression) and every IT-relevant ESCO transversal skill (accept criticism,
# cope with uncertainty, respect confidentiality, manage digital identity, think critically, …).
_NON_IT_SOFT_RAW = [
    # O*NET physical / sensory / psychomotor abilities (never IT soft skills)
    "Far Vision", "Near Vision", "Night Vision", "Peripheral Vision", "Depth Perception",
    "Glare Sensitivity", "Visual Color Discrimination", "Speech Clarity",
    # NB: "Speech Recognition" deliberately NOT listed — it is a real hard IT/ML skill (ASR), not the
    # O*NET sensory ability, and must not be pruned.
    "Hearing Sensitivity", "Auditory Attention", "Sound Localization", "Finger Dexterity",
    "Manual Dexterity", "Arm-Hand Steadiness", "Control Precision", "Multilimb Coordination",
    "Response Orientation", "Rate Control", "Reaction Time", "Wrist-Finger Speed",
    "Speed of Limb Movement", "Static Strength", "Explosive Strength", "Dynamic Strength",
    "Trunk Strength", "Stamina", "Extent Flexibility", "Dynamic Flexibility",
    "Gross Body Coordination", "Gross Body Equilibrium",
    # O*NET raw perceptual / attention / aptitude abilities (psychometric traits, not hiring skills)
    "Perceptual Speed", "Speed of Closure", "Flexibility of Closure", "Selective Attention",
    "Time Sharing", "Spatial Orientation", "Number Facility", "Problem Sensitivity",
    "Fluency of Ideas", "Originality", "Category Flexibility", "Memorization",
    # ESCO non-IT transversal "life skills" (health / physical / civic / environmental / cultural)
    "adopt ways to foster biodiversity and animal welfare",
    "adopt ways to reduce pollution",
    "adopt ways to reduce negative impact of consumption",
    "evaluate environmental impact of personal behaviour",
    "engage others in environment friendly behaviours",
    "apply hygiene standards",
    "maintain physical fitness",
    "maintain psychological well-being",
    "demonstrate awareness of health risks",
    "make an informed use of the health-care system",
    "manage chronic health conditions",
    "protect the health of others",
    "adjust to physical demands",
    "react to physical changes or hazards",
    "move objects",
    "manage financial and material resources",
    "participate actively in civic life",
    "promote the principles of democracy and rule of law",
    "appreciate diverse cultural and artistic expression",
    "respect the diversity of cultural values and norms",
    "apply knowledge of philosophy, ethics and religion",
    "apply knowledge of social sciences and humanities",
]
_NON_IT_SOFT = {K.normalize_label(x) for x in _NON_IT_SOFT_RAW}


def is_non_it_soft(label: str) -> bool:
    """True if `label` is a curated non-IT soft-branch entry (physical/psychometric O*NET ability or
    a non-IT ESCO life-skill) that should be pruned from the soft branch. Exact normalized match only."""
    return K.normalize_label(label) in _NON_IT_SOFT


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
