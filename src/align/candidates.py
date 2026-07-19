"""Embedding-based candidate generation across sources.

Loads a HuggingFace sentence-embedding model (nomic -> MiniLM), or falls back to
a TF-IDF char n-gram vectorizer if neither is available, so candidate generation
always runs. Candidates are the top-k nearest neighbours between every pair of
distinct sources, above a recall-oriented cosine floor.
"""

from __future__ import annotations

from .. import config as C
from .. import common as K


def load_entities():
    """Return (occupations, skills) as lists of dicts, excluding ISCO group nodes."""
    occ = [r for r in K.read_all(C.OCCUPATIONS_CSV)
           if r.get("occupation_type") != "isco_group"]
    skl = [r for r in K.read_all(C.SKILLS_CSV)
           if r.get("hard_soft_provisional") != "group"]
    return occ, skl


def entity_text(row):
    """Representative text for embedding: primary label (+ alts + short description)."""
    label = row.get("pref_label_en") or row.get("pref_label_fr") or ""
    alts = (row.get("alt_labels_en") or row.get("alt_labels_fr") or "").replace(" | ", ", ")
    desc = (row.get("description_en") or row.get("description_fr") or "")[:300]
    parts = [p for p in (label, alts, desc) if p]
    return ". ".join(parts)


class Embedder:
    def __init__(self):
        self.mode = None
        self.model = None
        candidates = []
        try:
            import einops  # noqa: F401  (nomic-embed-v2-moe requires it)
            candidates.append(C.EMBED_MODEL_PRIMARY)
        except Exception:
            pass
        candidates.append(C.EMBED_MODEL_FALLBACK)
        try:
            from sentence_transformers import SentenceTransformer
            for mid in candidates:
                try:
                    self.model = SentenceTransformer(mid, trust_remote_code=True,
                                                     token=C.HF_TOKEN or None)
                    self.mode, self.model_id = "st", mid
                    break
                except Exception:
                    continue
        except Exception:
            pass
        if self.mode is None:
            self.mode = "tfidf"

    def encode(self, texts):
        if self.mode == "st":
            return self.model.encode(list(texts), normalize_embeddings=True,
                                     show_progress_bar=False)
        from sklearn.feature_extraction.text import TfidfVectorizer
        vec = TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5), min_df=1)
        return vec.fit_transform([K.normalize_label(t) for t in texts])


def candidate_pairs(entities, embedder, topk=None, threshold=None):
    """Top-k cross-source neighbour pairs above the cosine threshold.

    Returns list of (row_a, row_b, cosine) with source_a != source_b, de-duplicated
    per unordered entity pair (highest similarity kept).
    """
    if not entities:
        return []
    topk = topk or C.EMBED_TOPK
    threshold = threshold if threshold is not None else C.EMBED_THRESHOLD

    from sklearn.metrics.pairwise import cosine_similarity
    import numpy as np

    texts = [entity_text(r) for r in entities]
    emb = embedder.encode(texts)

    # group row indices by source
    by_source = {}
    for i, r in enumerate(entities):
        by_source.setdefault(r["source"], []).append(i)
    sources = sorted(by_source)

    best = {}  # frozenset(eid_a, eid_b) -> (row_a, row_b, sim)
    for si in range(len(sources)):
        for sj in range(si + 1, len(sources)):
            idx_a = by_source[sources[si]]
            idx_b = by_source[sources[sj]]
            sub_a = emb[idx_a]
            sub_b = emb[idx_b]
            sim = cosine_similarity(sub_a, sub_b)  # (|a|, |b|)
            k = min(topk, len(idx_b))
            # top-k of b for each a, and top-k of a for each b (symmetric recall)
            for ai in range(sim.shape[0]):
                order = np.argsort(-sim[ai])[:k]
                for bj in order:
                    s = float(sim[ai, bj])
                    if s >= threshold:
                        _keep(best, entities[idx_a[ai]], entities[idx_b[bj]], s)
            kk = min(topk, len(idx_a))
            for bj in range(sim.shape[1]):
                order = np.argsort(-sim[:, bj])[:kk]
                for ai in order:
                    s = float(sim[ai, bj])
                    if s >= threshold:
                        _keep(best, entities[idx_a[ai]], entities[idx_b[bj]], s)
    return list(best.values())


def _keep(best, ra, rb, sim):
    key = frozenset((ra["entity_id"], rb["entity_id"]))
    prev = best.get(key)
    if prev is None or sim > prev[2]:
        best[key] = (ra, rb, sim)
