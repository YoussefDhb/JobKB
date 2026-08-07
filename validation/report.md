# JobKB validation report
_generated 2026-08-07T11:55:38+00:00_

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
- PASS — relations: no identical duplicate rows (0 identical dups; 34697 rows / 33439 unique (occ,skill,type))

## 2. External coverage benchmark (KB skill-vocabulary recall vs expert gold)
Gold skill mentions pooled across all splits; coverage = a mention's normalized `match_key` hits a KB primary/alt label (exact) or its nearest KB skill label is within 0.75 bge-m3 cosine (semantic).

| dataset | slice | gold | exact% | +semantic% | covered% |
|---|---|--:|--:|--:|--:|
| skillspan | ALL | 6423 | 11.0 | 57.2 | 57.7 |
| skillspan | knowledge/house | 928 | 7.8 | 39.2 | 39.8 |
| skillspan | knowledge/tech | 1840 | 27.3 | 72.6 | 73.4 |
| skillspan | skill/house | 1771 | 3.6 | 49.9 | 50.1 |
| skillspan | skill/tech | 1884 | 3.7 | 58.0 | 58.2 |
| sayfullina | ALL | 1140 | 7.1 | 62.0 | 62.5 |
| sayfullina | skill | 1140 | 7.1 | 62.0 | 62.5 |
| fijo | ALL | 692 | 0.3 | 35.0 | 35.0 |
| fijo | skill | 692 | 0.3 | 35.0 | 35.0 |

### Synonym-normalization (Sayfullina 234-cluster reference)
Of 108 clusters with ≥2 phrasings the KB contains, **22 (20.4%)** resolve all their phrasings to a single KB node (correct normalization).

## 3. LLM-connection accuracy audit
**38 `llm_inferred` occupation→skill links** (created with a cosine≥0.45 gate only) re-validated independently:
- NLI (occupation definition ⊨ "requires {skill}"): **38/38 (100.0%)** pass ≥0.5.
- Demand corroboration (occupation really demands the skill or a near one in its posting profile): **16/38 (42.1%)** (1 exact).
- Both signals agree (high-confidence): **16/38**.

**7955 `llm` descriptions** re-verified by NLI: **7955/7955 (100.0%)** pass ≥0.5.

