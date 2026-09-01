"""HF verification of candidate pairs."""

from __future__ import annotations
import re

from .. import config as C
from .. import common as K

_TRAILING_S = re.compile(r"s$")
_PAREN = re.compile(r"\s*\([^)]*\)\s*$")  


def _key(label):
    norm = K.normalize_label(_PAREN.sub("", label or ""))
    if not norm:
        return ""
    return " ".join(_TRAILING_S.sub("", tok) for tok in norm.split())


def _pref_keys(row):
    """Preferred-label keys only — the high-precision identity signal used to merge."""
    return {k for k in (_key(row.get("pref_label_en")), _key(row.get("pref_label_fr"))) if k}


def _label_keys(row):
    """All labels (pref + alt)."""
    keys = set()
    for field in (row.get("pref_label_en"), row.get("pref_label_fr"),
                  row.get("alt_labels_en"), row.get("alt_labels_fr")):
        for lbl in (field or "").split(" | "):
            k = _key(lbl)
            if k:
                keys.add(k)
    return keys


class Verifier:
    """Wraps the NLI model; disables itself gracefully if it can't be loaded."""

    def __init__(self):
        self.nli_ok = False
        self._pipe = None
        try:
            from transformers import pipeline
            self._pipe = pipeline("text-classification", model=C.NLI_MODEL,
                                  top_k=None, truncation=True, token=C.HF_TOKEN or None)
            self.nli_ok = True
        except Exception:
            self.nli_ok = False

    def entail_batch(self, texts):
        """Batched entailment."""
        if not self.nli_ok or not texts:
            return [None] * len(texts)
        try:
            inputs = [{"text": p[:600], "text_pair": h[:600]} for p, h in texts]
            outs = self._pipe(inputs, batch_size=C.NLI_BATCH_SIZE)
            res = []
            for o in outs:
                d = {x["label"].lower(): x["score"] for x in o}
                res.append(d.get("entailment"))
            return res
        except Exception:
            return [None] * len(texts)


def _desc(row):
    return row.get("description_en") or row.get("description_fr") or ""


def _label(row):
    return row.get("pref_label_en") or row.get("pref_label_fr") or ""


def verify_pairs(pairs, verifier, use_nli):
    # Pass 1: cheap signals + collect the NLI-eligible pairs (both directions) to batch.
    base = []
    nli_texts, nli_map = [], []
    for i, (ra, rb, sim) in enumerate(pairs):
        base.append({"ra": ra, "rb": rb, "sim": sim,
                     "pref": bool(_pref_keys(ra) & _pref_keys(rb)),
                     "alt": bool(_label_keys(ra) & _label_keys(rb)), "nli_m": None})
        if use_nli and verifier.nli_ok and sim >= C.NLI_MIN_SIM:
            da, db = _desc(ra), _desc(rb)
            if da and db:
                nli_map.append((i, "ab"))
                nli_texts.append((da, db))
                nli_map.append((i, "ba"))
                nli_texts.append((db, da))

    # Pass 2: one batched NLI inference for all eligible pairs.
    scores = verifier.entail_batch(nli_texts) if nli_texts else []
    partial = {}
    for (i, direction), s in zip(nli_map, scores):
        partial.setdefault(i, {})[direction] = s
    for i, d in partial.items():
        ea, eb = d.get("ab"), d.get("ba")
        if ea is not None and eb is not None:
            base[i]["nli_m"] = min(ea, eb)

    # Pass 3: assemble alignment rows.
    rows = []
    for b in base:
        ra, rb, sim = b["ra"], b["rb"], b["sim"]
        pref_match, alt_match, nli_m = b["pref"], b["alt"], b["nli_m"]
        conf = float(sim)
        method = f"embed:{sim:.2f}"
        if nli_m is not None and nli_m >= C.NLI_ENTAIL_MIN:
            conf = max(conf, 0.60 + 0.30 * nli_m)  
            method += f"+nli:{nli_m:.2f}"

        if pref_match:
            conf = max(conf, 0.95)
            relation = "skos:exactMatch"
            method = "pref_match+" + method
        elif alt_match:
            conf = max(conf, 0.85)
            relation = "skos:closeMatch"          
            method = "alt_match+" + method
        elif conf >= C.SKOS_CLOSE_MIN:
            relation = "skos:closeMatch"
        else:
            relation = "skos:relatedMatch"

        # Source-neutral MERGE decision (what the unified merge consumes).
        floor = C.MERGE_EMBED_OCC if use_nli else C.MERGE_EMBED_SKILL
        if pref_match:
            do_merge = "label"
        elif sim >= floor:
            nli_gate = use_nli and verifier.nli_ok
            if nli_gate and _desc(ra) and _desc(rb):
                do_merge = "semantic" if (nli_m is not None and nli_m >= C.NLI_ENTAIL_MIN) else ""
            else:
                do_merge = "semantic"
        else:
            do_merge = ""

        rows.append({
            "entity_id_a": ra["entity_id"], "source_a": ra["source"],
            "entity_id_b": rb["entity_id"], "source_b": rb["source"],
            "relation": relation, "confidence": round(conf, 4),
            "method": method, "validated": "auto", "merge": do_merge,
            "notes": f"{_label(ra)} <> {_label(rb)}",
        })
    return rows
