"""Typed state schemas for the LangGraph agent (controller + reflective workers).
"""

from __future__ import annotations

from typing import TypedDict


class DescState(TypedDict, total=False):
    """One description target flowing through the reflective description subgraph."""
    kind: str          # "occupation" | "skill"
    uid: str           # unified_id 
    label: str         # primary_label_en
    ctx: str           # grounding context (domain / Wikidata / aliases)
    correction: str    # corrective instruction injected on a reflect retry
    proposal: str      # the model's latest sentence
    ok: bool           # did it pass validation (length + NLI)?
    reason: str        # rejection reason when ok is False
    reflect: int       # retries used so far (bounded by AGENT_MAX_REFLECT)
    committed: bool    # accepted + written to the snapshot


class LinkState(TypedDict, total=False):
    """One occupation flowing through the reflective link subgraph."""
    occ_id: str
    occ_label: str
    occ_desc: str          # occupation definition
    window: int            # shortlist window index (widened on reflect)
    correction: str        # stricter re-ask instruction on reflect
    picks: list            # skill labels the LLM chose this pass
    excluded: list         # labels rejected in earlier passes
    verified: list         # [(skill_id, cosine)] that cleared BOTH cosine and NLI
    reflect: int
    _ovec: object          # occupation embedding vector, a declared channel so it PERSISTS across the
    _shortlist_ids: dict   # reflect->propose loop


class ControllerState(TypedDict, total=False):
    """Top-level controller state: which gaps to work and the running tally."""
    gaps: list             # subset of AGENT_GAPS to dispatch, in order
    stats: dict            # per-worker result dicts
    added_nodes: bool      # did the emerging worker add Wikidata-confirmed skill nodes?
