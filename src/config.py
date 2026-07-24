"""Central configuration. Leaf module so every stage can import it."""

from __future__ import annotations
import os

# Paths
SRC_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(SRC_DIR)
RESOURCES = os.path.join(ROOT, "resources")


def _load_dotenv(path=os.path.join(ROOT, ".env")):
    """Load KEY=VALUE lines from a project-root .env into os.environ (without overriding)."""
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

# KB validation (--validate): external gold benchmark + LLM-connection audit (read-only).
VALIDATION_RES_DIR = os.path.join(RESOURCES, "validation")
VALIDATION_OUT_DIR = os.path.join(ROOT, "validation")
VALIDATION_DATASETS = {
    # name -> (subdir, splits, has tags_knowledge, has source col, language)
    "skillspan":  ("skillspan",  ("train", "dev", "test"), True,  True,  "en"),
    "sayfullina": ("sayfullina", ("train", "dev", "test"), False, False, "en"),
    "fijo":       ("fijo",       ("train", "dev", "test"), False, False, "fr"),
}
SAYFULLINA_CLUSTERS_CSV = os.path.join(VALIDATION_RES_DIR, "sayfullina", "sayfullina_clusters.csv")
VALIDATION_SEMANTIC_MIN = 0.75         # bge-m3 cosine floor for "semantically covered"
VALIDATION_ANON_TOKENS = ("<organization>", "<address>", "<location>", "<anon_company>", "<anon_misc>")
VALIDATION_LINK_NLI_MIN = 0.50         # occ-def |= "requires {skill}" entailment floor
VALIDATION_DEMAND_SEMANTIC_MIN = 0.75  # demand-corroboration embedding floor

# Knowledge-base schema (English-primary; French secondary when present)

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
# Taxonomy tiers live as rows in skills.csv tagged by esco_skill_type; this marks them so
# hierarchy/merge/qa can exclude them from the real-skill set.
TAXONOMY_SKILL_MARKERS = ("skill_type", "skill_domain", "skill_category")
REL_FIELDS = ["occupation_entity_id", "skill_entity_id", "relation_type", "source", "weight"]
HIERARCHY_FIELDS = ["parent_entity_id", "child_entity_id", "entity_kind", "relation_type", "source"]
ALIGNMENT_FIELDS = [
    "entity_id_a", "source_a", "entity_id_b", "source_b",
    "relation", "confidence", "method", "validated", "merge", "notes",
]
# `description`/`description_source`: single concept description, precedence source -> wikidata -> llm.
# wikidata_* columns are filled by wikidata.enrich_rows() and never overwrite KB-authored text.
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
# Wikidata side table (--wikidata). `relation` is SKOS-typed (exactMatch/closeMatch) for RDF export.
WIKIDATA_LINKS_FIELDS = [
    "entity_id", "entity_kind", "unified_id", "label_en", "qid", "relation", "wikidata_url",
    "wd_label", "wd_description", "wd_aliases_en", "wd_aliases_fr",
    "instance_of", "match_method", "confidence",
]
# Resolution snapshot keyed by (norm_label, kind); empty qid = verified-unresolved (cached for offline).
WIKIDATA_SNAPSHOT_FIELDS = [
    "norm_label", "entity_kind", "qid", "wd_label", "wd_description",
    "wd_aliases_en", "wd_aliases_fr",
    "instance_of", "match_method", "confidence",
]

# IT-domain scope per source
# ISCO-08 sub-majors 25 (ICT professionals) + 35 (ICT technicians) + minor 133 (ICT service managers).
ISCO_IT_SUBMAJORS = ("25", "35")
ISCO_IT_MINORS = ("133",)  # ICT service managers

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


# ROME: domain M18 (info systems & telecom) + a few cross-branch IT/data métiers; exclude
# non-IT M18 (meteorology/cartography/geomatics) by label keyword.
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

# Source tags
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

# Sources that set their own it_subtype at ingest (the hierarchy keeps it rather than re-deriving
# from the label regex) — their shipped/derived classification beats a keyword match on a bare label.
SELF_CLASSIFIED_SUBDOMAIN_SOURCES = {SRC_SFIA, SRC_CSO, SRC_LIGHTCAST, SRC_KAGGLE, SRC_ECF,
                                     SRC_DATAJOBS, SRC_ZENODO, SRC_WEF, SRC_SOFTTAXO}

# CSO 3.5 is ~14.6k CS research topics; keep only the shallow IT-relevant part: descendants of these
# roots (via superTopicOf) down to CSO_MAX_DEPTH, deduped/capped. Roots ordered specific->generic.
CSO_ROOTS = (
    "computer_security", "machine_learning", "artificial_intelligence", "data_mining",
    "information_retrieval", "computer_networks", "human_computer_interaction",
    "computer_operating_systems", "software_engineering", "computer_programming",
    "internet", "software",
)
CSO_MAX_DEPTH = 2
# Per-branch cap keeps the subset balanced (CSO is AI-heavy; a global cap starves networks/data/web).
CSO_MAX_PER_BRANCH = 80
CSO_MAX_TOPICS = 700
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

# Evidence / demand relation sources (ADEM vacancies, mined postings): weighted demand edges between
# existing entities (no new nodes). ADEM keeps ROME IT families (M18*); JOBS keeps pairs seen >= min freq.
ADEM_ROME_PREFIX = "M18"
JOBS_MIN_FREQ = 2

# DATAJOBS (lukebarousse/data_jobs): 785k postings. Hybrid — harvests high-frequency absent tools as new
# skills (self-classified via job_type_skills) + adds weighted demand relations.
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

# ZENODO (Zenodo 3906955, Stack Overflow postings): hybrid like DATAJOBS but ~45x smaller, so gates
# are lower. Harvests absent hard tools + adds demand for both hard skills and the SOFTSKILLS vocabulary.
ZENODO_MIN_FREQ = 15        # keep a (role, hard-skill) demand pair only if seen in >= this many postings
ZENODO_MIN_SOFT_FREQ = 8    # soft-skill demand is legitimately sparser
ZENODO_MIN_SKILL_FREQ = 25  # harvest an absent hard token as a new skill only above this frequency
ZENODO_HL_SUBDOMAIN = {
    "Languages": "programming_languages",
    "Data Systems": "data_databases",
    "OS & Infrastructure": "systems_infrastructure",
    "Process & Methods": "methodology",
    "Libs & Frameworks": "",   # mixed web/backend/ML frameworks -> regex fallback
    "Development Tools": "",    # mixed (git/docker/jira/...) -> regex fallback
    "INVALIDO": "",
}

# DJINNI (~142k EN IT postings, role tag + free-text JD). Relation-only demand: skills extracted from
# the JD by strict full-label matching against concrete-tech labels only (the augmented/vendor-strip
# matcher is unsafe on prose — matches "teams"/"application"); single tokens >= 4 chars minus a denylist.
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

# LINKEDIN_SWE (~9.4k SWE postings, pre-extracted skills). Relation-only demand (no harvest — its
# job_skills mixes generic phrases that would pollute the vocabulary).
LINKEDIN_SWE_MIN_FREQ = 15        # keep a (role, skill) demand pair only if seen in >= this many postings

# KAGGLE_JOBS (kaggle job-skill-set, IT subset = 240 postings). Demand only; harvest off (too few rows).
KAGGLE_JOBS_MIN_FREQ = 3          # keep a (role, skill) demand pair only if seen in >= this many postings

# HuggingFace models (open-source, no API keys)
# Embedder bge-m3: strong EN<->FR similarity, no query/passage prefix. Falls back to MiniLM, then TF-IDF.
EMBED_MODEL_PRIMARY = os.environ.get("JOBKB_EMBED_MODEL", "BAAI/bge-m3")
EMBED_MODEL_FALLBACK = os.environ.get(
    "JOBKB_EMBED_MODEL_FALLBACK", "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")
# mDeBERTa NLI: verifies semantic occupation merges (mutual entailment on definitions), not just SKOS
# labels — merges are model-verified since there is no human review.
NLI_MODEL = os.environ.get("JOBKB_NLI_MODEL",
                           "MoritzLaurer/mDeBERTa-v3-base-mnli-xnli")
NLI_BATCH_SIZE = 16
EMBED_BATCH_SIZE = 32

# LLM enrichment (--llm): HF Inference Providers primary, local transformers fallback, fail-open.
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

# Skill categories eligible for LLM description generation = all hard categories from
# hierarchy.CATEGORIES (mirrored here to avoid a config<-hierarchy import cycle).
LLM_DESC_SKILL_SUBDOMAINS = frozenset({
    "programming_languages", "methodology", "web", "mobile_development", "data_databases",
    "data_engineering", "ai_ml", "systems_infrastructure", "cloud_devops", "hardware_embedded",
    "networks", "security", "it_management", "emerging_tech", "knowledge_general", "other_hard",
})
LLM_DESC_MAX_TARGETS = int(os.environ.get("JOBKB_LLM_DESC_MAX", "0"))  # 0 = unlimited (bounds API cost)
LLM_SNAPSHOT_FIELDS = ["task", "key", "model", "prompt_hash", "output", "created_at"]
LLM_REJECTED_FIELDS = ["task", "entity_id", "label", "output", "reason", "score"]

# Agentic enrichment (--agent, LangGraph): controller + reflective workers over the LLM_* tools.
# Reuses the same generations.csv snapshot (agent rows tagged model="agentic"); the LLM is optional,
# the deterministic verifiers drive control (the anchor worker needs no LLM).
AGENT_GAPS = ("description", "link", "emerging", "anchor")   # workers the controller can dispatch
AGENT_MAX_REFLECT = int(os.environ.get("JOBKB_AGENT_MAX_REFLECT", "2"))  # bounded retries per target
AGENT_LINK_NLI_MIN = VALIDATION_LINK_NLI_MIN  # links must clear cosine AND this NLI floor to be committed
AGENT_ANCHOR_MAX = int(os.environ.get("JOBKB_AGENT_ANCHOR_MAX", "200"))  # cap unattempted anchors/run
AGENT_OUT_DIR = os.path.join(ROOT, "agent")
AGENT_REPORT_MD = os.path.join(AGENT_OUT_DIR, "report.md")
AGENT_TAG = "agentic"                                        # snapshot `model` marker for agent commits

# Multilingual label completion (--translate): fill empty EN/FR labels from Wikidata labels, then local
# NLLB MT with a tech-term guard, each cross-lingually validated. Never overwrites a non-empty cell.
TRANSLATE_MT_MODEL = os.environ.get("JOBKB_TRANSLATE_MODEL", "facebook/nllb-200-distilled-600M")
TRANSLATE_LANG_CODES = {"en": "eng_Latn", "fr": "fra_Latn"}   # NLLB BCP-47-ish codes
TRANSLATE_MAX_NEW_TOKENS = 96          # labels are short; caps runaway generation
TRANSLATE_BATCH_SIZE = 16              # MT batch size (CPU)
TRANSLATE_XLING_MIN = 0.62             # cross-lingual bge-m3 floor, src vs output (back-translation
                                       # round-trip was too noisy on short labels; structural filters catch the rest)
# Output looks like a generated sentence, not a label -> reject (MT sometimes describes instead of names).
TRANSLATE_SENTENCE_STARTS = ("je ", "j'", "nous ", "vous ", "il s'agit", "c'est ", "cela ",
                             "i am ", "i'm ", "we ", "it is ", "this is ", "there ")
TRANSLATE_LEN_RATIO_MIN = 0.30         # output/source char-length ratio bounds (reject collapses/blow-ups)
TRANSLATE_LEN_RATIO_MAX = 3.50
TRANSLATE_ROME_EN_ENABLED = os.environ.get("JOBKB_TRANSLATE_ROME_EN", "1") == "1"  # fr->en for ROME rows
TRANSLATE_MAX_TARGETS = int(os.environ.get("JOBKB_TRANSLATE_MAX", "0"))  # 0 = unlimited (bounds runtime)
# Tech terms kept verbatim (never MT'd). Token-level heuristics (acronyms/CamelCase/versions) run in
# code; this covers common lowercase terms they miss.
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

# Alignment tunables
EMBED_TOPK = 5             # candidate neighbours per entity, per source pair
EMBED_THRESHOLD = 0.50     # recall-oriented cosine floor for candidate generation
SKOS_EXACT_MIN = 0.90      # >= exactMatch
SKOS_CLOSE_MIN = 0.70      # >= closeMatch, else relatedMatch
NLI_ENTAIL_MIN = 0.60      # entailment prob to count a direction as entailed
NLI_MIN_SIM = 0.70         # NLI-score every merge-candidate occ pair from here up (bge-m3: random pairs
                           # ~0.57, true EN<->FR matches ~0.72-0.79) — few clear it, so ~no extra cost

# Merge (de-duplication) thresholds — source-neutral, precision-first. Semantic occupation merges are
# triple-guarded (this floor + same ISCO group in merge.py + mutual NLI entailment in verify.py).
MERGE_EMBED_OCC = 0.72     # embedding floor for a semantic occupation merge (NLI + ISCO gated)
MERGE_EMBED_SKILL = 0.90   # near-identical embedding floor for a skill merge (no NLI gate)

# Deterministic same-concept dedup (align): merge skills sharing an identical match_key even when
# candidate generation missed the pair. MATCH_KEY_DISTINCT = keys to leave alone (they collide across
# distinct concepts: "http"<->"https"; the Master's-qualified "cybersecurity expert" variant).
MATCH_KEY_DISTINCT = frozenset({"http", "cybersecurity expert"})

# Authoritative it_subtype for skills whose members disagree across sources; applied in merge after the
# member majority, keyed by normalize_label(primary_en).
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

# Attachment (source -> ISCO group): embedding shortlists the top-K, NLI entailment (occ def -> group
# def) re-ranks. Flagged low-confidence (surfaced by QA, never dropped) when chosen sim < ATTACH_MIN_SIM.
# The flag uses sim, not entailment/margin (both are poor absolute signals for broader-group attaches).
ATTACH_MIN_SIM = 0.60
ATTACH_TOPK = 3            # embedding shortlist size that NLI re-ranks
ATTACH_NLI_WEIGHT = 0.5   # weight of NLI entailment vs embedding cosine in the re-rank score

# Curated ISCO overrides for emerging roles the auto-attach placed poorly (all were low-confidence).
# Keyed by occupation source_id -> ISCO code; applied in attach before the auto choice.
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

# Relevance / noise gate (src/relevance.py) — screens every pluggable StructuredSource at ingest:
# malformed labels + confidently non-IT entities are blocked (logged), the rest kept. Lenient by design.
# bge-m3 cosines run high for everything, so the discriminator is a clearly-higher non-IT similarity
# (sim_non >= REL_NONIT_HI AND a positive margin over IT), then blocked only if NLI also says non-IT.
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

# Wikidata enrichment (`--wikidata`) — resolve KB tech-skills/occupations to stable QIDs.
# Network READ-only via ONE batched SPARQL query per ~50 labels (label/alias match + class
# verification together). Every resolution is snapshotted to WIKIDATA_SNAPSHOT_CSV so rebuilds
# are offline/reproducible and interrupted runs resume. Precision: exact/alias label match AND an
# instance-of class check — QIDs are never hardcoded (all verified live).
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
WIKIDATA_SKILL_MAX_TOKENS = 3  # only short (entity-like) labels are candidates

# Wikidata aliases merged into alt_labels are hygiene-filtered (dedup, bounds, structural noise).
WIKIDATA_MAX_ALIASES = 8
WIKIDATA_ALIAS_MAX_TOKENS = 4
WIKIDATA_ALIAS_MAX_CHARS = 40

# instance-of (P31) / subclass-of (P279*) allowlist for concrete tech.
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
# Abstract IT fields/disciplines, matched by DIRECT P31 (P279* closure over these roots times out).
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
# Domain nodes are anchored via English label PROBES (their display labels are composite and never
# exact-match). Probes use Wikidata's exact (mostly lowercase) label case — Title Case hits disambig
# pages. First probe that resolves + class-verifies wins. dom_cross/dom_soft have no clean concept.
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
WIKIDATA_DOMAIN_FIELD_CLASSES = WIKIDATA_SKILL_FIELD_CLASSES + ("Q131339603",)  # + type of infrastructure
# Reject a candidate whose instance-of hits any of these, even on a label match. Q4167410
# (disambiguation) spuriously passes the P279* closure for many tech acronyms; journals/magazines are
# same-name homonyms of field skills (AI/ML/NLP) — denying them lets the real item win.
WIKIDATA_DENY_CLASSES = (
    "Q5",         # human
    "Q11424",     # film
    "Q482994",    # album
    "Q16521",     # taxon
    "Q7889",      # video game
    "Q4167410",   # Wikimedia disambiguation page
    "Q5633421",   # scientific journal
    "Q737498",    # academic journal
    "Q41298",     # magazine
    "Q1002697",   # periodical
)
# Description-based homonym guard (skills/domains only): drop an anchor whose terse Wikidata description
# reads as a settlement/periodical/creative-work/place. Patterns are specific so real tech items (whose
# description merely mentions such a word) are not flagged.
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
    # tech-adjacent homonyms (Q&A site / Wikimedia page), specific so real web tools aren't dropped
    r"\bStack Exchange site\b",
    r"\bWikimedia (template|category|module|project|permanent duplicate|duplicat)",
    r"\bsystem tray\b",
    r"\bnews (website|site|and media website)\b",
)

# Graph export (--export): the deduplicated concept graph as RDF/OWL Turtle, GraphML, JSON and
# self-contained HTML. Read-only over kb/, writes to export/.
EXPORT_OUT_DIR = os.path.join(ROOT, "export")
EXPORT_TTL = os.path.join(EXPORT_OUT_DIR, "jobkb.ttl")        # RDF/OWL Turtle (SKOS + jobkb ontology)
EXPORT_GRAPHML = os.path.join(EXPORT_OUT_DIR, "jobkb.graphml")  # Gephi / Cytoscape / yEd
EXPORT_JSON = os.path.join(EXPORT_OUT_DIR, "jobkb.json")     # nodes/edges graph JSON
EXPORT_HTML = os.path.join(EXPORT_OUT_DIR, "jobkb.html")     # interactive backbone overview
EXPORT_HTML_FULL = os.path.join(EXPORT_OUT_DIR, "jobkb_full.html")  # interactive full-graph viz
EXPORT_FORMATS = ("rdf", "graphml", "json", "viz", "fullviz")
# RDF namespaces: JOBKB_NS mints a concept IRI per unified_id/entity_id; WD_NS points at Wikidata.
JOBKB_NS = "https://w3id.org/jobkb/"
JOBKB_ONT = "https://w3id.org/jobkb/ontology#"
WD_NS = "http://www.wikidata.org/entity/"
