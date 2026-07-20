"""Embedding-based candidate generation across sources.

Loads a HuggingFace sentence-embedding model (bge-m3 -> MiniLM), or falls back to
a TF-IDF char n-gram vectorizer if neither is available, so candidate generation
always runs. Candidates are the top-k nearest neighbours between every pair of
distinct sources, above a recall-oriented cosine floor.

Embeddings are the whole runtime cost (bge-m3 on CPU), so computed vectors are cached
on disk keyed by (model_id, text). A threshold-only rebuild then reuses them and runs
in seconds instead of ~40 min; changing the embedding model invalidates the cache by key.
"""

from __future__ import annotations
import atexit
import os
import pickle

from .. import config as C
from .. import common as K


_SHARED_EMBEDDER = None
_VEC_CACHE = {}          # text -> vector (only populated in sentence-transformer mode)
_CACHE_PATH = None       # disk path for the current model's cache
_CACHE_DIRTY = False


def _load_disk_cache(model_id):
    """Load the on-disk vector cache for `model_id` into _VEC_CACHE (best-effort)."""
    global _CACHE_PATH
    _CACHE_PATH = os.path.join(C.KB_DIR, f".emb_cache_{model_id.replace('/', '_')}.pkl")
    try:
        if os.path.isfile(_CACHE_PATH):
            with open(_CACHE_PATH, "rb") as f:
                _VEC_CACHE.update(pickle.load(f))
    except Exception:
        pass
    atexit.register(_save_disk_cache)


def _save_disk_cache():
    if not _CACHE_DIRTY or not _CACHE_PATH:
        return
    try:
        os.makedirs(os.path.dirname(_CACHE_PATH), exist_ok=True)
        with open(_CACHE_PATH, "wb") as f:
            pickle.dump(_VEC_CACHE, f, protocol=pickle.HIGHEST_PROTOCOL)
    except Exception:
        pass


def get_embedder():
    """Process-wide singleton so bge-m3 is loaded once and shared by align + attach."""
    global _SHARED_EMBEDDER
    if _SHARED_EMBEDDER is None:
        _SHARED_EMBEDDER = Embedder()
        if _SHARED_EMBEDDER.mode == "st":
            _load_disk_cache(_SHARED_EMBEDDER.model_id)
    return _SHARED_EMBEDDER


def encode_cached(embedder, texts):
    """Encode `texts`, reusing previously computed vectors (st mode only).

    TF-IDF vectors are corpus-relative and cannot be cached across calls, so that mode
    just encodes directly. Returns a numpy array in st mode.
    """
    global _CACHE_DIRTY
    texts = list(texts)
    if embedder.mode != "st":
        return embedder.encode(texts)
    import numpy as np
    missing = list(dict.fromkeys(t for t in texts if t not in _VEC_CACHE))
    if missing:
        vecs = embedder.encode(missing)
        _CACHE_DIRTY = True
        for t, v in zip(missing, np.asarray(vecs)):
            _VEC_CACHE[t] = v
    return np.vstack([_VEC_CACHE[t] for t in texts])


def load_entities():
    """Return (occupations, skills) as lists of dicts, excluding ISCO group nodes."""
    occ = [r for r in K.read_all(C.OCCUPATIONS_CSV)
           if r.get("occupation_type") != "isco_group"]
    skl = [r for r in K.read_all(C.SKILLS_CSV)
           if r.get("esco_skill_type") not in ("skill_type", "skill_domain")]
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
        self.model_id = None
        # Use all CPU cores (torch is CPU-only here); helps the larger bge-m3.
        try:
            import os as _os
            import torch
            torch.set_num_threads(_os.cpu_count() or 1)
        except Exception:
            pass
        try:
            from sentence_transformers import SentenceTransformer
            for mid in (C.EMBED_MODEL_PRIMARY, C.EMBED_MODEL_FALLBACK):
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
            self.mode, self.model_id = "tfidf", "tfidf"
        print(f"[EMBED] model = {self.model_id} (mode={self.mode})")

    def encode(self, texts):
        if self.mode == "st":
            return self.model.encode(list(texts), normalize_embeddings=True,
                                     batch_size=C.EMBED_BATCH_SIZE, show_progress_bar=False)
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
    emb = encode_cached(embedder, texts)

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
