# JobKB validation report
_generated 2026-07-23T22:03:02+00:00_

## 1. Logical consistency — 13/13 invariants PASS
- PASS — hierarchy: no dangling edges (0 dangling)
- PASS — hierarchy: no self-loops (0 self-loops)
- PASS — hierarchy: acyclic (DAG)
- PASS — skills: exactly one category parent (0 multi-parent, 0 unplaced)
- PASS — occupations: one backbone + one domain parent (0 bad backbone, 0 bad facet)
- PASS — ISCO backbone: single root, all reach it (1 roots, 0 unreachable)
- PASS — ISCO: no non-IT group leakage (0 leaked groups)
- PASS — no skill->skill hierarchy edges (0 skill->skill edges)
- PASS — skills: hard_soft matches taxonomy (0 mismatched, 0 empty)
- PASS — relations: endpoints correctly typed (0 bad occ, 0 bad skill endpoints)
- PASS — unified: members valid & unshared (0 empty, 0 missing, 0 shared)
- PASS — ids: entity_id & unified_id unique (0 dup entity_id, 0 dup unified_id)
- PASS — relations: no identical duplicate rows (0 identical dups; 33166 rows / 32353 unique (occ,skill,type))

## 2. External coverage benchmark (KB skill-vocabulary recall vs expert gold)
Gold skill mentions pooled across all splits; coverage = a mention's normalized `match_key` hits a KB primary/alt label (exact) or its nearest KB skill label is within 0.75 bge-m3 cosine (semantic).

| dataset | slice | gold | exact% | +semantic% | covered% |
|---|---|--:|--:|--:|--:|
| skillspan | ALL | 6423 | 10.9 | 57.1 | 57.5 |
| skillspan | knowledge/house | 928 | 7.8 | 39.2 | 39.8 |
| skillspan | knowledge/tech | 1840 | 27.0 | 72.4 | 73.2 |
| skillspan | skill/house | 1771 | 3.6 | 49.9 | 50.1 |
| skillspan | skill/tech | 1884 | 3.7 | 57.7 | 58.0 |
| sayfullina | ALL | 1140 | 7.1 | 62.0 | 62.5 |
| sayfullina | skill | 1140 | 7.1 | 62.0 | 62.5 |
| fijo | ALL | 692 | 0.3 | 35.0 | 35.0 |
| fijo | skill | 692 | 0.3 | 35.0 | 35.0 |

### Synonym-normalization (Sayfullina 234-cluster reference)
Of 108 clusters with ≥2 phrasings the KB contains, **22 (20.4%)** resolve all their phrasings to a single KB node (correct normalization).

## 3. LLM-connection accuracy audit
**84 `llm_inferred` occupation→skill links** (created with a cosine≥0.45 gate only) re-validated independently:
- NLI (occupation definition ⊨ "requires {skill}"): **38/84 (45.2%)** pass ≥0.5.
- Demand corroboration (occupation really demands the skill or a near one in its posting profile): **16/84 (19.0%)** (1 exact).
- Both signals agree (high-confidence): **10/84**.

**24 `llm` descriptions** re-verified by NLI: **24/24 (100.0%)** pass ≥0.5.

