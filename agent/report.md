# JobKB agentic enrichment report
_generated 2026-08-06T20:32:38+00:00_

LangGraph controller + reflective workers (propose → verify → reflect/retry → commit). The LLM proposes; the deterministic verifiers (bge-m3, mDeBERTa NLI, Wikidata) decide. Gaps dispatched this run: `description`.

## Description worker (reflective definition generation)
- targets (uncached): **8007**
- committed: **7915**, deferred: 92, reflection retries used: 567
