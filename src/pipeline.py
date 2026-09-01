"""Orchestrator: run the JobKB build, whole or by stage."""

from __future__ import annotations
import os

from . import config as C
from . import common as K
from . import hierarchy
from . import align
from .align import attach
from . import merge
from .sources import registry

_OUTPUTS = [
    C.OCCUPATIONS_CSV, C.SKILLS_CSV, C.LABELS_CSV, C.OCC_SKILL_REL_CSV,
    C.HIERARCHY_CSV, C.ALIGNMENTS_CSV, C.UNIFIED_OCCUPATIONS_CSV,
    C.UNIFIED_SKILLS_CSV, C.PROVENANCE_CSV, C.BLOCKED_ENTITIES_CSV,
]

_TAXO = C.TAXONOMY_SKILL_MARKERS


def _clean():
    for p in _OUTPUTS:
        if os.path.isfile(p):
            os.remove(p)


def qa():
    """Integrity + coverage report"""
    occ = K.read_all(C.OCCUPATIONS_CSV)
    skl = K.read_all(C.SKILLS_CSV)
    hier = K.read_all(C.HIERARCHY_CSV)
    node_ids = {r["entity_id"] for r in occ} | {r["entity_id"] for r in skl}

    dangling = [e for e in hier
                if e["parent_entity_id"] not in node_ids
                or e["child_entity_id"] not in node_ids]

    real_occ = [r for r in occ if r["occupation_type"] != "isco_group"]
    en_cov = sum(1 for r in real_occ if r.get("pref_label_en"))
    # ISCO groups outside the IT branches leak scope.
    it_leak = [r for r in occ if r["occupation_type"] == "isco_group"
               and r.get("isco_code") and not C.is_isco_it(r.get("isco_code", ""))]

    # Orphans: real occupations / real skills with no parent in the hierarchy.
    occ_children = {e["child_entity_id"] for e in hier if e["entity_kind"] == "occupation"}
    occ_orphans = [r for r in real_occ if r["entity_id"] not in occ_children]
    real_skl = [r for r in skl if r.get("esco_skill_type") not in _TAXO]
    skl_children = {e["child_entity_id"] for e in hier if e["entity_kind"] == "skill"}
    skl_flat = [r for r in real_skl if r["entity_id"] not in skl_children]

    attach_lowconf = [e for e in hier if e["source"] == "ATTACH_LOWCONF"]

    rels = K.read_all(C.OCC_SKILL_REL_CSV)
    demand_rels = [r for r in rels if r.get("relation_type") == "demand"]
    demand_by_src = {}
    for r in demand_rels:
        demand_by_src[r.get("source", "?")] = demand_by_src.get(r.get("source", "?"), 0) + 1
    # relations must reference existing entities.
    rel_dangling = [r for r in rels if r["occupation_entity_id"] not in node_ids
                    or r["skill_entity_id"] not in node_ids]

    blocked = K.read_all(C.BLOCKED_ENTITIES_CSV) if os.path.isfile(C.BLOCKED_ENTITIES_CSV) else []
    gate_block = [b for b in blocked if b.get("decision") == "block"]
    gate_nonit = sum(1 for b in gate_block if b.get("reason") == "non_it")
    gate_malformed = sum(1 for b in gate_block if b.get("reason") == "malformed")
    gate_border = sum(1 for b in blocked if b.get("decision") == "keep")

    # Taxonomy structure: count the 3 skill-ontology tiers + the occupation->domain facet coverage.
    n_types = sum(1 for r in skl if r.get("esco_skill_type") == "skill_type")
    n_domains = sum(1 for r in skl if r.get("esco_skill_type") == "skill_domain")
    n_cats = sum(1 for r in skl if r.get("esco_skill_type") == "skill_category")
    facet = {e["child_entity_id"] for e in hier
             if e["entity_kind"] == "occupation" and e["relation_type"] == "in_domain"}
    occ_in_domain = sum(1 for r in real_occ if r["entity_id"] in facet)

    print("\n=== QA ===")
    print(f"occupations: {len(occ)} ({len(real_occ)} real, "
          f"{len(occ) - len(real_occ)} ISCO groups)")
    print(f"skills: {len(real_skl)} (+{len(skl) - len(real_skl)} taxonomy nodes)  |  "
          f"hierarchy edges: {len(hier)}  |  dangling: {len(dangling)}")
    print(f"skill taxonomy: {n_types} types / {n_domains} domains / {n_cats} categories  |  "
          f"occupations linked to a functional domain: {occ_in_domain}/{len(real_occ)}")
    print(f"EN label coverage (real occ): {en_cov}/{len(real_occ)}")
    print(f"occupation orphans (no hierarchy parent): {len(occ_orphans)}")
    print(f"low-confidence ISCO attachments (review): {len(attach_lowconf)}")
    print(f"skills not placed in ontology: {len(skl_flat)}")
    print(f"non-IT ISCO group leakage: {len(it_leak)}")
    print(f"relevance gate — blocked: {len(gate_block)} (non-IT {gate_nonit}, malformed "
          f"{gate_malformed}); borderline-kept: {gate_border}")
    print(f"occupation-skill relations: {len(rels)} (demand: {len(demand_rels)}"
          f"{' — ' + ', '.join(f'{s} {n}' for s, n in sorted(demand_by_src.items())) if demand_by_src else ''})"
          f"  |  dangling refs: {len(rel_dangling)}")
    if os.path.isfile(C.WIKIDATA_LINKS_CSV):
        wl = K.read_all(C.WIKIDATA_LINKS_CSV)
        wl_skill = sum(1 for r in wl if r.get("entity_kind") == "skill")
        wl_occ = sum(1 for r in wl if r.get("entity_kind") == "occupation")
        wl_dom = sum(1 for r in wl if r.get("entity_kind") == "domain")
        wl_high = sum(1 for r in wl if r.get("confidence") == "high")
        print(f"wikidata anchors: {len(wl)} ({wl_skill} skills, {wl_occ} occupations, "
              f"{wl_dom} domains; {wl_high} high-confidence)")
        occ_u = K.read_all(C.UNIFIED_OCCUPATIONS_CSV)
        skl_u = K.read_all(C.UNIFIED_SKILLS_CSV)
        # Referential integrity: every anchor must resolve to a live KB concept/node.
        occ_ids = {r["unified_id"] for r in occ_u}
        skl_ids = {r["unified_id"] for r in skl_u}
        dom_ids = {r["entity_id"] for r in skl if r.get("esco_skill_type") == "skill_domain"}
        valid = {"skill": skl_ids, "occupation": occ_ids, "domain": dom_ids}
        wl_dangling = [r for r in wl
                       if (r.get("unified_id") or r.get("entity_id"))
                       not in valid.get(r.get("entity_kind"), set())]
        # In-graph enrichment coverage on the concept layer.
        enr_skl = sum(1 for r in skl_u if r.get("wikidata_qid"))
        enr_occ = sum(1 for r in occ_u if r.get("wikidata_qid"))
        enr_desc = sum(1 for r in skl_u + occ_u if r.get("wikidata_description"))
        print(f"wikidata in-graph: {enr_skl} skills + {enr_occ} occupations carry a QID; "
              f"{enr_desc} carry a Wikidata description  |  dangling anchors: {len(wl_dangling)}")
        if wl_dangling:
            print(f"  WARNING: {len(wl_dangling)} wikidata anchors reference missing concepts e.g. "
                  f"{[ (r.get('entity_kind'), r.get('unified_id') or r.get('entity_id')) for r in wl_dangling[:3] ]}")

    # LLM enrichment coverage (pillar 3)
    occ_u = K.read_all(C.UNIFIED_OCCUPATIONS_CSV)
    skl_u = K.read_all(C.UNIFIED_SKILLS_CSV)
    from collections import Counter as _Cnt
    desc_src = _Cnt(r.get("description_source", "") for r in occ_u + skl_u if r.get("description"))
    n_desc = sum(1 for r in occ_u + skl_u if (r.get("description") or "").strip())
    n_hs = sum(1 for r in skl_u if (r.get("hard_soft") or "").strip())
    llm_links = [r for r in rels if r.get("relation_type") == "llm_inferred"]
    llm_skills = sum(1 for r in skl if r.get("source") == C.SRC_LLM)
    n_rej = len(K.read_all(C.LLM_REJECTED_CSV)) if os.path.isfile(C.LLM_REJECTED_CSV) else 0
    print(f"descriptions: {n_desc}/{len(occ_u) + len(skl_u)} concepts "
          f"(by source: {dict(desc_src)})  |  hard_soft: {n_hs}/{len(skl_u)} skills")
    if llm_links or llm_skills or n_rej or "llm" in desc_src:
        print(f"llm enrichment: {sum(1 for r in occ_u + skl_u if r.get('description_source') == 'llm')} "
              f"descriptions, {len(llm_links)} inferred links, {llm_skills} new Wikidata-confirmed skills; "
              f"{n_rej} outputs rejected by validation")

    # Multilingual label coverage (`--translate`)
    n_all = len(occ_u) + len(skl_u)
    def _cov(col):
        return sum(1 for r in occ_u + skl_u if (r.get(col) or "").strip())
    print(f"label coverage: primary EN {_cov('primary_label_en')}/{n_all}, "
          f"FR {_cov('primary_label_fr')}/{n_all}  |  alt EN {_cov('alt_labels_en')}/{n_all}, "
          f"FR {_cov('alt_labels_fr')}/{n_all}")
    if os.path.isfile(C.TRANSLATE_SNAPSHOT_CSV):
        tr = K.read_all(C.TRANSLATE_SNAPSHOT_CSV)
        tr_ok = _Cnt(r.get("direction", "") for r in tr if r.get("validated") == "1")
        tr_rej = len(K.read_all(C.TRANSLATE_REJECTED_CSV)) if os.path.isfile(C.TRANSLATE_REJECTED_CSV) else 0
        print(f"translation: validated MT by direction {dict(tr_ok)}; {tr_rej} rejected by validation")

    if dangling:
        print(f"  WARNING: {len(dangling)} dangling edges e.g. "
              f"{[(e['parent_entity_id'], e['child_entity_id']) for e in dangling[:3]]}")
    if rel_dangling:
        print(f"  WARNING: {len(rel_dangling)} occupation-skill relations reference missing entities")

    # Logical-consistency certificate
    from .validation import consistency as _consistency
    _cons = _consistency.check()
    print(_consistency.summary_line(_cons))

    return {"occupations": len(occ), "skills": len(real_skl), "edges": len(hier),
            "consistency_pass": sum(1 for _, ok, _ in _cons if ok), "consistency_total": len(_cons),
            "dangling": len(dangling), "occ_orphans": len(occ_orphans),
            "skl_flat": len(skl_flat), "attach_lowconf": len(attach_lowconf),
            "gate_blocked": len(gate_block), "gate_borderline": gate_border,
            "relations": len(rels), "demand_relations": len(demand_rels),
            "rel_dangling": len(rel_dangling)}


# Stage registry: every stage runnable standalone against the persisted kb.

STAGE_ORDER = ["ingest", "hierarchy", "align", "attach", "merge", "qa"]

# A file each stage expects to already exist
_STAGE_INPUT = {
    "hierarchy": C.SKILLS_CSV,
    "align": C.OCCUPATIONS_CSV,
    "attach": C.OCCUPATIONS_CSV,
    "merge": C.ALIGNMENTS_CSV,
    "qa": C.OCCUPATIONS_CSV,
}


def _ingest(source=None):
    """Ingest all built-in taxonomies or a single named source."""
    names = (source,) if source else registry.builtin_sources()
    prior_isco = {r["entity_id"]: r["isco_code"] for r in K.read_all(C.OCCUPATIONS_CSV)
                  if r.get("isco_code")}
    for name in names:
        registry.get(name).ingest()
    if prior_isco:
        occ = K.read_all(C.OCCUPATIONS_CSV)
        touched = set()
        for r in occ:
            if not r.get("isco_code") and prior_isco.get(r["entity_id"]):
                r["isco_code"] = prior_isco[r["entity_id"]]
                touched.add(r["source"])
        for src in touched:
            K.replace_source_rows(C.OCCUPATIONS_CSV, C.OCCUPATION_FIELDS, src,
                                  [r for r in occ if r["source"] == src])


def _hierarchy(source=None):
    hierarchy.run()


def _align(source=None):
    align.run(focus_source=source)


def _attach(source=None):
    attach.run(focus_source=source)


def _merge(source=None):
    merge.run()


def _qa(source=None):
    return qa()


# Post-merge enrichment stages (pillar 3)
def _enrich_wikidata(source=None):
    from . import wikidata
    wikidata.run()


def _enrich_llm(source=None):
    from . import llm
    llm.run()


def _enrich_agent(source=None):
    """Agentic enrichment (LangGraph controller + reflective workers)."""
    try:
        from . import agent
        agent.run()
    except ImportError as e:
        print(f"[agent] langgraph unavailable ({e}); falling back to one-shot llm.run().", flush=True)
        from . import llm
        llm.run()
    except Exception as e:
        print(f"[agent] agentic enrichment error ({type(e).__name__}: {e}); skipping (fail-open).",
              flush=True)


def _enrich_translate(source=None):
    from . import translate
    translate.run()


_STAGES = {
    "ingest": _ingest, "hierarchy": _hierarchy, "align": _align,
    "attach": _attach, "merge": _merge, "qa": _qa,
    "wikidata": _enrich_wikidata, "llm": _enrich_llm, "agent": _enrich_agent,
    "translate": _enrich_translate,
}

# Enrichment stages, in dependency order, inserted between merge and qa on a full build.
ENRICH_ORDER = ["wikidata", "agent", "translate"]


def run_stages(stages, source=None, clean=False):
    """Run the given stages (always in canonical order) against the current kb/.

    `source` scopes ingest/align/attach to one registered source. `clean` wipes kb/ first
    (a full build); selective runs leave kb/ intact. Returns the qa() dict if qa ran.
    """
    unknown = [s for s in stages if s not in _STAGES]
    if unknown:
        raise ValueError(f"Unknown stage(s): {', '.join(unknown)}. "
                         f"Valid stages: {', '.join(STAGE_ORDER)}")
    if source is not None:
        registry.get(source)
    selected = [s for s in STAGE_ORDER if s in set(stages)]

    K.ensure_dirs()
    if clean:
        _clean()

    import time as _t
    last = [_t.time()]

    def _stage(name):
        now = _t.time()
        print(f"--- {name} ---  (+{now - last[0]:.1f}s)", flush=True)
        last[0] = now

    result = None
    for name in selected:
        inp = _STAGE_INPUT.get(name)
        if inp and not clean and not os.path.isfile(inp):
            print(f"[warn] stage '{name}' expects {os.path.basename(inp)}, which is missing "
                  f"— run the earlier stages first.")
        _stage(name)
        out = _STAGES[name](source=source)
        if name == "qa":
            result = out

    # Running an upstream stage leaves downstream-derived data stale
    max_i = max(STAGE_ORDER.index(s) for s in selected)
    stale = [s for s in STAGE_ORDER[max_i + 1:] if s != "qa"]
    if stale:
        print(f"[note] downstream stage(s) not re-run: {', '.join(stale)}; "
              f"kb/ may be stale there -- re-run them (e.g. --from {stale[0]}) for consistency.")
    return result


def _run_enrichment():
    """Run the post-merge enrichment stages (wikidata -> llm -> translate) against the built kb/."""
    import time as _t
    for name in ENRICH_ORDER:
        t0 = _t.time()
        print(f"--- {name} (enrich) ---", flush=True)
        _STAGES[name]()
        print(f"    [{name} done +{_t.time() - t0:.1f}s]", flush=True)


def run_all(clean=True, do_align=True, core_only=False):
    """Full build: every stage, cleaning kb/ first."""
    if not do_align:
        stages = [s for s in STAGE_ORDER if s not in ("align", "attach", "merge")]
        return run_stages(stages, clean=clean)

    # Build core, then enrich, then qa.
    core = [s for s in STAGE_ORDER if s != "qa"]
    run_stages(core, clean=clean)
    if not core_only:
        _run_enrichment()
    return run_stages(["qa"])
