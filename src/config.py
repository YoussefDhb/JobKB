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
# Skills-only frameworks (no occupations): SFIA (professional IT skills) and CSO
# (computer-science research topics, curated subset). English-only.
SFIA_EN_DIR = os.path.join(RESOURCES, "SFIA", "en")
CSO_EN_DIR = os.path.join(RESOURCES, "CSO", "en")
LIGHTCAST_EN_DIR = os.path.join(RESOURCES, "LIGHTCAST", "en")
OTHERS_EN_DIR = os.path.join(RESOURCES, "OTHERS", "en")
# Zenodo 3906955 (Stack Overflow IT job postings + companion hard-skill category taxonomy).
ZENODO_DIR = os.path.join(OTHERS_EN_DIR, "zenodo")
ZENODO_JOBS_CSV = os.path.join(ZENODO_DIR, "jobs_complete.csv")
ZENODO_HL_CSV = os.path.join(ZENODO_DIR, "high-level-hard-skills.csv")
# WEF Global Skills Taxonomy 2021 + Education 4.0 (soft-skill enrichment).
WEF_SOFT_DIR = os.path.join(OTHERS_EN_DIR, "Soft-skills")
WEF_GLOBAL_CSV = os.path.join(WEF_SOFT_DIR, "Global-Skills-Taxonomy.csv")
WEF_COMPETENCIES_CSV = os.path.join(WEF_SOFT_DIR, "Skills-Taxonomy-Competencies.csv")
WEF_EDUCATION_CSV = os.path.join(WEF_SOFT_DIR, "Education4.0.csv")
# Job-posting demand datasets added 2026-07-22.
DJINNI_CSV = os.path.join(OTHERS_EN_DIR, "djinni-recruitment-dataset-job-descriptions-english.csv")
LINKEDIN_SWE_CSV = os.path.join(OTHERS_EN_DIR, "kaggle-LinkedIn-Software-Engineering-Jobs-Dataset.csv")
KAGGLE_JOBS_CSV = os.path.join(OTHERS_EN_DIR, "kaggle-job-skill-set.csv")
# Wikidata enrichment: the provided (noisy) programming-language/library export, plus a
# `retrieved/` folder where every SPARQL/API resolution is snapshotted so rebuilds are offline.
WIKIDATA_EN_DIR = os.path.join(RESOURCES, "WIKIDATA", "en")
WIKIDATA_RETRIEVED_DIR = os.path.join(RESOURCES, "WIKIDATA", "retrieved")
WIKIDATA_SRC_CSV = os.path.join(WIKIDATA_EN_DIR, "ESCO_v1.2.1-wikidata.csv")
WIKIDATA_SNAPSHOT_CSV = os.path.join(WIKIDATA_RETRIEVED_DIR, "resolutions.csv")

LLM_RETRIEVED_DIR = os.path.join(RESOURCES, "LLM", "retrieved")   # LLM generation snapshots (cache)
TRANSLATE_RETRIEVED_DIR = os.path.join(RESOURCES, "TRANSLATE", "retrieved")  # MT / Wikidata-label cache

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
BLOCKED_ENTITIES_CSV = os.path.join(KB_DIR, "blocked_entities.csv")  # relevance-gate rejects
LLM_SNAPSHOT_CSV = os.path.join(LLM_RETRIEVED_DIR, "generations.csv")  # cached LLM generations
LLM_REJECTED_CSV = os.path.join(KB_DIR, "llm_rejected.csv")   # LLM outputs that failed validation
TRANSLATE_SNAPSHOT_CSV = os.path.join(TRANSLATE_RETRIEVED_DIR, "translations.csv")  # cached MT (resumable)
TRANSLATE_WD_LABELS_CSV = os.path.join(TRANSLATE_RETRIEVED_DIR, "wd_labels.csv")    # authoritative @en/@fr
TRANSLATE_REJECTED_CSV = os.path.join(KB_DIR, "translate_rejected.csv")  # MT outputs that failed validation
WIKIDATA_LINKS_CSV = os.path.join(KB_DIR, "wikidata_links.csv")      # entity -> Wikidata QID anchors

# --------------------------------------------------------------------------------------
# KB validation (`--validate`): external gold benchmark + LLM-connection audit. Read-only over the
# graph (adds NO entities); consumes the three expert-annotated NER corpora the user provided. The
# graph logical-consistency suite (validation/consistency.py) runs automatically inside qa().
# --------------------------------------------------------------------------------------
VALIDATION_RES_DIR = os.path.join(RESOURCES, "validation")     # SkillSpan / Sayfullina / FIJO corpora
VALIDATION_OUT_DIR = os.path.join(ROOT, "validation")          # written report + per-track metrics CSVs
VALIDATION_DATASETS = {
    # name -> (subdir, splits, has tags_knowledge, has source col, language)
    "skillspan":  ("skillspan",  ("train", "dev", "test"), True,  True,  "en"),
    "sayfullina": ("sayfullina", ("train", "dev", "test"), False, False, "en"),
    "fijo":       ("fijo",       ("train", "dev", "test"), False, False, "fr"),
}
SAYFULLINA_CLUSTERS_CSV = os.path.join(VALIDATION_RES_DIR, "sayfullina", "sayfullina_clusters.csv")
VALIDATION_SEMANTIC_MIN = 0.75   # bge-m3 cosine floor for "semantically covered" (a gold mention is
                                 # covered if its nearest KB skill label clears this); reported next to
                                 # the stricter exact/alias coverage, never instead of it.
VALIDATION_ANON_TOKENS = ("<organization>", "<address>", "<location>", "<anon_company>", "<anon_misc>")
# LLM-connection audit thresholds (Track 3): re-verify the 84 llm_inferred links + 24 llm descriptions.
VALIDATION_LINK_NLI_MIN = 0.50       # occ-definition -> "requires {skill}" entailment to count as NLI-ok
VALIDATION_DEMAND_SEMANTIC_MIN = 0.75  # a link is demand-corroborated if the occ demands the skill OR a
                                       # skill this close to it (embedding) in its real posting profile

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
# The neutral skill ontology stores its type/domain/category nodes as rows in skills.csv, tagged in
# `esco_skill_type`. This is the single source of truth for "this skill row is a taxonomy node, not a
# real skill" — used by hierarchy/merge/qa to exclude the 3 taxonomy tiers from the real-skill set.
TAXONOMY_SKILL_MARKERS = ("skill_type", "skill_domain", "skill_category")
# `weight` carries a demand/frequency signal for evidence relations (ADEM vacancy positions,
# JOBS posting co-occurrence counts); "" for taxonomy relations. Missing keys default to "" on
# write, so the added column is backward-compatible with every existing relation writer.
REL_FIELDS = ["occupation_entity_id", "skill_entity_id", "relation_type", "source", "weight"]
HIERARCHY_FIELDS = ["parent_entity_id", "child_entity_id", "entity_kind", "relation_type", "source"]
ALIGNMENT_FIELDS = [
    "entity_id_a", "source_a", "entity_id_b", "source_b",
    "relation", "confidence", "method", "validated", "merge", "notes",
]
# Unified concepts carry their Wikidata anchor in-graph: qid + URL + Wikidata's terse description (a
# dedicated column that NEVER overwrites KB-authored text). Populated by wikidata.enrich_rows() from
# the side table; empty until `--wikidata` has run. Wikidata aliases are merged into alt_labels_*.
# `description` is a single authoritative concept description with `description_source` provenance:
# merge.py fills it by precedence (member-source description -> Wikidata description); the LLM stage
# (`--llm`) fills the remaining empties with `description_source="llm"`. Never overwrites a source desc.
UNIFIED_OCC_FIELDS = [
    "unified_id", "primary_label_en", "primary_label_fr",
    "alt_labels_en", "alt_labels_fr", "isco_code",
    "occupation_type", "sources", "member_entity_ids",
    "wikidata_qid", "wikidata_url", "wikidata_description",
    "description", "description_source",
]
UNIFIED_SKILL_FIELDS = [
    "unified_id", "primary_label_en", "primary_label_fr",
    "alt_labels_en", "alt_labels_fr", "hard_soft", "it_subtype",
    "sources", "member_entity_ids",
    "wikidata_qid", "wikidata_url", "wikidata_description",
    "description", "description_source",
]
PROVENANCE_FIELDS = [
    "entity_id", "source", "source_version", "retrieved_at", "retrieval_method", "notes",
]
BLOCKED_FIELDS = [
    "entity_kind", "source", "source_id", "label", "decision", "reason",
    "sim_it", "sim_non", "nli",
]
# Wikidata cross-reference (side table produced by the `--wikidata` enrichment). `relation` carries
# SKOS-typed semantics (skos:exactMatch / skos:closeMatch) so the layer is RDF-export-ready;
# `wd_aliases_en`/`wd_aliases_fr` are the fetched alternate labels (' | '-joined).
WIKIDATA_LINKS_FIELDS = [
    "entity_id", "entity_kind", "unified_id", "label_en", "qid", "relation", "wikidata_url",
    "wd_label", "wd_description", "wd_aliases_en", "wd_aliases_fr",
    "instance_of", "match_method", "confidence",
]
# Snapshot of every label resolved against Wikidata (empty qid = verified-unresolved, cached so a
# re-run is fully offline). Keyed by normalized label + kind.
WIKIDATA_SNAPSHOT_FIELDS = [
    "norm_label", "entity_kind", "qid", "wd_label", "wd_description",
    "wd_aliases_en", "wd_aliases_fr",
    "instance_of", "match_method", "confidence",
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
SRC_SFIA = "SFIA"   # skills-only: professional IT/digital competency framework
SRC_CSO = "CSO"     # skills-only: curated subset of computer-science research topics
SRC_LIGHTCAST = "LIGHTCAST"  # skills-only: Lightcast Open Skills (IT category)
SRC_KAGGLE = "KAGGLE"        # skills-only: small curated IT technical-skills taxonomy
SRC_ECF = "ECF"              # skills-only: European e-Competence Framework (EU ICT competences)
SRC_ADEM = "ADEM"            # relations-only: ADEM (Luxembourg) vacancy demand (ESCO×ROME)
SRC_JOBS = "JOBS"            # relations-only: mined IT job-posting evidence (role×skill)
SRC_DATAJOBS = "DATAJOBS"    # hybrid: harvested tool skills + large-scale demand (lukebarousse/data_jobs)
SRC_ZENODO = "ZENODO"        # hybrid: harvested tools + demand (Zenodo 3906955, Stack Overflow postings)
SRC_EMERGING = "EMERGING"    # curated emerging IT roles observed in data_jobs but absent from ESCO/O*NET
SRC_SOFTSKILLS = "SOFTSKILLS"  # curated noun-form soft/transversal skills used in IT hiring
SRC_SOFTTAXO = "SOFTTAXO"    # comprehensive curated IT soft-skills taxonomy (5 sub-domains + universal attach)
SRC_WEF = "WEF"              # WEF Global Skills Taxonomy (2021): structured soft skills + transversal attach
SRC_DJINNI = "DJINNI"        # relation-only demand: Djinni IT postings (role tag + free-text JD extraction)
SRC_LINKEDIN_SWE = "LINKEDIN_SWE"  # hybrid: LinkedIn software-engineering postings (pre-extracted skills)
SRC_KAGGLE_JOBS = "KAGGLE_JOBS"    # hybrid: kaggle job-skill-set, IT subset (pre-extracted skills)
SRC_LLM = "LLM"              # LLM-powered enrichment: generated descriptions, inferred links, and
                             # new emerging entities (each auto-validated + Wikidata-confirmed)
SRC_TRANSLATE = "TRANSLATE"  # multilingual label completion: Wikidata @en/@fr labels + validated MT

# Sources that contribute real (non ISCO-group) occupations that get aligned.
REAL_OCC_SOURCES = (SRC_ESCO, SRC_ONET, SRC_NOC, SRC_ROME, SRC_EMERGING)

# Sources trusted to set their own IT sub-domain (`it_subtype`) at ingest time; the neutral
# hierarchy keeps that placement instead of re-deriving it from the label regex. SFIA ships a
# hand-curated code->sub-domain map (its own category export is unreliable) and CSO derives the
# sub-domain from the IT root branch each topic descends from — both more reliable than a
# keyword match on a bare skill/topic label.
SELF_CLASSIFIED_SUBDOMAIN_SOURCES = {SRC_SFIA, SRC_CSO, SRC_LIGHTCAST, SRC_KAGGLE, SRC_ECF,
                                     SRC_DATAJOBS, SRC_ZENODO, SRC_WEF, SRC_SOFTTAXO}

# CSO curation: CSO 3.5 is ~14.6k CS *research topics* — far broader than a jobs/skills KB
# needs, and deep branches are noisy research fragments. We keep only the IT-relevant, shallow
# part: descendants (via `superTopicOf`) of these root branches, down to CSO_MAX_DEPTH, deduped
# and capped at CSO_MAX_TOPICS, ingested as knowledge-type skills classified by their branch.
# Roots are ordered specific->generic so a multi-parent topic takes the most precise branch.
CSO_ROOTS = (
    "computer_security", "machine_learning", "artificial_intelligence", "data_mining",
    "information_retrieval", "computer_networks", "human_computer_interaction",
    "computer_operating_systems", "software_engineering", "computer_programming",
    "internet", "software",
)
CSO_MAX_DEPTH = 2
# Per-branch cap keeps the subset balanced across sub-domains (CSO is heavily AI-weighted, and
# a single global cap would let BFS fill AI/ML before ever reaching networks/data/web). Each
# branch keeps its shallowest CSO_MAX_PER_BRANCH topics; CSO_MAX_TOPICS is an overall ceiling.
CSO_MAX_PER_BRANCH = 80
CSO_MAX_TOPICS = 700
# Each CSO root branch -> the neutral sub-domain its topics belong to.
CSO_BRANCH_SUBDOMAIN = {
    "artificial_intelligence": "ai_ml", "machine_learning": "ai_ml",
    "computer_security": "security",
    "data_mining": "data_databases", "information_retrieval": "data_databases",
    "computer_networks": "networks", "internet": "networks",
    "software_engineering": "programming_languages", "computer_programming": "programming_languages",
    "software": "programming_languages",
    "human_computer_interaction": "web",
    "computer_operating_systems": "systems_infrastructure",
}

# Evidence / demand relation sources (ADEM vacancies, mined job postings). These add
# occupation->skill edges between entities that ALREADY exist in the KB (no new nodes), tagged
# relation_type="demand" and weighted. ADEM keeps ROME IT families (M18*); JOBS keeps role->skill
# pairs seen in at least JOBS_MIN_FREQ postings (drops one-off extraction noise).
ADEM_ROME_PREFIX = "M18"
JOBS_MIN_FREQ = 2

# DATAJOBS (lukebarousse/data_jobs): 785k real postings, 10 data/IT roles, pre-extracted skills.
# A hybrid source: it (a) harvests the few genuinely-absent, high-frequency IT tools as new skill
# nodes (gate-screened, self-classified via job_type_skills) and (b) adds large-scale weighted
# `demand` role->skill relations. `job_type_skills` category -> neutral sub-domain (self-classified;
# "" -> defer to the hierarchy regex, e.g. mixed `libraries`/`other`).
DATAJOBS_MIN_FREQ = 50          # keep a (role, skill) demand pair only if seen in >= this many postings
DATAJOBS_MIN_SKILL_FREQ = 150   # harvest an absent token as a new skill only above this frequency
DATAJOBS_TYPE_SUBDOMAIN = {
    "programming": "programming_languages",
    "analyst_tools": "data_databases",
    "cloud": "cloud_devops",
    "databases": "data_databases",
    "os": "systems_infrastructure",
    "webframeworks": "web",
    "libraries": "",   # mixed (ML/data/viz) -> regex fallback
    "other": "",
    "async": "",
    "sync": "",
}

# ZENODO (Zenodo 3906955 — Montandon et al. 2019, "What Skills do IT Companies Look for in New
# Developers?", mined from Stack Overflow postings): 21k postings (we take the ~17.9k English) with
# clean `roles` (14 IT dev types), extracted `hard_skills` + `soft_skills`, and a companion
# hard-skill -> high-level-category taxonomy. A hybrid source like DATAJOBS: it (a) harvests the few
# genuinely-absent, frequent IT tools as new skill nodes (gate-screened, self-classified via the
# high-level category) and (b) adds weighted `demand` role->skill relations for BOTH hard skills and
# the curated SOFTSKILLS vocabulary (from the postings' extracted soft_skills). No occupations of its
# own (roles resolve to existing occupations; the one gap, back-end developer, is added via EMERGING).
# The dataset is ~45x smaller than DATAJOBS, so the demand/harvest gates are proportionally lower.
ZENODO_MIN_FREQ = 15        # keep a (role, hard-skill) demand pair only if seen in >= this many postings
ZENODO_MIN_SOFT_FREQ = 8    # soft-skill demand is legitimately sparser (from the clean soft_skills column)
ZENODO_MIN_SKILL_FREQ = 25  # harvest an absent hard token as a new skill only above this frequency
# high-level-hard-skills.csv category -> neutral sub-domain ("" -> defer to the hierarchy regex,
# which already classifies frameworks/tools like react/spring/docker/git precisely).
ZENODO_HL_SUBDOMAIN = {
    "Languages": "programming_languages",
    "Data Systems": "data_databases",
    "OS & Infrastructure": "systems_infrastructure",
    "Process & Methods": "methodology",
    "Libs & Frameworks": "",   # mixed web/backend/ML frameworks -> regex fallback
    "Development Tools": "",    # mixed (git/docker/jira/...) -> regex fallback
    "INVALIDO": "",
}

# DJINNI (djinni.com IT recruitment, ~142k EN postings, role tag + free-text JD). Relation-only demand
# (no harvest): the role (Primary Keyword) resolves to an occupation and skills are extracted from the
# Long Description by strict dictionary matching against the KB's CONCRETE-tech vocabulary. Free-text
# extraction must NOT use the augmented matcher's vendor/suffix-strip or paren-acronym variants (they
# match common English words like "teams"/"application"); only full labels (parens removed), single
# tokens >= 4 chars, minus a common-word denylist.
DJINNI_MIN_FREQ = 40          # keep a (role, skill) demand pair only if seen in >= this many postings
DJINNI_CONCRETE_SUBDOMAINS = frozenset({
    "programming_languages", "cloud_devops", "data_databases", "ai_ml", "web",
    "networks", "security", "systems_infrastructure", "emerging_tech",
    "mobile_development", "data_engineering", "hardware_embedded",
})
# Concrete-tech skill labels that are also common English words / too ambiguous for free-text matching.
DJINNI_TEXT_DENY = frozenset({
    "go", "r", "c", "d", "ml", "ai", "it", "ui", "ux", "qa", "os", "sql", "css", "html", "bi", "ci",
    "cd", "sap", "crm", "erp", "react", "spark", "rust", "swift", "scala", "unity", "word", "excel",
    "access", "ruby", "shell", "bash", "rest", "make", "servers", "server", "docking", "test", "testing",
    "design", "support", "lead", "other", "scale", "science", "software", "automation", "monitoring",
    "deployment", "english", "language", "communication", "statistics", "analytics", "security",
    "network", "database", "cloud", "agile", "scrum", "visualization", "scripting", "algorithms",
    "algorithm", "engineering", "development", "operations", "management",
})

# LINKEDIN_SWE (kaggle LinkedIn software-engineering postings, ~9.4k, pre-extracted comma-sep skills).
# Relation-only demand: role (job_title) -> software-developer family, skills resolved against existing
# KB skills via the augmented matcher. No harvest — LinkedIn's job_skills is a noisy free-form extraction
# (generic phrases like "coding"/"analysis"/"best practices") that would pollute the vocabulary.
LINKEDIN_SWE_MIN_FREQ = 15        # keep a (role, skill) demand pair only if seen in >= this many postings

# KAGGLE_JOBS (kaggle job-skill-set, IT subset = 240 postings, pre-extracted list skills). Small hybrid:
# generic IT-management/support titles -> occupations, demand relations; harvest disabled (too few rows).
KAGGLE_JOBS_MIN_FREQ = 3          # keep a (role, skill) demand pair only if seen in >= this many postings

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
# LLM-powered enrichment (pillar 3) — HuggingFace, validated (pillar 4), free-tier-economical
# --------------------------------------------------------------------------------------
# Generative LLM: HF Inference Providers (serverless) is primary; a small local transformers model is
# the offline fallback; if neither loads the enrichment is skipped (fail-open). Kept HuggingFace-only.
# Llama-3.1-8B-Instruct is fast/capable and reachable on the free tier (validated live). Override via
# env for a stronger model (e.g. Qwen/Qwen2.5-72B-Instruct) at higher credit cost.
LLM_API_MODEL = os.environ.get("JOBKB_LLM_MODEL", "meta-llama/Llama-3.1-8B-Instruct")
LLM_API_PROVIDER = os.environ.get("JOBKB_LLM_PROVIDER", "auto")   # HF Inference Providers routing
LLM_LOCAL_MODEL = os.environ.get("JOBKB_LLM_LOCAL_MODEL", "Qwen/Qwen2.5-3B-Instruct")  # offline fallback
LLM_MAX_TOKENS = 200
LLM_TEMPERATURE = 0.2       # low — factual, deterministic-ish definitions
LLM_TIMEOUT = 60
LLM_MAX_RETRIES = 4
LLM_RATE_SLEEP = 0.30       # polite pacing between API calls (free tier)
LLM_USE_LOCAL_FALLBACK = os.environ.get("JOBKB_LLM_LOCAL", "0") == "1"  # opt-in (local gen is slow on CPU)

# Validation thresholds for LLM outputs (reuses the IT-relevance gate + mDeBERTa NLI verifier).
LLM_DESC_MIN_CHARS = 20
LLM_DESC_MAX_CHARS = 400
LLM_DESC_NLI_MIN = 0.50     # generated description must entail "<label> is <description>" this strongly
LLM_HARDSOFT_NLI_MARGIN = 0.10  # zero-shot hard-vs-soft margin required to fill hard_soft
LLM_LINK_TOPK = 25          # embedding shortlist size per occupation for link inference
LLM_LINK_MIN_SIM = 0.45     # inferred occ->skill link must clear this embedding cosine (stored as weight)
LLM_LINK_MAX_PER_OCC = 15   # cap inferred links per occupation (avoid flooding)
LLM_LINK_MAX_OCC = int(os.environ.get("JOBKB_LLM_LINK_MAX", "40"))  # cap occupations processed (cost)
LLM_LINK_SPARSE_MAX = 6     # an occupation with <= this many existing relations is a link target
LLM_EMERGING_MAX_NEW = int(os.environ.get("JOBKB_LLM_EMERGING_MAX", "40"))  # cap new entities added

# Description generation is eligible for EVERY hard skill lacking a description (the full-coverage push;
# soft skills already sit near-complete). This is the complete set of hard categories from
# hierarchy.CATEGORIES (kept in sync here to avoid a config<-hierarchy import cycle). Coverage is
# credit-bound but snapshot-resumable, so it converges over successive runs. Set JOBKB_LLM_DESC_MAX to
# cap per-run cost when iterating.
LLM_DESC_SKILL_SUBDOMAINS = frozenset({
    "programming_languages", "methodology", "web", "mobile_development", "data_databases",
    "data_engineering", "ai_ml", "systems_infrastructure", "cloud_devops", "hardware_embedded",
    "networks", "security", "it_management", "emerging_tech", "knowledge_general", "other_hard",
})
LLM_DESC_MAX_TARGETS = int(os.environ.get("JOBKB_LLM_DESC_MAX", "0"))  # 0 = unlimited (bounds API cost)
LLM_SNAPSHOT_FIELDS = ["task", "key", "model", "prompt_hash", "output", "created_at"]
LLM_REJECTED_FIELDS = ["task", "entity_id", "label", "output", "reason", "score"]

# --------------------------------------------------------------------------------------
# Agentic enrichment (`--agent`, LangGraph): a controller that assesses the KB, prioritizes gaps,
# and dispatches reflective workers (propose -> verify -> reflect/retry -> commit). It reuses the LLM_*
# models/thresholds/snapshot above — it is a *smarter producer of the same generations.csv snapshot*
# the pipeline already consumes (agent rows tagged model="agentic"), so integration is unchanged.
# The LLM is one optional, budget-bounded tool; the deterministic verifiers (bge-m3 + NLI + Wikidata)
# drive control, so the agent stays useful even with the LLM backend dead (anchor worker needs none).
# --------------------------------------------------------------------------------------
AGENT_GAPS = ("description", "link", "emerging", "anchor")   # workers the controller can dispatch
AGENT_MAX_REFLECT = int(os.environ.get("JOBKB_AGENT_MAX_REFLECT", "2"))  # bounded retries per target
# NEW accept gate the one-shot pipeline lacked: an inferred link must clear the embedding cosine floor
# (LLM_LINK_MIN_SIM) AND be NLI-corroborated (occ definition |= "requires {skill}") — lifting the 45%
# NLI-pass rate the validation phase measured on the cosine-only llm_inferred links.
AGENT_LINK_NLI_MIN = VALIDATION_LINK_NLI_MIN
AGENT_ANCHOR_MAX = int(os.environ.get("JOBKB_AGENT_ANCHOR_MAX", "200"))  # cap unattempted anchors/run
AGENT_OUT_DIR = os.path.join(ROOT, "agent")                 # written agent report + per-gap metrics
AGENT_REPORT_MD = os.path.join(AGENT_OUT_DIR, "report.md")
AGENT_TAG = "agentic"                                        # snapshot `model` marker for agent commits

# --------------------------------------------------------------------------------------
# Multilingual label completion (`--translate`): fills empty EN/FR primary + alt labels on the
# unified tables. Quality-first ordering: authoritative Wikidata @en/@fr labels + aliases, then
# local HuggingFace MT (NLLB) with a tech-term guard, each cross-lingually validated. Fully local
# + snapshotted (free-tier-safe, resumable); never overwrites a non-empty cell or source data.
# --------------------------------------------------------------------------------------
TRANSLATE_MT_MODEL = os.environ.get("JOBKB_TRANSLATE_MODEL", "facebook/nllb-200-distilled-600M")
TRANSLATE_LANG_CODES = {"en": "eng_Latn", "fr": "fra_Latn"}   # NLLB BCP-47-ish codes
TRANSLATE_MAX_NEW_TOKENS = 96          # labels are short; caps runaway generation
TRANSLATE_BATCH_SIZE = 16              # MT batch size (CPU)
TRANSLATE_XLING_MIN = 0.62             # lenient cross-lingual floor: src vs output must be at least this
                                       # similar (bge-m3 is multilingual). A lenient floor catches gross
                                       # semantic failures; the structural filters below catch the rest.
                                       # (Back-translation round-trip was too noisy on short labels — it
                                       # dropped correct translations like "Monitoring"->"Surveillance".)
# Output looks like a generated sentence, not a label → reject (MT sometimes describes instead of names).
TRANSLATE_SENTENCE_STARTS = ("je ", "j'", "nous ", "vous ", "il s'agit", "c'est ", "cela ",
                             "i am ", "i'm ", "we ", "it is ", "this is ", "there ")
TRANSLATE_LEN_RATIO_MIN = 0.30         # output/source char-length ratio bounds (reject collapses/blow-ups)
TRANSLATE_LEN_RATIO_MAX = 3.50
TRANSLATE_ROME_EN_ENABLED = os.environ.get("JOBKB_TRANSLATE_ROME_EN", "1") == "1"  # fr->en for ROME rows
TRANSLATE_MAX_TARGETS = int(os.environ.get("JOBKB_TRANSLATE_MAX", "0"))  # 0 = unlimited (bounds runtime)
# Tech proper-noun / acronym guard: labels that are wholly one of these (or a single protected token)
# are kept verbatim, never machine-translated. Token-level heuristics (acronyms, CamelCase, version
# tokens) are applied in code; this lexicon covers common lowercase tech terms the heuristics miss.
TRANSLATE_TECH_LEXICON = frozenset({
    "python", "java", "javascript", "typescript", "kotlin", "swift", "golang", "rust", "scala",
    "docker", "kubernetes", "terraform", "ansible", "jenkins", "git", "linux", "unix", "bash",
    "react", "angular", "vue", "django", "flask", "spring", "node", "nodejs", "npm", "webpack",
    "tensorflow", "pytorch", "keras", "numpy", "pandas", "spark", "hadoop", "kafka", "airflow",
    "mongodb", "postgresql", "mysql", "redis", "elasticsearch", "snowflake", "databricks",
    "kubernetes", "openshift", "helm", "grafana", "prometheus", "nginx", "apache", "tomcat",
    "machine learning", "deep learning", "data science", "big data", "cloud", "cloud computing",
    "devops", "mlops", "cicd", "microservices", "blockchain", "cybersecurity", "middleware",
    "business intelligence", "business objects", "sharepoint", "power bi", "sql server",
    "active directory", "data warehouse", "data lake", "data mining", "web services",
})
TRANSLATE_SNAPSHOT_FIELDS = ["direction", "src_hash", "src_text", "output", "model", "validated",
                             "score", "reason", "created_at"]
TRANSLATE_WD_LABELS_FIELDS = ["qid", "label_en", "label_fr"]
TRANSLATE_REJECTED_FIELDS = ["direction", "src_text", "output", "reason", "score"]

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

# Deterministic same-concept dedup (align): skills with an identical match_key (normalized +
# singularized label) are the same concept and are merged even when embedding candidate generation
# missed the pair (notably intra-source exact duplicates the cross-source aligner never compares).
# MATCH_KEY_DISTINCT lists match_keys to LEAVE ALONE because the key collides across genuinely-distinct
# concepts: "http" collides HTTP with HTTPS (singularize https -> http); "cybersecurity expert" would
# fold the Master's-qualified variant into the base skill. The hard-vs-soft split (e.g. the hard vs soft
# "time management") is handled by a separate hard/soft guard in the linker, not this list.
MATCH_KEY_DISTINCT = frozenset({"http", "cybersecurity expert"})

# Authoritative it_subtype for skills whose members disagree across sources (same concept, different
# tag). Applied in merge after the member majority, keyed by the unified primary label in
# normalize_label() form. Resolves the known cross-source conflicts (e.g. ESCO tags "computer science"
# knowledge_general while ROME tags it other_hard; Cypress/Playwright are web testing tools, not ML).
IT_SUBTYPE_OVERRIDE = {
    "cypress": "web",                       # Cypress.io — front-end E2E testing framework
    "playwright": "web",                    # Playwright — browser automation/testing
    "cdn": "cloud_devops",                  # content delivery network — infra/devops
    "consul": "cloud_devops",               # HashiCorp Consul — service mesh/discovery
    "a/b testing": "methodology",           # experimentation practice
    "test driven development": "methodology",
    "workflow software": "other_hard",
    "distributed computing": "knowledge_general",
    "computer science": "knowledge_general",
    "computer technology": "knowledge_general",
    "digital systems": "knowledge_general",
    "information systems": "knowledge_general",
    "cryptocurrency": "emerging_tech",      # blockchain family
}

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

# Curated ISCO-08 unit-group overrides for emerging IT roles the embedding+NLI attach placed poorly
# (all were low-confidence). Keyed by occupation source_id -> 4-digit ISCO code; applied in attach
# BEFORE the automatic choice, forcing a high-confidence placement (removes them from the low-conf
# set). Deterministic, auditable, no human-in-loop at runtime. Only clearly-mis-attached roles with a
# confident better group are listed; genuinely-niche roles are left honestly low-confidence.
ISCO_OCC_OVERRIDE = {
    "M1405": "2511",   # Data scientist                 -> Systems Analysts (was 2523 Network Prof.)
    "M1423": "1330",   # Chief Data Officer             -> ICT Service Managers (executive; was 2521)
    "M1822": "2519",   # Spécialiste Jumeau Numérique   -> SW/Analysts n.e.c. (was 2523 Network Prof.)
    "M1835": "2523",   # Architecte systèmes et réseaux -> Network Professionals (was 3513 technician)
    "M1846": "2529",   # Ingénieur Cybersécurité        -> DB/Network Prof. n.e.c. (was 3513 technician)
    "M1857": "2522",   # Urbaniste Datacenter           -> Systems Administrators (was 2521 DB)
    "M1858": "1330",   # Chef de projet TMA             -> ICT Service Managers (was 2522 SysAdmin)
    "M1864": "1330",   # Product Owner                  -> ICT Service Managers (was 2522 SysAdmin)
    "M1865": "2512",   # Ingénieur blockchain           -> Software Developers (was 2523 Network Prof.)
    "M1866": "2529",   # Pentesteur                     -> DB/Network Prof. n.e.c. (security; was 2511)
    "M1872": "2511",   # Consultant décisionnel (BI)    -> Systems Analysts (was 2523 Network Prof.)
    "M1873": "2512",   # Spécialiste IA embarquée       -> Software Developers (was 2522 SysAdmin)
    "M1875": "1330",   # Coordinateur MOA SI            -> ICT Service Managers (was 2522 SysAdmin)
    "M1877": "2512",   # Développeur blockchain         -> Software Developers (was 2521 DB)
    "M1881": "1330",   # Chef de projet MOA SI          -> ICT Service Managers (was 2522 SysAdmin)
    "M1889": "2512",   # Ingénieur en IA                -> Software Developers (was 2523 Network Prof.)
}

# --------------------------------------------------------------------------------------
# Relevance / noise gate (src/relevance.py) — automatic, at ingest, for NEW sources
# --------------------------------------------------------------------------------------
# Every pluggable StructuredSource (SFIA/CSO/scraped/future) is screened before its rows are
# written: malformed labels and confidently non-IT entities are BLOCKED (logged to
# BLOCKED_ENTITIES_CSV), the rest are kept. Built-in taxonomies (code-filtered already) bypass
# this. Lenient by design — precision-first on BLOCKING so genuine IT is never dropped. bge-m3
# cosines run high for everything, so absolute IT-similarity does not separate the classes; the
# discriminator (calibrated on real data) is an item scoring **clearly closer to a non-IT domain**
# (`sim_non >= REL_NONIT_HI` AND a positive margin over its IT similarity) — that makes it a
# *candidate*, then BLOCKED only if the NLI verifier also says it isn't IT (`nli < REL_NLI_MIN`).
# Everything else is kept; a candidate the NLI rescues is kept + logged as borderline. Low-context
# IT terms ("dijkstra", "k-nearest neighbors") have LOW sim_non, so the floor protects them; true
# non-IT ("tax accounting" sim_non≈0.76, nli≈0.01) is caught. At these values SFIA-kept + CSO
# valid-IT show 0 false blocks. Reuses the cached bge-m3 + mDeBERTa, so the extra cost is ~nil.
RELEVANCE_GATE_ENABLED = True
REL_NONIT_HI = 0.65       # a candidate must score at least this cos to a non-IT domain anchor
REL_NONIT_MARGIN = 0.05   # ...and beat its own IT similarity by at least this margin
REL_NLI_MIN = 0.15        # ...then, if NLI entailment "...is about IT" is below this -> BLOCK non-IT

# Curated IT seed vocabulary — broad anchors so a novel-but-real IT skill still scores IT.
REL_IT_SEED = (
    "software development and programming", "computer networks and telecommunications",
    "cybersecurity and information security", "databases and data engineering",
    "artificial intelligence and machine learning", "cloud computing and devops",
    "web and mobile application development", "operating systems and IT infrastructure",
    "IT service management and governance", "data analytics and business intelligence",
    "computer hardware and embedded systems", "information technology",
)
# Non-IT domain anchors — the contrast class. Kept generic so clearly out-of-scope skills
# (marketing, HR, finance, facilities, healthcare, …) lose the IT-vs-non-IT comparison.
REL_NONIT_ANCHORS = (
    "marketing, advertising and brand management", "sales and customer relationship management",
    "human resources, recruitment and staff training", "accounting, finance and budgeting",
    "facilities, building and physical asset management", "healthcare, nursing and medicine",
    "law, legal practice and compliance", "agriculture, farming and forestry",
    "construction and civil engineering", "cooking, catering and hospitality",
    "teaching and classroom education", "logistics, warehousing and transport",
    "retail and store operations", "occupational health and physical safety",
    "hairdressing, beauty and personal care", "manufacturing, welding and metal fabrication",
    "driving and vehicle operation", "biology, genetics and laboratory science",
)

# --------------------------------------------------------------------------------------
# Wikidata enrichment (`--wikidata`) — resolve KB tech-skills/occupations to stable QIDs.
# Network READ-only via ONE batched SPARQL query per ~50 labels (label/alias match + class
# verification together). Every resolution is snapshotted to WIKIDATA_SNAPSHOT_CSV so rebuilds
# are offline/reproducible and interrupted runs resume. Precision: exact/alias label match AND an
# instance-of class check — QIDs are never hardcoded (all verified live).
# --------------------------------------------------------------------------------------
WIKIDATA_SPARQL_URL = "https://query.wikidata.org/sparql"
# Wikidata etiquette asks for a descriptive User-Agent identifying the client.
WIKIDATA_USER_AGENT = "JobKB/1.0 (IT knowledge-base research; enrichment) python-urllib"
WIKIDATA_RATE_SLEEP = 1.00     # seconds between SPARQL calls (gentle pacing; avoids WDQS throttling)
WIKIDATA_MAX_RETRIES = 15      # attempts on 429/5xx/timeout, then fail-open (429s wait for bucket refill)
# During the WDQS outage the service caps to ~1 req/min; on 429 we wait for the token bucket to refill
# (observed ~60s) rather than fail fast. Retry-After is honoured but capped so a huge hint can't stall.
WIKIDATA_THROTTLE_WAIT = 65        # seconds to wait after a 429 (bucket refill; empirically sufficient)
WIKIDATA_THROTTLE_MAX_WAIT = 120   # cap on a server-provided Retry-After

# Sub-domains eligible for Wikidata anchoring. Widened (for the description push) beyond the concrete-
# technology set to the two further hard sub-domains that carry genuine *named entities* — methodology
# (Scrum, Git, Agile, Kanban, Jira) and knowledge_general (computer science, information systems,
# distributed computing). The phrase-heavy sub-domains (it_management, other_hard) are deliberately
# EXCLUDED: their labels are competence phrases with no Wikidata item, so every candidate is a wasted
# (rate-limited) SPARQL round-trip that the class verification rejects anyway — those descriptions are
# the LLM stage's job. The authoritative wikidata_description is the highest-precision description
# source; the resolver's instance-of/subclass class check protects precision as recall widens, and the
# MAX_TOKENS bound keeps candidates to short, entity-like labels (e.g. "Scrum", "React Native").
WIKIDATA_SKILL_SUBDOMAINS = frozenset({
    "programming_languages", "data_databases", "cloud_devops", "ai_ml", "web",
    "networks", "security", "systems_infrastructure", "emerging_tech",
    "mobile_development", "data_engineering", "hardware_embedded",
    "methodology", "knowledge_general",
})
WIKIDATA_SKILL_MAX_TOKENS = 3  # only short (entity-like) labels are candidates (4-token labels are
                               # overwhelmingly competence phrases with no Wikidata item)

# In-graph enrichment: Wikidata aliases merged into a concept's alt_labels are hygiene-filtered to
# avoid noise — dropped if they duplicate an existing label, exceed these bounds, or are structural
# noise (relevance.is_structural_noise); at most WIKIDATA_MAX_ALIASES kept per concept.
WIKIDATA_MAX_ALIASES = 8
WIKIDATA_ALIAS_MAX_TOKENS = 4
WIKIDATA_ALIAS_MAX_CHARS = 40

# instance-of (P31) / subclass-of (P279*) allowlist. Q7397 (software) as a superclass captures
# most software subtypes (IDEs, version-control systems, …) through the P279* closure.
WIKIDATA_SKILL_CLASSES = (
    # concrete technologies / tools / products
    "Q9143",    # programming language
    "Q7397",    # software
    "Q341",     # free software
    "Q188860",  # software library
    "Q1330336", # web framework
    "Q271680",  # software framework
    "Q166142",  # application software
    "Q9135",    # operating system
    "Q8513",    # database
    "Q3966",    # computer hardware
    "Q783794",  # company
)
# Abstract IT fields / disciplines / techniques (data science, cloud computing, AI, cybersecurity,
# software development, …). These are matched by **direct P31** (the field concepts are directly
# instance-of these), NOT by P279* closure — walking the subclass tree of e.g. "academic discipline"
# is huge and times the query out. Candidates are already IT-scoped + exact-label-matched, so these
# broad classes stay IT-relevant in practice.
WIKIDATA_SKILL_FIELD_CLASSES = (
    "Q11862829",  # academic discipline
    "Q2465832",   # branch of science
    "Q1047113",   # field of study
    "Q2267705",   # field of study
    "Q112057532", # type of technology
    "Q123370638", # branch of computer science
    "Q4671286",   # academic major
)
WIKIDATA_OCC_CLASSES = (
    "Q28640",     # profession
    "Q12737077",  # occupation
)
# The 10 faceted-taxonomy functional-domain nodes (hierarchy.DOMAINS) are also anchored, so the KB's
# top-level skill/occupation domains carry stable QIDs. Domain node labels are composite
# ("Data, Analytics & AI") and never exact-match Wikidata, so each domain KEY supplies a few candidate
# English **label probes** (label alternates, exactly like the programming-language _language_seed) —
# each still verified live by class allowlist, best chosen. Domains resolve as abstract fields, so
# WIKIDATA_SKILL_FIELD_CLASSES applies by direct P31, plus the software-development process concept.
# dom_cross / dom_soft are custom composites with no clean single concept -> no probes (stay unresolved).
# Probe labels are in Wikidata's exact label case (mostly lowercase; rdfs:label matching is
# case-sensitive — Title Case matches disambiguation pages, e.g. "Software development" -> a disambig
# item). Each maps to a verified real concept (item + P31 confirmed live 2026-07-22): software
# development Q638608, web development Q386275, data science Q2374463, IT infrastructure Q594593,
# telecommunications Q418, computer security Q3510521, IT management Q1473265, emerging technologies
# Q120208. First probe that resolves + class-verifies wins; the alternates are honest fallbacks.
WIKIDATA_DOMAIN_PROBES = {
    "dom_software":    ("software development", "software engineering"),
    "dom_web_mobile":  ("web development", "mobile app development"),
    "dom_data_ai":     ("data science", "artificial intelligence"),
    "dom_infra_cloud": ("IT infrastructure", "cloud computing"),
    "dom_networks":    ("telecommunications", "computer network"),
    "dom_security":    ("computer security", "cybersecurity"),
    "dom_it_mgmt":     ("information technology management", "IT service management"),
    "dom_emerging":    ("emerging technologies",),
}
WIKIDATA_DOMAIN_CLASSES = ("Q638608",)  # software development (process) — for P279* closure
# fields/disciplines via direct P31, plus 'type of infrastructure' (Q131339603) so IT infrastructure
# resolves for the Infrastructure/Cloud domain (cloud computing itself has no P31).
WIKIDATA_DOMAIN_FIELD_CLASSES = WIKIDATA_SKILL_FIELD_CLASSES + ("Q131339603",)
# Backstop: reject a candidate whose instance-of hits any of these, even on a label match.
WIKIDATA_DENY_CLASSES = (
    "Q5",         # human
    "Q11424",     # film
    "Q482994",    # album
    "Q16521",     # taxon
    "Q7889",      # video game
    "Q4167410",   # Wikimedia disambiguation page — many tech acronyms (SQL/Git/AWS/…) have a
                  # disambiguation item that spuriously satisfies the P279* class closure; the real
                  # concept is a distinct QID, so disambiguation pages must be rejected outright.
    # Same-name non-tech homonyms that outrank the real concept: field-name skills (AI, ML, NLP)
    # collide with the academic JOURNAL of that name; product names collide with magazines. Journals
    # and magazines carry these standard P31s, so denying them lets the real field/tech item win.
    "Q5633421",   # scientific journal
    "Q737498",    # academic journal
    "Q41298",     # magazine
    "Q1002697",   # periodical
)
# Second, description-based precision guard (offline, robust): an anchor whose fetched Wikidata
# description reads as a settlement / periodical / creative work / place is a same-name homonym, not
# the technology — drop it. Complements the class deny for cases with many distinct P31 QIDs (cities,
# communes) that are impractical to enumerate as deny classes. Terse WD descriptions start with the
# type ("city in the United States", "scientific journal", "commune in …"), so these match safely.
# Patterns are deliberately specific (matched against a terse WD description) to avoid dropping a
# legitimate tech item whose description merely mentions a word — e.g. "video game development
# framework" (SpriteKit) or "…in a single executable file" (BusyBox) must NOT be flagged. Applied to
# skills/domains only; occupation anchors resolve via profession/occupation and are not homonym-prone.
WIKIDATA_NONIT_DESC_PATTERNS = (
    r"\b(city|town|village|municipality|commune|hamlet|borough|county|province|prefecture|"
    r"human settlement|census-designated place)\b",
    r"\b(journal|magazine|periodical|newspaper|manga|book series|anthology)\b",
    r"\bcomic books?\b|\bcomics\b|\bgraphic novel\b",
    r"\b(feature film|film directed|album by|studio album|song by|musical group|rock band)\b",
    r"\b(river|mountain|lake|island|airport|railway station|crater|asteroid|moth|butterfly)\b",
    r"\b(given name|surname|family name|first name|footballer|politician|actor|actress)\b",
    r"\bvideo game (publisher|developer|company|console|series)\b",
    r"\b(19|20)\d\d video game\b",
    # Tech-adjacent homonyms: a field/topic name that matched its Q&A site or a Wikimedia-internal
    # page, not the concept. Kept specific so real web tools (WordPress, Cloudflare, Stack Overflow,
    # phpBB, Google Sites) are NOT dropped.
    r"\bStack Exchange site\b",
    r"\bWikimedia (template|category|module|project|permanent duplicate|duplicat)",
    r"\bsystem tray\b",
    r"\bnews (website|site|and media website)\b",
)

# --------------------------------------------------------------------------------------
# Graph export (`--export`): materialize the unified concept graph as RDF/OWL (Turtle, SKOS),
# GraphML + nodes/edges JSON, and a self-contained interactive HTML overview. Read-only over kb/;
# writes only to export/. The graph is the deduplicated CONCEPT layer (entity ids remapped to their
# unified concept via member_entity_ids; taxonomy + ISCO nodes keep their own ids).
# --------------------------------------------------------------------------------------
EXPORT_OUT_DIR = os.path.join(ROOT, "export")
EXPORT_TTL = os.path.join(EXPORT_OUT_DIR, "jobkb.ttl")        # RDF/OWL Turtle (SKOS + jobkb ontology)
EXPORT_GRAPHML = os.path.join(EXPORT_OUT_DIR, "jobkb.graphml")  # Gephi / Cytoscape / yEd
EXPORT_JSON = os.path.join(EXPORT_OUT_DIR, "jobkb.json")     # nodes/edges (Neo4j / web viz)
EXPORT_HTML = os.path.join(EXPORT_OUT_DIR, "jobkb.html")     # self-contained interactive overview
EXPORT_FORMATS = ("rdf", "graphml", "json", "viz")
# Namespaces for the RDF export. JOBKB_NS mints an IRI per concept from its unified_id/entity_id;
# WD_NS points skos:exactMatch/closeMatch anchors at real Wikidata entities.
JOBKB_NS = "https://w3id.org/jobkb/"
JOBKB_ONT = "https://w3id.org/jobkb/ontology#"
WD_NS = "http://www.wikidata.org/entity/"
