"""Graft non-ISCO occupations (ONET/NOC/ROME) onto the ISCO hub.

Each non-ISCO occupation inherits the ISCO unit group of its best validated ESCO
match (exact/close). This is fully automatic and replaces the old gold-gated graft.
Occupations with no ESCO match stay unattached to the tree but still cluster during
the unified merge (and inherit an ISCO code there if any cluster member has one).
"""

from __future__ import annotations

from .. import config as C
from .. import common as K

GRAFT_RELATIONS = {"skos:exactMatch", "skos:closeMatch", "skos:narrowMatch", "skos:broadMatch"}


def graft(alignment_rows):
    occ = {r["entity_id"]: r for r in K.read_all(C.OCCUPATIONS_CSV)}

    best = {}  # non-ESCO occ eid -> (isco_code, confidence)
    for a in alignment_rows:
        ea, eb = a["entity_id_a"], a["entity_id_b"]
        if not (ea.startswith("OCC_") and eb.startswith("OCC_")):
            continue
        if a["relation"] not in GRAFT_RELATIONS:
            continue
        ra, rb = occ.get(ea), occ.get(eb)
        if not ra or not rb:
            continue
        conf = float(a["confidence"])
        for esco_row, other in ((ra, rb), (rb, ra)):
            if (esco_row["source"] == C.SRC_ESCO and C.is_isco_it(esco_row.get("isco_code", ""))
                    and other["source"] not in (C.SRC_ESCO, C.SRC_ISCO)):
                cur = best.get(other["entity_id"])
                if cur is None or conf > cur[1]:
                    best[other["entity_id"]] = (esco_row["isco_code"].strip(), conf)

    edges = []
    for eid, (isco, _conf) in best.items():
        edges.append({
            "parent_entity_id": K.mint_id("OCC_", C.SRC_ISCO, isco),
            "child_entity_id": eid,
            "entity_kind": "occupation", "relation_type": "broader_than",
            "source": "ALIGNMENT",
        })
    K.replace_source_rows(C.HIERARCHY_CSV, C.HIERARCHY_FIELDS, "ALIGNMENT", edges)
    return edges
