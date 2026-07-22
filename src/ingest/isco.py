"""Ingest the ISCO-08 hub (English), restricted to the IT branches.

ISCO-08 is the neutral standard backbone: every source's occupations attach onto these
groups. In scope: sub-major groups 25 (ICT professionals) & 35 (ICT technicians) and
minor group 133 (ICT service managers). We mint occupation nodes for each in-scope
sub-major/minor/unit group and connect them bottom-up; a node is a root when its parent
is out of scope (so the tree roots at 25, 35 and 133).
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

    # Collect every in-scope node at any level (the file also holds ISCO-68 rows, which
    # we must skip). A code qualifies via is_isco_it (25*/35*/133*).
    nodes = {}  # code -> label
    for _, r in df.iterrows():
        if (r.get("ISCO_version") or "").strip() != "ISCO-08":
            continue
        for code_col, label_col in (("sub_major", "sub_major_label"),
                                    ("minor", "minor_label"),
                                    ("unit", "description")):
            code = (r.get(code_col) or "").strip()
            if code and C.is_isco_it(code) and code not in nodes:
                nodes[code] = (r.get(label_col) or "").strip()

    occ_rows, label_rows, hier_rows = [], [], []

    for code, label in sorted(nodes.items()):
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

    # Synthetic super-root over the three in-scope ISCO branches (25/35/133) so the occupation tree is
    # a single connected hierarchy instead of three disconnected roots. Empty isco_code (it is not an
    # ISCO group itself) -> QA skips it in the IT-leakage check.
    root_eid = K.mint_id("OCC_", C.SRC_ISCO, "ICT")
    occ_rows.append({
        "entity_id": root_eid, "source": C.SRC_ISCO, "source_id": "ICT",
        "isco_code": "", "source_code": "",
        "pref_label_en": "Information and Communications Technology professions", "pref_label_fr": "",
        "alt_labels_en": "ICT occupations | IT occupations", "alt_labels_fr": "",
        "description_en": "Root of the IT occupation backbone: ISCO-08 ICT professionals (25), "
                          "ICT technicians (35) and ICT service managers (133).", "description_fr": "",
        "occupation_type": "isco_group", "label_language_status": "en_native",
    })
    label_rows.extend(K.make_label_rows(root_eid, "occupation", C.SRC_ISCO,
                                        preferred={"en": ["Information and Communications Technology professions"]}))

    # Bottom-up edges: parent = code without last digit, only if the parent is in scope
    # (so 25/35/133 attach to the ICT super-root; 133's out-of-scope parent 13 is dropped).
    for code in nodes:
        parent = code[:-1]
        parent_eid = K.mint_id("OCC_", C.SRC_ISCO, parent) if parent in nodes else root_eid
        hier_rows.append({
            "parent_entity_id": parent_eid,
            "child_entity_id": K.mint_id("OCC_", C.SRC_ISCO, code),
            "entity_kind": "occupation", "relation_type": "broader_than",
            "source": C.SRC_ISCO,
        })

    K.replace_source_rows(C.OCCUPATIONS_CSV, C.OCCUPATION_FIELDS, C.SRC_ISCO, occ_rows)
    K.upsert_labels(label_rows)
    K.replace_source_rows(C.HIERARCHY_CSV, C.HIERARCHY_FIELDS, C.SRC_ISCO, hier_rows)
    K.log_provenance(C.SRC_ISCO, [{
        "entity_id": C.SRC_ISCO, "source": C.SRC_ISCO, "source_version": "ISCO-08",
        "retrieved_at": K.now_iso(), "retrieval_method": "official_en_csv",
        "notes": f"{len(occ_rows)} groups, {len(hier_rows)} edges (IT branches 25/35/133)",
    }])
    print(f"[ISCO] {len(nodes)} IT group nodes; {len(hier_rows)} hierarchy edges "
          f"(roots: 25, 35, 133).")
