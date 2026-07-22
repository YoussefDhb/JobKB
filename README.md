# JobKB

An **English-primary**, IT-focused occupation & skill **knowledge base**, built
**fully automatically** from five local public taxonomies. French is kept as a
secondary language wherever a source provides it. There is **no scraping, no live
web calls, and no human in the loop** — cross-source duplicates are resolved and
alignments validated with open-source HuggingFace models.

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
| **e-CF 4.0** | **Skills only** — European e-Competence Framework (EU-standard ICT competences) | 41 professional ICT competences (Plan/Build/Run/Enable/Manage), self-classified into the taxonomy's 22 categories |
| **Soft skills** (curated) | **Skills only** — noun-form soft/transversal skills used in IT hiring | 22 recruiter-vocabulary soft skills (teamwork, communication, problem solving, work ethic, …) the ESCO verb-phrase competences lack; linked to occupations by posting evidence |
| **WEF Global Skills Taxonomy** (2021) | **Skills only** — authoritative soft-skill standard (World Economic Forum) | 47 structured soft skills (creative/systems thinking, mentoring, building trust, grit, growth mindset, …) across 5 WEF-aligned soft sub-domains; 16 core ones attached to every IT occupation as a `transversal` layer |
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

**Wikidata QID enrichment (connective tissue).** `python run_pipeline.py --wikidata` anchors the
KB's concrete technology/tool skills, its occupations, and its **10 functional-domain taxonomy
nodes** to **stable Wikidata QIDs** — the general-purpose, richly-linked hub that gives free entity
resolution for technologies, tools and companies no occupation taxonomy provides. It is a **side
table** (`kb/wikidata_links.csv`), so it adds **no nodes or relations** — the core graph is
untouched. **Populated: 1,248 anchors — 1,209 skills, 31 occupations, 8 domains (1,114
high-confidence, exact-match).** Resolution is a **single batched SPARQL query per ~50 labels** that
does label matching *and* class verification at once (QIDs are never hardcoded — a guessed QID is
often a person/film): a candidate is accepted only when our label equals the item's `rdfs:label`
(`match_method=exact`) or a `skos:altLabel` (`alias`) **and** its instance-of lands in a class
allowlist — concrete tech via `P31`/`P279*` closure over **bounded** roots (software / programming
language / library / framework / OS / database / hardware / company), plus IT fields/disciplines
**and occupations** via direct `P31` (academic discipline / branch of science / field of study /
type of technology / **profession / occupation** — closure over the last two, whose instance sets
run to millions, times the query out, so they resolve by direct `P31`; *data science*→Q2374463,
*software developer*→Q183888, *data engineer*→Q104659813 anchor this way), and never a denylist class
(human / film / album / taxon / video game). Ties break exact>alias, then by sitelink count. The 10
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

## Pipeline (package + orchestrator)

```
src/
  config.py        # paths, EN-primary schema, IT scope per source, HF model ids, tunables
  common.py        # deterministic ids, label normalization, idempotent CSV IO, provenance
  ingest/          # isco, esco, onet, noc, rome  (each IT-filtered, EN-primary)
  sources/         # pluggable source framework: base (StructuredSource/ExtractionSource) + registry + sfia, cso, demo
  hierarchy.py     # faceted ontology: skill -> category -> domain -> type + occupation -> domain facet
  align/           # candidates (embeddings) -> verify (batched NLI) -> attach (ISCO, all sources)
  merge.py         # source-neutral unified concept clustering / de-duplication
  incremental.py   # add/remove ONE source without a full rebuild
  pipeline.py      # orchestrator + QA/integrity report
run_pipeline.py    # CLI entry point
notebooks/
  inspect.ipynb    # QA & spot-checks over kb/
```

A full build takes **~2 h** on CPU, **dominated by mDeBERTa NLI verification** (~2 s/pair)
— a deliberate accuracy-over-speed trade-off (no human reviews the merges, so the models
must). bge-m3 embeddings are cached on disk (`kb/.emb_cache_*.pkl`, keyed by model + text)
so they are computed once and reused across runs; NLI re-verifies each build.

Run it:

```bash
python -m venv .venv && .venv\Scripts\activate
pip install -r requirements.txt
python run_pipeline.py            # full build (ingest -> ontology -> align -> attach -> merge)
python run_pipeline.py --no-align # ingest + skill ontology only (no HF model downloads)
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
   entailment are **flagged low-confidence** for QA (never dropped). No ESCO gateway,
   **zero hierarchy orphans**.
4. **Merge** — connected components of the merge graph become **unified concepts**.
   `label` edges always merge. A `semantic` **occupation** merge is triple-guarded —
   strong embedding **and** mutual NLI entailment on the definitions **and** the same
   ISCO group — so no occupation is de-duplicated on embedding similarity alone (the
   no-human-review safety gate). Labels/attributes are chosen by **source-neutral
   consensus** (no source ranking) — English-primary, French secondary, merged synonyms,
   consensus ISCO code, back-links to source members.

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

RDF/OWL graph export, and LLM content-enrichment (niche IT roles, emerging-tech
concepts, missing links) are intentionally out of scope for this reconstruction.
The previous French-primary, scraping/Wikidata/manual-translation pipeline and its
human `gold` alignment review have been fully removed.
