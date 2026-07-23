"""Shared helpers for the JobKB pipeline (migrated from the old jobkb_common.py).

Deterministic IDs, label normalization, idempotent CSV IO, provenance logging.
"""

from __future__ import annotations
import csv
import datetime as _dt
import hashlib
import os
import unicodedata as _ud

from . import config as C

csv.field_size_limit(10_000_000)


def ensure_dirs():
    os.makedirs(C.KB_DIR, exist_ok=True)


def mint_id(prefix: str, source: str, source_id: str) -> str:
    """Deterministic id: same (source, source_id) always yields the same id."""
    h = hashlib.sha1(f"{source}|{source_id}".encode("utf-8")).hexdigest()[:12]
    return f"{prefix}{h}"


def normalize_label(text: str) -> str:
    """Fold a label to a comparison key (accents/case/ligatures/dashes/quotes)."""
    if not text:
        return ""
    t = text.replace("’", "'").replace("‘", "'").replace("`", "'").replace("´", "'")
    for d in ("‑", "–", "—", "−"):
        t = t.replace(d, " ")
    # expand ligatures before the ascii fold (else they'd be dropped)
    t = (t.replace("œ", "oe").replace("Œ", "OE")
           .replace("æ", "ae").replace("Æ", "AE"))
    t = _ud.normalize("NFKD", t).encode("ascii", "ignore").decode("ascii")
    return " ".join(t.casefold().split())


def make_label_rows(entity_id, entity_kind, source, preferred=None, alts=None, hidden=None):
    """Build dedup'd label rows for an entity across languages/types."""
    rows, seen = [], set()

    def add(text, ltype, lang):
        text = (text or "").strip()
        if not text:
            return
        norm = normalize_label(text)
        key = (norm, ltype, lang)
        if key in seen:
            return
        seen.add(key)
        rows.append({
            "entity_id": entity_id, "entity_kind": entity_kind,
            "label_text": text, "label_norm": norm,
            "label_type": ltype, "language": lang, "source": source,
        })

    for lang, forms in (preferred or {}).items():
        for f in forms:
            add(f, "preferred", lang)
    for lang, forms in (alts or {}).items():
        for f in forms:
            add(f, "alt", lang)
    for lang, forms in (hidden or {}).items():
        for f in forms:
            add(f, "hidden", lang)
    return rows


def split_multi(value: str):
    """Split ESCO-style newline/pipe-delimited multi-label fields into a clean list."""
    if not value:
        return []
    parts = []
    for chunk in str(value).replace("\r", "\n").split("\n"):
        for piece in chunk.split("|"):
            piece = piece.strip()
            if piece:
                parts.append(piece)
    # de-dup, preserve order
    seen, out = set(), []
    for p in parts:
        if p not in seen:
            seen.add(p)
            out.append(p)
    return out


def _read_all(path):
    if not os.path.isfile(path):
        return []
    with open(path, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _write_all(path, fieldnames, rows):
    ensure_dirs()
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in fieldnames})


def replace_source_rows(path, fieldnames, source, new_rows):
    """Idempotent per-source write: drop this source's old rows, keep others, append new.

    Fully-identical duplicate rows within this source's contribution are collapsed (hygiene): a
    source occasionally emits the same relation/edge twice (e.g. a skill reached via two O*NET
    elements), and identical rows carry no extra information. Order-preserving; a no-op for entity
    tables where `entity_id` already makes every row unique.
    """
    existing = _read_all(path)
    kept = [r for r in existing if r.get("source") != source]
    seen, deduped = set(), []
    for r in new_rows:
        key = tuple(r.get(f) for f in fieldnames)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(r)
    _write_all(path, fieldnames, kept + deduped)


def write_csv(path, fieldnames, rows):
    _write_all(path, fieldnames, rows)


def upsert_labels(rows):
    """Additive, idempotent label write. Several stages contribute labels for the
    same source, so we merge on the full identity key instead of replacing by source."""
    existing = _read_all(C.LABELS_CSV)
    seen, out = set(), []
    for r in existing + list(rows):
        key = (r.get("entity_id"), r.get("label_norm"), r.get("label_type"),
               r.get("language"), r.get("source"))
        if key in seen:
            continue
        seen.add(key)
        out.append(r)
    _write_all(C.LABELS_CSV, C.LABEL_FIELDS, out)


def read_all(path):
    return _read_all(path)


def now_iso():
    return _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds")


def log_provenance(source, rows):
    replace_source_rows(C.PROVENANCE_CSV, C.PROVENANCE_FIELDS, source, rows)


def read_csv_smart(path, prefer_encodings=("utf-8-sig", "cp1252", "latin-1"), sep=None):
    """Read a CSV with encoding + separator autodetection into a pandas DataFrame (str)."""
    import pandas as pd
    last_err = None
    for enc in prefer_encodings:
        try:
            if sep is None:
                with open(path, encoding=enc) as f:
                    head = f.readline()
                use_sep = ";" if head.count(";") > head.count(",") else ","
            else:
                use_sep = sep
            df = pd.read_csv(path, encoding=enc, sep=use_sep, dtype=str,
                             keep_default_na=False, na_filter=False)
            return df
        except (UnicodeDecodeError, UnicodeError) as e:
            last_err = e
            continue
    raise RuntimeError(f"Could not read {path} with {prefer_encodings}: {last_err}")


def uri_tail(uri: str) -> str:
    return uri.rsplit("/", 1)[-1] if uri else uri
