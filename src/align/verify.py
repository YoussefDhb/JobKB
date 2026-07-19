"""HF verification of candidate pairs — the automatic replacement for the old
manual `gold` review.

Design (calibrated against real data): embedding similarity and NLI are noisy for
deciding *identity* (e.g. "software developer" ~ "web developer" ≈ 0.88), so they
drive the softer `closeMatch` / `relatedMatch` links (which still feed ISCO
grafting). `exactMatch` — the signal the unified merge consumes — is grounded on
**label identity across sources** (preferred + alternative labels, normalized and
singularized), which is high precision. Every accepted pair is validated
automatically ("auto"); no human labeling.
"""

from __future__ import annotations
import re

from .. import config as C
from .. import common as K

_TRAILING_S = re.compile(r"s$")
_PAREN = re.compile(r"\s*\([^)]*\)\s*$")  # trailing "(computer programming)" etc.


def _key(label):
    norm = K.normalize_label(_PAREN.sub("", label or ""))
    if not norm:
        return ""
    return " ".join(_TRAILING_S.sub("", tok) for tok in norm.split())


def _pref_keys(row):
    """Preferred-label keys only — the high-precision identity signal used to merge.

    Alt-label overlap is deliberately excluded here: distinct occupations often share
    an alternative label, and clustering on that transitively merges unrelated concepts.
    """
    return {k for k in (_key(row.get("pref_label_en")), _key(row.get("pref_label_fr"))) if k}


def _label_keys(row):
    """All labels (pref + alt) — a softer corroboration signal (closeMatch, not merge)."""
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

    def entail(self, premise, hypothesis):
        if not self.nli_ok or not premise or not hypothesis:
            return None
        try:
            out = self._pipe({"text": premise[:600], "text_pair": hypothesis[:600]})
            scores = {d["label"].lower(): d["score"] for d in out}
            return scores.get("entailment")
        except Exception:
            return None


def _desc(row):
    return row.get("description_en") or row.get("description_fr") or ""


def _label(row):
    return row.get("pref_label_en") or row.get("pref_label_fr") or ""


def verify_pairs(pairs, verifier, use_nli):
    rows = []
    for ra, rb, sim in pairs:
        pref_match = bool(_pref_keys(ra) & _pref_keys(rb))
        alt_match = bool(_label_keys(ra) & _label_keys(rb))
        conf = float(sim)
        method = f"embed:{sim:.2f}"

        if use_nli and verifier.nli_ok:
            ea = verifier.entail(_desc(ra), _desc(rb))
            eb = verifier.entail(_desc(rb), _desc(ra))
            if ea is not None and eb is not None:
                m = min(ea, eb)
                if m >= C.NLI_ENTAIL_MIN:
                    conf = max(conf, 0.60 + 0.30 * m)  # boost, capped ~0.90
                    method += f"+nli:{m:.2f}"

        if pref_match:
            conf = max(conf, 0.95)
            relation = "skos:exactMatch"          # this is what the unified merge consumes
            method = "pref_match+" + method
        elif alt_match:
            conf = max(conf, 0.85)
            relation = "skos:closeMatch"          # shared alt label -> related, not merged
            method = "alt_match+" + method
        elif conf >= C.SKOS_CLOSE_MIN:
            relation = "skos:closeMatch"
        else:
            relation = "skos:relatedMatch"

        rows.append({
            "entity_id_a": ra["entity_id"], "source_a": ra["source"],
            "entity_id_b": rb["entity_id"], "source_b": rb["source"],
            "relation": relation, "confidence": round(conf, 4),
            "method": method, "validated": "auto",
            "notes": f"{_label(ra)} <> {_label(rb)}",
        })
    return rows
