"""Automatic, agentic cross-source alignment (no human in the loop).

Embedding candidate generation -> HF verification (NLI on definitions for occupations,
label + embedding for skills) -> SKOS relations + a source-neutral `merge` flag consumed
by the unified merge. Attachment onto ISCO happens in the separate `attach` stage. All
open-source / HuggingFace; degrades gracefully offline.
"""

from __future__ import annotations

from .. import config as C
from .. import common as K
from . import candidates as _cand
from . import verify as _verify


def replace_alignments_for_source(name, new_rows):
    """Incremental alignment write: keep every existing alignment row that does NOT involve
    `name` on either side, then append the freshly computed new-vs-existing rows. Old<->old
    alignments are untouched — so adding a source never recomputes the others."""
    existing = K.read_all(C.ALIGNMENTS_CSV)
    kept = [r for r in existing
            if r.get("source_a") != name and r.get("source_b") != name]
    K.write_csv(C.ALIGNMENTS_CSV, C.ALIGNMENT_FIELDS, kept + new_rows)
    return len(kept)


def run(focus_source=None):
    """Cross-source alignment. `focus_source=None` aligns everything (full build) and
    overwrites the alignment table. A `focus_source` aligns only that source against the
    existing entities and merges the result in incrementally."""
    occ, skl = _cand.load_entities()

    embedder = _cand.get_embedder()
    verifier = _verify.Verifier()

    occ_pairs = _cand.candidate_pairs(occ, embedder, focus_source=focus_source)
    skl_pairs = _cand.candidate_pairs(skl, embedder, focus_source=focus_source)
    print(f"[ALIGN] candidates: {len(occ_pairs)} occupation, {len(skl_pairs)} skill"
          f"{f' (focus={focus_source})' if focus_source else ''}.")

    rows = []
    rows += _verify.verify_pairs(occ_pairs, verifier, use_nli=True)
    rows += _verify.verify_pairs(skl_pairs, verifier, use_nli=False)

    if focus_source is None:
        K.write_csv(C.ALIGNMENTS_CSV, C.ALIGNMENT_FIELDS, rows)
        n_total = len(rows)
    else:
        kept = replace_alignments_for_source(focus_source, rows)
        n_total = kept + len(rows)

    n_exact = sum(1 for r in rows if r["relation"] == "skos:exactMatch")
    n_merge = sum(1 for r in rows if r["merge"] in ("label", "semantic"))
    print(f"[ALIGN] {len(rows)} new alignments ({n_exact} exactMatch, "
          f"{n_merge} flagged-to-merge); {n_total} total. "
          f"NLI={'on' if verifier.nli_ok else 'off'}, embed={embedder.mode}.")

    K.log_provenance("ALIGNMENT", [{
        "entity_id": "ALIGNMENT", "source": "ALIGNMENT", "source_version": "-",
        "retrieved_at": K.now_iso(),
        "retrieval_method": f"embed:{embedder.mode}+nli:{'on' if verifier.nli_ok else 'off'}",
        "notes": f"{n_total} alignments, {n_merge} merge-flagged"
                 f"{f', focus={focus_source}' if focus_source else ''}",
    }])
