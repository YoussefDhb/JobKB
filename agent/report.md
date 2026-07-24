# JobKB agentic enrichment report
_generated 2026-07-23T23:14:16+00:00_

LangGraph controller + reflective workers (propose → verify → reflect/retry → commit). The LLM proposes; the deterministic verifiers (bge-m3, mDeBERTa NLI, Wikidata) decide. Gaps dispatched this run: `description, link, emerging, anchor`.

## Description worker (reflective definition generation)
- targets (uncached): **3**
- committed: **1**, deferred: 2, reflection retries used: 2

## Link worker (cosine **and** NLI-gated occupation→skill inference)
- occupations targeted: **6**
- links committed: **38** across 6 occupations; reflection retries used: 0
- every committed link cleared the embedding cosine floor **and** the NLI gate (occupation definition ⊨ "requires {skill}") — the accept criterion the cosine-only `llm_inferred` links lacked.

## Emerging worker (Wikidata-confirmed new tech)
- proposed: 39, new candidates: 5, added (QID-confirmed): **0**

## Anchor worker (deterministic — no LLM)
- anchor-eligible skills: 5994; unanchored: 4831; unattempted by Wikidata: **0**
- in the standard pipeline the `wikidata` stage runs first, so 0 unattempted here is expected and honest; standalone / after new data this does real resolution.
