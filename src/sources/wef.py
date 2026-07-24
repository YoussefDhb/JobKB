"""WEF Global Skills Taxonomy (2021) + Education 4.0. Two uses: (1) a structured soft-skill vocabulary —
in-scope soft/cognitive leaves are ingested as soft skills, each self-classified into one of five
WEF-aligned soft sub-domains (giving the soft branch real structure); (2) transversal attach — the core
universal skills link to every IT occupation as relation_type="transversal" (distinct from demand).
Skills-only; screen_relevance=False (bypasses the IT gate, like SOFTSKILLS).
"""

from __future__ import annotations

import csv
import os

from .. import config as C
from .. import common as K
from .base import StructuredSource
from . import evidence

# WEF Skill-Group (normalized) → one of the five soft sub-domains (see hierarchy.SUBDOMAINS).
# Only groups listed here are in scope; every other leaf (physical, technology, management, business,
# marketing, languages, ethics/civic/environmental, abilities) is dropped.
_WEF_GROUP_SUBDOMAIN = {
    # cognitive: creativity & problem-solving
    "creativity and problem solving": "soft_cognitive",
    "problem-solving": "soft_cognitive",
    "problem solving": "soft_cognitive",
    "cognitive (analytical)": "soft_cognitive",
    # self-management, resilience & dependability
    "motivation and self-awareness": "soft_self_management",
    "self-awareness": "soft_self_management",
    "initiative": "soft_self_management",
    "dependability and attention to detail": "soft_self_management",
    "attention to detail, trustworthiness": "soft_self_management",
    "resilience, flexibility and agility": "soft_self_management",
    "resilience, stress tolerance and flexibility": "soft_self_management",
    "self-regulatory (intra-personal)": "soft_self_management",
    # curiosity & lifelong learning
    "curiosity and lifelong learning": "soft_learning",
    "active learning and learning strategies": "soft_learning",
    # communication & collaboration
    "empathy and active listening": "soft_collaboration",
    "active listening, communication and information exchange": "soft_collaboration",
    "service orientation": "soft_collaboration",
    "social (inter-personal)": "soft_collaboration",
    # leadership & social influence
    "teaching, mentoring and coaching": "soft_leadership",
    "leadership and social influence": "soft_leadership",
}

# Extra alt labels for well-known concepts (surface forms + the ESCO verb-phrase equivalents), keyed
# by the leaf's match_key — boosts cross-source matching and same-label merges (SOFTSKILLS/ESCO).
_SYNONYMS = {
    "creative thinking": ["creativity", "think creatively", "express yourself creatively"],
    "creativity": ["creative thinking", "think creatively"],
    "analytical thinking": ["think analytically", "analytical skills", "analysis"],
    "critical thinking": ["think critically"],
    "systems thinking": ["systems analysis", "systems-level thinking"],
    "problem solving": ["solve problems", "identify problems", "problem-solving"],
    "communication": ["communicate", "address an audience", "communication skills"],
    "collaboration": ["teamwork", "team player", "work in teams", "build team spirit"],
    "adaptation to change": ["adaptability", "adapt to change", "adaptable", "flexibility"],
    "stress management": ["cope with stress", "manage stress", "work under pressure"],
    "frustration management": ["manage frustration"],
    "time management and prioritisation": ["time management", "manage time", "prioritisation",
                                           "prioritization", "meet deadlines"],
    "assuming responsibility": ["assume responsibility", "take responsibility", "responsibility",
                                "accountability"],
    "meeting commitments and deadlines": ["meet commitments", "meet deadlines"],
    "attention to detail": ["attend to detail", "detail-oriented", "meticulous"],
    "willingness to learn": ["demonstrate willingness to learn", "eager to learn",
                             "continuous learning", "lifelong learning"],
    "curiosity": ["demonstrate curiosity", "inquisitiveness"],
    "empathy": ["show empathy", "empathy & kindness", "socio-emotional awareness"],
    "initiative": ["show initiative", "take initiative", "proactivity", "self-starter"],
    "working independently": ["work independently", "autonomy"],
    "self-control": ["exercise self-control", "composure"],
    "persistence": ["show determination", "perseverance", "grit"],
    "ethical leadership": ["lead others", "leadership", "ethical leader"],
    "persuasion and negotiation": ["negotiation", "persuasion", "persuade", "negotiate"],
    "building trust": ["build trust", "trustworthiness"],
    "giving and receiving feedback": ["receiving feedback", "give feedback", "feedback"],
    "teaching": ["instruct others", "teaching and training", "train others"],
    "mentoring": ["mentor others", "mentorship"],
    "coaching": ["coach others"],
    "liaising, networking and exchanging information": ["liaising and networking", "networking",
                                                        "build networks"],
    "assisting and supporting co-workers": ["support co-workers", "assist colleagues"],
    "following instructions and procedures": ["follow instructions", "follow procedures"],
    "growth mindset": ["learning mindset"],
    "conscientiousness": ["conscientious", "diligence"],
}

# Leaves (by match_key) treated as universal → attached to every real IT occupation as `transversal`.
CORE_TRANSVERSAL = {
    "creative thinking", "analytical thinking", "critical thinking", "systems thinking",
    "problem solving", "communication", "collaboration", "adaptation to change",
    "stress management", "willingness to learn", "curiosity", "initiative",
    "attention to detail", "time management and prioritisation", "assuming responsibility",
    "empathy", "giving and receiving feedback",
}

_FILES = (C.WEF_GLOBAL_CSV, C.WEF_COMPETENCIES_CSV, C.WEF_EDUCATION_CSV)

# Substrings flagging a tech/hard leaf filed under an in-scope cognitive group (drop it as redundant).
_SKIP_SUBSTR = ("programming", "digital skill")


def _canon_key(mk):
    """Fold British/American spelling (-ise/-ize, -yse/-yze) so cross-file variants de-dupe to one node
    (e.g. 'prioritisation' == 'prioritization', 'analyse' == 'analyze')."""
    import re
    mk = re.sub(r"iz(e|es|ation|ing|ed)\b", lambda m: "is" + m.group(1), mk)
    return mk.replace("yze", "yse").replace("yzes", "yses")


def _load_wef_skills():
    """Union of in-scope soft/cognitive leaves across the 3 WEF files, de-duped by canonical match_key.
    Returns list of dicts: {source_id, label, alts, desc, it_subtype, core}."""
    by_key = {}
    order = []
    for path in _FILES:
        if not os.path.isfile(path):
            continue
        with open(path, encoding="utf-8-sig", errors="replace", newline="") as fh:
            for r in csv.DictReader(fh):
                skill = (r.get("Skill") or "").strip()
                if not skill:
                    continue
                cat = (r.get("Category") or "").strip()
                sub = (r.get("Sub-Category") or "").strip()
                # Education4.0 has no "Skill Group" column → its Sub-Category is the group.
                group = (r.get("Skill Group") or "").strip() or sub
                subdomain = _WEF_GROUP_SUBDOMAIN.get(K.normalize_label(group))
                if not subdomain:
                    continue  # out-of-scope branch
                mk = evidence.match_key(skill)
                if not mk or any(sub in mk for sub in _SKIP_SUBSTR):
                    continue
                ckey = _canon_key(mk)
                if ckey not in by_key:
                    by_key[ckey] = {
                        "source_id": K.normalize_label(skill).replace(" ", "_")[:60] or ckey.replace(" ", "_"),
                        "label": skill,
                        "alts": set(_SYNONYMS.get(mk, [])),
                        "desc": f"{cat} → {sub} → {group} (WEF Global Skills Taxonomy).",
                        "it_subtype": subdomain,
                        "core": mk in CORE_TRANSVERSAL or ckey in CORE_TRANSVERSAL,
                    }
                    order.append(ckey)
                else:
                    # a cross-file variant spelling → keep as an alt label
                    if K.normalize_label(skill) != K.normalize_label(by_key[ckey]["label"]):
                        by_key[ckey]["alts"].add(skill)
    out = []
    for mk in order:
        rec = by_key[mk]
        rec["alts"] = sorted(a for a in rec["alts"] if K.normalize_label(a) != K.normalize_label(rec["label"]))
        out.append(rec)
    return out


WEF_SKILLS = _load_wef_skills()


class WefSource(StructuredSource):
    name = C.SRC_WEF
    contributes_occupations = False
    needs_attach = False
    builtin = True
    screen_relevance = False   # curated & authoritative; transversal terms bypass the IT gate
    version = "WEF-global-skills-taxonomy-2021"
    retrieval_method = "wef_taxonomy_curation"

    def skills(self):
        for s in WEF_SKILLS:
            yield {
                "source_id": s["source_id"],
                "label_en": s["label"],
                "alt_en": s["alts"],
                "desc_en": s["desc"],
                "hard_soft": "soft",
                "method": "wef_soft_skill",
                "it_subtype": s["it_subtype"],
            }

    def ingest(self) -> None:
        super().ingest()   # writes the soft-skill nodes/labels (gate-bypassed), empty relations

        # Broad transversal attach: the universal WEF soft skills → every real IT occupation.
        core_ids = [K.mint_id("SKL_", self.name, s["source_id"]) for s in WEF_SKILLS if s["core"]]
        occ_ids = [r["entity_id"] for r in K.read_all(C.OCCUPATIONS_CSV)
                   if r.get("occupation_type") != "isco_group"]
        rel_rows = [evidence.relation_row(o, sid, self.name, weight="", relation_type="transversal")
                    for o in occ_ids for sid in core_ids]
        evidence.write_relations(self.name, rel_rows)

        K.log_provenance(self.name, [{
            "entity_id": self.name, "source": self.name, "source_version": self.version,
            "retrieved_at": K.now_iso(), "retrieval_method": self.retrieval_method,
            "notes": f"{len(WEF_SKILLS)} soft skills; {len(rel_rows)} transversal relations "
                     f"({len(core_ids)} core skills × {len(occ_ids)} occupations)",
        }])
        print(f"[{self.name}] {len(rel_rows)} transversal relations "
              f"({len(core_ids)} core soft skills × {len(occ_ids)} IT occupations).")
