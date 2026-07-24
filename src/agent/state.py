"""Typed state schemas for the LangGraph agent (controller + reflective workers).

Kept deliberately small: the heavy objects (LLM client, NLI verifier, embedder, KB rows) live in a
`tools.Toolbox` the node closures capture — only the per-run *decision* state flows through the graph.
"""

from __future__ import annotations

from typing import TypedDict


class DescState(TypedDict, total=False):
    """One description target flowing through the reflective description subgraph."""
    kind: str          # "occupation" | "skill"
    uid: str           # unified_id (snapshot key)
    label: str         # primary_label_en
    ctx: str           # grounding context (domain / Wikidata / aliases)
    correction: str    # corrective instruction injected on a reflect retry ("" on the first pass)
    proposal: str      # the model's latest sentence
    ok: bool           # did it pass validation (length + NLI)?
    reason: str        # rejection reason when ok is False
    reflect: int       # retries used so far (bounded by AGENT_MAX_REFLECT)
    committed: bool     # accepted + written to the snapshot


class LinkState(TypedDict, total=False):
    """One occupation flowing through the reflective link subgraph."""
    occ_id: str
    occ_label: str
    occ_desc: str          # occupation definition, if any (premise for the NLI gate)
    window: int            # shortlist window index (widened on reflect)
    correction: str        # stricter re-ask instruction on reflect
    picks: list            # skill labels the LLM chose this pass
    excluded: list         # labels rejected in earlier passes (never re-proposed)
    verified: list         # [(skill_id, cosine)] that cleared BOTH cosine and NLI
    reflect: int


class ControllerState(TypedDict, total=False):
    """Top-level controller state: which gaps to work and the running tally."""
    gaps: list             # subset of AGENT_GAPS to dispatch, in order
    stats: dict            # per-worker result dicts (assembled for the report)
    added_nodes: bool      # did the emerging worker add Wikidata-confirmed skill nodes?
