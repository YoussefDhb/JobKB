# JobKB validation report
_generated 2026-07-23T22:52:31+00:00_

## 3. LLM-connection accuracy audit
**38 `llm_inferred` occupation→skill links** (created with a cosine≥0.45 gate only) re-validated independently:
- NLI (occupation definition ⊨ "requires {skill}"): **38/38 (100.0%)** pass ≥0.5.
- Demand corroboration (occupation really demands the skill or a near one in its posting profile): **10/38 (26.3%)** (0 exact).
- Both signals agree (high-confidence): **10/38**.

**26 `llm` descriptions** re-verified by NLI: **26/26 (100.0%)** pass ≥0.5.

