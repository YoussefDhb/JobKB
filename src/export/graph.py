"""Build the unified CONCEPT graph from `kb/` — the single in-memory model every serializer consumes.

The KB stores per-source entities (`occupations.csv`, `skills.csv`) plus a deduplicated concept layer
(`unified_*.csv`). Hierarchy and occupation→skill edges reference the per-source **entity ids**; this
module remaps each real endpoint to its **unified concept** via `member_entity_ids`, while the taxonomy
tiers (type/domain/category) and ISCO group nodes — which are not merged — keep their own entity id. The
result is the clean, deduplicated graph the audit verified dangle-free (0 unmapped entities, 0
unresolvable edge endpoints).

Returns `(nodes, edges)`:
  node = {id, kind, label_en, label_fr, alt_en[list], alt_fr[list], description, hard_soft, it_subtype,
          isco_code, sources[list], wikidata_qid, wikidata_url, wikidata_relation}
  edge = {source, target, type, subtype, weight, prov}
Wikidata anchors ride on the concept nodes (qid/url/relation) rather than as leaf nodes; the RDF
serializer emits them as `skos:exactMatch`/`closeMatch` triples to real Wikidata IRIs.
"""

from __future__ import annotations

import os

from .. import config as C
from .. import common as K

_TAXO = C.TAXONOMY_SKILL_MARKERS


def _split(v):
    return [p for p in (v or "").split(" | ") if p]


def _entity_to_unified(uocc, uskl):
    """entity_id -> unified_id, from the unified concepts' member lists."""
    e2u = {}
    for r in uocc + uskl:
        for m in _split(r.get("member_entity_ids")):
            e2u[m] = r["unified_id"]
    return e2u


def build_graph():
    occ = K.read_all(C.OCCUPATIONS_CSV)
    skl = K.read_all(C.SKILLS_CSV)
    uocc = K.read_all(C.UNIFIED_OCCUPATIONS_CSV)
    uskl = K.read_all(C.UNIFIED_SKILLS_CSV)
    hier = K.read_all(C.HIERARCHY_CSV)
    rels = K.read_all(C.OCC_SKILL_REL_CSV)
    wl = K.read_all(C.WIKIDATA_LINKS_CSV) if os.path.isfile(C.WIKIDATA_LINKS_CSV) else []

    e2u = _entity_to_unified(uocc, uskl)
    nodes = {}

    def add(nid, **attrs):
        nodes[nid] = attrs

    # --- unified concept nodes ---
    for r in uocc:
        add(r["unified_id"], kind="occupation",
            label_en=r.get("primary_label_en", ""), label_fr=r.get("primary_label_fr", ""),
            alt_en=_split(r.get("alt_labels_en")), alt_fr=_split(r.get("alt_labels_fr")),
            description=r.get("description", ""), hard_soft="", it_subtype="",
            isco_code=r.get("isco_code", ""), sources=_split(r.get("sources")),
            wikidata_qid=r.get("wikidata_qid", ""), wikidata_url=r.get("wikidata_url", ""),
            wikidata_relation="")
    for r in uskl:
        add(r["unified_id"], kind="skill",
            label_en=r.get("primary_label_en", ""), label_fr=r.get("primary_label_fr", ""),
            alt_en=_split(r.get("alt_labels_en")), alt_fr=_split(r.get("alt_labels_fr")),
            description=r.get("description", ""), hard_soft=r.get("hard_soft", ""),
            it_subtype=r.get("it_subtype", ""), isco_code="", sources=_split(r.get("sources")),
            wikidata_qid=r.get("wikidata_qid", ""), wikidata_url=r.get("wikidata_url", ""),
            wikidata_relation="")

    # --- taxonomy tier nodes (type / domain / category) — kept as their own entity ids ---
    _KIND = {"skill_type": "skill_type", "skill_domain": "skill_domain", "skill_category": "skill_category"}
    for r in skl:
        st = r.get("esco_skill_type")
        if st in _TAXO:
            add(r["entity_id"], kind=_KIND[st],
                label_en=r.get("pref_label_en", ""), label_fr=r.get("pref_label_fr", ""),
                alt_en=[], alt_fr=[], description=r.get("description_en", ""), hard_soft="",
                it_subtype=r.get("it_subtype", ""), isco_code="", sources=[r.get("source", "")],
                wikidata_qid="", wikidata_url="", wikidata_relation="")

    # --- ISCO group nodes (incl. the ICT super-root) ---
    for r in occ:
        if r.get("occupation_type") == "isco_group":
            add(r["entity_id"], kind="isco_group",
                label_en=r.get("pref_label_en", ""), label_fr=r.get("pref_label_fr", ""),
                alt_en=[], alt_fr=[], description=r.get("description_en", ""), hard_soft="",
                it_subtype="", isco_code=r.get("isco_code", ""), sources=[r.get("source", "")],
                wikidata_qid="", wikidata_url="", wikidata_relation="")

    # --- attach Wikidata anchors (qid + relation) onto the concept/domain nodes ---
    for r in wl:
        nid = r.get("unified_id") or r.get("entity_id")
        if nid in nodes and r.get("qid"):
            nodes[nid]["wikidata_qid"] = r["qid"]
            nodes[nid]["wikidata_url"] = r.get("wikidata_url", "")
            nodes[nid]["wikidata_relation"] = r.get("relation", "skos:exactMatch")

    def resolve(eid):
        """Map an edge endpoint to a graph node id: unified concept for real entities, own id for
        taxonomy/ISCO nodes."""
        return e2u.get(eid) or (eid if eid in nodes else None)

    edges = []
    # hierarchy: broader_than -> skos:broader (child -> parent); in_domain -> jobkb:inDomain (occ -> domain).
    # Skill->category broader edges are NOT remapped here: a merged skill would otherwise inherit each
    # member's (possibly divergent) category and gain multiple parents. Instead we regenerate a SINGLE
    # skill->category edge below from the unified concept's authoritative `it_subtype` — preserving the
    # KB's single-category-parent invariant at the concept level. Taxonomy (category->domain->type) and
    # ISCO-tree broader edges are already single-parent, so they pass through.
    for e in hier:
        p, c = resolve(e["parent_entity_id"]), resolve(e["child_entity_id"])
        if p is None or c is None:
            continue
        if e["relation_type"] == "in_domain":
            edges.append({"source": c, "target": p, "type": "in_domain", "subtype": "",
                          "weight": "", "prov": e.get("source", "")})
        elif nodes[c]["kind"] == "skill":
            continue  # regenerated from it_subtype below
        else:
            edges.append({"source": c, "target": p, "type": "broader", "subtype": "",
                          "weight": "", "prov": e.get("source", "")})
    # single authoritative skill -> category edge from the unified it_subtype
    catkey2node = {a["it_subtype"]: nid for nid, a in nodes.items() if a["kind"] == "skill_category"}
    for nid, a in nodes.items():
        if a["kind"] == "skill" and a.get("it_subtype") in catkey2node:
            edges.append({"source": nid, "target": catkey2node[a["it_subtype"]], "type": "broader",
                          "subtype": "", "weight": "", "prov": "TAXONOMY"})
    # occupation -> skill relations -> jobkb:requiresSkill (typed by relation_type)
    for r in rels:
        o, s = resolve(r["occupation_entity_id"]), resolve(r["skill_entity_id"])
        if o is None or s is None:
            continue
        edges.append({"source": o, "target": s, "type": "requires",
                      "subtype": r.get("relation_type", ""), "weight": r.get("weight", ""),
                      "prov": r.get("source", "")})

    # de-duplicate identical edges (same endpoints+type+subtype+prov collapse; a concept can inherit
    # the same edge from several merged members)
    seen, uniq = set(), []
    for e in edges:
        k = (e["source"], e["target"], e["type"], e["subtype"], e["prov"])
        if k in seen:
            continue
        seen.add(k)
        uniq.append(e)

    node_list = [dict(id=nid, **attrs) for nid, attrs in nodes.items()]
    return node_list, uniq
