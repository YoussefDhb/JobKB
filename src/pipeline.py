"""Orchestrator: run the whole JobKB build end-to-end, idempotently.

    ingest (ISCO -> ESCO -> ONET -> NOC -> ROME) -> hierarchy -> align -> merge -> QA
"""

from __future__ import annotations
import os

from . import config as C
from . import common as K
from .ingest import isco, esco, onet, noc, rome
from . import hierarchy
from . import align
from . import merge

_OUTPUTS = [
    C.OCCUPATIONS_CSV, C.SKILLS_CSV, C.LABELS_CSV, C.OCC_SKILL_REL_CSV,
    C.HIERARCHY_CSV, C.ALIGNMENTS_CSV, C.UNIFIED_OCCUPATIONS_CSV,
    C.UNIFIED_SKILLS_CSV, C.PROVENANCE_CSV,
]


def _clean():
    for p in _OUTPUTS:
        if os.path.isfile(p):
            os.remove(p)


def qa():
    """Lightweight integrity + coverage report (non-fatal warnings)."""
    occ = K.read_all(C.OCCUPATIONS_CSV)
    skl = K.read_all(C.SKILLS_CSV)
    hier = K.read_all(C.HIERARCHY_CSV)
    node_ids = {r["entity_id"] for r in occ} | {r["entity_id"] for r in skl}

    dangling = [e for e in hier
                if e["parent_entity_id"] not in node_ids
                or e["child_entity_id"] not in node_ids]

    real_occ = [r for r in occ if r["occupation_type"] != "isco_group"]
    en_cov = sum(1 for r in real_occ if r.get("pref_label_en"))
    it_leak = [r for r in occ if r["occupation_type"] == "isco_group"
               and not C.is_isco_it(r.get("isco_code", ""))]

    print("\n=== QA ===")
    print(f"occupations: {len(occ)} ({len(real_occ)} real, "
          f"{len(occ) - len(real_occ)} ISCO groups)")
    print(f"skills: {len(skl)}  |  hierarchy edges: {len(hier)}  |  dangling: {len(dangling)}")
    print(f"EN label coverage (real occ): {en_cov}/{len(real_occ)}")
    print(f"non-IT ISCO group leakage: {len(it_leak)}")
    if dangling:
        print(f"  WARNING: {len(dangling)} dangling hierarchy edges (first 3): "
              f"{[ (e['parent_entity_id'], e['child_entity_id']) for e in dangling[:3] ]}")
    return {"occupations": len(occ), "skills": len(skl), "edges": len(hier),
            "dangling": len(dangling)}


def run_all(clean=True, do_align=True):
    K.ensure_dirs()
    if clean:
        _clean()

    print("--- ingest ---")
    isco.run()
    esco.run()
    onet.run()
    noc.run()
    rome.run()

    print("--- hierarchy ---")
    hierarchy.run()

    if do_align:
        print("--- align ---")
        align.run()
        print("--- merge ---")
        merge.run()

    return qa()
