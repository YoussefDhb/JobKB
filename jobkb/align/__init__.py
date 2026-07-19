"""Automatic, agentic cross-source alignment (no human in the loop).

Pipeline: embedding candidate generation -> HF verification (NLI on definitions
for occupations, label+embedding for skills) -> auto-graft non-ISCO occupations
onto the ISCO hub. All open-source / HuggingFace; degrades gracefully offline.
"""

from __future__ import annotations

from .. import config as C
from .. import common as K
from . import candidates as _cand
from . import verify as _verify
from . import graft as _graft


def run():
    occ, skl = _cand.load_entities()

    embedder = _cand.Embedder()
    verifier = _verify.Verifier()

    occ_pairs = _cand.candidate_pairs(occ, embedder)
    skl_pairs = _cand.candidate_pairs(skl, embedder)
    print(f"[ALIGN] candidates: {len(occ_pairs)} occupation, {len(skl_pairs)} skill.")

    rows = []
    rows += _verify.verify_pairs(occ_pairs, verifier, use_nli=True)
    rows += _verify.verify_pairs(skl_pairs, verifier, use_nli=False)

    K.write_csv(C.ALIGNMENTS_CSV, C.ALIGNMENT_FIELDS, rows)
    n_exact = sum(1 for r in rows if r["relation"] == "skos:exactMatch")
    n_close = sum(1 for r in rows if r["relation"] == "skos:closeMatch")
    print(f"[ALIGN] {len(rows)} alignments written "
          f"({n_exact} exactMatch, {n_close} closeMatch). NLI={'on' if verifier.nli_ok else 'off'}, "
          f"embed={embedder.mode}.")

    graft_edges = _graft.graft(rows)
    print(f"[ALIGN] grafted {len(graft_edges)} non-ISCO occupations onto the hub.")

    K.log_provenance("ALIGNMENT", [{
        "entity_id": "ALIGNMENT", "source": "ALIGNMENT", "source_version": "-",
        "retrieved_at": K.now_iso(),
        "retrieval_method": f"embed:{embedder.mode}+nli:{'on' if verifier.nli_ok else 'off'}",
        "notes": f"{len(rows)} alignments, {len(graft_edges)} grafts",
    }])
