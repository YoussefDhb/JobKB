"""Orchestrator: run the JobKB build, whole or by stage, idempotently.

Stages (canonical order): ingest -> hierarchy -> align -> attach -> merge -> qa.
Each writes `kb/` per-source and idempotently, so any stage (or contiguous range) can run
standalone against the persisted KB — see `run_stages` and the `run_pipeline.py` flags
(`--stages`, `--from`, `--to`, `--source`). A full build is just every stage with a clean.
"""

from __future__ import annotations
import os

from . import config as C
from . import common as K
from . import hierarchy
from . import align
from .align import attach
from . import merge
from .sources import registry

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


# --------------------------------------------------------------------------------------
# Stage registry — every stage runnable standalone against the persisted kb/.
# --------------------------------------------------------------------------------------

STAGE_ORDER = ["ingest", "hierarchy", "align", "attach", "merge", "qa"]

# A file each stage expects to already exist (used only for a soft "run earlier stages
# first" warning on a selective run).
_STAGE_INPUT = {
    "hierarchy": C.SKILLS_CSV,
    "align": C.OCCUPATIONS_CSV,
    "attach": C.OCCUPATIONS_CSV,
    "merge": C.ALIGNMENTS_CSV,
    "qa": C.OCCUPATIONS_CSV,
}


def _ingest(source=None):
    """Ingest all built-in taxonomies (in registration order) or a single named source.

    Re-ingest rebuilds a source's occupation rows from scratch, which blanks the
    attach-derived `isco_code` (attach writes it back onto the rows). Preserve the previous
    value across a re-ingest so the ISCO backbone survives without an immediate re-attach.
    """
    names = (source,) if source else registry.builtin_sources()
    prior_isco = {r["entity_id"]: r["isco_code"] for r in K.read_all(C.OCCUPATIONS_CSV)
                  if r.get("isco_code")}
    for name in names:
        registry.get(name).ingest()
    if prior_isco:
        occ = K.read_all(C.OCCUPATIONS_CSV)
        touched = set()
        for r in occ:
            if not r.get("isco_code") and prior_isco.get(r["entity_id"]):
                r["isco_code"] = prior_isco[r["entity_id"]]
                touched.add(r["source"])
        for src in touched:
            K.replace_source_rows(C.OCCUPATIONS_CSV, C.OCCUPATION_FIELDS, src,
                                  [r for r in occ if r["source"] == src])


def _hierarchy(source=None):
    hierarchy.run()


def _align(source=None):
    align.run(focus_source=source)


def _attach(source=None):
    attach.run(focus_source=source)


def _merge(source=None):
    merge.run()


def _qa(source=None):
    return qa()


_STAGES = {
    "ingest": _ingest, "hierarchy": _hierarchy, "align": _align,
    "attach": _attach, "merge": _merge, "qa": _qa,
}


def run_stages(stages, source=None, clean=False):
    """Run the given stages (always in canonical order) against the current kb/.

    `source` scopes ingest/align/attach to one registered source. `clean` wipes kb/ first
    (a full build); selective runs leave kb/ intact. Returns the qa() dict if qa ran.
    """
    unknown = [s for s in stages if s not in _STAGES]
    if unknown:
        raise ValueError(f"Unknown stage(s): {', '.join(unknown)}. "
                         f"Valid stages: {', '.join(STAGE_ORDER)}")
    if source is not None:
        registry.get(source)  # validate early (raises with the known-source list)
    selected = [s for s in STAGE_ORDER if s in set(stages)]

    K.ensure_dirs()
    if clean:
        _clean()

    import time as _t
    last = [_t.time()]

    def _stage(name):
        now = _t.time()
        print(f"--- {name} ---  (+{now - last[0]:.1f}s)", flush=True)
        last[0] = now

    result = None
    for name in selected:
        inp = _STAGE_INPUT.get(name)
        if inp and not clean and not os.path.isfile(inp):
            print(f"[warn] stage '{name}' expects {os.path.basename(inp)}, which is missing "
                  f"— run the earlier stages first.")
        _stage(name)
        out = _STAGES[name](source=source)
        if name == "qa":
            result = out

    # Running an upstream stage leaves downstream-derived data stale (e.g. re-ingesting a
    # source resets its rows; hierarchy/align/attach/merge must re-run to stay consistent).
    max_i = max(STAGE_ORDER.index(s) for s in selected)
    stale = [s for s in STAGE_ORDER[max_i + 1:] if s != "qa"]
    if stale:
        print(f"[note] downstream stage(s) not re-run: {', '.join(stale)}; "
              f"kb/ may be stale there -- re-run them (e.g. --from {stale[0]}) for consistency.")
    return result


def run_all(clean=True, do_align=True):
    """Full build: every stage, cleaning kb/ first. `do_align=False` stops after hierarchy."""
    stages = list(STAGE_ORDER)
    if not do_align:
        stages = [s for s in stages if s not in ("align", "attach", "merge")]
    return run_stages(stages, clean=clean)
