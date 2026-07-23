"""Attach every source's occupations onto the ISCO-08 backbone — source-equal.

ISCO-08 is the neutral international standard (ESCO/SOC/NOC/ROME all crosswalk to it).
ESCO occupations carry a native ISCO code and self-attach during ingest. ONET, NOC and
ROME occupations are attached here by **direct alignment to the ISCO groups themselves** —
never routed through ESCO. Attachment is a two-stage, model-verified decision (no human in
the loop): embedding gives a top-K shortlist of ISCO unit groups, then an NLI verifier
(mDeBERTa entailment of the occupation definition -> the group definition) re-ranks the
shortlist, so a strong embedding to the *wrong* group can be overridden by the definition
semantics. Each occupation gets its inferred `isco_code` written back. Placements whose
chosen embedding or entailment is weak are flagged low-confidence for QA (never dropped).
Result: no ESCO gateway, and no hierarchy orphans.
"""

from __future__ import annotations
from collections import defaultdict

from .. import config as C
from .. import common as K
from . import candidates as cand
from . import verify as _verify

ATTACH_SRC = "ATTACH"
ATTACH_LOWCONF_SRC = "ATTACH_LOWCONF"  # attached to best group, but flagged for review


def _needs_attach():
    """Sources needing ISCO attachment, from the registry (ESCO self-attaches natively)."""
    from ..sources import registry
    return set(registry.needs_attach_sources())


def _group_text(row):
    return ". ".join(p for p in (row.get("pref_label_en", ""),
                                 row.get("description_en", "")[:400]) if p)


def _occ_desc(row):
    return row.get("description_en") or row.get("description_fr") or ""


def _write_attach_edges(edges, lowconf_edges, focus_source):
    """Write ATTACH / ATTACH_LOWCONF hierarchy edges. Full mode replaces both groups
    wholesale; focus mode preserves other sources' attach edges and replaces only those
    for the focus source's occupations (keyed by child occupation id)."""
    if focus_source is None:
        K.replace_source_rows(C.HIERARCHY_CSV, C.HIERARCHY_FIELDS, ATTACH_SRC, edges)
        K.replace_source_rows(C.HIERARCHY_CSV, C.HIERARCHY_FIELDS, ATTACH_LOWCONF_SRC, lowconf_edges)
        return
    focus_children = {e["child_entity_id"] for e in edges + lowconf_edges}
    existing = K.read_all(C.HIERARCHY_CSV)
    kept = [r for r in existing
            if not (r.get("source") in (ATTACH_SRC, ATTACH_LOWCONF_SRC)
                    and r.get("child_entity_id") in focus_children)]
    K.write_csv(C.HIERARCHY_CSV, C.HIERARCHY_FIELDS, kept + edges + lowconf_edges)


def run(focus_source=None):
    """Attach occupations to ISCO. `focus_source=None` (re)attaches every non-native source;
    a `focus_source` attaches only that source's occupations, preserving the others' edges."""
    occ = K.read_all(C.OCCUPATIONS_CSV)
    needs = _needs_attach()
    attach_srcs = ({focus_source} & needs) if focus_source is not None else needs
    # Attach targets: the specific ISCO unit groups (4-digit codes, incl. 1330).
    targets = [r for r in occ if r.get("occupation_type") == "isco_group"
               and len(r.get("source_code", "")) == 4]
    to_attach = [r for r in occ if r.get("source") in attach_srcs]
    if not targets or not to_attach:
        print(f"[ATTACH] nothing to attach{f' for {focus_source}' if focus_source else ''}.")
        return []

    import numpy as np
    from sklearn.metrics.pairwise import cosine_similarity

    embedder = cand.get_embedder()                    # shared bge-m3 (loaded once)
    verifier = _verify.Verifier()                     # shared mDeBERTa
    g_texts = [_group_text(g) for g in targets]
    g_desc = [t.get("description_en", "") for t in targets]
    o_texts = [cand.entity_text(o) for o in to_attach]
    # Reuse cached vectors where align already encoded these occupations.
    emb_g = cand.encode_cached(embedder, g_texts)
    emb_o = cand.encode_cached(embedder, o_texts)
    sim = cosine_similarity(emb_o, emb_g)             # (|occ|, |groups|)

    k = min(C.ATTACH_TOPK, len(targets))
    shortlist = [np.argsort(-sim[i])[:k].tolist() for i in range(len(to_attach))]

    # Batch every (occupation definition -> candidate group definition) entailment once.
    nli_texts, nli_map = [], []
    for i, o in enumerate(to_attach):
        od = _occ_desc(o)
        if not od:
            continue
        for j in shortlist[i]:
            if g_desc[j]:
                nli_map.append((i, j))
                nli_texts.append((od, g_desc[j]))
    nli_scores = verifier.entail_batch(nli_texts) if nli_texts else []
    entail = {}
    for (i, j), s in zip(nli_map, nli_scores):
        if s is not None:
            entail[(i, j)] = float(s)

    edges, lowconf_edges = [], []
    counts = defaultdict(int)
    low = []
    overrides = 0
    curated = 0
    code_to_j = {targets[j]["source_code"]: j for j in range(len(targets))}
    for i, o in enumerate(to_attach):              # `o` is the same dict object as in `occ`
        # Curated ISCO override: a hand-verified placement for an emerging role the automatic attach
        # got wrong. Forces a high-confidence edge (skips the low-conf flag) — deterministic, no human
        # in the loop at runtime. Only applies when the target group exists.
        forced_code = C.ISCO_OCC_OVERRIDE.get(o.get("source_id", ""))
        if forced_code in code_to_j:
            j = code_to_j[forced_code]
            o["isco_code"] = targets[j]["source_code"]
            edges.append({
                "parent_entity_id": targets[j]["entity_id"],
                "child_entity_id": o["entity_id"],
                "entity_kind": "occupation", "relation_type": "broader_than",
                "source": ATTACH_SRC,
            })
            counts[o["source"]] += 1
            curated += 1
            continue
        # Choice = NLI re-ranking of the embedding shortlist: score = cosine + weighted
        # entailment, so a strong embedding to the wrong group can be overridden by the
        # definition semantics. Missing definition -> reduces to embedding argmax.
        emb_top = shortlist[i][0]
        best_j, best_score, best_sim, best_ent = None, -1e9, 0.0, None
        for j in shortlist[i]:
            s_emb = float(sim[i, j])
            ent = entail.get((i, j))
            score = s_emb + C.ATTACH_NLI_WEIGHT * (ent if ent is not None else 0.0)
            if score > best_score:
                best_j, best_score, best_sim, best_ent = j, score, s_emb, ent
        j = best_j
        if j != emb_top:
            overrides += 1
        o["isco_code"] = targets[j]["source_code"]  # write inferred ISCO code back (in place)
        edge = {
            "parent_entity_id": targets[j]["entity_id"],
            "child_entity_id": o["entity_id"],
            "entity_kind": "occupation", "relation_type": "broader_than",
            "source": ATTACH_SRC,
        }
        # Review flag uses the embedding confidence of the chosen group: entailment is a good
        # *relative* signal (re-ranking) but a poor *absolute* one for a hypernym attach (a
        # correct occupation->broader-group pair often has low entailment), so it is not used
        # to flag. Flags surface genuinely uncertain placements (catch-all / niche roles).
        if best_sim < C.ATTACH_MIN_SIM:
            edge["source"] = ATTACH_LOWCONF_SRC
            lowconf_edges.append(edge)
            low.append((o.get("pref_label_en") or o.get("pref_label_fr") or o["entity_id"],
                        o["source"], targets[j]["source_code"], best_sim, best_ent))
        else:
            edges.append(edge)
        counts[o["source"]] += 1

    # Persist the inferred isco_code onto the attached occupation rows (mutated above).
    for src in attach_srcs:
        rows = [r for r in occ if r["source"] == src]
        if rows:
            K.replace_source_rows(C.OCCUPATIONS_CSV, C.OCCUPATION_FIELDS, src, rows)

    _write_attach_edges(edges, lowconf_edges, focus_source)
    K.log_provenance(ATTACH_SRC, [{
        "entity_id": ATTACH_SRC, "source": ATTACH_SRC, "source_version": "-",
        "retrieved_at": K.now_iso(),
        "retrieval_method": f"embed:{embedder.model_id}+nli:{C.NLI_MODEL}",
        "notes": f"{len(edges)+len(lowconf_edges)} attached, top-{k} NLI re-ranked "
                 f"({overrides} NLI overrode embedding top-1; {curated} curated ISCO overrides; "
                 f"{len(lowconf_edges)} low-confidence: sim<{C.ATTACH_MIN_SIM})",
    }])
    print(f"[ATTACH] {len(edges)+len(lowconf_edges)} occupations attached to ISCO "
          f"(embed={embedder.model_id}, NLI re-rank top-{k}, nli={'on' if verifier.nli_ok else 'off'}); "
          f"{', '.join(f'{s}:{counts[s]}' for s in sorted(counts))}; "
          f"NLI moved {overrides} off embedding top-1; {curated} curated overrides; "
          f"{len(lowconf_edges)} low-confidence.")
    for lbl, src, code, s, e in low[:10]:
        es = f"{e:.2f}" if e is not None else "n/a"
        print(f"    low-conf: [{src}] {lbl} -> ISCO {code} (sim={s:.2f}, entail={es})")
    return edges + lowconf_edges
