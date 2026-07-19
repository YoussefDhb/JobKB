"""Ingest NOC 2021 (bilingual EN + FR), IT unit groups (5-digit).

NOC contributes bilingual occupation labels plus illustrative-example synonyms,
which strengthen cross-source occupation alignment. NOC "Main duties" are
sentence-level and are folded into the description rather than minted as skills.
NOC occupations carry no ISCO code and are grafted onto the hub during alignment.
"""

from __future__ import annotations
import os

from .. import config as C
from .. import common as K

STRUCT_EN = os.path.join(C.NOC_EN_DIR, "noc_2021_version_1.0_-_classification_structure.csv")
ELEM_EN = os.path.join(C.NOC_EN_DIR, "noc_2021_version_1.0_-_elements.csv")
STRUCT_FR = os.path.join(C.NOC_FR_DIR, "cnp_2021_version_1.0_-_structure_de_la_classification.csv")
ELEM_FR = os.path.join(C.NOC_FR_DIR, "cnp_2021_version_1.0_-_elements.csv")

CODE_EN = "Code - NOC 2021 V1.0"
CODE_FR = "Code dela CNP 2021 v1.0"
EXAMPLE_TYPES = {"Illustrative example(s)", "All examples"}
EXAMPLE_TYPES_FR = {"Exemple(s) illustratif(s)", "Tous les exemples"}


def _elements_en():
    """code -> {'examples': [...], 'duties': [...]}"""
    out = {}
    if not os.path.isfile(ELEM_EN):
        return out
    df = K.read_csv_smart(ELEM_EN)
    for _, r in df.iterrows():
        code = (r.get(CODE_EN) or "").strip()
        if not code:
            continue
        etype = (r.get("Element Type Label English") or "").strip()
        text = (r.get("Element Description English") or "").strip()
        if not text:
            continue
        bucket = out.setdefault(code, {"examples": [], "duties": []})
        if etype in EXAMPLE_TYPES:
            bucket["examples"].append(text)
        elif etype == "Main duties":
            bucket["duties"].append(text)
    return out


def _fr_structure():
    """code -> (title_fr, definition_fr)"""
    out = {}
    if not os.path.isfile(STRUCT_FR):
        return out
    df = K.read_csv_smart(STRUCT_FR)
    for _, r in df.iterrows():
        code = (r.get(CODE_FR) or "").strip()
        if code:
            out[code] = (r.get("Titres de classes", "").strip(),
                         r.get("Définitions de la classe", "").strip())
    return out


def _fr_examples():
    """code -> [example_fr, ...]"""
    out = {}
    if not os.path.isfile(ELEM_FR):
        return out
    df = K.read_csv_smart(ELEM_FR)
    for _, r in df.iterrows():
        code = (r.get(CODE_FR) or "").strip()
        etype = (r.get("Nom du type d'élément Français") or "").strip()
        text = (r.get("Description d'élément Français") or "").strip()
        if code and text and etype in EXAMPLE_TYPES_FR:
            out.setdefault(code, []).append(text)
    return out


def run():
    struct = K.read_csv_smart(STRUCT_EN)
    elems = _elements_en()
    fr_struct = _fr_structure()
    fr_examples = _fr_examples()

    occ_rows, label_rows = [], []
    for _, r in struct.iterrows():
        if (r.get("Level") or "").strip() != "5":
            continue
        code = (r.get(CODE_EN) or "").strip()
        if not C.is_noc_it(code):
            continue
        eid = K.mint_id("OCC_", C.SRC_NOC, code)
        pref_en = (r.get("Class title") or "").strip()
        def_en = (r.get("Class definition") or "").strip()
        bucket = elems.get(code, {"examples": [], "duties": []})
        examples_en = [e.strip() for e in bucket["examples"]]
        duties = " ".join(bucket["duties"]).strip()
        desc_en = (def_en + (" Main duties: " + duties if duties else "")).strip()
        pref_fr, def_fr = fr_struct.get(code, ("", ""))
        examples_fr = [e.strip() for e in fr_examples.get(code, [])]

        occ_rows.append({
            "entity_id": eid, "source": C.SRC_NOC, "source_id": code,
            "isco_code": "", "source_code": code,
            "pref_label_en": pref_en, "pref_label_fr": pref_fr,
            "alt_labels_en": " | ".join(examples_en),
            "alt_labels_fr": " | ".join(examples_fr),
            "description_en": desc_en, "description_fr": def_fr,
            "occupation_type": "noc_occupation",
            "label_language_status": "en_plus_fr" if pref_fr else "en_native",
        })
        label_rows.extend(K.make_label_rows(
            eid, "occupation", C.SRC_NOC,
            preferred={"en": [pref_en], "fr": [pref_fr] if pref_fr else []},
            alts={"en": examples_en, "fr": examples_fr}))

    K.replace_source_rows(C.OCCUPATIONS_CSV, C.OCCUPATION_FIELDS, C.SRC_NOC, occ_rows)
    K.upsert_labels(label_rows)
    K.log_provenance(C.SRC_NOC, [{
        "entity_id": C.SRC_NOC, "source": C.SRC_NOC, "source_version": "NOC 2021 v1.0",
        "retrieved_at": K.now_iso(), "retrieval_method": "official_en_fr_csv",
        "notes": f"{len(occ_rows)} IT unit-group occupations (bilingual)",
    }])
    print(f"[NOC] {len(occ_rows)} IT occupations (bilingual EN/FR).")
