# JobKB

An **English-primary, IT-focused occupation & skill knowledge base**, built fully automatically from
local public taxonomies. French is a first-class secondary language (labels completed from Wikidata and
validated NLLB machine translation). There is **no scraping and no human in the loop**: cross-source
duplicates are resolved and alignments validated with open-source HuggingFace models, and a single build
runs the whole pipeline — alignment, faceted ontology, ISCO attachment, unified merge, then Wikidata QID
anchoring, LLM description/link generation and bilingual label completion — every step validated before it
touches the graph, snapshot-resumable and fail-open (a build with no HF token still succeeds).

## Quickstart

```bash
python -m venv .venv && .venv\Scripts\activate      # Windows (source .venv/bin/activate on Unix)
pip install -r requirements.txt
cp .env.example .env        # add HF_TOKEN=hf_... (optional; enrichment is fail-open without it)

python run_pipeline.py                 # full build + enrichment  (~a few hours on CPU, NLI-bound)
python run_pipeline.py --core-only     # full build, no enrichment (fast, network-free)
python run_pipeline.py --stages qa     # integrity + consistency report over the current kb/
```

See `COMMANDS.md` for the full command reference.

## Sources

Scope = **core IT + managers + data**, applied consistently to every source. There is no
ISCO↔SOC↔NOC↔ROME crosswalk in these datasets, so the cross-source **alignment is the crosswalk**; no
source is privileged (ESCO uses its native ISCO code, ONET/NOC/ROME attach directly to ISCO by embedding
similarity).

| Source | Role | IT scope |
|---|---|---|
| **ISCO-08** | Neutral backbone (every source attaches to it) | sub-major 25 & 35 + minor 133 |
| **ESCO** | Occupations, skills, relations (native ISCO code) | `iscoGroup` 25/35/133 + all digital/digComp skills |
| **ONET** | IT occupations + technology tools | SOC 15-12xx + 15-2051 + 11-3021 |
| **NOC 2021** | Bilingual EN/FR occupations | minors 2122/2123 + 20012, 21211, 21311, 2222x |
| **ROME** | French métiers + competences (cross-lingual) | domain M18 + data/CDO codes |
| **SFIA 9** | Skills only — professional IT competency framework | 95 IT-scoped skills |
| **CSO 3.5** | Skills only — Computer Science Ontology subset | ~530 IT topics (superTopicOf, depth≤2, balanced) |
| **Lightcast Open Skills** | Skills only — large categorised taxonomy | IT category (17.0) ≈ 5,240 skills |
| **Kaggle technical skills** | Skills only | 528 skills, 9 IT categories |
| **e-CF 4.0** | Skills only — EU e-Competence Framework | 41 ICT competences, self-classified |
| **Soft skills** (curated) | Skills only — recruiter-vocabulary soft skills | 22 noun-form soft skills |
| **WEF Global Skills Taxonomy** | Skills only — soft-skill standard | 47 soft skills, 5 sub-domains; 16 core → transversal |
| **IT soft-skills taxonomy** (curated) | Skills only — comprehensive IT soft skills | 38 new soft skills; 10 core → transversal |
| **ADEM** (Luxembourg) | Relations only — real vacancy demand | weighted `demand` edges on M18* occupations |
| **Job postings** (mined) | Relations only | role→skill `demand` edges |
| **data_jobs** (lukebarousse) | Hybrid — 785k postings | harvests ~50 tools + large-scale `demand` |
| **zenodo** (Montandon 2019) | Hybrid — 17.9k SO postings | 55 tools + `demand` (hard & soft) |
| **Djinni** | Relations only — 142k IT postings | `demand` across 15 occupations |
| **LinkedIn SWE** | Relations only — 9.4k SWE postings | `demand` → software-developer family |
| **Kaggle job-skill-set** | Relations only — 240 IT postings | `demand` for IT support/PM/manager roles |
| **Emerging roles** (curated) | Occupations absent from ESCO/O*NET | 6 roles (Analytics/MLOps/BI/Data-Gov/Full-Stack/Back-End), ISCO-attached |

**Skills-only sources** contribute skills but no occupations (`contributes_occupations=False`), so they
skip ISCO attachment: their skills are classified into the ontology, aligned/merged with the existing
vocabulary, and reach occupations transitively. **Relation-only sources** add weighted `demand`
occupation→skill edges between existing entities (no new nodes). The soft branch has real structure (five
WEF-aligned sub-domains + a catch-all); a curated IT-relevance filter (`relevance.is_non_it_soft`) prunes
O*NET psychometric abilities and non-IT ESCO life-skills, keeping the branch IT-focused. Curated
authoritative lists (WEF/soft-skills) bypass the semantic IT gate, like the code-filtered taxonomies.

## Pipeline

```
src/
  config.py        # paths, EN-primary schema, IT scope per source, HF model ids, tunables
  common.py        # deterministic ids, label normalization, idempotent CSV IO, provenance
  ingest/          # isco, esco, onet, noc, rome  (each IT-filtered, EN-primary)
  sources/         # pluggable source framework: base + registry + per-source loaders
  hierarchy.py     # faceted ontology: skill -> category -> domain -> type + occupation -> domain facet
  relevance.py     # automatic IT-relevance / noise gate at ingest (for pluggable sources)
  align/           # candidates (embeddings) -> verify (NLI) + match_key dedup -> attach (ISCO)
  merge.py         # source-neutral unified concept clustering / de-duplication
  wikidata.py      # QID anchoring + authoritative descriptions/aliases (enrichment)
  llm.py           # HF LLM descriptions / inferred links / emerging tech (one-shot enrichment)
  agent/           # LangGraph agentic enrichment (supersedes llm on a full build)
  translate.py     # bilingual EN/FR label completion (enrichment)
  validation/      # consistency invariants + external gold coverage + LLM-link audit
  export/          # graph export: RDF/OWL Turtle + GraphML + JSON + interactive HTML
  incremental.py   # add/remove ONE source without a full rebuild
  pipeline.py      # orchestrator + QA/integrity report (self-certifies consistency)
run_pipeline.py    # CLI entry point
notebooks/inspect.ipynb   # verification & testing notebook over kb/
```

Core stages are `ingest → hierarchy → align → attach → merge → qa`, each idempotent and runnable
standalone against the existing `kb/`. On a full build the post-merge enrichment stages run automatically:
`… → merge → **wikidata → agent → translate** → qa` (Wikidata first — its QIDs/descriptions feed the
rest; the `agent` stage falls back to the one-shot `llm.run()` if `langgraph` is absent). Each enrichment
stage is fail-open and snapshot-resumable. `--core-only` skips them.

```bash
python run_pipeline.py --stages merge            # re-derive unified concepts (seconds)
python run_pipeline.py --from align              # align -> attach -> merge -> qa
python run_pipeline.py --stages ingest --source ESCO   # re-ingest one source
python run_pipeline.py --list-stages
```

A full build takes a few hours on CPU, dominated by mDeBERTa NLI verification (~2 s/pair — the models
review every merge since no human does, a deliberate accuracy-over-speed trade-off). bge-m3 embeddings are
disk-cached (`kb/.emb_cache_*.pkl`), so a threshold-only rebuild reuses them.

## Adding a source

A source is added to an existing KB without a rebuild — ingested, standardized, aligned only against the
existing entities, attached to ISCO, and merged:

```bash
python run_pipeline.py --add NAME      # incrementally add one registered source
python run_pipeline.py --remove NAME   # remove it and repair the graph
python run_pipeline.py --list-sources
```

To add a dataset, subclass `StructuredSource` (`src/sources/base.py`, see `sfia.py`/`cso.py`) and register
it in `src/sources/registry.py`. Every pluggable source is screened at ingest by the relevance/noise gate
(`src/relevance.py`): malformed and confidently non-IT rows are blocked (logged to
`kb/blocked_entities.csv`); built-in code-filtered taxonomies bypass it.

## Alignment, taxonomy & merge

Alignment is automatic and model-verified: embedding candidate generation (bge-m3) → NLI verification
(mDeBERTa on definitions for occupations) → SKOS relations + a source-neutral merge flag. `merge.py`
clusters the `exactMatch` graph into unified concepts (English-primary label, merged synonyms, hub ISCO
code, member back-links). A semantic occupation merge is triple-guarded (embedding floor + same ISCO group
+ mutual NLI entailment), so nothing is de-duplicated on similarity alone.

The taxonomy is a **faceted 4-level ontology** over a shared functional-domain layer: skills go
`skill → category (22) → domain (10) → type (2 hard/soft)`, and each occupation is linked (`in_domain`) to
one of the same 10 domains, so the graph is navigable `occupation ↔ domain ↔ category ↔ skill`. ISCO stays
the authoritative occupation backbone.

## Knowledge-base schema (`kb/`)

| File | Contents |
|---|---|
| `occupations.csv` | one row per source occupation / ISCO-group node (EN+FR labels, ISCO & source codes) |
| `skills.csv` | one row per source skill (+ `TAXONOMY` type/domain/category nodes), hard/soft + IT category |
| `labels.csv` | every preferred/alt label per entity, per language |
| `occupation_skill_relations.csv` | occupation ↔ skill links (essential/optional/demand/transversal/llm_inferred) |
| `hierarchy.csv` | ISCO tree + source→ISCO attachment + skill→category→domain→type + occupation→domain facet |
| `concept_alignments.csv` | cross-source matches (SKOS relation, confidence, method, validated) |
| `unified_occupations.csv` / `unified_skills.csv` | de-duplicated unified concepts |
| `provenance.csv` | audit trail: what each stage produced and when |

## Validation (`--validate`)

Read-only over the graph (`src/validation/`); writes `validation/report.md` + per-track CSVs. Three tracks:

1. **Logical-consistency certificate** — 13 graph-logic invariants (acyclicity, single-parent, ISCO
   reachability, no skill→skill edges, endpoint types, unified integrity, id uniqueness, …). Runs inside
   `qa()`, so every build self-certifies `consistency: 13/13 invariants PASS`.
2. **External coverage benchmark** vs three expert-annotated NER corpora (SkillSpan, Sayfullina, FIJO),
   exact/alias + bge-m3 semantic:

   | dataset · slice | gold | exact | +semantic |
   |---|--:|--:|--:|
   | SkillSpan · knowledge/tech (IT hard) | 1,840 | 27.0% | **73.2%** |
   | SkillSpan · skill/tech | 1,884 | 3.7% | 58.0% |
   | Sayfullina · soft | 1,140 | 7.1% | 62.5% |
   | FIJO · French soft | 692 | 0.3% | 35.0% |

   IT hard-skill coverage is strong; exact is low by construction (multi-word gold vs a noun taxonomy) and
   residual misses are items the KB correctly excludes (degrees, "Consulting", …).
3. **LLM-connection audit** — re-validates the `llm_inferred` links (NLI + demand corroboration) and LLM
   descriptions, confirming the inferred links are the KB's least-corroborated content and belong in a
   separate `llm_inferred` type, never mixed into `demand`.

## Graph export (`--export`)

Materializes the deduplicated **concept graph** (11,424 nodes / ~44k edges; read-only over `kb/`, writes
to `export/`). Endpoints are remapped to unified concepts via `member_entity_ids`, and each skill links to
its single authoritative category.

- **`jobkb.ttl`** — RDF/OWL Turtle (SKOS + a light JobKB ontology: class disjointness, typed
  `requiresSkill`/`inDomain` object properties, `skos:exactMatch` to Wikidata; ~167k triples). Loads in
  Protégé/GraphDB; a lightweight rdflib axiom self-check stands in for a Java reasoner.
- **`jobkb.graphml`** — for Gephi / Cytoscape / yEd.
- **`jobkb.json`** — generic `{meta, nodes, edges}` graph JSON for web/D3 or a custom graph-DB loader.
- **`jobkb.html`** — self-contained interactive backbone overview (~300 nodes; inline canvas, no external
  library).
- **`jobkb_full.html`** — self-contained interactive full graph (all 11,424 / 44,176). The layout is
  precomputed in Python, so the browser runs no physics; colour = domain, hover highlights a node's links.

## Not in this build

The reasoner side is intentionally an rdflib axiom self-check, not a bundled Java DL reasoner. The
`SDE-jobhuntai` raw-postings extraction (an `ExtractionSource` using HF skill-extraction) is a future data
add. The previous French-primary, scraping/manual-translation pipeline and its human `gold` review are
fully removed.
