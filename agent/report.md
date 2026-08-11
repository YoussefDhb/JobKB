# JobKB agentic enrichment report
_generated 2026-08-11T22:18:33+00:00_

LangGraph controller + reflective workers (propose → verify → reflect/retry → commit). The LLM proposes; the deterministic verifiers (bge-m3, mDeBERTa NLI, Wikidata) decide. Gaps dispatched this run: `description, link, emerging, anchor`.

## Description worker (reflective definition generation)
- targets (uncached): **84**
- committed: **4**, deferred: 80, reflection retries used: 4

## Link worker (cosine **and** NLI-gated occupation→skill inference)
- occupations targeted: **24**
- links committed: **38** across 6 occupations; reflection retries used: 0
- every committed link cleared the embedding cosine floor **and** the NLI gate (occupation definition ⊨ "requires {skill}") — the accept criterion the cosine-only `llm_inferred` links lacked.

## Emerging worker (Wikidata-confirmed new tech)
- proposed: 39, new candidates: 35, added (QID-confirmed): **0**

## Anchor worker (deterministic — no LLM)
- anchor-eligible skills: 5998; unanchored: 4834; unattempted by Wikidata: **0**
- in the standard pipeline the `wikidata` stage runs first, so 0 unattempted here is expected and honest; standalone / after new data this does real resolution.
