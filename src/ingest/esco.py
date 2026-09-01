"""Ingest ESCO, IT occupations and their skills."""

from __future__ import annotations
import os

from .. import config as C
from .. import common as K

OCC_EN = os.path.join(C.ESCO_EN_DIR, "occupations_en.csv")
OCC_FR = os.path.join(C.ESCO_FR_DIR, "occupations_fr.csv")
SKILLS_EN = os.path.join(C.ESCO_EN_DIR, "skills_en.csv")
SKILLS_FR = os.path.join(C.ESCO_FR_DIR, "skills_fr.csv")
REL_EN = os.path.join(C.ESCO_EN_DIR, "occupationSkillRelations_en.csv")
DIGITAL = os.path.join(C.ESCO_EN_DIR, "digitalSkillsCollection_en.csv")
DIGCOMP = os.path.join(C.ESCO_EN_DIR, "digCompSkillsCollection_en.csv")


def _collection_rows(path):
    """conceptUri -> row for an ESCO skill collection."""
    out = {}
    if os.path.isfile(path):
        df = K.read_csv_smart(path)
        for _, r in df.iterrows():
            uri = (r.get("conceptUri") or "").strip()
            if uri:
                out[uri] = r
    return out


def _fr_labels(path):
    """conceptUri -> (pref_fr, [alt_fr]) from an optional French ESCO file."""
    out = {}
    if not os.path.isfile(path):
        return out
    df = K.read_csv_smart(path)
    for _, r in df.iterrows():
        uri = (r.get("conceptUri") or "").strip()
        if uri:
            out[uri] = (r.get("preferredLabel", "").strip(),
                        K.split_multi(r.get("altLabels", "")))
    return out


def run():
    occ_df = K.read_csv_smart(OCC_EN)
    skills_df = K.read_csv_smart(SKILLS_EN)
    rel_df = K.read_csv_smart(REL_EN)
    occ_fr = _fr_labels(OCC_FR)
    skl_fr = _fr_labels(SKILLS_FR)

    # In-scope IT occupations.
    in_scope = occ_df[occ_df["iscoGroup"].map(C.is_isco_it)]
    occ_uris = set(in_scope["conceptUri"])

    occ_rows, skill_rows, rel_rows, label_rows, hier_rows = [], [], [], [], []

    # --- Occupations ---
    for _, r in in_scope.iterrows():
        uri = r["conceptUri"].strip()
        sid = K.uri_tail(uri)
        eid = K.mint_id("OCC_", C.SRC_ESCO, sid)
        pref_en = r.get("preferredLabel", "").strip()
        alts_en = K.split_multi(r.get("altLabels", ""))
        hidden_en = K.split_multi(r.get("hiddenLabels", ""))
        desc_en = (r.get("description") or r.get("definition") or "").strip()
        isco = (r.get("iscoGroup") or "").strip()
        pref_fr, alts_fr = occ_fr.get(uri, ("", []))
        occ_rows.append({
            "entity_id": eid, "source": C.SRC_ESCO, "source_id": sid,
            "isco_code": isco, "source_code": "",
            "pref_label_en": pref_en, "pref_label_fr": pref_fr,
            "alt_labels_en": " | ".join(alts_en), "alt_labels_fr": " | ".join(alts_fr),
            "description_en": desc_en, "description_fr": "",
            "occupation_type": "esco_occupation",
            "label_language_status": "en_plus_fr" if pref_fr else "en_native",
        })
        label_rows.extend(K.make_label_rows(
            eid, "occupation", C.SRC_ESCO,
            preferred={"en": [pref_en], "fr": [pref_fr] if pref_fr else []},
            alts={"en": alts_en, "fr": alts_fr}, hidden={"en": hidden_en}))
        # Attach to its ISCO unit group on the hub.
        if C.is_isco_it(isco):
            hier_rows.append({
                "parent_entity_id": K.mint_id("OCC_", C.SRC_ISCO, isco),
                "child_entity_id": eid,
                "entity_kind": "occupation", "relation_type": "broader_than",
                "source": C.SRC_ESCO,
            })

    # --- Relations (occupation -> skill), restricted to in-scope occupations ---
    rel_scope = rel_df[rel_df["occupationUri"].isin(occ_uris)]
    needed_skill_uris = set(rel_scope["skillUri"])

    # Skill set = skills linked to in-scope occupations UNION the full ESCO digital/digital-competence collections
    collection = {**_collection_rows(DIGITAL), **_collection_rows(DIGCOMP)}
    all_skill_uris = needed_skill_uris | set(collection)

    master = {r["conceptUri"].strip(): r for _, r in skills_df.iterrows()}
    skl_index = {}
    for uri in all_skill_uris:
        if uri in master:
            skl_index[uri] = master[uri]
        elif uri in collection:
            skl_index[uri] = collection[uri]  # same field names

    for _, r in rel_scope.iterrows():
        occ_eid = K.mint_id("OCC_", C.SRC_ESCO, K.uri_tail(r["occupationUri"]))
        skl_eid = K.mint_id("SKL_", C.SRC_ESCO, K.uri_tail(r["skillUri"]))
        rel_rows.append({
            "occupation_entity_id": occ_eid, "skill_entity_id": skl_eid,
            "relation_type": (r.get("relationType") or "essential").strip(),
            "source": C.SRC_ESCO,
        })

    # --- Skill nodes (only those linked to in-scope occupations) ---
    for uri, r in skl_index.items():
        sid = K.uri_tail(uri)
        eid = K.mint_id("SKL_", C.SRC_ESCO, sid)
        pref_en = r.get("preferredLabel", "").strip()
        alts_en = K.split_multi(r.get("altLabels", ""))
        hidden_en = K.split_multi(r.get("hiddenLabels", ""))
        desc_en = r.get("description", "").strip()
        skilltype = (r.get("skillType") or "").strip()
        reuse = (r.get("reuseLevel") or "").strip()
        pref_fr, alts_fr = skl_fr.get(uri, ("", []))
        hs = "hard"
        method = "esco_knowledge_pillar" if skilltype == "knowledge" else "esco_skillcompetence_default"
        skill_rows.append({
            "entity_id": eid, "source": C.SRC_ESCO, "source_id": sid,
            "pref_label_en": pref_en, "pref_label_fr": pref_fr,
            "alt_labels_en": " | ".join(alts_en), "alt_labels_fr": " | ".join(alts_fr),
            "description_en": desc_en, "description_fr": "",
            "esco_skill_type": skilltype, "esco_reuse_level": reuse,
            "hard_soft_provisional": hs, "hard_soft_method": method, "it_subtype": "",
        })
        label_rows.extend(K.make_label_rows(
            eid, "skill", C.SRC_ESCO,
            preferred={"en": [pref_en], "fr": [pref_fr] if pref_fr else []},
            alts={"en": alts_en, "fr": alts_fr}, hidden={"en": hidden_en}))

    K.replace_source_rows(C.OCCUPATIONS_CSV, C.OCCUPATION_FIELDS, C.SRC_ESCO, occ_rows)
    K.replace_source_rows(C.SKILLS_CSV, C.SKILL_FIELDS, C.SRC_ESCO, skill_rows)
    K.replace_source_rows(C.OCC_SKILL_REL_CSV, C.REL_FIELDS, C.SRC_ESCO, rel_rows)
    K.replace_source_rows(C.HIERARCHY_CSV, C.HIERARCHY_FIELDS, C.SRC_ESCO, hier_rows)
    K.upsert_labels(label_rows)
    K.log_provenance(C.SRC_ESCO, [{
        "entity_id": C.SRC_ESCO, "source": C.SRC_ESCO, "source_version": "ESCO v1.2 (en)",
        "retrieved_at": K.now_iso(), "retrieval_method": "official_en_csv",
        "notes": f"{len(occ_rows)} occ, {len(skill_rows)} skills, {len(rel_rows)} relations",
    }])
    print(f"[ESCO] {len(occ_rows)} IT occupations, {len(skill_rows)} skills, "
          f"{len(rel_rows)} occ-skill relations.")
