"""Central configuration"""

from __future__ import annotations
import os

# Paths
SRC_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(SRC_DIR)
RESOURCES = os.path.join(ROOT, "resources")


def _load_dotenv(path=os.path.join(ROOT, ".env")):
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
# Skills-only frameworks: SFIA and CSO
SFIA_EN_DIR = os.path.join(RESOURCES, "SFIA", "en")
CSO_EN_DIR = os.path.join(RESOURCES, "CSO", "en")
LIGHTCAST_EN_DIR = os.path.join(RESOURCES, "LIGHTCAST", "en")
OTHERS_EN_DIR = os.path.join(RESOURCES, "OTHERS", "en")
# Zenodo (Stack Overflow IT job postings + companion hard-skill category).
ZENODO_DIR = os.path.join(OTHERS_EN_DIR, "zenodo")
ZENODO_JOBS_CSV = os.path.join(ZENODO_DIR, "jobs_complete.csv")
ZENODO_HL_CSV = os.path.join(ZENODO_DIR, "high-level-hard-skills.csv")
# WEF Global Skills Taxonomy + Education 4.0 (soft-skill enrichment).
WEF_SOFT_DIR = os.path.join(OTHERS_EN_DIR, "Soft-skills")
WEF_GLOBAL_CSV = os.path.join(WEF_SOFT_DIR, "Global-Skills-Taxonomy.csv")
WEF_COMPETENCIES_CSV = os.path.join(WEF_SOFT_DIR, "Skills-Taxonomy-Competencies.csv")
WEF_EDUCATION_CSV = os.path.join(WEF_SOFT_DIR, "Education4.0.csv")
# Job-posting demand datasets
DJINNI_CSV = os.path.join(OTHERS_EN_DIR, "djinni-recruitment-dataset-job-descriptions-english.csv")
LINKEDIN_SWE_CSV = os.path.join(OTHERS_EN_DIR, "kaggle-LinkedIn-Software-Engineering-Jobs-Dataset.csv")
KAGGLE_JOBS_CSV = os.path.join(OTHERS_EN_DIR, "kaggle-job-skill-set.csv")
# Wikidata enrichment
WIKIDATA_EN_DIR = os.path.join(RESOURCES, "WIKIDATA", "en")
WIKIDATA_RETRIEVED_DIR = os.path.join(RESOURCES, "WIKIDATA", "retrieved")
WIKIDATA_SRC_CSV = os.path.join(WIKIDATA_EN_DIR, "ESCO_v1.2.1-wikidata.csv")
WIKIDATA_SNAPSHOT_CSV = os.path.join(WIKIDATA_RETRIEVED_DIR, "resolutions.csv")

# Web-scraping enrichment
SCRAPED_DIR = os.path.join(RESOURCES, "SCRAPED")
SCRAPED_FIELDS = ["site", "url", "lang", "title", "company", "location", "text",
                  "tags", "posted_at", "retrieved_at"]

LLM_RETRIEVED_DIR = os.path.join(RESOURCES, "LLM", "retrieved")   # LLM generation snapshots
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
TRANSLATE_SNAPSHOT_CSV = os.path.join(TRANSLATE_RETRIEVED_DIR, "translations.csv")  # cached MT
TRANSLATE_WD_LABELS_CSV = os.path.join(TRANSLATE_RETRIEVED_DIR, "wd_labels.csv")    # authoritative @en/@fr
TRANSLATE_REJECTED_CSV = os.path.join(KB_DIR, "translate_rejected.csv")  # MT outputs that failed validation
WIKIDATA_LINKS_CSV = os.path.join(KB_DIR, "wikidata_links.csv")      # entity -> Wikidata QID anchors

# KB validation: external benchmark + LLM-connection audit
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
VALIDATION_LINK_NLI_MIN = 0.50         # occ-def entailment floor
VALIDATION_DEMAND_SEMANTIC_MIN = 0.75  # demand-corroboration embedding floor



# Knowledge-base schema

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
# Taxonomy tiers tagged by esco_skill_type
TAXONOMY_SKILL_MARKERS = ("skill_type", "skill_domain", "skill_category")
REL_FIELDS = ["occupation_entity_id", "skill_entity_id", "relation_type", "source", "weight"]
HIERARCHY_FIELDS = ["parent_entity_id", "child_entity_id", "entity_kind", "relation_type", "source"]
ALIGNMENT_FIELDS = [
    "entity_id_a", "source_a", "entity_id_b", "source_b",
    "relation", "confidence", "method", "validated", "merge", "notes",
]
# `description`/`description_source`: single concept description, precedence source -> wikidata -> llm.
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
# Wikidata side table
WIKIDATA_LINKS_FIELDS = [
    "entity_id", "entity_kind", "unified_id", "label_en", "qid", "relation", "wikidata_url",
    "wd_label", "wd_description", "wd_aliases_en", "wd_aliases_fr",
    "instance_of", "match_method", "confidence",
]
# Resolution snapshot keyed by (norm_label, kind)
WIKIDATA_SNAPSHOT_FIELDS = [
    "norm_label", "entity_kind", "qid", "wd_label", "wd_description",
    "wd_aliases_en", "wd_aliases_fr",
    "instance_of", "match_method", "confidence",
]

# IT-domain scope per source
# ISCO-08 sub-majors 25 (ICT professionals) + 35 (ICT technicians) + minor 133 (ICT service managers).
ISCO_IT_SUBMAJORS = ("25", "35")
ISCO_IT_MINORS = ("133",) 

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
    code = (code or "").strip()
    return code.startswith(ISCO_IT_SUBMAJORS) or code.startswith(ISCO_IT_MINORS)


# ONET: Computer occupations (SOC 15-12xx) + Data Scientists (15-2051) + IT managers (11-3021).
ONET_IT_SOC_PREFIXES = ("15-12",)
ONET_IT_SOC_EXTRA = {"15-2051", "11-3021"}


def is_onet_it(onet_soc_code: str) -> bool:
    soc = (onet_soc_code or "").strip()[:7]
    return soc.startswith(ONET_IT_SOC_PREFIXES) or soc in ONET_IT_SOC_EXTRA


# NOC 2021 (5-digit): computer/software professionals & developers (minors 2122, 2123),
NOC_IT_MINOR_PREFIXES = ("2122", "2123")
NOC_IT_UNIT_GROUPS = {
    "20012",  # Computer and information systems managers
    "21211",  # Data scientists
    "21311",  # Computer engineers
    "22220",  # Computer network and web technicians
    "22221",  # User support technicians
    "22222",  # Information systems testing technicians
}


def is_noc_it(code: str) -> bool:
    code = (code or "").strip()
    return code.startswith(NOC_IT_MINOR_PREFIXES) or code in NOC_IT_UNIT_GROUPS


# ROME: domain M18 (info systems & telecom) + a few cross-branch IT/data métiers
ROME_DOMAIN_IN_SCOPE = "M18"
ROME_IT_EXTRA_CODES = {"M1405", "M1419", "M1423", "M1426"}
ROME_EXCLUDE_LABEL_KEYWORDS = ("meteo", "cartograph", "geomat", "climat", "topograph")


def is_rome_it(code: str, label: str = "") -> bool:
    code = (code or "").strip()
    in_scope = code.startswith(ROME_DOMAIN_IN_SCOPE) or code in ROME_IT_EXTRA_CODES
    if not in_scope:
        return False
    from .common import normalize_label
    norm = normalize_label(label)
    return not any(kw in norm for kw in ROME_EXCLUDE_LABEL_KEYWORDS)

# Source tags
SRC_ESCO = "ESCO"
SRC_ISCO = "ISCO"
SRC_ONET = "ONET"
SRC_NOC = "NOC"
SRC_ROME = "ROME"
SRC_SFIA = "SFIA"  
SRC_CSO = "CSO"     
SRC_LIGHTCAST = "LIGHTCAST"
SRC_KAGGLE = "KAGGLE"       
SRC_ECF = "ECF"        
SRC_ADEM = "ADEM"          
SRC_JOBS = "JOBS"          
SRC_DATAJOBS = "DATAJOBS"  
SRC_ZENODO = "ZENODO"       
SRC_EMERGING = "EMERGING"    
SRC_SOFTSKILLS = "SOFTSKILLS"  
SRC_SOFTTAXO = "SOFTTAXO"   
SRC_WEF = "WEF"             
SRC_DJINNI = "DJINNI"   
SRC_LINKEDIN_SWE = "LINKEDIN_SWE" 
SRC_KAGGLE_JOBS = "KAGGLE_JOBS"   
SRC_SCRAPER = "SCRAPER"     
SRC_LLM = "LLM"              
SRC_TRANSLATE = "TRANSLATE" 

# Sources that contribute real occupations that get aligned.
REAL_OCC_SOURCES = (SRC_ESCO, SRC_ONET, SRC_NOC, SRC_ROME, SRC_EMERGING)

# Sources that set their own it_subtype at ingest.
SELF_CLASSIFIED_SUBDOMAIN_SOURCES = {SRC_SFIA, SRC_CSO, SRC_LIGHTCAST, SRC_KAGGLE, SRC_ECF,
                                     SRC_DATAJOBS, SRC_ZENODO, SRC_WEF, SRC_SOFTTAXO, SRC_SCRAPER}

# CSO 3.5: keep only the IT-relevant part
CSO_ROOTS = (
    "computer_security", "machine_learning", "artificial_intelligence", "data_mining",
    "information_retrieval", "computer_networks", "human_computer_interaction",
    "computer_operating_systems", "software_engineering", "computer_programming",
    "internet", "software",
)
CSO_MAX_DEPTH = 2
# Per-branch cap keeps the subset balanced.
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

# Evidence / demand relation sources.
ADEM_ROME_PREFIX = "M18"
JOBS_MIN_FREQ = 2

# DATAJOBS
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

# ZENODO
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

# DJINNI
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

# LINKEDIN_SWE
LINKEDIN_SWE_MIN_FREQ = 15        # keep a (role, skill) demand pair only if seen in >= this many postings

# Kaggle job-skill-set
KAGGLE_JOBS_MIN_FREQ = 3          # keep a (role, skill) demand pair only if seen in >= this many postings

# SCRAPER 
SCRAPER_MIN_SKILL_FREQ = 4     # harvest a novel span as a new skill only at/above this posting frequency
SCRAPER_MIN_OCC_FREQ = 2       # mint a cleaned role only at/above this (+ it must end in an occupational head)
SCRAPER_MIN_DEMAND_FREQ = 2    # keep a (title, skill) demand pair only at/above this frequency
SCRAPER_TITLE_MAX_WORDS = 4    # a cleaned role longer than this reads as an over-specific title -> skip
# Self-classify a harvested novel skill into an it_subtype by keyword
SCRAPER_SUBDOMAIN = {
    "docker": "cloud_devops", "kubernetes": "cloud_devops", "terraform": "cloud_devops",
    "ansible": "cloud_devops", "jenkins": "cloud_devops", "gitlab ci": "cloud_devops",
    "react": "web", "angular": "web", "vue": "web", "svelte": "web", "next.js": "web",
    "flutter": "mobile_development", "swiftui": "mobile_development", "jetpack compose": "mobile_development",
    "pytorch": "ai_ml", "tensorflow": "ai_ml", "hugging face": "ai_ml", "langchain": "ai_ml",
    "llm": "ai_ml", "rag": "ai_ml", "mlflow": "ai_ml",
    "snowflake": "data_databases", "dbt": "data_engineering", "airflow": "data_engineering",
    "kafka": "data_engineering", "databricks": "data_engineering",
    "kotlin": "programming_languages", "rust": "programming_languages", "golang": "programming_languages",
    "solidity": "emerging_tech", "web3": "emerging_tech",
}
# Title cleaning
SCRAPER_TITLE_STOPWORDS = frozenset({
    "senior", "junior", "lead", "principal", "staff", "confirme", "confirmee", "expert", "expert(e)",
    "experimente", "experimentee", "debutant", "debutante", "stagiaire", "apprenti", "apprentie",
    "alternant", "alternante", "h", "f", "h/f", "f/h", "m/f", "m/w", "w/m", "cdi", "cdd", "stage",
    "alternance", "apprentissage", "freelance", "interim", "temps", "plein", "partiel", "remote",
    "teletravail", "hybride", "onsite", "fulltime", "part", "time", "contract", "permanent",
    "intern", "internship", "trainee", "graduate",
})

# HF neural skill-span extractor
SCRAPER_EXTRACTOR_MODEL = os.environ.get("JOBKB_SCRAPER_EXTRACTOR",
                                         "algiraldohe/lm-ner-linkedin-skills-recognition")
SCRAPER_EXTRACTOR_ENABLED = os.environ.get("JOBKB_SCRAPER_NEURAL", "1") == "1"

# Crawl bounds + network etiquette
SCRAPER_USER_AGENT = "Mozilla/5.0 (compatible; JobKB/1.0; +IT knowledge-base research)"
SCRAPER_RATE_SLEEP = 1.50        # seconds between requests
SCRAPER_MAX_RETRIES = 4          # attempts on 5xx/timeout, then fail-open (skip the page)
SCRAPER_TIMEOUT = 30             # per-request seconds
SCRAPER_MAX_PAGES = 5            # listing pages crawled per HTML board per run
SCRAPER_MAX_POSTINGS = 400       # total postings kept per adapter per run
SCRAPER_MAX_PER_QUERY = 100      # cap per API category/industry sweep call
SCRAPER_ATS_MAX_PER_TOKEN = 40   # cap IT postings kept per ATS company token
SCRAPER_RESPECT_ROBOTS = True    # honour robots.txt

# --- Multi-source acquisition (Tier A keyless APIs / Tier B ATS boards / Tier C trend signals) ---------
SCRAPER_TIERS = {
    "apis":   ["jobicy", "remotive", "remoteok", "themuse", "wwr"],
    "ats":    ["ats"],
    "trends": ["hn", "github", "stackoverflow"],
}
# Tier A — server-side category/industry filters
JOBICY_INDUSTRIES = ("dev", "data-science", "engineering", "devops-sysadmin",
                     "cybersecurity", "qa-testing", "technical-support")
REMOTIVE_CATEGORIES = ("software-development", "data", "devops", "qa",
                       "information-technology", "artificial-intelligence")
THEMUSE_CATEGORIES = ("Software Engineering", "Data Science", "Computer and IT")
WWR_FEEDS = ("remote-programming-jobs", "remote-devops-sysadmin-jobs",
             "remote-back-end-programming-jobs", "remote-front-end-programming-jobs",
             "remote-full-stack-programming-jobs")
# Tier B — curated, live-verified public ATS board tokens
SCRAPER_ATS_BOARDS = (
    [("greenhouse", t) for t in (
        "stripe", "airbnb", "gitlab", "coinbase", "databricks", "cloudflare", "robinhood", "datadog",
        "reddit", "dropbox", "discord", "mongodb", "pinterest", "instacart", "twilio", "asana", "lyft",
        "elastic")]
    + [("ashby", t) for t in ("openai", "notion", "ramp", "linear", "replit", "clickhouse", "posthog")]
    + [("lever", t) for t in ("palantir", "gopuff", "unlimit")]
)
# Tier C — emerging-tech trend signals.
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")
GITHUB_TREND_TOPICS = ("llm", "rag", "ai-agents", "vector-database", "webassembly", "rust",
                       "kubernetes", "observability", "mlops", "data-engineering")
SCRAPER_TREND_MIN_STARS = 200    # only established-enough repos count as a real emerging-tech signal

# Recency-weighted demand: recent postings weigh more, so `demand` tracks the current market.
SCRAPER_RECENCY_HALFLIFE_DAYS = 45.0
SCRAPER_RETENTION_DAYS = int(os.environ.get("JOBKB_SCRAPER_RETENTION", "120")) 

# HuggingFace models
# Embedder bge-m3: strong EN<->FR similarity, no query/passage prefix. Falls back to MiniLM, then TF-IDF.
EMBED_MODEL_PRIMARY = os.environ.get("JOBKB_EMBED_MODEL", "BAAI/bge-m3")
EMBED_MODEL_FALLBACK = os.environ.get(
    "JOBKB_EMBED_MODEL_FALLBACK", "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")
# mDeBERTa NLI: verifies semantic occupation merges (mutual entailment on definitions), not just SKOS
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
LLM_USE_LOCAL_FALLBACK = os.environ.get("JOBKB_LLM_LOCAL", "0") == "1"

# Validation thresholds for LLM outputs
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

# Skill categories eligible for LLM description generation
LLM_DESC_SKILL_SUBDOMAINS = frozenset({
    "programming_languages", "methodology", "web", "mobile_development", "data_databases",
    "data_engineering", "ai_ml", "systems_infrastructure", "cloud_devops", "hardware_embedded",
    "networks", "security", "it_management", "emerging_tech", "knowledge_general", "other_hard",
})
LLM_DESC_MAX_TARGETS = int(os.environ.get("JOBKB_LLM_DESC_MAX", "0"))  # 0 = unlimited
LLM_SNAPSHOT_FIELDS = ["task", "key", "model", "prompt_hash", "output", "created_at"]
LLM_REJECTED_FIELDS = ["task", "entity_id", "label", "output", "reason", "score"]

# Agentic enrichment (--agent, LangGraph)
AGENT_GAPS = ("description", "link", "emerging", "anchor")   # workers the controller can dispatch
AGENT_MAX_REFLECT = int(os.environ.get("JOBKB_AGENT_MAX_REFLECT", "2"))  # bounded retries per target
AGENT_LINK_NLI_MIN = VALIDATION_LINK_NLI_MIN  # links must clear cosine AND this NLI floor to be committed
AGENT_ANCHOR_MAX = int(os.environ.get("JOBKB_AGENT_ANCHOR_MAX", "200"))  # cap unattempted anchors/run
AGENT_OUT_DIR = os.path.join(ROOT, "agent")
AGENT_REPORT_MD = os.path.join(AGENT_OUT_DIR, "report.md")
AGENT_TAG = "agentic"                                   
AGENT_DESC_CHECKPOINT = int(os.environ.get("JOBKB_AGENT_DESC_CHECKPOINT", "25"))

# Multilingual label completion (--translate): fill empty EN/FR labels from Wikidata labels
TRANSLATE_MT_MODEL = os.environ.get("JOBKB_TRANSLATE_MODEL", "facebook/nllb-200-distilled-600M")
TRANSLATE_LANG_CODES = {"en": "eng_Latn", "fr": "fra_Latn"}
TRANSLATE_MAX_NEW_TOKENS = 96          
TRANSLATE_BATCH_SIZE = 16              
TRANSLATE_XLING_MIN = 0.62             # cross-lingual floor
                               
TRANSLATE_SENTENCE_STARTS = ("je ", "j'", "nous ", "vous ", "il s'agit", "c'est ", "cela ",
                             "i am ", "i'm ", "we ", "it is ", "this is ", "there ")
TRANSLATE_LEN_RATIO_MIN = 0.30         # output/source char-length ratio bounds
TRANSLATE_LEN_RATIO_MAX = 3.50
TRANSLATE_ROME_EN_ENABLED = os.environ.get("JOBKB_TRANSLATE_ROME_EN", "1") == "1"
TRANSLATE_MAX_TARGETS = int(os.environ.get("JOBKB_TRANSLATE_MAX", "0"))

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
NLI_MIN_SIM = 0.70         # NLI-score every merge-candidate occ pair from here up 

# Merge (de-duplication) thresholds
MERGE_EMBED_OCC = 0.72     # embedding floor for a semantic occupation merge
MERGE_EMBED_SKILL = 0.90   # near-identical embedding floor for a skill merge

# Deterministic same-concept dedup
MATCH_KEY_DISTINCT = frozenset({"http", "cybersecurity expert"})

# Authoritative it_subtype for skills whose members disagree across sources
IT_SUBTYPE_OVERRIDE = {
    "cypress": "web",                       
    "playwright": "web",                  
    "cdn": "cloud_devops",                  
    "consul": "cloud_devops",              
    "a/b testing": "methodology",           
    "test driven development": "methodology",
    "workflow software": "other_hard",
    "distributed computing": "knowledge_general",
    "computer science": "knowledge_general",
    "computer technology": "knowledge_general",
    "digital systems": "knowledge_general",
    "information systems": "knowledge_general",
    "cryptocurrency": "emerging_tech",      
}

# Attachment (source -> ISCO group)
ATTACH_MIN_SIM = 0.60
ATTACH_TOPK = 3            # embedding shortlist size that NLI re-ranks
ATTACH_NLI_WEIGHT = 0.5   # weight of NLI entailment vs embedding cosine in the re-rank score

# Curated ISCO overrides for emerging roles the auto-attach placed poorly
ISCO_OCC_OVERRIDE = {
    "M1405": "2511",   # Data scientist                 -> Systems Analysts
    "M1423": "1330",   # Chief Data Officer             -> ICT Service Managers
    "M1822": "2519",   # Spécialiste Jumeau Numérique   -> SW/Analysts n.e.c.
    "M1835": "2523",   # Architecte systèmes et réseaux -> Network Professionals
    "M1846": "2529",   # Ingénieur Cybersécurité        -> DB/Network Prof. n.e.c.
    "M1857": "2522",   # Urbaniste Datacenter           -> Systems Administrators
    "M1858": "1330",   # Chef de projet TMA             -> ICT Service Managers
    "M1864": "1330",   # Product Owner                  -> ICT Service Managers
    "M1865": "2512",   # Ingénieur blockchain           -> Software Developers
    "M1866": "2529",   # Pentesteur                     -> DB/Network Prof. n.e.c.
    "M1872": "2511",   # Consultant décisionnel (BI)    -> Systems Analysts
    "M1873": "2512",   # Spécialiste IA embarquée       -> Software Developers
    "M1875": "1330",   # Coordinateur MOA SI            -> ICT Service Managers
    "M1877": "2512",   # Développeur blockchain         -> Software Developers
    "M1881": "1330",   # Chef de projet MOA SI          -> ICT Service Managers
    "M1889": "2512",   # Ingénieur en IA                -> Software Developers
}

# Relevance / noise gate
RELEVANCE_GATE_ENABLED = True
REL_NONIT_HI = 0.65       # a candidate must score at least this cos to a non-IT domain anchor
REL_NONIT_MARGIN = 0.05   # a candidate must beat its own IT similarity by at least this margin
REL_NLI_MIN = 0.15        # if NLI entailment "...is about IT" is below this -> BLOCK non-IT

# Curated IT seed vocabulary
REL_IT_SEED = (
    "software development and programming", "computer networks and telecommunications",
    "cybersecurity and information security", "databases and data engineering",
    "artificial intelligence and machine learning", "cloud computing and devops",
    "web and mobile application development", "operating systems and IT infrastructure",
    "IT service management and governance", "data analytics and business intelligence",
    "computer hardware and embedded systems", "information technology",
)
# Non-IT domain anchors
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

# Wikidata enrichment (`--wikidata`)
WIKIDATA_SPARQL_URL = "https://query.wikidata.org/sparql"
WIKIDATA_USER_AGENT = "JobKB/1.0 (IT knowledge-base research; enrichment) python-urllib"
WIKIDATA_RATE_SLEEP = 1.00     # seconds between SPARQL calls 
WIKIDATA_MAX_RETRIES = 15      # attempts on 429/5xx/timeout, then fail-open
# Retry-After is honoured but capped so a huge hint can't stall.
WIKIDATA_THROTTLE_WAIT = 65        # seconds to wait after a 429 error
WIKIDATA_THROTTLE_MAX_WAIT = 120   # cap on a server-provided Retry-After

# Sub-domains eligible for Wikidata anchoring.
WIKIDATA_SKILL_SUBDOMAINS = frozenset({
    "programming_languages", "data_databases", "cloud_devops", "ai_ml", "web",
    "networks", "security", "systems_infrastructure", "emerging_tech",
    "mobile_development", "data_engineering", "hardware_embedded",
    "methodology", "knowledge_general",
})
WIKIDATA_SKILL_MAX_TOKENS = 3  # only short labels are candidates

# Wikidata aliases merged into alt_labels are hygiene-filtered.
WIKIDATA_MAX_ALIASES = 8
WIKIDATA_ALIAS_MAX_TOKENS = 4
WIKIDATA_ALIAS_MAX_CHARS = 40

# instance-of (P31) / subclass-of (P279*) allowlist for concrete tech.
WIKIDATA_SKILL_CLASSES = (
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
# Abstract IT fields/disciplines.
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
WIKIDATA_DOMAIN_CLASSES = ("Q638608",)  # software development (process)
WIKIDATA_DOMAIN_FIELD_CLASSES = WIKIDATA_SKILL_FIELD_CLASSES + ("Q131339603",)

# Reject a candidate whose instance-of hits any of these
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
# Description-based homonym guard (skills/domains only)
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
    # tech-adjacent homonyms
    r"\bStack Exchange site\b",
    r"\bWikimedia (template|category|module|project|permanent duplicate|duplicat)",
    r"\bsystem tray\b",
    r"\bnews (website|site|and media website)\b",
)

# Graph export (--export)
EXPORT_OUT_DIR = os.path.join(ROOT, "export")
EXPORT_TTL = os.path.join(EXPORT_OUT_DIR, "jobkb.ttl")        # RDF/OWL Turtle (SKOS + jobkb ontology)
EXPORT_GRAPHML = os.path.join(EXPORT_OUT_DIR, "jobkb.graphml")  # Gephi / Cytoscape / yEd
EXPORT_JSON = os.path.join(EXPORT_OUT_DIR, "jobkb.json")     # nodes/edges graph JSON
EXPORT_HTML = os.path.join(EXPORT_OUT_DIR, "jobkb.html")     # interactive overview
EXPORT_HTML_FULL = os.path.join(EXPORT_OUT_DIR, "jobkb_full.html")  # interactive full-graph viz
EXPORT_FORMATS = ("rdf", "graphml", "json", "viz", "fullviz")
# RDF namespaces; WD_NS points at Wikidata.
JOBKB_NS = "https://w3id.org/jobkb/"
JOBKB_ONT = "https://w3id.org/jobkb/ontology#"
WD_NS = "http://www.wikidata.org/entity/"
