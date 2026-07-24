"""Reflective worker subgraphs (LangGraph): each a small StateGraph looping propose -> verify ->
(reflect -> propose)* -> commit/defer, bounded by AGENT_MAX_REFLECT.
"""

from __future__ import annotations

import re

from langgraph.graph import StateGraph, START, END

from .. import config as C
from .. import common as K
from .state import DescState, LinkState


# Description worker — reflective definition generation
def _desc_targets(tb):
    """Occupations + eligible hard skills lacking a description, minus those already cached."""
    from .. import llm
    occ = K.read_all(C.UNIFIED_OCCUPATIONS_CSV)
    skl = K.read_all(C.UNIFIED_SKILLS_CSV)
    targets = []
    for r in occ:
        if llm._needs_desc(r) and (r.get("primary_label_en") or "").strip():
            targets.append(("occupation", r, llm._occ_context(r)))
    for r in skl:
        if (llm._needs_desc(r) and (r.get("primary_label_en") or "").strip()
                and r.get("it_subtype") in C.LLM_DESC_SKILL_SUBDOMAINS):
            targets.append(("skill", r, llm._skill_context(r)))
    if C.LLM_DESC_MAX_TARGETS:
        targets = targets[:C.LLM_DESC_MAX_TARGETS]
    # skip anything already generated + validated in a prior run (agent or llm)
    return [(k, r, ctx) for (k, r, ctx) in targets
            if not tb.snap.get(("desc", r["unified_id"]), {}).get("output")]


def _build_desc_graph(tb):
    from .. import llm

    def propose(s: DescState) -> DescState:
        user = f"{s['kind']}: {s['label']}" + (f"\ncontext: {s['ctx']}" if s['ctx'] else "")
        if s.get("correction"):
            user += f"\n{s['correction']}"
        raw = tb.generate(llm._DESC_SYS, user)
        if raw is None:
            return {"proposal": "", "reason": "no_backend"}
        out = llm._first_sentence(llm._clean_desc(s["label"], raw), C.LLM_DESC_MAX_CHARS)
        return {"proposal": out}

    def verify(s: DescState) -> DescState:
        if not s.get("proposal"):
            return {"ok": False, "reason": s.get("reason") or "empty"}
        ok, _score = tb.check_description("desc", s["uid"], s["label"], s["proposal"])
        return {"ok": ok, "reason": "" if ok else "rejected"}

    def reflect(s: DescState) -> DescState:
        return {"reflect": s.get("reflect", 0) + 1,
                "correction": (f"Your previous definition was rejected ({s.get('reason')}). "
                               f"Reply with ONE concise factual sentence that specifically defines "
                               f"'{s['label']}' — no preamble, no quotes, no label echo.")}

    def commit(s: DescState) -> DescState:
        tb.commit_generation("desc", s["uid"], s["proposal"])
        return {"committed": True}

    def route(s: DescState) -> str:
        if s.get("ok"):
            return "commit"
        if s.get("proposal") and s.get("reflect", 0) < C.AGENT_MAX_REFLECT:
            return "reflect"   # had a real (rejected) generation and retries left
        return "defer"         # no backend, or reflection budget exhausted

    g = StateGraph(DescState)
    g.add_node("propose", propose)
    g.add_node("verify", verify)
    g.add_node("reflect", reflect)
    g.add_node("commit", commit)
    g.add_edge(START, "propose")
    g.add_edge("propose", "verify")
    g.add_conditional_edges("verify", route, {"commit": "commit", "reflect": "reflect", "defer": END})
    g.add_edge("reflect", "propose")
    g.add_edge("commit", END)
    return g.compile()


def run_descriptions(tb, stats):
    targets = _desc_targets(tb)
    if not targets:
        stats["description"] = {"targets": 0, "committed": 0, "deferred": 0, "reflected": 0}
        return
    if not tb.has_llm:
        stats["description"] = {"targets": len(targets), "committed": 0,
                                "deferred": len(targets), "reflected": 0, "note": "no backend (deferred)"}
        return
    app = _build_desc_graph(tb)
    committed = deferred = reflected = 0
    for kind, row, ctx in targets:
        final = app.invoke({"kind": kind, "uid": row["unified_id"], "label": row["primary_label_en"],
                            "ctx": ctx, "reflect": 0, "correction": "", "committed": False})
        reflected += final.get("reflect", 0)
        if final.get("committed"):
            committed += 1
        else:
            deferred += 1
    tb.save()
    stats["description"] = {"targets": len(targets), "committed": committed,
                            "deferred": deferred, "reflected": reflected}


# Link worker — reflective occupation->skill inference with a NEW cosine+NLI accept gate
_STRICTER = ("Be stricter: pick ONLY skills that are unquestionably core to this occupation. "
             "Ignore any you were offered before.")


def _build_link_graph(tb):
    from .. import llm

    def propose(s: LinkState) -> LinkState:
        window = s.get("window", 0)
        shortlist = [sk for sk in tb.shortlist(s["_ovec"], window * C.LLM_LINK_TOPK, C.LLM_LINK_TOPK)
                     if sk["pref_label_en"] not in set(s.get("excluded", []))]
        if not shortlist:
            return {"picks": [], "_shortlist_ids": {}}
        numbered = "\n".join(f"{i+1}. {sk['pref_label_en']}" for i, sk in enumerate(shortlist))
        user = f"occupation: {s['occ_label']}\ncandidate skills:\n{numbered}"
        if s.get("correction"):
            user += f"\n{s['correction']}"
        raw = tb.generate(llm._LINK_SYS, user)
        if raw is None:
            return {"picks": [], "_shortlist_ids": {}}
        nums = sorted({int(n) for n in re.findall(r"\d+", raw) if 1 <= int(n) <= len(shortlist)})
        picks = [shortlist[n - 1]["pref_label_en"] for n in nums][:C.LLM_LINK_MAX_PER_OCC]
        return {"picks": picks,
                "_shortlist_ids": {sk["pref_label_en"]: sk["entity_id"] for sk in shortlist}}

    def verify(s: LinkState) -> LinkState:
        verified, newly_excluded = list(s.get("verified", [])), []
        for lbl in s.get("picks", []):
            sk = tb.skill_by_label(lbl)
            if not sk:
                continue
            cos = tb.cosine(sk["entity_id"], s["_ovec"])
            if cos < C.LLM_LINK_MIN_SIM:
                newly_excluded.append(lbl)
                continue
            # NEW gate: when the occupation has a definition, require NLI corroboration too — this is
            # what lifts the cosine-only 45% NLI-pass rate the validation phase measured.
            e = tb.nli(s["occ_desc"], f"This occupation requires {lbl}.") if s.get("occ_desc") else None
            if e is not None and e < C.AGENT_LINK_NLI_MIN:
                newly_excluded.append(lbl)
                continue
            verified.append((sk["entity_id"], round(cos, 3)))
        # de-dup verified by skill id (across reflect passes)
        seen, dedup = set(), []
        for sid, cos in verified:
            if sid not in seen:
                seen.add(sid)
                dedup.append((sid, cos))
        return {"verified": dedup, "excluded": list(s.get("excluded", [])) + newly_excluded}

    def reflect(s: LinkState) -> LinkState:
        return {"reflect": s.get("reflect", 0) + 1, "window": s.get("window", 0) + 1,
                "correction": _STRICTER}

    def route(s: LinkState) -> str:
        if s.get("verified"):
            return "done"
        if s.get("reflect", 0) < C.AGENT_MAX_REFLECT:
            return "reflect"
        return "done"

    g = StateGraph(LinkState)
    g.add_node("propose", propose)
    g.add_node("verify", verify)
    g.add_node("reflect", reflect)
    g.add_edge(START, "propose")
    g.add_edge("propose", "verify")
    g.add_conditional_edges("verify", route, {"reflect": "reflect", "done": END})
    g.add_edge("reflect", "propose")
    return g.compile()


def run_links(tb, stats):
    from .. import llm
    from ..align import candidates as cand
    from ..sources import evidence as ev
    occ_raw, _skl = cand.load_entities()
    targets = llm._link_targets(occ_raw)
    if not targets:
        stats["link"] = {"targets": 0, "links": 0, "occupations_linked": 0, "nli_gated": 0}
        return
    if not tb.has_llm:
        stats["link"] = {"targets": len(targets), "links": 0, "occupations_linked": 0,
                         "nli_gated": 0, "note": "no backend (deferred)"}
        return
    app = _build_link_graph(tb)
    new_rels, n_links, kept_occ, reflected = [], 0, 0, 0
    for o in targets:
        ovec = tb.occ_vector(o)
        occ_desc = o.get("description_en") or o.get("description_fr") or ""
        cached = tb.snap.get(("link", o["entity_id"]))
        if cached and cached.get("output") is not None:
            # offline-resumable: re-verify the cached picks without re-calling the LLM
            picks = [p for p in (cached["output"] or "").split(" | ") if p]
            verified = []
            for lbl in picks:
                sk = tb.skill_by_label(lbl)
                if not sk:
                    continue
                cos = tb.cosine(sk["entity_id"], ovec)
                if cos < C.LLM_LINK_MIN_SIM:
                    continue
                e = tb.nli(occ_desc, f"This occupation requires {lbl}.") if occ_desc else None
                if e is not None and e < C.AGENT_LINK_NLI_MIN:
                    continue
                verified.append((sk["entity_id"], round(cos, 3)))
        else:
            final = app.invoke({"occ_id": o["entity_id"], "occ_label": o["pref_label_en"],
                                "occ_desc": occ_desc, "window": 0, "excluded": [], "verified": [],
                                "reflect": 0, "correction": "", "_ovec": ovec})
            reflected += final.get("reflect", 0)
            verified = final.get("verified", [])
            # cache the accepted skill labels so re-runs cost nothing (mirrors llm._task_links)
            verified_ids = {sid for sid, _c in verified}
            kept_lbls = [lbl for lbl in final.get("picks", [])
                         if (tb.skill_by_label(lbl) or {}).get("entity_id") in verified_ids]
            tb.commit_generation("link", o["entity_id"], " | ".join(kept_lbls))
        if verified:
            kept_occ += 1
            for sid, cos in verified:
                new_rels.append(ev.relation_row(o["entity_id"], sid, C.SRC_LLM,
                                                str(cos), relation_type="llm_inferred"))
                n_links += 1
    ev.write_relations(C.SRC_LLM, new_rels)
    tb.save()
    stats["link"] = {"targets": len(targets), "links": n_links,
                     "occupations_linked": kept_occ, "reflected": reflected}


# Emerging worker — propose new tech, keep ONLY Wikidata-confirmed (delegates to the hardened
# llm._task_emerging tool-chain; the controller dispatch is what makes it agentic, and the
# external Wikidata confirmation IS the verification step).
def run_emerging(tb, stats):
    if not tb.has_llm:
        stats["emerging"] = {"proposed": 0, "added_skills": 0, "note": "no backend (deferred)"}
        return False
    from .. import llm
    res = llm._task_emerging(tb.client, tb.snap, tb.validator)
    tb.save()
    stats["emerging"] = res
    return res.get("added_skills", 0) > 0


# Anchor worker — deterministic (NO LLM): confirm unanchored, anchor-eligible tech skills against
# Wikidata. Runs even with dead credits. In the normal pipeline the `wikidata` stage runs first, so
# this typically reports 0 unattempted gaps (honest); standalone/after new data it does real work.
def run_anchor(tb, stats):
    from .. import wikidata as W
    # anchor-eligible unified skills (mirror wikidata._skill_candidates) lacking a QID
    eligible = [r for r in K.read_all(C.UNIFIED_SKILLS_CSV)
                if r.get("it_subtype") in C.WIKIDATA_SKILL_SUBDOMAINS
                and (r.get("primary_label_en") or "").strip()
                and len((r["primary_label_en"]).split()) <= C.WIKIDATA_SKILL_MAX_TOKENS]
    unanchored = [r for r in eligible if not (r.get("wikidata_qid") or "").strip()]
    wsnap = W._load_snapshot()
    unattempted = [r for r in unanchored
                   if (K.normalize_label(r["primary_label_en"]), "skill") not in wsnap]
    stats["anchor"] = {"eligible": len(eligible), "unanchored": len(unanchored),
                       "unattempted": len(unattempted)}
    if unattempted:
        # reuse the hardened, snapshot-resumable resolver (only queries the unattempted labels)
        n = min(len(unattempted), C.AGENT_ANCHOR_MAX)
        stats["anchor"]["resolving"] = n
        W.run()  # idempotent: resumes from snapshot, re-writes side table, re-integrates
        after = [r for r in K.read_all(C.UNIFIED_SKILLS_CSV)
                 if r.get("it_subtype") in C.WIKIDATA_SKILL_SUBDOMAINS
                 and (r.get("wikidata_qid") or "").strip()]
        stats["anchor"]["anchored_now"] = len(after)
    return False
