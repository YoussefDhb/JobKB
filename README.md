# JobKB

An **English-primary**, IT-focused occupation & skill **knowledge base**, built
**fully automatically** from local public taxonomies. French is a first-class
secondary language: every concept's EN/FR labels are completed bilingually from
authoritative Wikidata labels and validated HuggingFace machine translation. There
is **no scraping and no human in the loop** — cross-source duplicates are resolved and
alignments validated with open-source HuggingFace models. **Enrichment is automatic**:
a single build runs the full pipeline — cross-source alignment, faceted ontology, ISCO
attachment, unified merge, then Wikidata QID anchoring, LLM description/link generation,
and bilingual label completion — all validated before anything touches the graph, all
snapshot-resumable and fail-open (the only network calls are read-only, cached Wikidata
SPARQL and HuggingFace inference; a build with no token still succeeds).

## Sources (IT-filtered, English where available)

Scope = **core IT + managers + data** (professionals, technicians, the ICT-manager
tier, and cross-branch data roles), applied consistently to every source.

| Source | Role | IT scope filter |
|---|---|---|
| **ISCO-08** | Neutral standard backbone (every source attaches to it) | sub-major **25** & **35** + minor **133** (ICT service managers) |
| **ESCO** | Occupations, skills, relations. Carries a native ISCO code. | `iscoGroup` in `25`/`35`/`133`; **all** digital + digComp skills |
| **ONET** | Rich IT occupations + real technology tools (`software_skills`) | SOC `15-12xx` + `15-2051` (Data Scientists) + `11-3021` (IT managers) |
| **NOC 2021** | Bilingual (EN/FR) occupations + illustrative-example synonyms | minors `2122`/`2123` + `20012`, `21211`, `21311`, `2222x` |
| **ROME** | French métiers + competences + definitions (cross-lingual) | domain **`M18`** + data/CDO codes `M1405/M1419/M1423/M1426` |
| **SFIA 9** | **Skills only** — curated professional IT/digital competency framework | 95 IT-scoped skills (business/HR/marketing/finance dropped) |
| **CSO 3.5** | **Skills only** — curated subset of the Computer Science Ontology (emerging-tech vocabulary) | ~530 topics: IT branches (AI/ML, security, software, data, networks, …) via `superTopicOf`, depth≤2, per-branch balanced, de-duped |
| **Lightcast Open Skills** | **Skills only** — large, cleanly-categorised skills taxonomy | Information Technology category (`17.0`) = ~5,240 skills across 70 authoritative IT subcategories |
| **Kaggle technical skills** | **Skills only** — small curated IT technical-skills list | 528 skills, 9 IT categories |
| **e-CF 4.0** | **Skills only** — European e-Competence Framework (EU-standard ICT competences) | 41 professional ICT competences (Plan/Build/Run/Enable/Manage), self-classified into the taxonomy's 22 categories; source CSV's pre-mangled apostrophes (U+FFFD) repaired at ingest |
| **Soft skills** (curated) | **Skills only** — noun-form soft/transversal skills used in IT hiring | 22 recruiter-vocabulary soft skills (teamwork, communication, problem solving, work ethic, …) the ESCO verb-phrase competences lack; linked to occupations by posting evidence |
| **WEF Global Skills Taxonomy** (2021) | **Skills only** — authoritative soft-skill standard (World Economic Forum) | 47 structured soft skills (creative/systems thinking, mentoring, building trust, grit, growth mindset, …) across 5 WEF-aligned soft sub-domains; 16 core ones attached to every IT occupation as a `transversal` layer |
| **IT soft-skills taxonomy** (curated) | **Skills only** — comprehensive IT soft skills across the 5 soft sub-domains | 38 genuinely-new soft skills (technical communication, stakeholder management, resilience, technical leadership, learning agility, data-driven decision making, code-review etiquette, …) grounded in WEF/O*NET/SFIA + engineering "power-skills"; self-classified, dedup-skips already-covered terms; 10 universal ones attached to every IT occupation as `transversal` |
| **ADEM (Luxembourg)** | **Relations only** — real vacancy demand (ESCO×ROME) | 1,758 weighted `demand` edges on IT ROME occupations (`M18*`) |
| **Job postings (mined)** | **Relations only** — mined IT postings (25 roles) | 1,013 role→skill `demand` edges (matched to existing entities) |
| **data_jobs** (lukebarousse) | **Hybrid** — 785k real postings, 10 data/IT roles | harvests ~50 genuinely-absent IT tools as new skills + 1,193 large-scale weighted `demand` edges |
| **zenodo** (Montandon 2019) | **Hybrid** — 17.9k English Stack Overflow postings, 14 IT dev roles | harvests 55 absent tools + 533 `demand` edges (hard **and** soft skills; roles resolve to existing occupations) |
| **Djinni** (IT recruitment) | **Relations only** — 142k IT postings, 34 role tags, free-text JDs | 2,402 `demand` edges across **15 occupations** (DevOps/mobile/QA/data/sysadmin/security/…) via strict concrete-tech text extraction |
| **LinkedIn SWE** (kaggle) | **Relations only** — 9.4k software-engineering postings | 888 `demand` edges (pre-extracted skills → software-developer family) |
| **kaggle job-skill-set** (IT) | **Relations only** — 240 IT-management/support postings | 162 `demand` edges (IT support/PM/manager/security-analyst — under-represented occupations) |
| **Emerging roles** (curated) | **Occupations** — labor-market roles absent from ESCO/O*NET | 6 roles (Analytics Engineer, MLOps Engineer, BI Developer, Data Governance Analyst, Full Stack Developer, Back-End Developer), ISCO-attached, demand-profiled from data_jobs + zenodo |

There is no ISCO↔SOC↔NOC↔ROME crosswalk shipped with these datasets, so the
cross-source **alignment itself acts as the crosswalk**. **No source is privileged:**
ESCO uses its native ISCO code; ONET, NOC and ROME each attach **directly** to the
ISCO groups by embedding similarity (never routed through ESCO).

**Skills-only sources.** SFIA, CSO, Lightcast, Kaggle, e-CF and the curated soft-skills list
contribute skills but no occupations (`contributes_occupations = False`, `needs_attach = False`), so
they skip ISCO attachment entirely. Their skills are classified into the neutral ontology,
aligned/merged against the existing skill vocabulary, and reach occupations **transitively** — a
skill that merges into a unified skill inherits that concept's occupation relations. Lightcast/Kaggle/e-CF self-classify via
their authoritative category maps (e-CF's 41 competences merge cleanly with existing skills where
they overlap — e.g. Risk Management with SFIA/ROME/ESCO, User Experience with CSO, Application
Development with Lightcast — and add higher-level professional competences where they are distinct).

**Soft / transversal skills.** The KB's only transversal skills were ESCO's *verb-phrase*
competences ("build team spirit", "manage time"); the **noun-form soft skills recruiters actually
name** (teamwork, communication, problem solving, time management, work ethic, attention to detail,
…) were absent. A small curated list adds 22 of them — distilled from the soft-skill datasets
analysed for the KB (Zenodo's `soft_skills` column and annotation file, and the Mendeley
software-engineering skill survey, whose person-classification *structure* is otherwise rejected).
Each carries the equivalent ESCO verb-phrase as an alt label and is **linked to occupations by real
posting evidence**: the `zenodo` source attributes weighted `demand` edges from postings' extracted
soft skills (e.g. communication / teamwork / responsibility → software developer, system
administrator, back-end developer, …). Being a curated authoritative list of deliberately
non-IT-*specific* terms, it bypasses the semantic IT-relevance gate (like the code-filtered built-in
taxonomies) rather than being wrongly blocked.

The **WEF Global Skills Taxonomy** (World Economic Forum, 2021) + Education 4.0 add 47 more soft
skills and, more importantly, give the soft branch **real internal structure**: the single flat
`soft_transversal` bucket is replaced by **five WEF-aligned soft sub-domains** — `soft_cognitive`
(creativity & problem-solving), `soft_self_management` (self-management, resilience & dependability),
`soft_collaboration` (communication & collaboration), `soft_leadership` (leadership & social
influence), `soft_learning` (curiosity & lifelong learning) — plus a `soft_transversal` catch-all.
Every soft skill (ESCO verb-phrases, the curated nouns, WEF terms) is routed into a group by a
keyword classifier; WEF self-classifies via its own skill-groups. Because these transversal skills
rarely appear in job postings (so demand evidence can't link them), the 16 **core** WEF skills the
Future-of-Jobs framing treats as universal (creative/analytical/critical/systems thinking, problem
solving, communication, collaboration, adaptability, resilience, curiosity, initiative, attention to
detail, time management, responsibility, empathy, feedback) are attached to **every IT occupation**
as a distinct `relation_type="transversal"` layer (source `WEF`, no weight — kept separate from the
`demand` signal so it stays auditable and never dilutes demand rankings).

The **IT soft-skills taxonomy** (`src/sources/soft_taxonomy.py`, source `SOFTTAXO`) then makes the soft
branch **comprehensive**: since soft skills are the KB's minority, it adds **38 genuinely-new** soft
skills that IT hiring and performance reviews actually name but the KB still lacked — technical &
written communication, active-listening/stakeholder management, cross-functional & remote collaboration,
technical leadership, ownership, delegation, resilience, dealing with ambiguity, learning agility,
staying current with technology, data-driven decision making, product thinking, code-review etiquette,
and more — curated from established frameworks (WEF Global Skills Taxonomy, O*NET Work Styles, SFIA
behavioural factors) and the software-engineering "power-skills" literature. Each carries an **explicit
soft sub-domain** (`SOFTTAXO` is in `SELF_CLASSIFIED_SUBDOMAIN_SOURCES`) so it lands in the right group
rather than the catch-all — this nearly doubled `soft_learning` and materially grew every soft
sub-domain. It is **self-deduping**: any candidate whose normalized label already names an existing
skill (any source) is skipped (9 were), so only genuinely-new nodes are created and the `align` stage
confirmed **0 further merges**. A curated **`core` subset of 10 universal** IT soft skills is attached to
**every IT occupation** as `transversal` edges (2,560 edges), exactly like the WEF core — distinct from
`demand`. Gate-bypassed and (like every source) run through the normal ingest→hierarchy→align→merge→qa
pipeline, then given French labels by `--translate`; all QA invariants stay 0 and the `demand` count is
unchanged.

Finally, a **curated IT-relevance filter keeps the soft branch IT-focused** (`relevance.is_non_it_soft`):
O*NET's **Abilities** are psychometric aptitudes, not workplace soft skills, and ESCO's transversal
collection carries broad **life skills** — so physical/sensory/perceptual O*NET abilities (Far/Near
Vision, Finger Dexterity, Speech Clarity, Perceptual Speed, …) and non-IT ESCO transversal skills
(maintain physical fitness, apply hygiene standards, foster biodiversity, participate in civic life, …)
are pruned at the O*NET ingest and the ESCO transversal load (35 removed). Matching is **exact-normalized-
label only** — substrings would wrongly hit real IT skills ("integrated development environment", "Cyber
Hygiene", "Physical Layers", "healthcare data systems") — and the cognitive/verbal O*NET abilities
(reasoning, comprehension/expression) plus every IT-relevant ESCO transversal skill (cope with
uncertainty, respect confidentiality, manage digital identity, think critically, …) are kept.

**Relation-only enrichment sources.** ADEM (real Luxembourg vacancy demand, already linked to
ESCO + ROME) and the mined IT job postings add weighted `demand` occupation→skill edges **between
entities that already exist in the KB** — no new nodes. Each edge carries a demand `weight`
(vacancy positions / posting co-occurrence), so an IT occupation gains a demand-ranked skill
profile. **data_jobs** (lukebarousse, 785k real postings across 10 data/IT roles) is a **hybrid**:
it adds large-scale weighted `demand` edges at scale (Data Analyst→Excel/Tableau/Power BI/SQL,
Data Engineer→Spark/AWS/Kafka/Scala, …) via an **augmented matcher** (exact/alias keys plus
parenthetical-acronym and vendor/suffix stripping, so short tokens like `gcp`/`power bi`/`kafka`
resolve to verbose KB labels — never substring matching, which would confuse `airflow` the tool with
CFD airflow), and **harvests** the handful of genuinely-absent, high-frequency IT tools (databricks,
matplotlib, seaborn, plotly, dax, golang, …) as new gate-screened, self-classified skill nodes.
**zenodo** (Montandon et al. 2019, *"What Skills do IT Companies Look for in New Developers?"*,
17.9k English Stack Overflow postings across 14 developer roles) is a second hybrid built on the same
machinery: its 14 clean roles resolve to existing occupations (only *back-end developer* was a genuine
gap → added via Emerging roles), it harvests 55 further absent tools (kubernetes, kafka, gcp, redis,
jenkins, react-native, vue.js, spring-boot, …) classified via the dataset's companion hard-skill
category taxonomy, and it writes 533 weighted `demand` edges for **both** hard skills and the curated
soft skills (giving Back-End Developer a Java/Spring/DBMS/AWS profile, Full-Stack a JavaScript/React/
Node.js/C# one).

Three further job-posting sources add **relation-only** demand (no new nodes — endpoints resolve against
the existing KB). **Djinni** (142k English IT postings from the Djinni recruitment platform, tagged with
a role keyword and a free-text description) is the largest and most role-diverse: it resolves the role
tag to an occupation and mines skills from the description. Free-text extraction is precision-critical —
the token-list matcher's vendor/suffix-strip and paren-acronym variants match common English words on
prose ("teams"←Microsoft Teams, "application"←PuTTY (Application)) — so Djinni matches **only full
labels, restricted to concrete-tech sub-domains, with a min-length + common-word denylist guard**,
yielding clean profiles (DevOps→Kubernetes/Docker/Terraform/Jenkins/Ansible; Android→Kotlin/Flutter/
Firebase; QA→Selenium/Jira/Postman) across 15 occupations (2,402 edges). **LinkedIn SWE** (9.4k
software-engineering postings) and the **kaggle job-skill-set** IT subset (240 IT-management/support
postings) add 888 and 162 demand edges from their pre-extracted skill lists — both relation-only (no
harvest: their extractions mix genuine tools with generic phrases like "coding"/"best practices" that
would pollute the vocabulary). A fourth candidate, the **1.3M-row "LinkedIn Jobs & Skills" file, was
rejected** after careful analysis: it has no role column (titles only in URL slugs), is ~90% non-IT, and
mining 500k rows surfaced **zero genuinely-new IT skills** (all frequent absent tokens are non-IT /
credentials) — nothing to add.

**Occupation-gap augmentation.** Mining raw job titles/roles against every KB occupation label
(pref **and** alt, all sources) surfaced a few well-attested roles that the standard taxonomies
(ESCO v1.2 / O*NET) don't carry yet. The **Emerging roles** source adds these as real occupations
(Analytics Engineer, MLOps Engineer, BI Developer, Data Governance Analyst, Full Stack Developer,
Back-End Developer) — attached to ISCO by the same model-verified `attach` stage as ONET/ROME (all
land in sensible groups, e.g. Back-End/Full-Stack → 2512 Software developers), then demand-profiled
from data_jobs and zenodo. This documents a deliberate augmentation of the taxonomy backbone with
labor-market-observed roles. Occupation-gap audits of the other datasets found no further genuine
gaps: SFIA/CSO/Lightcast/Kaggle/e-CF carry no occupations, the core ESCO/O*NET/ROME IT filters are
well-targeted, and **13 of zenodo's 14 roles already resolved** to existing occupations (back-end
developer being the sole addition). Endpoints are resolved against the current `kb/` (ESCO uuid / ROME code / normalized
label), so nothing dangles. Both are curated to
avoid noise: SFIA is scoped to IT + IT-management (its ~40 general business/HR/marketing/finance
skills are dropped) with a hand-curated code→sub-domain map (its shipped category export is
unreliable); CSO is a research-topic ontology, so only its shallow IT-relevant subset is kept
(descendants of `config.CSO_ROOTS`, depth ≤ `CSO_MAX_DEPTH`, per-branch balanced and de-duplicated)
and each topic is classified by the IT **root branch** it descends from (`CSO_BRANCH_SUBDOMAIN`)
rather than dumped into one flat bucket.

**Wikidata QID enrichment (connective tissue, woven into the graph).** `python run_pipeline.py
--wikidata` (also run automatically in the full build) anchors the KB's technology/tool/knowledge
skills, its occupations, and its **10 functional-domain taxonomy nodes** to **stable Wikidata QIDs** —
the general-purpose, richly-linked hub that gives free entity resolution for technologies, tools and
companies no occupation taxonomy provides. **Populated: 1,202 anchors — 1,163 skills, 31 occupations,
8 domains (1,038 high-confidence, exact-match); 1,134 carry a Wikidata description.** The skill
candidate gate spans the concrete-technology sub-domains **plus the two further hard sub-domains that
carry genuine named entities** — `methodology` (Scrum, Git, Agile) and `knowledge_general` (computer
science, information systems) — while the phrase-heavy sub-domains (`it_management`, `other_hard`) are
excluded (their competence-phrase labels have no Wikidata item, so each would be a wasted rate-limited
query the class check rejects — those descriptions are the LLM's job). Short, entity-like labels only
(≤3 tokens); the resolver's own instance-of/subclass **class verification protects precision** as
recall widens. Each anchored skill's authoritative `wikidata_description` becomes the concept's
description where it has none (precedence source → Wikidata → LLM) — the highest-precision way to close
the description gap for well-known tech. The anchors are **woven into the concept layer**: each unified skill/occupation
carries `wikidata_qid` + `wikidata_url` + a `wikidata_description` (Wikidata's terse one-liner, in a
dedicated column that never overwrites KB-authored text), and cleaned Wikidata aliases are merged
into `alt_labels` (hygiene-filtered: deduped against existing labels, parenthetical near-duplicates
and over-long phrases dropped, capped). `merge.py` re-derives these columns from the side table on
every rebuild, so the enrichment survives a standalone re-merge and stays idempotent. The
`kb/wikidata_links.csv` **cross-reference layer** additionally carries a SKOS `relation`
(`skos:exactMatch` / `skos:closeMatch`) so it is RDF-export-ready; it adds **no nodes or relations**
to the core graph. Resolution is a **single batched SPARQL query per ~50 labels** that
does label matching *and* class verification at once (QIDs are never hardcoded — a guessed QID is
often a person/film): a candidate is accepted only when our label equals the item's `rdfs:label`
(`match_method=exact`) or a `skos:altLabel` (`alias`) **and** its instance-of lands in a class
allowlist — concrete tech via `P31`/`P279*` closure over **bounded** roots (software / programming
language / library / framework / OS / database / hardware / company), plus IT fields/disciplines
**and occupations** via direct `P31` (academic discipline / branch of science / field of study /
type of technology / **profession / occupation** — closure over the last two, whose instance sets
run to millions, times the query out, so they resolve by direct `P31`; *data science*→Q2374463,
*software developer*→Q183888, *data engineer*→Q104659813 anchor this way), and never a denylist class
(human / film / album / taxon / video game / **Wikimedia disambiguation page** / **scientific &
academic journal** / **magazine** — these last three because tech acronyms and field names collide
with a same-name disambiguation page, journal, or magazine that would otherwise outrank the real
concept). A second **description-based homonym guard** then drops any anchor whose fetched Wikidata
description reads as a settlement, periodical, creative work, Q&A (Stack Exchange) site, or
Wikimedia-internal page — a same-name homonym, not the technology — tuned to keep genuine web tools
(WordPress, Cloudflare, Stack Overflow) and game frameworks (SpriteKit). Ties break exact>alias, then
by sitelink count. The 10
domain nodes are resolved by curated English **label probes** (case-exact — `rdfs:label` matching is
case-sensitive, so a Title-Cased probe hits a disambiguation page) verified by the same class check:
*software development*→Q638608, *web development*→Q386275, *data science*→Q2374463, *IT
infrastructure*→Q594593, *telecommunications*→Q418, *computer security*→Q3510521, *IT
management*→Q1473265, *emerging technologies*→Q120208 (the two composite domains — *General &
Cross-cutting IT*, *Soft & Transversal* — have no clean single concept and stay honestly unresolved).
Every resolution — including verified-*unresolved* — is **snapshotted** to
`resources/WIKIDATA/retrieved/` and flushed each chunk, so a re-run is fully offline/reproducible and
an interruption resumes from the last flush; a failed query leaves its labels *inconclusive*
(retried), never a false 'unresolved'. HTTP is polite (descriptive User-Agent, paced, backed-off,
**fail-open**) and **throttle-resilient** — on a `429` it waits for the query-service token bucket to
refill (the run above completed straight through an active WDQS rate-limit outage). The provided
`ESCO_v1.2.1-wikidata.csv` is a noisy export whose QIDs were lost; its one clean signal —
programming-language synonyms — broadens matching for language skills (e.g. `golang`→Go).

**LLM-powered enrichment (pillar 3), auto-validated (pillar 4).** `python run_pipeline.py --llm
[tasks]` uses a HuggingFace LLM to make the KB more complete without sacrificing reliability. Because
the KB is built **with no human in the loop**, every LLM output is **validated before it touches the
graph** — the IT-relevance gate (`src/relevance.py`) + the mDeBERTa NLI verifier (`src/align/verify.py`)
— tagged with provenance (`description_source="llm"`, `relation_type="llm_inferred"`, `source="LLM"`),
and it **never overwrites** a source/curated value. Four tasks (`src/llm.py`): **(T1) descriptions** —
concise, factual, NLI-validated definitions for **every occupation and hard skill that still lacks one
after the Wikidata pass** (the eligibility gate was widened from 5 niche sub-domains to all hard
categories, so the ~8k description-less Lightcast/ROME/Kaggle skills are now in scope), grounded on
label + taxonomy context + any Wikidata description; because generation is credit-bound but
snapshot-resumable, coverage **converges across successive automatic builds**; **(T2) fill `hard_soft`** —
**deterministically derived from each skill's taxonomy placement** (category→domain→type; `merge`
applies `hierarchy.skill_type` as the single source of truth, so `hard_soft` can never contradict the
category — e.g. a technical skill in a hard category can't be tagged soft) so **every** skill is typed
consistently; **(T3)
inferred links** — occupation→skill relations the demand data missed, chosen by the LLM from an
embedding shortlist of the *existing* KB vocabulary (never invented) and NLI-verified; **(T4) emerging
tech** — the LLM proposes emerging technologies absent from the taxonomies, and only those a **real
Wikidata QID confirms** are added (`source="LLM"`, hierarchy-classified). The unified `description`
column is filled by precedence **source → Wikidata → LLM** (`description_source` records which). The
client is **HuggingFace-only**: HF Inference Providers (a small capable instruct model,
`meta-llama/Llama-3.1-8B-Instruct` by default) as primary, an optional **local** `transformers` model
(`JOBKB_LLM_LOCAL=1`) as offline fallback, and **fail-open** — on no credits / offline the generation
tasks are simply skipped and the build still succeeds. Every generation is **snapshotted**
(`resources/LLM/retrieved/`) so re-runs make **zero** API calls (free-tier-friendly) and are
resumable; validation rejects are logged to `kb/llm_rejected.csv`. `--llm` runs **after merge**; its
values are re-woven idempotently on every subsequent `--stages merge`.

**Multilingual label completion (bilingual KB), auto-validated.** `python run_pipeline.py --translate`
fills the empty `primary_label_en/fr` and `alt_labels_en/fr` columns so the KB is a complete bilingual
resource (`src/translate.py`). Because there is **no human in the loop**, every filled label is
**validated before it touches the graph** and source/curated labels are **never overwritten**. It works
in three quality-first layers: **(L1) Wikidata** — for concepts carrying a QID, the authoritative
`@en`/`@fr` `rdfs:label` and multilingual aliases are used directly (free, accurate; this is the **only**
source used for `alt_labels`, so no alias noise); **(L2) machine translation** — a **local** HuggingFace
model (`facebook/nllb-200-distilled-600M`) translates the remaining primary labels (`fr→en` for the
French-only ROME concepts, `en→fr` for the English sources) behind a **tech-term preservation guard** so
technology names are **never** Frenchified — "Docker", "Python", "Machine Learning", "Business
Intelligence" etc. are kept verbatim (word- and phrase-level, plus acronyms/CamelCase/versions); **(L3)**
if MT is unavailable or an output fails validation, the cell is simply **left empty** (fail-open, no bad
data). Each MT output is checked by a **lenient cross-lingual semantic floor** (bge-m3 compares the source
against the translation directly — a single clean signal) plus **structural filters** (sentence-instead-
of-label, length blow-up, lost tech token); rejects are logged to `kb/translate_rejected.csv`. Everything
is **snapshotted** (`resources/TRANSLATE/retrieved/`) so re-runs recompute **nothing** and the job is
resumable/observable (checkpointed every 200 labels). Fully local ⇒ **free-tier-safe**; provenance is
tagged `source="TRANSLATE"`. This lifted primary-label coverage to **EN 11,346/11,366 (99.8%)** and
**FR 10,980/11,366 (96.6%)** — up from 81.6 % / 35.7 % — with all QA invariants unchanged (labels are
purely additive). `--translate` runs **after merge** (automatically, last of the enrichment stages, so it
also lifts the French-only ROME concepts into English via `fr→en`); its values re-weave idempotently on
every subsequent `--stages merge`.

**Description coverage — Wikidata now, LLM converging.** The two prongs above make description coverage
a first-class, unbounded target: the Wikidata pass supplies **990 authoritative descriptions** for
well-known tech, and the LLM description gate is widened from 5 niche sub-domains to **all hard
categories** (~8,000 description-less Lightcast/ROME/Kaggle skills are now eligible, up from ~356). LLM
generation is **credit-bound and snapshot-resumable** — on a depleted HuggingFace free tier it fails
open (0 generated, build still succeeds) and simply resumes on the next automatic build when credits
refresh, so coverage **converges over successive builds** rather than in one shot. Current concept
descriptions: **3,319/11,366** (source 2,305 · Wikidata 990 · LLM 24), with the LLM prong ready to fill
the remainder as credits allow.

## Pipeline (package + orchestrator)

```
src/
  config.py        # paths, EN-primary schema, IT scope per source, HF model ids, tunables
  common.py        # deterministic ids, label normalization, idempotent CSV IO, provenance
  ingest/          # isco, esco, onet, noc, rome  (each IT-filtered, EN-primary)
  sources/         # pluggable source framework: base (StructuredSource/ExtractionSource) + registry + sfia, cso, demo
  hierarchy.py     # faceted ontology: skill -> category -> domain -> type + occupation -> domain facet
  align/           # candidates (embeddings) -> verify (batched NLI) + deterministic match_key dedup -> attach (ISCO, curated overrides)
  merge.py         # source-neutral unified concept clustering / de-duplication (+ hard_soft & it_subtype reconciliation)
  wikidata.py      # QID anchoring + authoritative descriptions/aliases (enrichment stage)
  llm.py           # HF LLM descriptions / inferred links / emerging tech, auto-validated (enrichment stage)
  translate.py     # bilingual EN/FR label completion (Wikidata labels + validated MT) (enrichment stage)
  incremental.py   # add/remove ONE source without a full rebuild
  pipeline.py      # orchestrator (core + enrichment stages) + QA/integrity report
run_pipeline.py    # CLI entry point
notebooks/
  inspect.ipynb    # QA & spot-checks over kb/
```

**Enrichment is part of the build.** The full pipeline is
`ingest → hierarchy → align → attach → merge → **wikidata → llm → translate** → qa`: the three
post-merge enrichment stages (Wikidata QID anchoring, LLM descriptions/links, bilingual label
completion) run **automatically** after `merge`, in that dependency order (Wikidata first — its QIDs
and descriptions feed the others), so a plain `python run_pipeline.py` produces a **fully-enriched** KB
in one command. Each enrichment stage is **fail-open** (no HF token / credits / offline → it logs and
skips, the build still succeeds) and **snapshot-resumable** (`resources/*/retrieved/`), so a rebuild
with complete snapshots re-weaves cheaply and `qa` (which runs last) reports the enriched coverage.
Pass **`--core-only`** for a fast, network-free core build without the enrichment stages; the standalone
`--wikidata` / `--llm` / `--translate` flags still run any one stage on its own.

A full build takes **a few hours** on CPU: the core is **dominated by mDeBERTa NLI verification**
(~2 s/pair; no human reviews the merges, so the models must — a deliberate accuracy-over-speed
trade-off), and enrichment adds rate-limited Wikidata SPARQL + LLM generation on top. bge-m3 embeddings
are cached on disk (`kb/.emb_cache_*.pkl`, keyed by model + text) so they are computed once and reused;
NLI re-verifies each build.

Run it:

```bash
python -m venv .venv && .venv\Scripts\activate
pip install -r requirements.txt
python run_pipeline.py             # full build + enrichment (ingest -> ... -> merge -> wikidata,llm,translate -> qa)
python run_pipeline.py --core-only # full build WITHOUT enrichment (fast, network-free)
python run_pipeline.py --no-align  # ingest + skill ontology only (no HF model downloads)
```

### Run only the stages you need

Stages are `ingest -> hierarchy -> align -> attach -> merge -> qa`, each idempotent, so any
stage or contiguous range can run **against the existing `kb/`** (never wiped unless `--clean`)
— no need to re-run the ~2 h build after a small change:

```bash
python run_pipeline.py --stages merge            # re-derive unified concepts only (seconds)
python run_pipeline.py --stages attach,merge     # re-attach + re-merge (after tuning attach)
python run_pipeline.py --from align              # align -> attach -> merge -> qa
python run_pipeline.py --to hierarchy            # ingest + hierarchy only
python run_pipeline.py --stages ingest --source ESCO   # re-ingest just one source
python run_pipeline.py --stages qa               # integrity report only
python run_pipeline.py --list-stages
```

`--source NAME` scopes ingest/align/attach to one source (uses the incremental focus path).
Running an upstream stage marks the downstream ones stale (the run prints a `[note]` telling
you what to re-run). Re-ingesting **preserves the attach-derived `isco_code`**, so
`ingest → merge` stays correct without a costly re-attach; re-run `hierarchy` after a
re-ingest to restore the derived skill rows (it's ~1 s).

## Adding a source incrementally (open for extension)

A new data source can be **added to an existing KB without rebuilding it**: it is ingested,
standardized to the schema, aligned only against the existing entities, attached to ISCO, and
merged into the unified concepts. Because every KB write is per-source and idempotent
(`common.replace_source_rows`) and embeddings are cached by text, the others are never
recomputed — a new source takes minutes, not a full rebuild.

```bash
python run_pipeline.py --list-sources     # show registered sources
python run_pipeline.py --add DEMO          # ingest + align + attach + merge just DEMO
python run_pipeline.py --remove DEMO       # delete DEMO and repair the graph (instant)
```

To add your own dataset, subclass `StructuredSource` (in `src/sources/base.py`) and implement
the `occupations()`, `skills()`, `relations()` generators returning plain normalized dicts; the
base mints deterministic ids, builds labels, applies English-primary standardization
(`label_language_status`: `en_native` / `en_plus_fr` / `fr_only` — a French-only source gains
its English label later via alignment, exactly like ROME), and persists everything. Register it
in `src/sources/registry.py` with `contributes_occupations` / `needs_attach` flags. Downstream,
`hierarchy` classifies its skills (Hard/Soft + IT sub-domain), `attach` assigns an ISCO group
(NLI-verified) if it has no native code, and `merge` de-duplicates it against existing concepts —
so the new source ends up structurally identical to the built-in taxonomies.
`src/sources/demo_dataset.py` is a worked example (a throwaway synthetic dataset).
For **unstructured** inputs (scraped postings), subclass `ExtractionSource` and implement
`documents()` + `extract(text)` (a stub wired to an HF skill-extractor).

### Relevance / noise gate (automatic, at ingest)

Any pluggable source is screened by `src/relevance.py` **before its rows are written**, so
non-IT and malformed data never enter the KB (the 5 built-in taxonomies keep their authoritative
code-based IT filter and bypass the gate). Per incoming skill/occupation:

- **Structural noise** — empty / non-alphanumeric / math-notation labels are blocked.
- **IT-relevance** — a contrastive test on the shared bge-m3 embeddings: an item is a *candidate*
  only if it scores clearly closer to a **non-IT domain** anchor than to the IT space
  (`sim_non ≥ REL_NONIT_HI` with a margin), and is blocked **only if** the mDeBERTa NLI verifier
  also judges it non-IT. Everything else is kept; a candidate the NLI rescues is kept and logged
  as *borderline*. It is **lenient by design** (calibrated so genuine IT is never dropped — 0 false
  blocks on the curated SFIA/CSO sets) and **fail-open** if the models can't load.

Every decision is auditable in `kb/blocked_entities.csv` (label, reason, `sim_it`/`sim_non`/`nli`),
and `--stages qa` reports the blocked / borderline counts. No human in the loop.

The build is **idempotent**: entity ids are deterministic, each stage owns its
source rows, and `run_pipeline.py` rebuilds `kb/` clean by default.

## Alignment, attachment & merge (no human in the loop, source-equal)

1. **Candidates** — multilingual sentence embeddings (`BAAI/bge-m3`, a top open
   multilingual model with strong EN↔FR cross-lingual matching and no query/passage
   prefix; → `paraphrase-multilingual-MiniLM-L12-v2` → TF-IDF as offline fallbacks)
   give the top-k nearest neighbours between every pair of sources.
2. **Verify** — an accurate multilingual **NLI model**
   (`MoritzLaurer/mDeBERTa-v3-base-mnli-xnli`, batched, run only on promising pairs)
   checks bidirectional entailment of the two definitions. Confidence maps to SKOS
   (`exactMatch`/`closeMatch`/`relatedMatch`); each pair also gets a source-neutral
   **merge flag** — `label` (identical preferred label) or `semantic`. `validated = auto`.
3. **Attach** — **every** ONET/NOC/ROME occupation attaches **directly** to an ISCO
   group by a two-stage, model-verified decision (ESCO uses its native code): embedding
   gives a top-K shortlist of ISCO unit groups, then **NLI entailment** of the
   occupation definition → each group's definition **re-ranks** the shortlist, so a
   strong embedding to the wrong group can be overridden by the definition semantics.
   The inferred ISCO code is written back; placements with weak embedding *or* weak
   entailment are **flagged low-confidence** for QA (never dropped). A small **curated
   `ISCO_OCC_OVERRIDE` map** (`src/config.py`) fixes the handful of emerging roles the
   automatic attach placed poorly (e.g. *Data scientist* → Systems Analysts rather than
   Computer Network Professionals, *Product Owner* / *MOA coordinators* → ICT Service
   Managers): keyed by occupation `source_id`, applied deterministically before the
   automatic choice, forcing a high-confidence edge. No ESCO gateway, **zero hierarchy
   orphans**.
4. **Merge** — connected components of the merge graph become **unified concepts**.
   `label` edges always merge. A `semantic` **occupation** merge is triple-guarded —
   strong embedding **and** mutual NLI entailment on the definitions **and** the same
   ISCO group — so no occupation is de-duplicated on embedding similarity alone (the
   no-human-review safety gate). Labels/attributes are chosen by **source-neutral
   consensus** (no source ranking) — English-primary, French secondary, merged synonyms,
   consensus ISCO code, back-links to source members. A skill's `hard_soft` is a
   **deterministic function of its taxonomy placement** (`it_subtype → domain → type`), and
   a small curated **`IT_SUBTYPE_OVERRIDE`** reconciles the few labels sources tag
   inconsistently (e.g. *Cypress*/*Playwright* → web, not ML; *computer science* →
   knowledge_general, not other_hard).

   **Deterministic same-concept dedup.** Cross-source embedding candidate generation never
   compares two rows from the *same* source, and cross-lingual duplicates only surface once a
   French label is translated — so a **deterministic exact-`match_key` linker** (`src/align`)
   adds high-precision `exactMatch`/`label` edges for every group of skills whose English label
   (native, else the validated MT of the French label from the translate snapshot) shares an
   identical normalized+singularized key. It collapses same-source duplicates (ROME's two
   "Team management" entries) and cross-lingual ones ("Informatique" ↔ "computer science") while
   two guards preserve genuinely-distinct concepts: grouping by (key, **hard/soft class**) keeps
   the hard vs soft "time management" apart, and a curated **`MATCH_KEY_DISTINCT`** allowlist
   skips keys that collide across distinct concepts (HTTP vs HTTPS, the "cybersecurity expert
   (MS)" degree variant). This cut the unified-skill match_key collisions from ~48 groups to the
   3 deliberately-distinct ones.

### The taxonomy — a faceted, graph-navigable ontology

Occupations and skills share one **functional-domain** vocabulary, so the graph is navigable
end-to-end: **`occupation ↔ domain ↔ category ↔ skill`**.

**Skills — a 4-level tree** (`skill → category → domain → type`). Every skill of every source is
classified into one of **22 fine categories**, which roll up into **10 broad domains** (Software
Development · Web & Mobile · Data, Analytics & AI · Infrastructure, Systems & Cloud · Networks &
Telecom · Cybersecurity · IT Management, Governance & Support · Emerging Technologies · General &
Cross-cutting IT · Soft & Transversal), which roll up into **2 types** (Hard / Soft). No skill is left
flat, and no source shapes the tree — a self-classified source's category is trusted, otherwise a
label classifier assigns it (with high-precision overrides for the fine categories `mobile_development`,
`data_engineering`, `hardware_embedded` that post-date the source maps). The soft branch is structured
after the WEF Global Skills Taxonomy (5 soft categories + a catch-all).

**Occupations — the ISCO-08 backbone, connected + faceted.** Occupations attach to ISCO groups
(`occupation → unit → minor → sub-major`), now rooted under a single **"ICT professions"** super-root
over branches 25/35/133 (one connected tree). Each real occupation is **also** linked (`in_domain`) to
one of the same 10 domain nodes — resolved from its label then ISCO code — so e.g. *data scientist* and
the *TensorFlow*/*Spark* skills both hang under **Data, Analytics & AI**. ISCO remains the authoritative
occupation standard; the domain facet only enriches navigation.

```
TYPE      Technical skills                                   Soft & transversal skills
            │                                                      │
DOMAIN    Data, Analytics & AI ─────────┐                    Soft & Transversal
            │                           │ (in_domain)              │
CATEGORY  AI & ML   Big data & data-eng │                    Leadership · Collaboration · …
            │          │                │                         │
SKILL     TensorFlow  Apache Spark      └── data scientist   teamwork · mentoring · …
                                            (occupation)
```

All models are open-source; if none can be loaded (e.g. offline) the pipeline
degrades gracefully (TF-IDF candidates, NLI off) and still produces the KB.

## Knowledge-base schema (`kb/`)

| File | Contents |
|---|---|
| `occupations.csv` | one row per source occupation / ISCO-group node (EN + FR labels, ISCO & source codes) |
| `skills.csv` | one row per source skill (+ `TAXONOMY` type/domain/category nodes), hard/soft + IT category |
| `labels.csv` | every preferred/alt/hidden label per entity, per language |
| `occupation_skill_relations.csv` | occupation ↔ skill links (essential/optional) |
| `hierarchy.csv` | ISCO tree (rooted at "ICT professions") + every-source→ISCO attachment + skill→category→domain→type (`broader_than`) + occupation→domain facet (`in_domain`) |
| `concept_alignments.csv` | cross-source matches with SKOS relation, confidence, method, `validated` |
| `unified_occupations.csv` | de-duplicated unified occupations (merged members) |
| `unified_skills.csv` | de-duplicated unified skills |
| `provenance.csv` | audit trail: what each stage produced and when |

## Not in this build (deliberate follow-ons)

RDF/OWL graph export is intentionally out of scope for this reconstruction. (LLM
content-enrichment — descriptions, inferred links, emerging-tech concepts — is **now
part of the automatic pipeline**, see the enrichment stages above.) The previous
French-primary, scraping/Wikidata/manual-translation pipeline and its human `gold`
alignment review have been fully removed.
