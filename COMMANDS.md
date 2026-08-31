# JobKB — Command Guide

This guide covers everything you need about kb building, exploring, extending, and exporting.

> Pipeline stages, in order: `ingest → hierarchy → align → attach → merge → qa`.

> Run every command from the project root with the virtual environment active.

## Common Commands

| I want to… | Command |
|---|---|
| Build the whole KB (enriched) | `python run_pipeline.py` |
| Build fast, no network/models | `python run_pipeline.py --core-only` |
| Explore it (notebook) | `jupyter notebook notebooks/inspect.ipynb` |
| Check integrity | `python run_pipeline.py --stages qa` |
| Export the graph (RDF/GraphML/JSON/HTML) | `python run_pipeline.py --export` |
| Update the KB (live jobs) | `python run_pipeline.py --refresh-scraper` |


## 1. Setup

```bash
python -m venv .venv
.venv\Scripts\activate            # Windows   (source .venv/bin/activate on macOS/Linux)
pip install -r requirements.txt
```

Copy `.env.example` to `.env` and add your HuggingFace token: `HF_TOKEN=hf_...`
(without a token the build still succeeds, it just skips LLM steps).


## 2. Build the knowledge base


```bash
python run_pipeline.py              # full build + enrichment
python run_pipeline.py --core-only  # everything EXCEPT enrichment — fast, offline, network-free
python run_pipeline.py --keep       # full build but keep the existing kb/
```

Enrichment (Wikidata QIDs, agentic LLM descriptions/links, bilingual EN/FR labels) runs automatically after `merge`. Generation is snapshot-resumable, so coverage converges over successive runs, even for a HF free-tier (`JOBKB_LLM_LOCAL=1`).

## 3. Explore & share the result

The showcase notebook is like a guided tour: architecture, integrity, the faceted taxonomy, 10 real recommender use-cases, and an interactive graph.

```bash
jupyter notebook notebooks/inspect.ipynb
jupyter nbconvert --to notebook --execute --inplace notebooks/inspect.ipynb   # run headless
```

**Export the graph** (writes to `export/`):

```bash
python run_pipeline.py --export            # all formats at once
```

| Format | File | Use with |
|---|---|---|
| `--export rdf` | `export/jobkb.ttl` | Protégé / GraphDB (RDF/OWL + SKOS, axiom-checked) |
| `--export graphml` | `export/jobkb.graphml` | Gephi / Cytoscape / yEd / networkx |
| `--export json` | `export/jobkb.json` | web / D3 / custom loaders |
| `--export viz` | `export/jobkb.html` | interactive backbone map |
| `--export fullviz` | `export/jobkb_full.html` | interactive full graph |

## 4. Data sources

A full build already ingests every registered source. Use `--add` / `--remove` only to update a single source against the existing `kb/` (no full rebuild is needed).

```bash
python run_pipeline.py --list-sources    # all sources + their flags
python run_pipeline.py --add NAME        # ingest+align+attach+merge one source
python run_pipeline.py --remove NAME     # drop a source and repair the graph
```

| Group | Sources | Contributes |
|---|---|---|
| **Occupation taxonomies** | ISCO · ESCO · O*NET · NOC · ROME | the occupation backbone + skills |
| **Skill taxonomies** | SFIA · CSO · LIGHTCAST · KAGGLE · ECF · SOFTSKILLS · WEF · SOFTTAXO | IT + soft skills |
| **Emerging roles** | EMERGING | new IT occupations (ISCO-attached) |
| **Labour-market demand** | ADEM · JOBS · DATAJOBS · DJINNI · LINKEDIN_SWE · KAGGLE_JOBS · ZENODO | weighted occupation→skill `demand` edges |
| **Linked data** | `--wikidata` | Wikidata QID anchors (`kb/wikidata_links.csv`) |
| **Real-time** | SCRAPER | live job postings |

Every source is screened by the relevance gate at ingest: non-IT / malformed rows are blocked before they enter the KB. Inspect: `cat kb/blocked_entities.csv` or the `relevance gate — blocked: N` line in `qa`.

To add your own dataset: subclass `StructuredSource` in `src/sources/base.py` (see `sfia.py`), register it in `src/sources/registry.py`, then `--add YOURSOURCE`.

## 5. Real-time web scraping

Keeps the KB current with the fast-moving IT market. Two steps keep the core build reproducible: a crawl snapshots raw postings, then an offline ingest. The scrapping is an opt-in and not part of the full build.

```bash
python run_pipeline.py --scrape all         # crawl every source
python run_pipeline.py --add SCRAPER         # ingest the snapshots
python run_pipeline.py --refresh-scraper     # crawl all + re-ingest + enrich in one step
python run_pipeline.py --remove SCRAPER      # undo
```

Three keyless, IT-filtered tiers (`--scrape apis|ats|trends`): **APIs** (Jobicy, Remotive, RemoteOK, The Muse, WWR), **ATS boards** (Greenhouse, Ashby, Lever) and **Trend signals** (Hacker News, GitHub, Stack Overflow). 

New roles are minted only if recurring, genuinely new, IT-skilled, and role-headed; `demand` edges are recency-weighted so they track the current market.

You can schedule `--refresh-scraper` a few times a day:

```bash
# Linux/macOS cron (every 6h):
cd /path/to/JobKB && .venv/bin/python run_pipeline.py --refresh-scraper >> scrape.log 2>&1
# Windows Task Scheduler (hourly):
schtasks /create /tn JobKB-Scrape /sc HOURLY /tr "d:\JobKB-final\.venv\Scripts\python.exe d:\JobKB-final\run_pipeline.py --refresh-scraper"
```

The scrapping is polite by design: descriptive User-Agent, retries/back-off, rate-limiting. Each row keeps its source `url` for attribution, respecting each site's ToS is the operator's responsibility.

A `GITHUB_TOKEN` can be added in `.env` to raise GitHub's rate limit.

## 6. Enrichment

These run automatically on a full build (`wikidata → agent → translate`). Run them individually to top up an existing KB. All are snapshot-cached and fail-open.

```bash
python run_pipeline.py --wikidata     # anchor skills + occupations to Wikidata QIDs
python run_pipeline.py --agent        # agentic LLM enrichment (LangGraph: propose→verify→reflect→commit)
python run_pipeline.py --translate    # fill empty EN/FR labels (Wikidata labels + validated NLLB MT)
```

The first `--wikidata` run queries WDQS; re-runs are fully offline. The agent writes `agent/report.md`.

## 7. Validation

```bash
python run_pipeline.py --validate              # all 3 tracks -> validation/report.md + CSVs
python run_pipeline.py --validate consistency  # 13-invariant certificate (no models)
```

- **consistency** : 13 graph-logic invariants (acyclicity, single-parent, no skill→skill, ISCO
  reachability…); also runs inside every `qa` (`consistency: 13/13 invariants PASS`).
- **coverage** : skill-vocabulary recall vs SkillSpan / Sayfullina / FIJO (exact + semantic).
- **llm** : re-audits the `llm_inferred` links and LLM descriptions (NLI + demand corroboration).

## 8. Advanced Commands

Run selected stages against the existing `kb/` (never wiped unless with `--clean`):

```bash
python run_pipeline.py --stages merge          # re-derive unified concepts
python run_pipeline.py --from align            # from a stage to the end
python run_pipeline.py --from attach --to merge # a contiguous range
python run_pipeline.py --stages ingest --source ESCO   # scope to one source
```

Running an upstream stage marks downstream ones stale: the run prints a `[note]` telling you what to re-run. `--stages` and `--from/--to` are mutually exclusive.

**Swap models** (env vars):

```bash
$env:JOBKB_EMBED_MODEL="BAAI/bge-m3"                                  # embedder
$env:JOBKB_NLI_MODEL="MoritzLaurer/mDeBERTa-v3-base-mnli-xnli"        # NLI verifier
```

The embedding cache lives at `kb/.emb_cache_<model>.pkl` (you can delete if you want to force re-encoding).

**Common workflows:**

```bash
python run_pipeline.py --stages merge                # tuned a threshold -> re-derive concepts
python run_pipeline.py --from attach                 # changed attach logic -> re-attach + merge
python run_pipeline.py --stages ingest,hierarchy,merge --source ESCO   # fixed one source's mapping
python run_pipeline.py --stages qa                   # just check integrity
```

## Important Paths

| Path | Contents |
|---|---|
| `kb/` | the built knowledge base (unified concepts, relations, hierarchy, labels, provenance) |
| `export/` | graph exports (`jobkb.ttl` / `.graphml` / `.json` / `.html` / `_full.html`) |
| `validation/` | validation report + per-track CSVs |
| `notebooks/inspect.ipynb` | the showcase / verification notebook |
| `src/config.py` | all tunable thresholds, model ids, and source settings |
| `.env` | secrets (`HF_TOKEN`, optional `GITHUB_TOKEN`) |
