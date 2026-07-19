"""Central configuration for the JobKB pipeline.

English-primary, local-sources-only, IT-focused. This module is a leaf (no imports
from the rest of the package) so every stage can rely on it.
"""

from __future__ import annotations
import os

# --------------------------------------------------------------------------------------
# Paths
# --------------------------------------------------------------------------------------

SRC_DIR = os.path.dirname(os.path.abspath(__file__))      # .../src
ROOT = os.path.dirname(SRC_DIR)                            # project root
RESOURCES = os.path.join(ROOT, "resources")               # raw input taxonomies


# --------------------------------------------------------------------------------------
# .env loading (no external dependency)
# --------------------------------------------------------------------------------------

def _load_dotenv(path=os.path.join(ROOT, ".env")):
    """Populate os.environ from a project-root .env (KEY=VALUE per line).

    Runs at import so any HuggingFace call later in the process is authenticated.
    Does not override variables already set in the real environment.
    """
    if not os.path.isfile(path):
        return
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            key, value = key.strip(), value.strip().strip('"').strip("'")
            if key and key not in os.environ:
                os.environ[key] = value


_load_dotenv()

# HuggingFace reads either name; mirror the token so both work.
HF_TOKEN = os.environ.get("HF_TOKEN") or os.environ.get("HUGGINGFACE_HUB_TOKEN") or ""
if HF_TOKEN:
    os.environ.setdefault("HF_TOKEN", HF_TOKEN)
    os.environ.setdefault("HUGGINGFACE_HUB_TOKEN", HF_TOKEN)

ESCO_EN_DIR = os.path.join(RESOURCES, "ESCO", "en")
ESCO_FR_DIR = os.path.join(RESOURCES, "ESCO", "fr")
ISCO_EN_DIR = os.path.join(RESOURCES, "ISCO", "en")
ONET_EN_DIR = os.path.join(RESOURCES, "ONET", "en")
NOC_EN_DIR = os.path.join(RESOURCES, "NOC", "en")
NOC_FR_DIR = os.path.join(RESOURCES, "NOC", "fr")
ROME_FR_DIR = os.path.join(RESOURCES, "ROME", "fr")

KB_DIR = os.path.join(ROOT, "kb")   # built knowledge base output

OCCUPATIONS_CSV = os.path.join(KB_DIR, "occupations.csv")
SKILLS_CSV = os.path.join(KB_DIR, "skills.csv")
LABELS_CSV = os.path.join(KB_DIR, "labels.csv")
OCC_SKILL_REL_CSV = os.path.join(KB_DIR, "occupation_skill_relations.csv")
HIERARCHY_CSV = os.path.join(KB_DIR, "hierarchy.csv")
ALIGNMENTS_CSV = os.path.join(KB_DIR, "concept_alignments.csv")
UNIFIED_OCCUPATIONS_CSV = os.path.join(KB_DIR, "unified_occupations.csv")
UNIFIED_SKILLS_CSV = os.path.join(KB_DIR, "unified_skills.csv")
PROVENANCE_CSV = os.path.join(KB_DIR, "provenance.csv")

# --------------------------------------------------------------------------------------
# Knowledge-base schema (English-primary; French secondary when present)
# --------------------------------------------------------------------------------------

OCCUPATION_FIELDS = [
    "entity_id", "source", "source_id", "isco_code", "source_code",
    "pref_label_en", "pref_label_fr", "alt_labels_en", "alt_labels_fr",
    "description_en", "description_fr", "occupation_type", "label_language_status",
]
SKILL_FIELDS = [
    "entity_id", "source", "source_id",
    "pref_label_en", "pref_label_fr", "alt_labels_en", "alt_labels_fr",
    "description_en", "description_fr",
    "esco_skill_type", "esco_reuse_level",
    "hard_soft_provisional", "hard_soft_method", "it_subtype",
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
UNIFIED_OCC_FIELDS = [
    "unified_id", "primary_label_en", "primary_label_fr",
    "alt_labels_en", "alt_labels_fr", "isco_code",
    "occupation_type", "sources", "member_entity_ids",
]
UNIFIED_SKILL_FIELDS = [
    "unified_id", "primary_label_en", "primary_label_fr",
    "alt_labels_en", "alt_labels_fr", "hard_soft", "it_subtype",
    "sources", "member_entity_ids",
]
PROVENANCE_FIELDS = [
    "entity_id", "source", "source_version", "retrieved_at", "retrieval_method", "notes",
]

# --------------------------------------------------------------------------------------
# IT-domain scope per source
# --------------------------------------------------------------------------------------

# ISCO-08 sub-major groups 25 (ICT professionals) and 35 (ICT technicians) are
# entirely IT, so a code starting with "25" or "35" is in scope.
ISCO_IT_SUBMAJORS = ("25", "35")

# English labels for the IT unit groups (used to name minted ISCO nodes and as a
# stable in-scope reference set).
ISCO_IT_UNIT_GROUPS = {
    "2511": "Systems analysts",
    "2512": "Software developers",
    "2513": "Web and multimedia developers",
    "2514": "Applications programmers",
    "2519": "Software and applications developers and analysts not elsewhere classified",
    "2521": "Database designers and administrators",
    "2522": "Systems administrators",
    "2523": "Computer network professionals",
    "2529": "Database and network professionals not elsewhere classified",
    "3511": "Information and communications technology operations technicians",
    "3512": "Information and communications technology user support technicians",
    "3513": "Computer network and systems technicians",
    "3514": "Web technicians",
    "3521": "Broadcasting and audiovisual technicians",
    "3522": "Telecommunications engineering technicians",
}


def is_isco_it(code: str) -> bool:
    """True if a (bare) ISCO-08 code is within the IT sub-major branches."""
    code = (code or "").strip()
    return code.startswith(ISCO_IT_SUBMAJORS)


# ONET: Computer occupations (SOC 15-12xx) plus Data Scientists (15-2051).
ONET_IT_SOC_PREFIXES = ("15-12",)
ONET_IT_SOC_EXTRA = {"15-2051"}


def is_onet_it(onet_soc_code: str) -> bool:
    """O*NET-SOC codes look like '15-1252.00'; the SOC-2018 stem is the first 7 chars."""
    soc = (onet_soc_code or "").strip()[:7]
    return soc.startswith(ONET_IT_SOC_PREFIXES) or soc in ONET_IT_SOC_EXTRA


# NOC 2021 (5-digit): computer/software professionals & developers (minors 2122, 2123),
# plus specific unit groups for managers, data scientists, computer engineers, technicians.
NOC_IT_MINOR_PREFIXES = ("2122", "2123")
NOC_IT_UNIT_GROUPS = {
    "20012",  # Computer and information systems managers
    "21211",  # Data scientists
    "21311",  # Computer engineers (except software engineers and designers)
    "22220",  # Computer network and web technicians
    "22221",  # User support technicians
    "22222",  # Information systems testing technicians
}


def is_noc_it(code: str) -> bool:
    code = (code or "").strip()
    return code.startswith(NOC_IT_MINOR_PREFIXES) or code in NOC_IT_UNIT_GROUPS


# ROME: professional domain M18 "Systemes d'information et de telecommunication".
ROME_DOMAIN_IN_SCOPE = "M18"

# --------------------------------------------------------------------------------------
# Source tags
# --------------------------------------------------------------------------------------

SRC_ESCO = "ESCO"
SRC_ISCO = "ISCO"
SRC_ONET = "ONET"
SRC_NOC = "NOC"
SRC_ROME = "ROME"

# Sources that contribute real (non ISCO-group) occupations that get aligned.
REAL_OCC_SOURCES = (SRC_ESCO, SRC_ONET, SRC_NOC, SRC_ROME)

# --------------------------------------------------------------------------------------
# HuggingFace models (fully open-source; no API keys)
# --------------------------------------------------------------------------------------

EMBED_MODEL_PRIMARY = os.environ.get("JOBKB_EMBED_MODEL", "nomic-ai/nomic-embed-text-v2-moe")
EMBED_MODEL_FALLBACK = os.environ.get(
    "JOBKB_EMBED_MODEL_FALLBACK", "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")
NLI_MODEL = os.environ.get("JOBKB_NLI_MODEL", "MoritzLaurer/mDeBERTa-v3-base-mnli-xnli")

# --------------------------------------------------------------------------------------
# Alignment tunables
# --------------------------------------------------------------------------------------

EMBED_TOPK = 5             # candidate neighbours per entity, per source pair
EMBED_THRESHOLD = 0.50     # recall-oriented cosine floor for candidate generation
SKOS_EXACT_MIN = 0.90      # >= exactMatch
SKOS_CLOSE_MIN = 0.70      # >= closeMatch, else relatedMatch
NLI_ENTAIL_MIN = 0.60      # entailment prob to count a direction as entailed
