"""Ingest ROME: IT metiers + appellations + competences + definitions."""

from __future__ import annotations
import os

from .. import config as C
from .. import common as K

CODE_ROME = os.path.join(C.ROME_FR_DIR, "unix_referentiel_code_rome_v461_utf8.csv")
APPELLATION = os.path.join(C.ROME_FR_DIR, "unix_referentiel_appellation_v461_utf8.csv")
COMPETENCE = os.path.join(C.ROME_FR_DIR, "unix_referentiel_competence_v461_utf8.csv")
SAVOIR = os.path.join(C.ROME_FR_DIR, "unix_referentiel_savoir_v461_utf8.csv")
LIENS = os.path.join(C.ROME_FR_DIR, "unix_liens_rome_referentiels_v461_utf8.csv")
TEXTE = os.path.join(C.ROME_FR_DIR, "unix_texte_v461_utf8.csv")

# code_rubrique within bloc 5 -> (referential, hard/soft, method)
RUBRIQUE = {
    "1": ("competence", "hard", "rome_savoir_faire"),
    "2": ("competence", "soft", "rome_savoir_etre"),
    "3": ("savoir", "hard", "rome_savoir"),
}


def _definitions():
    """code_rome -> definition text (unix_texte, bloc 3, ordered by position_phrase)."""
    out = {}
    if not os.path.isfile(TEXTE):
        return out
    df = K.read_csv_smart(TEXTE)
    df = df[df["code_compo_bloc"].str.strip() == "3"]
    for code, grp in df.groupby("code_rome"):
        try:
            grp = grp.sort_values("position_phrase", key=lambda s: s.astype(int))
        except Exception:
            pass
        text = " ".join(x.strip() for x in grp["libelle_texte"] if x.strip())
        out[(code or "").strip()] = text.strip()
    return out


def run():
    metiers = K.read_csv_smart(CODE_ROME)
    appels = K.read_csv_smart(APPELLATION)
    comps = K.read_csv_smart(COMPETENCE)
    savoirs = K.read_csv_smart(SAVOIR)
    liens = K.read_csv_smart(LIENS)
    definitions = _definitions()

    # In-scope ROME codes (IT), computed once from the metiers, then reused for appellations / competences.
    in_scope = {(r.get("code_rome") or "").strip()
                for _, r in metiers.iterrows()
                if C.is_rome_it((r.get("code_rome") or "").strip(),
                                r.get("libelle_rome", ""))}

    comp_lbl = {r["code_ogr"].strip(): (r.get("libelle_competence", "").strip(),
                                        r.get("cat_comp", "").strip())
                for _, r in comps.iterrows()}
    savoir_lbl = {r["code_ogr_savoir"].strip(): r.get("libelle_savoir", "").strip()
                  for _, r in savoirs.iterrows()}

    # Appellations grouped by ROME code.
    syn = {}
    for _, r in appels.iterrows():
        code = (r.get("code_rome") or "").strip()
        if code in in_scope:
            lbl = (r.get("libelle_appellation_long") or "").strip()
            if lbl:
                syn.setdefault(code, []).append(lbl)

    occ_rows, skill_rows, rel_rows, label_rows = [], [], [], []
    skills = {}  # norm -> skill row

    # --- Metiers ---
    seen_codes = set()
    for _, r in metiers.iterrows():
        code = (r.get("code_rome") or "").strip()
        if code not in in_scope or code in seen_codes:
            continue
        seen_codes.add(code)
        eid = K.mint_id("OCC_", C.SRC_ROME, code)
        pref_fr = (r.get("libelle_rome") or "").strip()
        alts_fr = []
        seen_syn = set()
        for s in syn.get(code, []):
            n = K.normalize_label(s)
            if n and n not in seen_syn:
                seen_syn.add(n)
                alts_fr.append(s)
        occ_rows.append({
            "entity_id": eid, "source": C.SRC_ROME, "source_id": code,
            "isco_code": "", "source_code": code,
            "pref_label_en": "", "pref_label_fr": pref_fr,
            "alt_labels_en": "", "alt_labels_fr": " | ".join(alts_fr),
            "description_en": "", "description_fr": definitions.get(code, ""),
            "occupation_type": "rome_metier", "label_language_status": "fr_only",
        })
        label_rows.extend(K.make_label_rows(
            eid, "occupation", C.SRC_ROME,
            preferred={"fr": [pref_fr]}, alts={"fr": alts_fr}))

    # --- Competences (bloc 5, routed by rubrique) ---
    bloc5 = liens[(liens["code_compo_bloc"].str.strip() == "5")
                  & (liens["code_rome"].isin(in_scope))]
    for _, r in bloc5.iterrows():
        rub = (r.get("code_rubrique") or "").strip()
        if rub not in RUBRIQUE:
            continue
        ref, hard_soft, method = RUBRIQUE[rub]
        ogr = (r.get("code_ogr") or "").strip()
        if ref == "competence":
            label = comp_lbl.get(ogr, ("", ""))[0]
        else:
            label = savoir_lbl.get(ogr, "")
        label = (label or "").strip()
        if not label:
            continue
        norm = K.normalize_label(label)
        if not norm:
            continue
        sid = f"{method}:{norm}"
        eid = K.mint_id("SKL_", C.SRC_ROME, sid)
        if norm not in skills:
            skills[norm] = {
                "entity_id": eid, "source": C.SRC_ROME, "source_id": sid,
                "pref_label_en": "", "pref_label_fr": label,
                "alt_labels_en": "", "alt_labels_fr": "",
                "description_en": "", "description_fr": "",
                "esco_skill_type": "", "esco_reuse_level": "",
                "hard_soft_provisional": hard_soft, "hard_soft_method": method,
                "it_subtype": "",
            }
            label_rows.extend(K.make_label_rows(eid, "skill", C.SRC_ROME,
                                                preferred={"fr": [label]}))
        rel_rows.append({
            "occupation_entity_id": K.mint_id("OCC_", C.SRC_ROME, r["code_rome"].strip()),
            "skill_entity_id": skills[norm]["entity_id"],
            "relation_type": "essential", "source": C.SRC_ROME,
        })

    skill_rows = list(skills.values())
    K.replace_source_rows(C.OCCUPATIONS_CSV, C.OCCUPATION_FIELDS, C.SRC_ROME, occ_rows)
    K.replace_source_rows(C.SKILLS_CSV, C.SKILL_FIELDS, C.SRC_ROME, skill_rows)
    K.replace_source_rows(C.OCC_SKILL_REL_CSV, C.REL_FIELDS, C.SRC_ROME, rel_rows)
    K.upsert_labels(label_rows)
    K.log_provenance(C.SRC_ROME, [{
        "entity_id": C.SRC_ROME, "source": C.SRC_ROME, "source_version": "ROME v461",
        "retrieved_at": K.now_iso(), "retrieval_method": "official_fr_csv",
        "notes": f"{len(occ_rows)} M18 metiers, {len(skill_rows)} skills, {len(rel_rows)} relations",
    }])
    print(f"[ROME] {len(occ_rows)} M18 metiers, {len(skill_rows)} skills, "
          f"{len(rel_rows)} occ-skill relations.")
