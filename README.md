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

There is no ISCO↔SOC↔NOC↔ROME crosswalk shipped with these datasets, so the
cross-source **alignment itself acts as the crosswalk**. **No source is privileged:**
ESCO uses its native ISCO code; ONET, NOC and ROME each attach **directly** to the
ISCO groups by embedding similarity (never routed through ESCO).

## Pipeline (package + orchestrator)

```
src/
  config.py        # paths, EN-primary schema, IT scope per source, HF model ids, tunables
  common.py        # deterministic ids, label normalization, idempotent CSV IO, provenance
  ingest/          # isco, esco, onet, noc, rome  (each IT-filtered, EN-primary)
  hierarchy.py     # neutral skill ontology: every skill -> IT sub-domain -> Hard/Soft
  align/           # candidates (embeddings) -> verify (batched NLI) -> attach (ISCO, all sources)
  merge.py         # source-neutral unified concept clustering / de-duplication
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

The **skill hierarchy** is a single neutral ontology: every skill of every source is
classified into an IT **sub-domain** (programming, data, networks, security, cloud,
web, AI/ML, systems, IT management, methodology, ...) under a **Hard/Soft** type —
`skill → sub-domain → type`. No skill is left flat, and no source shapes the tree.

All models are open-source; if none can be loaded (e.g. offline) the pipeline
degrades gracefully (TF-IDF candidates, NLI off) and still produces the KB.

## Knowledge-base schema (`kb/`)

| File | Contents |
|---|---|
| `occupations.csv` | one row per source occupation / ISCO-group node (EN + FR labels, ISCO & source codes) |
| `skills.csv` | one row per source skill (+ `TAXONOMY` type/sub-domain nodes), hard/soft + IT sub-domain |
| `labels.csv` | every preferred/alt/hidden label per entity, per language |
| `occupation_skill_relations.csv` | occupation ↔ skill links (essential/optional) |
| `hierarchy.csv` | ISCO tree + every-source→ISCO attachment + skill→sub-domain→type (`broader_than`) |
| `concept_alignments.csv` | cross-source matches with SKOS relation, confidence, method, `validated` |
| `unified_occupations.csv` | de-duplicated unified occupations (merged members) |
| `unified_skills.csv` | de-duplicated unified skills |
| `provenance.csv` | audit trail: what each stage produced and when |

## Not in this build (deliberate follow-ons)

RDF/OWL graph export, and LLM content-enrichment (niche IT roles, emerging-tech
concepts, missing links) are intentionally out of scope for this reconstruction.
The previous French-primary, scraping/Wikidata/manual-translation pipeline and its
human `gold` alignment review have been fully removed.
