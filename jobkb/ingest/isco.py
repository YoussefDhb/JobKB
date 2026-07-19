"""Ingest the ISCO-08 hub (English), restricted to the IT branches (sub-major 25 & 35).

ISCO is the backbone hierarchy: every other source's occupations are grafted onto
these unit groups during alignment. We mint occupation nodes for sub-major (2-digit),
minor (3-digit) and unit (4-digit) groups and connect them bottom-up.
"""

from __future__ import annotations
import os

from .. import config as C
from .. import common as K

STRUCT_FILE = os.path.join(C.ISCO_EN_DIR, "ISCO-08 EN.csv")
DEFINITIONS_FILE = os.path.join(C.ISCO_EN_DIR, "ISCO-08 EN Structure and definitions.csv")


def _load_definitions():
    """code -> (title, definition) from the ';'-separated definitions file."""
    out = {}
    if not os.path.isfile(DEFINITIONS_FILE):
        return out
    df = K.read_csv_smart(DEFINITIONS_FILE, sep=";")
    for _, r in df.iterrows():
        code = (r.get("ISCO 08 Code") or "").strip()
        if code:
            out[code] = (r.get("Title EN", "").strip(), r.get("Definition", "").strip())
    return out


def run():
    defs = _load_definitions()
    df = K.read_csv_smart(STRUCT_FILE)

    # Collect the distinct nodes at each level for the IT branches.
    submajors, minors, units = {}, {}, {}
    for _, r in df.iterrows():
        sub = (r.get("sub_major") or "").strip()
        if not sub.startswith(C.ISCO_IT_SUBMAJORS):
            continue
        submajors[sub] = (r.get("sub_major_label") or "").strip()
        mino = (r.get("minor") or "").strip()
        minors[mino] = (r.get("minor_label") or "").strip()
        unit = (r.get("unit") or "").strip()
        units[unit] = (r.get("description") or "").strip()

    occ_rows, label_rows, hier_rows = [], [], []

    def node(code, label, level):
        eid = K.mint_id("OCC_", C.SRC_ISCO, code)
        title, definition = defs.get(code, ("", ""))
        pref = title or label
        occ_rows.append({
            "entity_id": eid, "source": C.SRC_ISCO, "source_id": code,
            "isco_code": code, "source_code": code,
            "pref_label_en": pref, "pref_label_fr": "",
            "alt_labels_en": "", "alt_labels_fr": "",
            "description_en": definition, "description_fr": "",
            "occupation_type": "isco_group", "label_language_status": "en_native",
        })
        label_rows.extend(K.make_label_rows(eid, "occupation", C.SRC_ISCO,
                                            preferred={"en": [pref]}))
        return eid

    for code, label in sorted(submajors.items()):
        node(code, label, 2)
    for code, label in sorted(minors.items()):
        node(code, label, 3)
    for code, label in sorted(units.items()):
        node(code, label, 4)

    # Bottom-up edges: unit -> minor -> sub-major (parent = code without last digit).
    def edge(child_code, parent_code):
        hier_rows.append({
            "parent_entity_id": K.mint_id("OCC_", C.SRC_ISCO, parent_code),
            "child_entity_id": K.mint_id("OCC_", C.SRC_ISCO, child_code),
            "entity_kind": "occupation", "relation_type": "broader_than",
            "source": C.SRC_ISCO,
        })

    for code in units:
        if code[:3] in minors:
            edge(code, code[:3])
    for code in minors:
        if code[:2] in submajors:
            edge(code, code[:2])

    K.replace_source_rows(C.OCCUPATIONS_CSV, C.OCCUPATION_FIELDS, C.SRC_ISCO, occ_rows)
    K.upsert_labels(label_rows)
    K.replace_source_rows(C.HIERARCHY_CSV, C.HIERARCHY_FIELDS, C.SRC_ISCO, hier_rows)
    K.log_provenance(C.SRC_ISCO, [{
        "entity_id": C.SRC_ISCO, "source": C.SRC_ISCO, "source_version": "ISCO-08",
        "retrieved_at": K.now_iso(), "retrieval_method": "official_en_csv",
        "notes": f"{len(occ_rows)} groups, {len(hier_rows)} edges (IT branches 25/35)",
    }])
    print(f"[ISCO] {len(submajors)} sub-major, {len(minors)} minor, {len(units)} unit groups; "
          f"{len(hier_rows)} hierarchy edges.")
