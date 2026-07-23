"""Readers for the three expert-annotated validation corpora (`resources/validation/`).

All three are BIO/IOB token-tagged NER CSVs (one sentence per row; `tokens` and `tags_*` are
stringified Python lists). We do not train anything, so we pool all splits and extract the annotated
skill-mention *surface strings* — the gold set our KB vocabulary is measured against.

- SkillSpan : `tags_skill` + `tags_knowledge` layers, `source` in {tech (StackOverflow/IT), house}.
- Sayfullina: `tags_skill` (soft only); plus an optional external synonym-cluster reference list.
- FIJO      : `tags_skill` with 4 French competency families (RELATIONNEL/PENSEE/PERSONNEL/RESULTATS).
"""

from __future__ import annotations

import ast
import csv
import os

from .. import config as C

_ANON = set(C.VALIDATION_ANON_TOKENS)


def _spans_from_bio(tokens, tags):
    """Walk BIO tags; yield (surface_string, span_type). Anonymization tokens are dropped; a span that
    is empty after dropping them is discarded."""
    spans, cur, cur_type = [], [], None
    for tok, tag in zip(tokens, tags):
        prefix = tag[0] if tag else "O"
        typ = tag.split("-", 1)[1] if "-" in tag else ""
        if prefix == "B":
            if cur:
                spans.append((cur, cur_type))
            cur, cur_type = [tok], typ
        elif prefix == "I" and cur:
            cur.append(tok)
        else:  # O (or a stray I with no open span)
            if cur:
                spans.append((cur, cur_type))
            cur, cur_type = [], None
    if cur:
        spans.append((cur, cur_type))
    out = []
    for toks, typ in spans:
        kept = [t for t in toks if t.lower() not in _ANON]
        surface = " ".join(kept).strip()
        if surface:
            out.append((surface, typ))
    return out


def _read_rows(dataset):
    subdir, splits, _has_k, _has_src, _lang = C.VALIDATION_DATASETS[dataset]
    for split in splits:
        path = os.path.join(C.VALIDATION_RES_DIR, subdir, f"{dataset}_{split}.csv")
        if not os.path.isfile(path):
            continue
        with open(path, encoding="utf-8", newline="") as fh:
            for r in csv.DictReader(fh):
                yield split, r


def gold_mentions(dataset):
    """Pool all splits; return a list of dicts: {surface, layer, subset, category, language}.

    `layer` in {skill, knowledge}; `subset` in {tech, house, ""}; `category` = the typed span label
    (e.g. FIJO family) when present. Duplicates are preserved here (frequency is informative); callers
    that want the unique gold set dedup on the normalized surface."""
    _subdir, _splits, has_k, has_src, lang = C.VALIDATION_DATASETS[dataset]
    rows = []
    for _split, r in _read_rows(dataset):
        try:
            tokens = ast.literal_eval(r["tokens"])
        except (ValueError, SyntaxError):
            continue
        subset = (r.get("source") or "") if has_src else ""
        layers = [("skill", "tags_skill")] + ([("knowledge", "tags_knowledge")] if has_k else [])
        for layer, col in layers:
            raw = r.get(col)
            if not raw:
                continue
            try:
                tags = ast.literal_eval(raw)
            except (ValueError, SyntaxError):
                continue
            for surface, typ in _spans_from_bio(tokens, tags):
                rows.append({"surface": surface, "layer": layer, "subset": subset,
                             "category": typ, "language": lang})
    return rows


def load_sayfullina_clusters():
    """Load the external Sayfullina synonym-cluster reference list if it was fetched.

    Expected shape at SAYFULLINA_CLUSTERS_CSV: columns `cluster_id, term` (one term per row), or
    `cluster_id, terms` (terms ' | '-joined). Returns {cluster_id: [terms]} or {} if absent (the
    coverage track then runs corpus-only for Sayfullina)."""
    path = C.SAYFULLINA_CLUSTERS_CSV
    if not os.path.isfile(path):
        return {}
    clusters = {}
    with open(path, encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        cols = [c.lower() for c in (reader.fieldnames or [])]
        for r in reader:
            low = {k.lower(): v for k, v in r.items()}
            cid = (low.get("cluster_id") or low.get("cluster") or low.get("id") or "").strip()
            if "terms" in cols:
                terms = [t.strip() for t in (low.get("terms") or "").split(" | ") if t.strip()]
            else:
                terms = [t for t in [(low.get("term") or low.get("skill") or "").strip()] if t]
            if not cid or not terms:
                continue
            clusters.setdefault(cid, [])
            for t in terms:
                if t not in clusters[cid]:
                    clusters[cid].append(t)
    return clusters
