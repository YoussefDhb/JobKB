"""Controller graph (LangGraph) — assess the KB, dispatch reflective workers, re-integrate.
"""

from __future__ import annotations

from langgraph.graph import StateGraph, START, END

from .. import config as C
from .. import common as K
from .state import ControllerState
from . import workers


def build(tb):
    def assess(s: ControllerState) -> ControllerState:
        gaps = s.get("gaps") or list(C.AGENT_GAPS)
        backend = "live" if tb.has_llm else "none (generative gaps will defer)"
        print(f"[AGENT] assess: gaps={gaps}; generative backend={backend}", flush=True)
        return {"gaps": gaps, "stats": {}, "added_nodes": False}

    def description(s: ControllerState) -> ControllerState:
        if "description" in s["gaps"]:
            workers.run_descriptions(tb, s["stats"])
            print(f"[AGENT] description: {s['stats'].get('description')}", flush=True)
        return {}

    def link(s: ControllerState) -> ControllerState:
        if "link" in s["gaps"]:
            workers.run_links(tb, s["stats"])
            print(f"[AGENT] link: {s['stats'].get('link')}", flush=True)
        return {}

    def emerging(s: ControllerState) -> ControllerState:
        added = workers.run_emerging(tb, s["stats"]) if "emerging" in s["gaps"] else False
        if "emerging" in s["gaps"]:
            print(f"[AGENT] emerging: {s['stats'].get('emerging')}", flush=True)
        return {"added_nodes": s.get("added_nodes") or added}

    def anchor(s: ControllerState) -> ControllerState:
        if "anchor" in s["gaps"]:
            workers.run_anchor(tb, s["stats"])
            print(f"[AGENT] anchor: {s['stats'].get('anchor')}", flush=True)
        return {}

    def finalize(s: ControllerState) -> ControllerState:
        # Weave enrichment back into the KB.
        if s.get("added_nodes"):
            from .. import hierarchy
            from ..align import run as align_run
            hierarchy.run()
            align_run(focus_source=C.SRC_LLM)
        from .. import merge
        merge.run()
        K.log_provenance("AGENT", [{
            "entity_id": "AGENT", "source": "AGENT",
            "source_version": f"langgraph; api={C.LLM_API_MODEL}",
            "retrieved_at": K.now_iso(),
            "retrieval_method": "langgraph controller + reflective workers (propose/verify/reflect)",
            "notes": "; ".join(f"{k}={v}" for k, v in s["stats"].items())[:500],
        }])
        return {}

    g = StateGraph(ControllerState)
    for name, fn in (("assess", assess), ("description", description), ("link", link),
                     ("emerging", emerging), ("anchor", anchor), ("finalize", finalize)):
        g.add_node(name, fn)
    g.add_edge(START, "assess")
    g.add_edge("assess", "description")
    g.add_edge("description", "link")
    g.add_edge("link", "emerging")
    g.add_edge("emerging", "anchor")
    g.add_edge("anchor", "finalize")
    g.add_edge("finalize", END)
    return g.compile()
