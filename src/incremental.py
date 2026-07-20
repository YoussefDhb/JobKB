"""Incremental source management — add or remove ONE source without a full rebuild.

`add_source(name)` ingests only that source, aligns it against the existing entities,
attaches its occupations to ISCO and re-derives the unified concepts — reusing the
embedding cache so existing entities are never re-encoded. `remove_source(name)` deletes
everything that source owns and repairs the graph, returning the KB to its prior state.
Both rely on the per-source idempotency of the KB writes (`common.replace_source_rows`).
"""

from __future__ import annotations

from . import config as C
from . import common as K
from . import hierarchy, merge, pipeline
from . import align
from .align import attach
from .sources import registry


def _refresh_global_provenance():
    """Incremental align/attach log stage provenance for only the focused slice; rewrite the
    global ALIGNMENT/ATTACH provenance to reflect the whole KB (and drop focus references)."""
    n_align = len(K.read_all(C.ALIGNMENTS_CSV))
    hier = K.read_all(C.HIERARCHY_CSV)
    n_attach = sum(1 for h in hier if h.get("source") in ("ATTACH", "ATTACH_LOWCONF"))
    K.log_provenance("ALIGNMENT", [{
        "entity_id": "ALIGNMENT", "source": "ALIGNMENT", "source_version": "-",
        "retrieved_at": K.now_iso(), "retrieval_method": "incremental",
        "notes": f"{n_align} alignments total"}])
    K.log_provenance("ATTACH", [{
        "entity_id": "ATTACH", "source": "ATTACH", "source_version": "-",
        "retrieved_at": K.now_iso(), "retrieval_method": "incremental",
        "notes": f"{n_attach} ISCO attach edges total"}])


def add_source(name: str):
    src = registry.get(name)
    print(f"=== add source: {name} ===")
    src.ingest()                        # per-source idempotent write of the new rows
    hierarchy.run()                     # classify the new skills into the ontology (cheap)
    align.run(focus_source=name)        # align only new-vs-existing; append alignments
    if src.needs_attach:
        attach.run(focus_source=name)   # attach only this source's occupations to ISCO
    merge.run()                         # cheap recompute of unified concepts over full graph
    _refresh_global_provenance()
    return pipeline.qa()


def _prune_missing_refs():
    """Drop hierarchy edges, alignment rows and occ-skill relations that reference entity
    ids no longer present (after a source's rows were deleted) — keeps the graph consistent."""
    occ_ids = {r["entity_id"] for r in K.read_all(C.OCCUPATIONS_CSV)}
    skl_ids = {r["entity_id"] for r in K.read_all(C.SKILLS_CSV)}
    node_ids = occ_ids | skl_ids

    hier = K.read_all(C.HIERARCHY_CSV)
    hier_kept = [e for e in hier
                 if e.get("parent_entity_id") in node_ids and e.get("child_entity_id") in node_ids]
    if len(hier_kept) != len(hier):
        K.write_csv(C.HIERARCHY_CSV, C.HIERARCHY_FIELDS, hier_kept)

    aligns = K.read_all(C.ALIGNMENTS_CSV)
    al_kept = [a for a in aligns
               if a.get("entity_id_a") in node_ids and a.get("entity_id_b") in node_ids]
    if len(al_kept) != len(aligns):
        K.write_csv(C.ALIGNMENTS_CSV, C.ALIGNMENT_FIELDS, al_kept)

    rels = K.read_all(C.OCC_SKILL_REL_CSV)
    rel_kept = [r for r in rels
                if r.get("occupation_entity_id") in occ_ids and r.get("skill_entity_id") in skl_ids]
    if len(rel_kept) != len(rels):
        K.write_csv(C.OCC_SKILL_REL_CSV, C.REL_FIELDS, rel_kept)


def remove_source(name: str):
    print(f"=== remove source: {name} ===")
    # Delete every row this source owns (all keyed by the `source` column).
    for path, fields in ((C.OCCUPATIONS_CSV, C.OCCUPATION_FIELDS),
                         (C.SKILLS_CSV, C.SKILL_FIELDS),
                         (C.OCC_SKILL_REL_CSV, C.REL_FIELDS),
                         (C.LABELS_CSV, C.LABEL_FIELDS),
                         (C.HIERARCHY_CSV, C.HIERARCHY_FIELDS),
                         (C.PROVENANCE_CSV, C.PROVENANCE_FIELDS)):
        K.replace_source_rows(path, fields, name, [])
    # Drop alignments that involve the source on either side.
    aligns = K.read_all(C.ALIGNMENTS_CSV)
    al_kept = [a for a in aligns if a.get("source_a") != name and a.get("source_b") != name]
    if len(al_kept) != len(aligns):
        K.write_csv(C.ALIGNMENTS_CSV, C.ALIGNMENT_FIELDS, al_kept)
    # Remove now-dangling edges/relations (e.g. ATTACH edges to the removed occupations).
    _prune_missing_refs()
    hierarchy.run()   # rebuild the skill ontology edges from the remaining skills
    merge.run()       # re-derive unified concepts
    _refresh_global_provenance()
    return pipeline.qa()
