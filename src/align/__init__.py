"""Automatic, agentic cross-source alignment."""

from __future__ import annotations

from .. import config as C
from .. import common as K
from . import candidates as _cand
from . import verify as _verify


def _fr_en_translation_map():
    """{normalize(french label) -> validated English MT} from the persisted translate fr_en snapshot."""
    import os
    m = {}
    if os.path.isfile(C.TRANSLATE_SNAPSHOT_CSV):
        for r in K.read_all(C.TRANSLATE_SNAPSHOT_CSV):
            if r.get("direction") == "fr_en" and r.get("validated") == "1" and r.get("output"):
                m.setdefault(K.normalize_label(r.get("src_text", "")), r["output"])
    return m


def _exact_key_skill_edges(skl):
    """Deterministic same-concept dedup for skills sharing an identical (English) match_key."""
    from .. import hierarchy as H
    from ..sources import evidence as _ev
    tmap = _fr_en_translation_map()
    groups = {}
    for r in skl:
        en = (r.get("pref_label_en") or "").strip()
        if not en: 
            en = tmap.get(K.normalize_label(r.get("pref_label_fr") or ""), "")
        key = _ev.match_key(en or r.get("pref_label_fr") or "")
        if not key or key in C.MATCH_KEY_DISTINCT:
            continue
        cls = H.skill_type(r.get("it_subtype", "")) or (r.get("hard_soft_provisional") or "")
        groups.setdefault((key, cls), []).append(r)

    rows = []
    for (_key, _cls), members in groups.items():
        if len(members) < 2:
            continue
        anchor = members[0]
        alab = anchor.get("pref_label_en") or anchor.get("pref_label_fr") or ""
        for m in members[1:]:
            mlab = m.get("pref_label_en") or m.get("pref_label_fr") or ""
            rows.append({
                "entity_id_a": anchor["entity_id"], "source_a": anchor["source"],
                "entity_id_b": m["entity_id"], "source_b": m["source"],
                "relation": "skos:exactMatch", "confidence": 0.97,
                "method": "match_key_exact", "validated": "auto", "merge": "label",
                "notes": f"{alab} <> {mlab} (exact key)",
            })
    return rows


def replace_alignments_for_source(name, new_rows):
    """Incremental alignment write: keep every existing alignment row that does NOT involve
    `name` on either side."""
    existing = K.read_all(C.ALIGNMENTS_CSV)
    kept = [r for r in existing
            if r.get("source_a") != name and r.get("source_b") != name]
    K.write_csv(C.ALIGNMENTS_CSV, C.ALIGNMENT_FIELDS, kept + new_rows)
    return len(kept)


def run(focus_source=None):
    """Cross-source alignment."""
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
        # Full build: augment with the deterministic exact-match_key dedup edges and rewrite the table.
        exact_rows = _exact_key_skill_edges(skl)
        rows += exact_rows
        K.write_csv(C.ALIGNMENTS_CSV, C.ALIGNMENT_FIELDS, rows)
        n_total = len(rows)
        print(f"[ALIGN] +{len(exact_rows)} deterministic exact-match_key skill dedup edges.")
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
