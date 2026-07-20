"""Orchestrator: run the whole JobKB build end-to-end, idempotently.

    ingest (ISCO/ESCO/ONET/NOC/ROME) -> skill ontology -> align -> attach -> merge -> QA
"""

from __future__ import annotations
import os

from . import config as C
from . import common as K
from .ingest import isco, esco, onet, noc, rome
from . import hierarchy
from . import align
from .align import attach
from . import merge

_OUTPUTS = [
    C.OCCUPATIONS_CSV, C.SKILLS_CSV, C.LABELS_CSV, C.OCC_SKILL_REL_CSV,
    C.HIERARCHY_CSV, C.ALIGNMENTS_CSV, C.UNIFIED_OCCUPATIONS_CSV,
    C.UNIFIED_SKILLS_CSV, C.PROVENANCE_CSV,
]

_TAXO = ("skill_type", "skill_domain")


def _clean():
    for p in _OUTPUTS:
        if os.path.isfile(p):
            os.remove(p)


def qa():
    """Integrity + coverage report (non-fatal warnings)."""
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

    # Orphans: real occupations / real skills with no parent in the hierarchy.
    occ_children = {e["child_entity_id"] for e in hier if e["entity_kind"] == "occupation"}
    occ_orphans = [r for r in real_occ if r["entity_id"] not in occ_children]
    real_skl = [r for r in skl if r.get("esco_skill_type") not in _TAXO]
    skl_children = {e["child_entity_id"] for e in hier if e["entity_kind"] == "skill"}
    skl_flat = [r for r in real_skl if r["entity_id"] not in skl_children]

    attach_lowconf = [e for e in hier if e["source"] == "ATTACH_LOWCONF"]

    print("\n=== QA ===")
    print(f"occupations: {len(occ)} ({len(real_occ)} real, "
          f"{len(occ) - len(real_occ)} ISCO groups)")
    print(f"skills: {len(real_skl)} (+{len(skl) - len(real_skl)} taxonomy nodes)  |  "
          f"hierarchy edges: {len(hier)}  |  dangling: {len(dangling)}")
    print(f"EN label coverage (real occ): {en_cov}/{len(real_occ)}")
    print(f"occupation orphans (no hierarchy parent): {len(occ_orphans)}")
    print(f"low-confidence ISCO attachments (review): {len(attach_lowconf)}")
    print(f"skills not placed in ontology: {len(skl_flat)}")
    print(f"non-IT ISCO group leakage: {len(it_leak)}")
    if dangling:
        print(f"  WARNING: {len(dangling)} dangling edges e.g. "
              f"{[(e['parent_entity_id'], e['child_entity_id']) for e in dangling[:3]]}")
    return {"occupations": len(occ), "skills": len(real_skl), "edges": len(hier),
            "dangling": len(dangling), "occ_orphans": len(occ_orphans),
            "skl_flat": len(skl_flat), "attach_lowconf": len(attach_lowconf)}


def run_all(clean=True, do_align=True):
    import time as _t
    _last = [_t.time()]

    def _stage(name):
        now = _t.time()
        print(f"--- {name} ---  (+{now - _last[0]:.1f}s)", flush=True)
        _last[0] = now

    K.ensure_dirs()
    if clean:
        _clean()

    _stage("ingest")
    isco.run()
    esco.run()
    onet.run()
    noc.run()
    rome.run()

    _stage("skill ontology")
    hierarchy.run()

    if do_align:
        _stage("align")
        align.run()
        _stage("attach")
        attach.run()
        _stage("merge")
        merge.run()

    _stage("qa")
    return qa()
