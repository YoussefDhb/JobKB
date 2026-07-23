"""External coverage benchmark (Track 2): does the KB vocabulary contain the skills that expert
annotators marked in real job-posting text?

Read-only. For each gold skill-mention string (pooled across all splits — we fit nothing, so there is
no train/test leakage) we ask two questions against the unified KB skills:
  - EXACT/ALIAS coverage: does its normalized+singularized `match_key` hit a KB primary or alt label?
  - SEMANTIC coverage: is its nearest KB skill label within `VALIDATION_SEMANTIC_MIN` bge-m3 cosine?
Exact is the honest headline; semantic shows paraphrases the label-matcher misses. Reported side by
side, broken out by dataset / subset (tech vs house) / layer (skill vs knowledge) / language.

Plus the Sayfullina synonym-normalization test: within each reference cluster, do the phrasings that
the KB *does* contain resolve to the SAME KB node (correct normalization) or fragment?
"""

from __future__ import annotations

from collections import defaultdict

from .. import config as C
from .. import common as K
from ..sources import evidence as ev
from ..align import candidates as cand
from . import datasets as D


def _index(lang):
    """{match_key(label) -> unified_id} over KB unified-skill primary + alt labels in `lang`."""
    pf, af = f"primary_label_{lang}", f"alt_labels_{lang}"
    idx = {}
    for r in K.read_all(C.UNIFIED_SKILLS_CSV):
        for lbl in [r.get(pf)] + (r.get(af) or "").split(" | "):
            k = ev.match_key(lbl or "")
            if k:
                idx.setdefault(k, r["unified_id"])
    return idx


def _kb_labels(lang):
    """[(unified_id, primary_label)] for KB skills with a non-empty primary label in `lang`."""
    pf = f"primary_label_{lang}"
    out = []
    for r in K.read_all(C.UNIFIED_SKILLS_CSV):
        lab = (r.get(pf) or "").strip()
        if lab:
            out.append((r["unified_id"], lab))
    return out


def _semantic_nearest(embedder, gold_texts, kb_texts):
    """Return (best_score, best_index) per gold string against kb_texts (bge-m3 cosine). st-mode only."""
    import numpy as np
    kb_vecs = cand.encode_cached(embedder, kb_texts)          # (K, d), normalized
    g_vecs = cand.encode_cached(embedder, gold_texts)         # (N, d), normalized
    best_score = np.zeros(len(gold_texts), dtype="float32")
    best_idx = np.zeros(len(gold_texts), dtype="int64")
    for s in range(0, len(gold_texts), 512):                  # chunk to bound the sim matrix
        chunk = g_vecs[s:s + 512]
        sims = chunk @ kb_vecs.T
        best_score[s:s + 512] = sims.max(axis=1)
        best_idx[s:s + 512] = sims.argmax(axis=1)
    return best_score, best_idx


def _unique_gold(mentions):
    """Collapse mentions to unique normalized surfaces, keeping a representative + slice + frequency."""
    seen = {}
    for m in mentions:
        key = K.normalize_label(m["surface"])
        if not key:
            continue
        g = seen.get(key)
        if g is None:
            seen[key] = {"surface": m["surface"], "layer": m["layer"], "subset": m["subset"],
                         "category": m["category"], "language": m["language"], "count": 1}
        else:
            g["count"] += 1
    return list(seen.values())


def evaluate(dataset, embedder=None):
    """Return a list of per-gold records with exact/semantic coverage + best KB match."""
    lang = C.VALIDATION_DATASETS[dataset][4]
    golds = _unique_gold(D.gold_mentions(dataset))
    idx = _index(lang)
    for g in golds:
        mk = ev.match_key(g["surface"])
        g["exact"] = mk in idx
        g["exact_uid"] = idx.get(mk, "")
        g["sem_score"] = ""
        g["sem_uid"] = ""
        g["semantic"] = False

    if embedder is not None and embedder.mode == "st":
        kb = _kb_labels(lang)
        kb_uids = [u for u, _ in kb]
        scores, idxs = _semantic_nearest(embedder, [g["surface"] for g in golds], [t for _, t in kb])
        for i, g in enumerate(golds):
            g["sem_score"] = round(float(scores[i]), 3)
            g["sem_uid"] = kb_uids[int(idxs[i])]
            g["semantic"] = float(scores[i]) >= C.VALIDATION_SEMANTIC_MIN
    return golds


def _rate(golds, key):
    n = len(golds)
    c = sum(1 for g in golds if g[key])
    return c, n, (round(100 * c / n, 1) if n else 0.0)


def aggregate(dataset, golds):
    """Overall + per-slice (layer, subset) exact & semantic coverage rates."""
    slices = defaultdict(list)
    slices[("ALL", "")] = list(golds)
    for g in golds:
        slices[(g["layer"], g["subset"])].append(g)
    rows = []
    for (layer, subset), gs in sorted(slices.items()):
        ec, en, ep = _rate(gs, "exact")
        sc, sn, sp = _rate(gs, "semantic")
        cov = sum(1 for g in gs if g["exact"] or g["semantic"])
        rows.append({"dataset": dataset, "layer": layer, "subset": subset, "gold": en,
                     "exact_n": ec, "exact_pct": ep, "semantic_n": sc, "semantic_pct": sp,
                     "covered_pct": round(100 * cov / en, 1) if en else 0.0})
    return rows


def normalization_test(embedder=None):
    """Sayfullina synonym-normalization: within each reference cluster, of the phrasings the KB
    contains, do they resolve to the SAME KB node? Returns (summary dict, per-cluster rows) or None."""
    clusters = D.load_sayfullina_clusters()
    if not clusters:
        return None
    idx = _index("en")
    kb = _kb_labels("en")
    kb_uids = [u for u, _ in kb]
    kb_texts = [t for _, t in kb]

    # Resolve every distinct cluster term once (exact -> semantic fallback).
    terms = sorted({t for ts in clusters.values() for t in ts})
    resolved = {}
    for t in terms:
        resolved[t] = idx.get(ev.match_key(t), "")
    if embedder is not None and embedder.mode == "st":
        need = [t for t in terms if not resolved[t]]
        if need:
            scores, idxs = _semantic_nearest(embedder, need, kb_texts)
            for i, t in enumerate(need):
                if float(scores[i]) >= C.VALIDATION_SEMANTIC_MIN:
                    resolved[t] = kb_uids[int(idxs[i])]

    rows = []
    n_eval = n_collapsed = 0
    for cid, ts in clusters.items():
        present = [resolved[t] for t in ts if resolved.get(t)]
        distinct = set(present)
        if len(present) >= 2:
            n_eval += 1
            collapsed = len(distinct) == 1
            n_collapsed += int(collapsed)
            rows.append({"cluster_id": cid, "cluster_size": len(ts), "resolved": len(present),
                         "distinct_kb_nodes": len(distinct), "collapsed": collapsed,
                         "example": ts[0]})
    summary = {"clusters_total": len(clusters), "clusters_evaluable": n_eval,
               "clusters_collapsed": n_collapsed,
               "collapse_rate_pct": round(100 * n_collapsed / n_eval, 1) if n_eval else 0.0}
    return summary, rows
