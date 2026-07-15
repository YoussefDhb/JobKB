
# shared foundation for the JobKB pipeline

from __future__ import annotations
import csv
import datetime as _dt
import hashlib
import os
import unicodedata as _ud

csv.field_size_limit(10_000_000)


# defining paths

SRC_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(SRC_DIR)
DATASETS = os.path.join(ROOT, "Datasets")
ESCO_DIR = os.path.join(DATASETS, "ESCO")
ISCO_DIR = os.path.join(DATASETS, "ISCO")
ROME_DIR = os.path.join(DATASETS, "ROME")
CANONICAL_DIR = os.path.join(ROOT, "canonical")
SCRAPED_DIR   = os.path.join(ROOT, "scraped")
LLM_IO_DIR    = os.path.join(ROOT, "llm_io")
PROMPT_DIR    = os.path.join(LLM_IO_DIR, "prompts")
RESPONSE_DIR  = os.path.join(LLM_IO_DIR, "responses")

OCCUPATIONS_CSV = os.path.join(CANONICAL_DIR, "occupations.csv")
SKILLS_CSV = os.path.join(CANONICAL_DIR, "skills.csv")
LABELS_CSV = os.path.join(CANONICAL_DIR, "labels.csv")
OCC_SKILL_REL_CSV = os.path.join(CANONICAL_DIR, "occupation_skill_relations.csv")
HIERARCHY_CSV = os.path.join(CANONICAL_DIR, "hierarchy.csv")
ALIGNMENTS_CSV = os.path.join(CANONICAL_DIR, "concept_alignments.csv")
PROVENANCE_CSV = os.path.join(CANONICAL_DIR, "provenance.csv")


TRANSLATION_SUGGESTIONS_CSV = os.path.join(CANONICAL_DIR, "translation_suggestions.csv")

ALIGNMENT_REVIEW_CSV   = os.path.join(CANONICAL_DIR, "alignment_review.csv")
REVIEW_TRANSLATED_CSV  = os.path.join(SCRAPED_DIR, "review_translated.csv")

# canonical schema

OCCUPATION_FIELDS = [
    "entity_id", "source", "source_id", "isco_code",
    "pref_label_fr", "pref_label_en", "alt_labels_fr", "alt_labels_en",
    "description_fr", "description_en", "occupation_type", "label_language_status",
]
SKILL_FIELDS = [
    "entity_id", "source", "source_id",
    "pref_label_fr", "pref_label_en", "alt_labels_fr", "alt_labels_en",
    "description_fr", "description_en",
    "esco_skill_type", "esco_reuse_level", "hard_soft_provisional", "hard_soft_method",
]
LABEL_FIELDS = [
    "entity_id", "entity_kind", "label_text", "label_norm",
    "label_type", "language", "source",
]
REL_FIELDS = ["occupation_entity_id", "skill_entity_id", "relation_type", "source"]
HIERARCHY_FIELDS = ["parent_entity_id", "child_entity_id", "entity_kind", "relation_type", "source"]
ALIGNMENT_FIELDS = [
    "entity_id_a", "source_a", "entity_id_b", "source_b",
    "relation", "confidence", "method", "validated", "notes",
]
PROVENANCE_FIELDS = [
    "entity_id", "source", "source_version", "retrieved_at", "retrieval_method", "notes",
]


# IT-domain scope

ISCO_UNIT_GROUPS_IN_SCOPE = {
    "2511": "Analystes de systemes",
    "2512": "Concepteurs de logiciels",
    "2513": "Concepteurs de sites internet et d'outils multimedias",
    "2514": "Programmeurs d'applications",
    "2519": "Concepteurs et analystes de logiciels, et concepteurs de multimedia n.c.a.",
    "2521": "Concepteurs et administrateurs de bases de donnees",
    "2522": "Administrateurs de systemes",
    "2523": "Ingenieurs et specialistes des reseaux informatiques",
    "2529": "Ingenieurs et specialistes des bases de donnees et des reseaux n.c.a.",
    "3511": "Techniciens TIC, maintenance",
    "3512": "Techniciens TIC, assistance aux utilisateurs",
    "3513": "Techniciens, reseaux et systemes informatiques",
    "3514": "Techniciens de l'internet",
}
ROME_DOMAIN_IN_SCOPE = "M18"  # Systemes d'information et de telecommunication



# ------------------------------------------------------------------------------------------------------------------------

# predefined functions for standardized processing

def ensure_dirs():
    os.makedirs(CANONICAL_DIR, exist_ok=True)


# Generating a unique identifier (ID) based on a given prefix, source, and source_id.
# The same input will always produce the same ID, which is useful for maintaining consistency across different runs and versions of datasets.
def mint_id(prefix: str, source: str, source_id: str) -> str:
    h = hashlib.sha1(f"{source}|{source_id}".encode("utf-8")).hexdigest()[:12]
    return f"{prefix}{h}"


# This function normalizes a given text label by performing several transformations to ensure that different variations of the same label are treated as equivalent.
# exp: 'Developpeur', 'developpeur', ' DEVELOPPEUR ' -> one shared key
# Useful for creating a consistent representation of labels in datasets.

def normalize_label(text: str) -> str:
    if not text:
        return ""
    # unify apostrophe/quote variants to a straight apostrophe (kept: tokens stay meaningful)
    t = text.replace("\u2019", "'").replace("\u2018", "'").replace("`", "'").replace("\u00b4", "'")
    # unify dash variants to a space
    for d in ("\u2011", "\u2013", "\u2014", "\u2212"):
        t = t.replace(d, " ")
    # expand common French ligatures BEFORE the ascii fold (else they'd be dropped)
    t = (t.replace("\u0153", "oe").replace("\u0152", "OE")
           .replace("\u00e6", "ae").replace("\u00c6", "AE"))
    # NFKD accent strip
    t = _ud.normalize("NFKD", t).encode("ascii", "ignore").decode("ascii")
    return " ".join(t.casefold().split())


# Constructing a list of label rows for a given entity (occupation or skill) based on its preferred, alternative, and hidden labels in various languages.
def make_label_rows(entity_id, entity_kind, source, preferred=None, alts=None, hidden=None):
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


def _read_all(path):
    if not os.path.isfile(path):
        return []
    with open(path, encoding="utf-8") as f:
        return list(csv.DictReader(f))


# Write a list of dicts to a CSV file. Missing fields are filled with empty strings.
def _write_all(path, fieldnames, rows):
    ensure_dirs()
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in fieldnames})


# if a source is reprocessed, we want to replace its rows in the canonical CSV with the new ones, rather than appending duplicates.
def replace_source_rows(path, fieldnames, source, new_rows):
    existing = _read_all(path)
    kept = [r for r in existing if r.get("source") != source]
    _write_all(path, fieldnames, kept + new_rows)


def write_csv(path, fieldnames, rows):
    _write_all(path, fieldnames, rows)


# Return current UTC time in ISO 8601 format
# for logging the retrieval time of datasets, ensuring that the timestamp is in a standardized format.
def now_iso():
    return _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds")


# log provenance of a source dataset version, for traceability
def log_provenance(source, rows):
    replace_source_rows(PROVENANCE_CSV, PROVENANCE_FIELDS, source, rows)


# Read a CSV file with automatic encoding detection.
def read_csv_smart(path, prefer_encodings=("utf-8-sig", "cp1252", "latin-1"), sep=None):
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


# Extract the last segment of a URI, often used to get the unique identifier or name from a full URI.
def uri_tail(uri: str) -> str:
    return uri.rsplit("/", 1)[-1] if uri else uri
