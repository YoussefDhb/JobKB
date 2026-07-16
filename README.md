# JobKB

A knowledge-graph pipeline that reconciles IT occupations and skills, in French,
from several heterogeneous public sources.


## Sources

| Source | What it provides | Scope filter |
|---|---|---|
| **ESCO**  | EU occupation/skill taxonomy | 13 IT-related ISCO unit groups (`Datasets/ESCO/*_fr.csv`) |
| **ISCO-08** | Hierarchical occupation skeleton (nested codes, e.g. `2512 ⊂ 251 ⊂ 25 ⊂ 2`) | groups needed to root the ESCO subset |
| **ROME** | France occupation nomenclature | domain `M18` (informatique) |
| **Wikidata** | Emerging IT concepts, via live SPARQL query | occupations under IT-related anchor concepts |
| **RemoteOK / Arbeitnow** | Real job postings, via public JSON APIs | keyword-filtered to IT titles/tags |

## Pipeline

Notebooks in `notebooks/` run in order and share helpers/paths/schema from
`notebooks/jobkb_common.py`. Each stage writes into `canonical/` and appends
an entry to `canonical/provenance.csv`.

1. **`01_ingest_esco_isco.ipynb`** — filters ESCO occupations to the IT ISCO
   scope, pulls their linked skills, classifies each skill hard/soft (soft =
   member of ESCO's transversal collection), then builds the ISCO hierarchy
   and attaches ESCO occupations to their base group.
2. **`02_ingest_rome_wikidata_scraped-data.ipynb`** — ingests ROME's M18
   occupations (with appellation synonyms) and their "savoir-faire/savoir-être/
   savoirs" as skills; runs a live Wikidata SPARQL query for emerging IT
   concepts; scrapes and ingests RemoteOK + Arbeitnow job postings (cached as
   JSON under `scraped/`).
3. **`03_translate_data.ipynb`** — batches English labels (from Wikidata/
   RemoteOK/Arbeitnow) into LLM translation prompts (`llm_io/prompts/`),
   ingests the pasted-back responses (`llm_io/responses/`), applies accepted
   translations, and generates a manual review file
   (`scraped/review_translated.csv`) to accept/reject scraped entities.
4. **`04_align_entities.ipynb`** — resolves the same real-world occupation
   across sources using exact-label matching plus multilingual sentence-
   embedding similarity (`paraphrase-multilingual-MiniLM-L12-v2`), assigns a
   SKOS relation (`exactMatch` / `closeMatch` / `relatedMatch`) and confidence
   score, and exports `canonical/alignment_review.csv` for manual labeling + threshold evaluation.
   It also grafts non-ESCO occupations (ROME/RemoteOK/Arbeitnow) onto the ISCO
   hierarchy: any occupation directly matched to an ESCO occupation
   inherits that occupation's ISCO group (`source=ALIGNMENT` edges in
   `hierarchy.csv`; ties broken by highest-confidence match).
5. **`05_build_hierarchy.ipynb`** — adds ESCO's transversal soft-skills
   collection (reclassifying already-linked skills hard→soft where
   applicable), builds the skill hierarchy from ESCO skill groups, and
   sub-types hard skills (language/tech, network, security, database, ...).

## Canonical schema (`canonical/`)

| File | Contents |
|---|---|
| `occupations.csv` | one row per occupation/job-title/ISCO-group node |
| `skills.csv` | one row per skill/skill-group node, with hard/soft + IT subtype |
| `labels.csv` | every preferred/alt/hidden label per entity, per language |
| `occupation_skill_relations.csv` | occupation ↔ skill links (essential/optional) |
| `hierarchy.csv` | broader/narrower edges (ISCO tree + alignment grafts, ESCO skill groups) |
| `concept_alignments.csv` | cross-source entity matches with confidence + method |
| `alignment_review.csv` | alignment matches exported for manual labeling |
| `translation_suggestions.csv` | LLM-proposed translations, with status |
| `provenance.csv` | audit trail: what each ingestion run wrote and when |

Entity IDs are deterministic, so re-running a
notebook against unchanged input reproduces the same IDs. Each stage replaces
only the rows it owns (`source` column), so notebooks can be re-run
independently without clobbering other sources' data.

## Setup

```
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

Run the notebooks in `notebooks/` in numeric order (`01` → `05`). Some steps
require manual intervention between runs.
