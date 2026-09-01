"""Ingest ONET, IT occupations."""

from __future__ import annotations
import os

from .. import config as C
from .. import common as K
from .. import relevance as R

OCC = os.path.join(C.ONET_EN_DIR, "occupation_data.csv")
ESS_SKILLS = os.path.join(C.ONET_EN_DIR, "essential_skills.csv")
KNOWLEDGE = os.path.join(C.ONET_EN_DIR, "knowledge.csv")
ABILITIES = os.path.join(C.ONET_EN_DIR, "abilities.csv")
SOFTWARE = os.path.join(C.ONET_EN_DIR, "software_skills.csv")
CONTENT_MODEL = os.path.join(C.ONET_EN_DIR, "content_model_reference.csv")

IMPORTANCE_MIN = 3.0 


def _content_descriptions():
    out = {}
    if os.path.isfile(CONTENT_MODEL):
        df = K.read_csv_smart(CONTENT_MODEL)
        for _, r in df.iterrows():
            out[(r.get("Element ID") or "").strip()] = (r.get("Description") or "").strip()
    return out


def _soc_stem(onet_soc: str) -> str:
    return (onet_soc or "").strip()[:7]


def _to_float(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def run():
    occ_df = K.read_csv_smart(OCC)
    it_occ = occ_df[occ_df["O*NET-SOC Code"].map(C.is_onet_it)]
    it_codes = set(it_occ["O*NET-SOC Code"])
    descriptions = _content_descriptions()

    occ_rows, label_rows = [], []
    for _, r in it_occ.iterrows():
        code = r["O*NET-SOC Code"].strip()
        eid = K.mint_id("OCC_", C.SRC_ONET, code)
        pref = r.get("Title", "").strip()
        desc = r.get("Description", "").strip()
        occ_rows.append({
            "entity_id": eid, "source": C.SRC_ONET, "source_id": code,
            "isco_code": "", "source_code": _soc_stem(code),
            "pref_label_en": pref, "pref_label_fr": "",
            "alt_labels_en": "", "alt_labels_fr": "",
            "description_en": desc, "description_fr": "",
            "occupation_type": "onet_occupation", "label_language_status": "en_native",
        })
        label_rows.extend(K.make_label_rows(eid, "occupation", C.SRC_ONET,
                                            preferred={"en": [pref]}))

    # Skills: dedup within ONET on normalized label; keep first description seen.
    skills = {}   
    rel_rows = []

    def add_skill(occ_code, name, hard_soft, method, subtype="", desc=""):
        name = (name or "").strip()
        if not name or occ_code not in it_codes:
            return
        norm = K.normalize_label(name)
        if not norm:
            return
        # Prune O*NET psychometric / physical / sensory abilities from the soft branch
        if hard_soft == "soft" and R.is_non_it_soft(name):
            return
        sid = f"{method}:{norm}"
        eid = K.mint_id("SKL_", C.SRC_ONET, sid)
        if norm not in skills:
            skills[norm] = {
                "entity_id": eid, "source": C.SRC_ONET, "source_id": sid,
                "pref_label_en": name, "pref_label_fr": "",
                "alt_labels_en": "", "alt_labels_fr": "",
                "description_en": desc, "description_fr": "",
                "esco_skill_type": "", "esco_reuse_level": "",
                "hard_soft_provisional": hard_soft, "hard_soft_method": method,
                "it_subtype": subtype,
            }
            label_rows.extend(K.make_label_rows(eid, "skill", C.SRC_ONET,
                                                preferred={"en": [name]}))
        rel_rows.append({
            "occupation_entity_id": K.mint_id("OCC_", C.SRC_ONET, occ_code),
            "skill_entity_id": skills[norm]["entity_id"],
            "relation_type": "essential", "source": C.SRC_ONET,
        })

    def ingest_rated(path, hard_soft, method):
        if not os.path.isfile(path):
            return
        df = K.read_csv_smart(path)
        for _, r in df.iterrows():
            if (r.get("Scale ID") or "").strip() != "IM":
                continue
            if (val := _to_float(r.get("Data Value"))) is None or val < IMPORTANCE_MIN:
                continue
            desc = descriptions.get((r.get("Element ID") or "").strip(), "")
            add_skill(r.get("O*NET-SOC Code", "").strip(), r.get("Element Name", ""),
                      hard_soft, method, desc=desc)

    ingest_rated(ESS_SKILLS, "hard", "onet_skill")
    ingest_rated(KNOWLEDGE, "hard", "onet_knowledge")
    ingest_rated(ABILITIES, "soft", "onet_ability")

    # Software tools -> concrete technology skills.
    if os.path.isfile(SOFTWARE):
        sw = K.read_csv_smart(SOFTWARE)
        for _, r in sw.iterrows():
            occ_code = r.get("O*NET-SOC Code", "").strip()
            if occ_code not in it_codes:
                continue
            tool = (r.get("Workplace Example") or "").strip()
            add_skill(occ_code, tool, "hard", "onet_software",
                      subtype="langage_ou_techno_nommee")

    skill_rows = list(skills.values())
    K.replace_source_rows(C.OCCUPATIONS_CSV, C.OCCUPATION_FIELDS, C.SRC_ONET, occ_rows)
    K.replace_source_rows(C.SKILLS_CSV, C.SKILL_FIELDS, C.SRC_ONET, skill_rows)
    K.replace_source_rows(C.OCC_SKILL_REL_CSV, C.REL_FIELDS, C.SRC_ONET, rel_rows)
    K.upsert_labels(label_rows)
    K.log_provenance(C.SRC_ONET, [{
        "entity_id": C.SRC_ONET, "source": C.SRC_ONET, "source_version": "O*NET 28.x",
        "retrieved_at": K.now_iso(), "retrieval_method": "official_en_csv",
        "notes": f"{len(occ_rows)} occ, {len(skill_rows)} skills, {len(rel_rows)} relations",
    }])
    print(f"[ONET] {len(occ_rows)} IT occupations, {len(skill_rows)} skills, "
          f"{len(rel_rows)} occ-skill relations.")
