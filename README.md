# JobKB

An **English-primary**, IT-focused occupation & skill **knowledge base**, built
**fully automatically** from five local public taxonomies. French is kept as a
secondary language wherever a source provides it. There is **no scraping, no live
web calls, and no human in the loop** — cross-source duplicates are resolved and
alignments validated with open-source HuggingFace models.

## Sources (IT-filtered, English where available)

| Source | Role | IT scope filter |
|---|---|---|
| **ISCO-08** | Backbone hierarchy (the hub every source attaches to) | sub-major groups **25** & **35** (ICT professionals / technicians) |
| **ESCO** | Occupations (+ skills, relations, skill groups). Carries the ISCO code. | occupations whose `iscoGroup` starts with `25`/`35` |
| **ONET** | Rich IT occupations + real technology tools (`software_skills`) | SOC `15-12xx` (Computer) + `15-2051` (Data Scientists) |
| **NOC 2021** | Bilingual (EN/FR) occupations + illustrative-example synonyms | unit groups in minors `2122`/`2123` + `20012`, `21211`, `21311`, `2222x` |
| **ROME** | French métiers + competences (French enrichment) | professional domain **`M18`** |

There is no ISCO↔SOC↔NOC↔ROME crosswalk shipped with these datasets, so the
cross-source **alignment itself acts as the crosswalk**: ONET, NOC and ROME
occupations are grafted onto the ISCO hub through validated matches to ESCO.

## Pipeline (package + orchestrator)

```
jobkb/
  config.py        # paths, EN-primary schema, IT scope per source, HF model ids, tunables
  common.py        # deterministic ids, label normalization, idempotent CSV IO, provenance
  ingest/          # isco, esco, onet, noc, rome  (each IT-filtered, EN-primary)
  hierarchy.py     # ESCO skill-group tree + hard/soft (transversal) + IT sub-typing
  align/           # candidates (embeddings) -> verify (NLI, no human) -> graft (ISCO hub)
  merge.py         # canonical concept clustering / de-duplication
  pipeline.py      # orchestrator + QA/integrity report
run_pipeline.py    # CLI entry point
notebooks/
  inspect.ipynb    # QA & spot-checks over canonical/
  test.ipynb       # WorkRB benchmark sanity check
```

Run it:

```bash
python -m venv .venv && .venv\Scripts\activate
pip install -r requirements.txt
python run_pipeline.py            # full build (ingest -> hierarchy -> align -> merge)
python run_pipeline.py --no-align # ingest + hierarchy only (no HF model downloads)
```

The build is **idempotent**: entity ids are deterministic, each stage owns its
source rows, and `run_pipeline.py` rebuilds `canonical/` clean by default.

## Alignment & validation (no human in the loop)

1. **Candidates** — multilingual sentence embeddings (`nomic-embed-text-v2-moe`
   → `paraphrase-multilingual-MiniLM-L12-v2` → TF-IDF fallback) give the top-k
   nearest neighbours between every pair of sources.
2. **Verify** — for occupations, a multilingual **NLI model**
   (`mDeBERTa-v3-base-mnli-xnli`) checks bidirectional entailment of the two
   definitions (mutual entailment ⇒ same concept); skills rely on normalized-label
   identity + embedding similarity. Confidence maps to SKOS
   (`exactMatch` / `closeMatch` / `relatedMatch`, plus `broad/narrowMatch` for
   asymmetric entailment). Every accepted pair is `validated = auto`.
3. **Graft** — each non-ISCO occupation inherits the ISCO unit group of its best
   validated ESCO match.
4. **Merge** — connected components of the `exactMatch` graph become **canonical
   concepts** (`canonical_occupations.csv`, `canonical_skills.csv`) with an
   English-primary label, French secondary, merged synonyms, the hub ISCO code,
   and back-links to their source members.

All models are open-source; if none can be loaded (e.g. offline) the pipeline
degrades gracefully (TF-IDF candidates, NLI off) and still produces the KB.

## Canonical schema (`canonical/`)

| File | Contents |
|---|---|
| `occupations.csv` | one row per source occupation / ISCO-group node (EN + FR labels, ISCO & source codes) |
| `skills.csv` | one row per source skill / skill-group, with hard/soft + IT subtype |
| `labels.csv` | every preferred/alt/hidden label per entity, per language |
| `occupation_skill_relations.csv` | occupation ↔ skill links (essential/optional) |
| `hierarchy.csv` | ISCO tree + ESCO skill groups + alignment grafts (`broader_than` edges) |
| `concept_alignments.csv` | cross-source matches with SKOS relation, confidence, method, `validated` |
| `canonical_occupations.csv` | de-duplicated canonical occupations (merged members) |
| `canonical_skills.csv` | de-duplicated canonical skills |
| `provenance.csv` | audit trail: what each stage produced and when |

## Not in this build (deliberate follow-ons)

RDF/OWL graph export, and LLM content-enrichment (niche IT roles, emerging-tech
concepts, missing links) are intentionally out of scope for this reconstruction.
The previous French-primary, scraping/Wikidata/manual-translation pipeline and its
human `gold` alignment review have been fully removed.
