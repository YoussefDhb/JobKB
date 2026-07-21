"""Shared helpers for *relation-only* enrichment sources (ADEM, JOBS).

These sources add occupation->skill edges between entities that ALREADY exist in the KB — no new
occupation/skill nodes. They resolve endpoints against the current `kb/` (by ESCO uuid / ROME code
for ADEM, by normalized label for JOBS) and write weighted `demand` relations. Reads are done at
ingest time, so ESCO/ROME/skill sources must already be ingested (guaranteed by registration order
and by the incremental `--add` running against an existing KB).
"""

from __future__ import annotations

import re

from .. import config as C
from .. import common as K

_TAXO = ("skill_type", "skill_domain")
_PAREN = re.compile(r"\s*\([^)]*\)")


def match_key(label: str) -> str:
    """Normalized + singularized key for cross-source label matching (same idea as verify._key):
    accent/case-fold, drop parentheticals, strip a trailing 's' from each token."""
    norm = K.normalize_label(_PAREN.sub("", label or ""))
    if not norm:
        return ""
    return " ".join(t[:-1] if len(t) > 3 and t.endswith("s") and not t.endswith("ss") else t
                    for t in norm.split())


def _label_index(rows, label_fields):
    idx = {}
    for r in rows:
        for field in label_fields:
            for lbl in (r.get(field) or "").split(" | "):
                k = match_key(lbl)
                if k and k not in idx:
                    idx[k] = r["entity_id"]
    return idx


def occ_index():
    """{match_key(label) -> occupation entity_id} for real occupations (excludes ISCO groups)."""
    occ = [r for r in K.read_all(C.OCCUPATIONS_CSV) if r.get("occupation_type") != "isco_group"]
    return _label_index(occ, ("pref_label_en", "pref_label_fr", "alt_labels_en", "alt_labels_fr"))


def skill_index():
    """{match_key(label) -> skill entity_id} for real skills (excludes taxonomy nodes)."""
    skl = [r for r in K.read_all(C.SKILLS_CSV) if r.get("esco_skill_type") not in _TAXO]
    return _label_index(skl, ("pref_label_en", "pref_label_fr", "alt_labels_en", "alt_labels_fr"))


def esco_skill_by_uuid():
    """{ESCO skill uuid (source_id) -> skill entity_id}."""
    return {r["source_id"]: r["entity_id"]
            for r in K.read_all(C.SKILLS_CSV) if r.get("source") == C.SRC_ESCO}


def rome_occ_by_code():
    """{ROME code (source_code) -> occupation entity_id}."""
    return {r["source_code"]: r["entity_id"]
            for r in K.read_all(C.OCCUPATIONS_CSV)
            if r.get("source") == C.SRC_ROME and r.get("source_code")}


def relation_row(occ_id, skill_id, source, weight, relation_type="demand"):
    return {"occupation_entity_id": occ_id, "skill_entity_id": skill_id,
            "relation_type": relation_type, "source": source, "weight": weight}


def write_relations(source, rows):
    K.replace_source_rows(C.OCC_SKILL_REL_CSV, C.REL_FIELDS, source, rows)
