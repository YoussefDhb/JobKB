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
    "relation", "confidence", "method", "validated", "merge", "notes",
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

# IT scope = core + managers + data. ISCO-08 sub-major groups 25 (ICT professionals)
# and 35 (ICT technicians) are entirely IT; minor group 133 (ICT service managers) adds
# the IT-manager tier (CIO/CTO/CDO/IT project manager). A code within these branches is
# in scope.
ISCO_IT_SUBMAJORS = ("25", "35")
ISCO_IT_MINORS = ("133",)  # ICT service managers

# English labels for the IT unit groups (used to name minted ISCO nodes and as a
# stable in-scope reference set).
ISCO_IT_UNIT_GROUPS = {
    "1330": "Information and communications technology service managers",
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
    """True if a (bare) ISCO-08 code is within the IT branches (25, 35, or 133)."""
    code = (code or "").strip()
    return code.startswith(ISCO_IT_SUBMAJORS) or code.startswith(ISCO_IT_MINORS)


# ONET: Computer occupations (SOC 15-12xx) + Data Scientists (15-2051) + IT managers (11-3021).
ONET_IT_SOC_PREFIXES = ("15-12",)
ONET_IT_SOC_EXTRA = {"15-2051", "11-3021"}


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


# ROME: professional domain M18 "Systemes d'information et de telecommunication",
# plus cross-branch IT/data metiers ROME files elsewhere (data scientist/analyst under
# marketing M14, chief data/digital officers). A few M18 metiers are not IT (meteorology,
# cartography, geomatics) and are excluded by label keyword.
ROME_DOMAIN_IN_SCOPE = "M18"
ROME_IT_EXTRA_CODES = {"M1405", "M1419", "M1423", "M1426"}
ROME_EXCLUDE_LABEL_KEYWORDS = ("meteo", "cartograph", "geomat", "climat", "topograph")


def is_rome_it(code: str, label: str = "") -> bool:
    code = (code or "").strip()
    in_scope = code.startswith(ROME_DOMAIN_IN_SCOPE) or code in ROME_IT_EXTRA_CODES
    if not in_scope:
        return False
    from .common import normalize_label  # local import to avoid cycle
    norm = normalize_label(label)
    return not any(kw in norm for kw in ROME_EXCLUDE_LABEL_KEYWORDS)

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

# Primary embedder: BAAI/bge-m3 — a top open multilingual model (XLM-RoBERTa-large,
# ~560M) with strong EN<->FR cross-lingual similarity and, unlike nomic/e5, **no query/
# passage prefix** requirement (symmetric-safe). Chosen for precision on the occupation
# backbone + skill matching. Falls back to the lighter MiniLM only when bge-m3 can't load
# (e.g. offline / not cached), and to TF-IDF if sentence-transformers is unavailable.
EMBED_MODEL_PRIMARY = os.environ.get("JOBKB_EMBED_MODEL", "BAAI/bge-m3")
EMBED_MODEL_FALLBACK = os.environ.get(
    "JOBKB_EMBED_MODEL_FALLBACK", "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")
# Accurate multilingual NLI (mDeBERTa-v3-base, MNLI+XNLI). Used to VERIFY semantic
# occupation merges (mutual entailment on definitions), not just to label SKOS relations —
# the KB is built with no human review, so merge decisions are model-verified. Override
# with JOBKB_NLI_MODEL=MoritzLaurer/multilingual-MiniLMv2-L6-mnli-xnli for a faster build.
NLI_MODEL = os.environ.get("JOBKB_NLI_MODEL",
                           "MoritzLaurer/mDeBERTa-v3-base-mnli-xnli")
NLI_BATCH_SIZE = 16
EMBED_BATCH_SIZE = 32

# --------------------------------------------------------------------------------------
# Alignment tunables
# --------------------------------------------------------------------------------------

EMBED_TOPK = 5             # candidate neighbours per entity, per source pair
EMBED_THRESHOLD = 0.50     # recall-oriented cosine floor for candidate generation
SKOS_EXACT_MIN = 0.90      # >= exactMatch
SKOS_CLOSE_MIN = 0.70      # >= closeMatch, else relatedMatch
NLI_ENTAIL_MIN = 0.60      # entailment prob to count a direction as entailed
NLI_MIN_SIM = 0.70         # run the mDeBERTa verifier from just below the semantic-merge
                           # floor upward, so every merge-candidate occupation pair is NLI-
                           # scored (the gate). Calibrated to bge-m3: random cross-source occ
                           # pairs sit ~0.57 median, while TRUE cross-lingual EN<->FR matches
                           # land ~0.72-0.79 (e.g. "Software Developers" <> "Développeur
                           # informatique" ≈ 0.76). NLI volume stays tiny (few pairs clear
                           # 0.70 with definitions on both sides), so this costs ~no time.

# Merge (de-duplication) thresholds — source-neutral, precision-first. A pair merges on
# shared preferred label ("label"), OR a strong embedding signal ("semantic"). Alt-label
# overlap alone never merges. Semantic OCCUPATION merges are triple-guarded: embedding
# floor here + SAME ISCO group (merge.py) + mutual NLI entailment on definitions
# (verify.py) — no occupation is de-duplicated on embedding similarity alone. The floor is
# deliberately recall-friendly (true EN<->FR matches sit ~0.72-0.79); precision comes from
# the NLI gate and the same-ISCO-group constraint (e.g. software-dev 2512 <> web-dev 2513
# clear the embedding+NLI bar but are blocked by different ISCO groups).
MERGE_EMBED_OCC = 0.72     # embedding floor for a semantic occupation merge (NLI + ISCO gated)
MERGE_EMBED_SKILL = 0.90   # near-identical embedding floor for a skill merge (no NLI gate)

# Attachment (source -> ISCO group). The best group is chosen by NLI-re-ranking the top-K
# embedding candidates: embedding gives a shortlist, then mDeBERTa entailment (occupation
# definition -> ISCO group definition) decides among them, so a strong embedding to the
# wrong group can be overridden by the definition semantics. The final score blends the two.
# An edge is flagged low-confidence (surfaced by QA, never dropped) when the chosen group's
# embedding sim is below ATTACH_MIN_SIM. Entailment drives the re-ranking (a good *relative*
# signal) but not the flag — a correct occupation->broader-group attach often has low
# absolute entailment, so it is a poor flag. NOTE: the top1-top2 *margin* is also a poor
# signal — adjacent ISCO IT unit groups (2512/2513/2519) overlap heavily, so a correct
# attach routinely has a tiny margin — hence it is not used either.
ATTACH_MIN_SIM = 0.60
ATTACH_TOPK = 3            # embedding shortlist size that NLI re-ranks
ATTACH_NLI_WEIGHT = 0.5   # weight of NLI entailment vs embedding cosine in the re-rank score
