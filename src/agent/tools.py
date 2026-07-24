"""The agent's toolbox — thin wrappers over the KB's existing, hardened primitives.
"""

from __future__ import annotations

import numpy as np

from .. import config as C
from .. import common as K


class Toolbox:
    """Lazily-constructed, run-scoped holder for the shared models + KB snapshot."""

    def __init__(self):
        self._client = None
        self._validator = None
        self._embedder = None
        self._skl_raw = None
        self._skl_vecs = None
        self._by_lbl = None
        self._id2vec = None
        from .. import llm
        self._llm = llm
        self.snap = llm._load_snapshot()   # the shared generations.csv cache (agent shares it with llm)

    # ---- generative tool (optional; dead-credit safe) ---------------------------------------
    @property
    def client(self):
        if self._client is None:
            self._client = self._llm.LLMClient()
        return self._client

    @property
    def has_llm(self) -> bool:
        """True only if a generative backend actually came up (API alive or local loaded)."""
        return self.client.ok

    def generate(self, system: str, user: str):
        return self.client.chat(system, user)

    # ---- validation tools (NLI) -------------------------------------------------------------
    @property
    def validator(self):
        if self._validator is None:
            self._validator = self._llm.Validator()
        return self._validator

    def check_description(self, task, uid, label, desc):
        """(ok, score) via length + NLI; logs the reject on the shared validator."""
        return self.validator.check_description(task, uid, label, desc)

    def nli(self, premise: str, hypothesis: str) -> float | None:
        """Entailment prob of `hypothesis` given `premise`, or None if NLI is unavailable."""
        v = self.validator
        if not v.nli_ok or not premise or not hypothesis:
            return None
        s = v.v.entail_batch([(premise, hypothesis)])[0]
        return s

    # ---- retrieval tool (bge-m3 shortlist over the existing skill vocabulary) ----------------
    def _ensure_skill_index(self):
        if self._skl_raw is not None:
            return
        from ..align import candidates as cand
        self._embedder = cand.get_embedder()
        _occ, skl_raw = cand.load_entities()
        skl_raw = [s for s in skl_raw if s.get("esco_skill_type") != "skill_category"
                   and (s.get("pref_label_en") or "").strip()]
        self._skl_raw = skl_raw
        self._skl_vecs = np.asarray(cand.encode_cached(self._embedder, [cand.entity_text(s) for s in skl_raw]))
        self._by_lbl = {s["pref_label_en"]: s for s in skl_raw}
        self._id2vec = {skl_raw[i]["entity_id"]: self._skl_vecs[i] for i in range(len(skl_raw))}

    def occ_vector(self, occ_row):
        self._ensure_skill_index()
        from ..align import candidates as cand
        return np.asarray(self._embedder.encode([cand.entity_text(occ_row)]))[0]

    def shortlist(self, occ_vec, start: int, k: int):
        """Skills ranked `start..start+k` by cosine to `occ_vec`. Widening `start` on reflect surfaces
        fresh candidates instead of re-proposing the same rejected top-k."""
        self._ensure_skill_index()
        sims = self._skl_vecs @ occ_vec
        order = np.argsort(-sims)[start:start + k]
        return [self._skl_raw[i] for i in order]

    def cosine(self, skill_id: str, occ_vec) -> float:
        self._ensure_skill_index()
        return float(self._id2vec[skill_id] @ occ_vec)

    def skill_by_label(self, label: str):
        self._ensure_skill_index()
        return self._by_lbl.get(label)

    # ---- persistence ------------------------------------------------------------------------
    def commit_generation(self, task: str, key: str, output: str, prompt_hash: str = "") -> None:
        """Write an accepted generation to the shared snapshot, tagged as agent-produced."""
        self.snap[(task, key)] = {"task": task, "key": key, "model": C.AGENT_TAG,
                                  "prompt_hash": prompt_hash, "output": output,
                                  "created_at": K.now_iso()}

    def save(self) -> None:
        self._llm._save_snapshot(self.snap)
        if self._validator is not None:
            self._validator.dump_rejects()
