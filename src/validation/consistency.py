"""Graph logical-consistency validator (objective 1).

A read-only, model-free suite of invariants that certifies the knowledge graph is logically sound —
the guarantees the build is *supposed* to uphold, asserted explicitly rather than assumed. `check()`
returns an ordered list of `(name, ok, detail)`; `qa()` prints a one-line summary and any failures, so
**every build self-certifies**. Nothing here modifies `kb/`.

The suite deliberately re-checks a few properties `qa()` already reports (dangling edges, orphans,
leakage) so it stands alone as the authoritative consistency certificate, and adds the properties that
were previously only assumed: acyclicity, single-parent, `hard_soft`↔taxonomy, no skill→skill edges,
ISCO backbone reachability, relation endpoint type-correctness, unified-concept integrity, and
id-uniqueness. Duplicate relations are reported (total rows vs unique triples).
"""

from __future__ import annotations

from collections import Counter

from .. import config as C
from .. import common as K
from .. import hierarchy as H

_TAXO = C.TAXONOMY_SKILL_MARKERS


def _load():
    occ = K.read_all(C.OCCUPATIONS_CSV)
    skl = K.read_all(C.SKILLS_CSV)
    hier = K.read_all(C.HIERARCHY_CSV)
    rels = K.read_all(C.OCC_SKILL_REL_CSV)
    uocc = K.read_all(C.UNIFIED_OCCUPATIONS_CSV)
    uskl = K.read_all(C.UNIFIED_SKILLS_CSV)
    return occ, skl, hier, rels, uocc, uskl


def _has_cycle(edges):
    """edges: list of (parent, child) directed parent->child. Iterative DFS 3-colouring; returns a
    representative node on a back-edge, or None if acyclic."""
    adj = {}
    nodes = set()
    for p, c in edges:
        adj.setdefault(p, []).append(c)
        nodes.add(p)
        nodes.add(c)
    WHITE, GRAY, BLACK = 0, 1, 2
    color = {n: WHITE for n in nodes}
    for start in nodes:
        if color[start] != WHITE:
            continue
        stack = [(start, iter(adj.get(start, ())))]
        color[start] = GRAY
        while stack:
            node, it = stack[-1]
            advanced = False
            for nxt in it:
                if color[nxt] == GRAY:
                    return nxt
                if color[nxt] == WHITE:
                    color[nxt] = GRAY
                    stack.append((nxt, iter(adj.get(nxt, ()))))
                    advanced = True
                    break
            if not advanced:
                color[node] = BLACK
                stack.pop()
    return None


def check():
    """Run every invariant; return an ordered list of (name, ok: bool, detail: str)."""
    occ, skl, hier, rels, uocc, uskl = _load()
    out = []

    def add(name, ok, detail=""):
        out.append((name, bool(ok), detail))

    occ_ids = {r["entity_id"] for r in occ}
    real_occ = [r for r in occ if r.get("occupation_type") != "isco_group"]
    real_occ_ids = {r["entity_id"] for r in real_occ}
    skl_ids = {r["entity_id"] for r in skl}
    real_skl_ids = {r["entity_id"] for r in skl if r.get("esco_skill_type") not in _TAXO}
    node_ids = occ_ids | skl_ids

    # 1. No dangling hierarchy edges.
    dangling = [e for e in hier if e["parent_entity_id"] not in node_ids
                or e["child_entity_id"] not in node_ids]
    add("hierarchy: no dangling edges", not dangling, f"{len(dangling)} dangling")

    # 2. No self-loops.
    self_loops = [e for e in hier if e["parent_entity_id"] == e["child_entity_id"]]
    add("hierarchy: no self-loops", not self_loops, f"{len(self_loops)} self-loops")

    # 3. Acyclic (whole hierarchy, all edge types, directed parent->child).
    cyc = _has_cycle([(e["parent_entity_id"], e["child_entity_id"]) for e in hier])
    add("hierarchy: acyclic (DAG)", cyc is None, "" if cyc is None else f"cycle at {cyc}")

    # 4. Every real skill has exactly one category parent (single path to a type).
    skl_parent_ct = Counter(e["child_entity_id"] for e in hier
                            if e["entity_kind"] == "skill" and e["relation_type"] == "broader_than")
    multi_skl = [c for c in real_skl_ids if skl_parent_ct.get(c, 0) > 1]
    none_skl = [c for c in real_skl_ids if skl_parent_ct.get(c, 0) == 0]
    add("skills: exactly one category parent", not multi_skl and not none_skl,
        f"{len(multi_skl)} multi-parent, {len(none_skl)} unplaced")

    # 5. Every real occupation has exactly one backbone parent + one domain facet parent.
    occ_bb_ct = Counter(e["child_entity_id"] for e in hier
                        if e["entity_kind"] == "occupation" and e["relation_type"] == "broader_than")
    occ_facet_ct = Counter(e["child_entity_id"] for e in hier
                           if e["entity_kind"] == "occupation" and e["relation_type"] == "in_domain")
    bad_bb = [o for o in real_occ_ids if occ_bb_ct.get(o, 0) != 1]
    bad_facet = [o for o in real_occ_ids if occ_facet_ct.get(o, 0) != 1]
    add("occupations: one backbone + one domain parent", not bad_bb and not bad_facet,
        f"{len(bad_bb)} bad backbone, {len(bad_facet)} bad facet")

    # 6. ISCO backbone reachability: exactly one root, every occupation reaches it.
    bb_edges = [(e["child_entity_id"], e["parent_entity_id"]) for e in hier
                if e["entity_kind"] == "occupation" and e["relation_type"] == "broader_than"]
    parent_of = {c: p for c, p in bb_edges}
    roots = {p for _, p in bb_edges} - {c for c, _ in bb_edges}

    def _reaches_root(node):
        seen = set()
        while node in parent_of and node not in seen:
            seen.add(node)
            node = parent_of[node]
        return node in roots
    unreachable = [o for o in real_occ_ids if not _reaches_root(o)]
    add("ISCO backbone: single root, all reach it", len(roots) == 1 and not unreachable,
        f"{len(roots)} roots, {len(unreachable)} unreachable")

    # 7. No non-IT ISCO group leakage (groups outside 25/35/133).
    leak = [r for r in occ if r.get("occupation_type") == "isco_group"
            and r.get("isco_code") and not C.is_isco_it(r.get("isco_code", ""))]
    add("ISCO: no non-IT group leakage", not leak, f"{len(leak)} leaked groups")

    # 8. NO skill->skill edges (a locked constraint): no hierarchy edge between two real skills.
    s2s_hier = [e for e in hier if e["parent_entity_id"] in real_skl_ids
                and e["child_entity_id"] in real_skl_ids]
    add("no skill->skill hierarchy edges", not s2s_hier, f"{len(s2s_hier)} skill->skill edges")

    # 9. hard_soft is consistent with the taxonomy (unified skills): hard_soft == skill_type(it_subtype),
    #    and neither hard_soft nor it_subtype is empty.
    hs_bad, hs_empty = [], []
    for r in uskl:
        hs, sub = (r.get("hard_soft") or ""), (r.get("it_subtype") or "")
        if not hs or not sub:
            hs_empty.append(r["unified_id"])
        elif hs != (H.skill_type(sub) or hs):
            hs_bad.append(r["unified_id"])
    add("skills: hard_soft matches taxonomy", not hs_bad and not hs_empty,
        f"{len(hs_bad)} mismatched, {len(hs_empty)} empty")

    # 10. Relation endpoint type-correctness: occ endpoint is a REAL occupation, skill endpoint a REAL
    #     skill (not a taxonomy node) — stronger than the combined-set membership qa uses.
    bad_occ_ep = [r for r in rels if r["occupation_entity_id"] not in real_occ_ids]
    bad_skl_ep = [r for r in rels if r["skill_entity_id"] not in real_skl_ids]
    add("relations: endpoints correctly typed", not bad_occ_ep and not bad_skl_ep,
        f"{len(bad_occ_ep)} bad occ, {len(bad_skl_ep)} bad skill endpoints")

    # 11. Unified-concept integrity: members non-empty, resolve to base nodes, not shared across two
    #     unified concepts; unified_id unique.
    member_of = {}
    empty_members, missing_members, shared = 0, 0, 0
    for r in uocc + uskl:
        mids = [m for m in (r.get("member_entity_ids") or "").split(" | ") if m]
        if not mids:
            empty_members += 1
        for m in mids:
            if m not in node_ids:
                missing_members += 1
            if m in member_of and member_of[m] != r["unified_id"]:
                shared += 1
            member_of[m] = r["unified_id"]
    add("unified: members valid & unshared",
        not empty_members and not missing_members and not shared,
        f"{empty_members} empty, {missing_members} missing, {shared} shared")

    # 12. Id uniqueness (base entity_id, unified_id).
    dup_eid = [k for k, v in Counter([r["entity_id"] for r in occ + skl]).items() if v > 1]
    dup_uid = [k for k, v in Counter([r["unified_id"] for r in uocc + uskl]).items() if v > 1]
    add("ids: entity_id & unified_id unique", not dup_eid and not dup_uid,
        f"{len(dup_eid)} dup entity_id, {len(dup_uid)} dup unified_id")

    # 13. Relations de-duplicated: 0 fully-identical rows; report total vs unique triples.
    triples = Counter((r["occupation_entity_id"], r["skill_entity_id"], r.get("relation_type", ""),
                       r.get("source", ""), r.get("weight", "")) for r in rels)
    identical = sum(v - 1 for v in triples.values() if v > 1)
    uniq_pairs = len({(r["occupation_entity_id"], r["skill_entity_id"], r.get("relation_type", ""))
                      for r in rels})
    add("relations: no identical duplicate rows", identical == 0,
        f"{identical} identical dups; {len(rels)} rows / {uniq_pairs} unique (occ,skill,type)")

    return out


def summary_line(results=None):
    """`consistency: P/N invariants PASS` plus any failing names — for qa()."""
    results = results if results is not None else check()
    npass = sum(1 for _, ok, _ in results if ok)
    line = f"consistency: {npass}/{len(results)} invariants PASS"
    fails = [f"{name} ({detail})" for name, ok, detail in results if not ok]
    if fails:
        line += "  |  FAIL: " + "; ".join(fails)
    return line
