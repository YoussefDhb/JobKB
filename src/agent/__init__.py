"""Agentic enrichment (LangGraph): a controller assesses the KB and dispatches reflective workers that
loop propose -> verify -> reflect/retry -> commit over the KB's own tools (bge-m3, NLI, Wikidata).
"""

from __future__ import annotations

import os

from .. import config as C
from .. import common as K

ALL_GAPS = C.AGENT_GAPS


def run(gaps=ALL_GAPS) -> dict:
    """Assess the KB, dispatch the requested reflective workers, re-integrate, and report."""
    gaps = [g for g in gaps if g in C.AGENT_GAPS]
    if not gaps:
        print(f"[AGENT] no valid gaps in {gaps!r}; valid: {C.AGENT_GAPS}", flush=True)
        return {}
    from .tools import Toolbox
    from . import controller
    tb = Toolbox()
    app = controller.build(tb)
    final = app.invoke({"gaps": gaps})
    stats = final.get("stats", {})
    _write_report(gaps, stats)
    print(f"[AGENT] done. report -> {C.AGENT_REPORT_MD}", flush=True)
    return stats


def _write_report(gaps, stats) -> None:
    os.makedirs(C.AGENT_OUT_DIR, exist_ok=True)
    lines = ["# JobKB agentic enrichment report", f"_generated {K.now_iso()}_", "",
             "LangGraph controller + reflective workers (propose → verify → reflect/retry → commit). "
             "The LLM proposes; the deterministic verifiers (bge-m3, mDeBERTa NLI, Wikidata) decide. "
             f"Gaps dispatched this run: `{', '.join(gaps)}`.", ""]

    d = stats.get("description")
    if d is not None:
        lines += ["## Description worker (reflective definition generation)",
                  f"- targets (uncached): **{d.get('targets', 0)}**",
                  f"- committed: **{d.get('committed', 0)}**, deferred: {d.get('deferred', 0)}, "
                  f"reflection retries used: {d.get('reflected', 0)}"
                  + (f" — {d['note']}" if d.get("note") else ""), ""]

    l = stats.get("link")
    if l is not None:
        lines += ["## Link worker (cosine **and** NLI-gated occupation→skill inference)",
                  f"- occupations targeted: **{l.get('targets', 0)}**",
                  f"- links committed: **{l.get('links', 0)}** across {l.get('occupations_linked', 0)} "
                  f"occupations; reflection retries used: {l.get('reflected', 0)}"
                  + (f" — {l['note']}" if l.get("note") else ""),
                  "- every committed link cleared the embedding cosine floor **and** the NLI gate "
                  "(occupation definition ⊨ \"requires {skill}\") — the accept criterion the "
                  "cosine-only `llm_inferred` links lacked.", ""]

    e = stats.get("emerging")
    if e is not None:
        lines += ["## Emerging worker (Wikidata-confirmed new tech)",
                  f"- proposed: {e.get('proposed', 0)}, new candidates: {e.get('new_candidates', 0)}, "
                  f"added (QID-confirmed): **{e.get('added_skills', 0)}**"
                  + (f" — {e['note']}" if e.get("note") else ""), ""]

    a = stats.get("anchor")
    if a is not None:
        lines += ["## Anchor worker (deterministic — no LLM)",
                  f"- anchor-eligible skills: {a.get('eligible', 0)}; unanchored: {a.get('unanchored', 0)}; "
                  f"unattempted by Wikidata: **{a.get('unattempted', 0)}**"
                  + (f"; resolved this run: {a.get('resolving')}" if a.get("resolving") else ""),
                  "- in the standard pipeline the `wikidata` stage runs first, so 0 unattempted here "
                  "is expected and honest; standalone / after new data this does real resolution.", ""]

    with open(C.AGENT_REPORT_MD, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines))
