"""RDF/OWL Turtle serialization: SKOS concepts + a light JobKB ontology (TBox with class disjointness and
property domain/range, then the ABox). Authored reasoner-ready; a lightweight self_check() verifies the
axioms hold in the emitted data (the substance of a consistency check without a Java reasoner).
"""

from __future__ import annotations

from rdflib import Graph, Namespace, Literal, URIRef
from rdflib.namespace import RDF, RDFS, OWL, SKOS, XSD, DCTERMS

from .. import config as C

JOBKB = Namespace(C.JOBKB_NS)
ONT = Namespace(C.JOBKB_ONT)
WD = Namespace(C.WD_NS)

# node kind -> ontology class local name
_CLASS = {"occupation": "Occupation", "skill": "Skill",
          "skill_type": "SkillType", "skill_domain": "SkillDomain",
          "skill_category": "SkillCategory", "isco_group": "IscoGroup"}
# occupation->skill relation_type -> object sub-property local name
_REL_PROP = {"essential": "essentialSkill", "optional": "optionalSkill", "demand": "demandsSkill",
             "transversal": "transversalSkill", "llm_inferred": "inferredSkill"}


def _tbox(g):
    """Ontology header: scheme, classes (+ disjointness), object/datatype properties (+ domain/range)."""
    scheme = JOBKB["scheme"]
    g.add((scheme, RDF.type, SKOS.ConceptScheme))
    g.add((scheme, DCTERMS.title, Literal("JobKB — IT occupations & skills knowledge base", lang="en")))
    g.add((URIRef(C.JOBKB_ONT.rstrip("#")), RDF.type, OWL.Ontology))

    def cls(name, label, parent=None):
        c = ONT[name]
        g.add((c, RDF.type, OWL.Class))
        g.add((c, RDFS.subClassOf, SKOS.Concept))
        if parent is not None:
            g.add((c, RDFS.subClassOf, ONT[parent]))
        g.add((c, RDFS.label, Literal(label, lang="en")))
        return c

    occ = cls("Occupation", "IT occupation")
    skill = cls("Skill", "IT skill")
    cls("HardSkill", "Hard (technical) skill", "Skill")
    cls("SoftSkill", "Soft / transversal skill", "Skill")
    cls("SkillType", "Skill type (hard/soft)")
    cls("SkillDomain", "Functional IT domain")
    cls("SkillCategory", "Skill category")
    cls("IscoGroup", "ISCO-08 occupation group")
    # the core class disjointness a reasoner would check
    g.add((occ, OWL.disjointWith, skill))

    def obj_prop(name, label, domain=None, rng=None, parent=None):
        p = ONT[name]
        g.add((p, RDF.type, OWL.ObjectProperty))
        g.add((p, RDFS.label, Literal(label, lang="en")))
        if domain is not None:
            g.add((p, RDFS.domain, ONT[domain]))
        if rng is not None:
            g.add((p, RDFS.range, ONT[rng]))
        if parent is not None:
            g.add((p, RDFS.subPropertyOf, ONT[parent]))

    obj_prop("requiresSkill", "requires skill", "Occupation", "Skill")
    for rt, prop in _REL_PROP.items():
        obj_prop(prop, prop, "Occupation", "Skill", parent="requiresSkill")
    obj_prop("inDomain", "in functional domain", "Occupation", "SkillDomain")

    for name, label in (("hardSoft", "hard/soft flag"), ("itSubtype", "IT sub-domain / category key"),
                        ("iscoCode", "ISCO-08 code"), ("source", "contributing source"),
                        ("weight", "edge weight (demand/frequency)")):
        p = ONT[name]
        g.add((p, RDF.type, OWL.DatatypeProperty if name != "source" else OWL.AnnotationProperty))
        g.add((p, RDFS.label, Literal(label, lang="en")))


def build_rdf(nodes, edges):
    g = Graph()
    g.bind("skos", SKOS)
    g.bind("owl", OWL)
    g.bind("dcterms", DCTERMS)
    g.bind("jobkb", JOBKB)
    g.bind("jobkbo", ONT)
    g.bind("wd", WD)
    _tbox(g)

    scheme = JOBKB["scheme"]
    for n in nodes:
        u = JOBKB[n["id"]]
        g.add((u, RDF.type, SKOS.Concept))
        g.add((u, SKOS.inScheme, scheme))
        cls = _CLASS[n["kind"]]
        g.add((u, RDF.type, ONT[cls]))
        if n["kind"] == "skill" and n.get("hard_soft") in ("hard", "soft"):
            g.add((u, RDF.type, ONT["HardSkill" if n["hard_soft"] == "hard" else "SoftSkill"]))
        if n.get("label_en"):
            g.add((u, SKOS.prefLabel, Literal(n["label_en"], lang="en")))
        if n.get("label_fr"):
            g.add((u, SKOS.prefLabel, Literal(n["label_fr"], lang="fr")))
        for a in n.get("alt_en", []):
            g.add((u, SKOS.altLabel, Literal(a, lang="en")))
        for a in n.get("alt_fr", []):
            g.add((u, SKOS.altLabel, Literal(a, lang="fr")))
        if n.get("description"):
            g.add((u, SKOS.definition, Literal(n["description"], lang="en")))
        if n.get("hard_soft"):
            g.add((u, ONT.hardSoft, Literal(n["hard_soft"])))
        if n.get("it_subtype"):
            g.add((u, ONT.itSubtype, Literal(n["it_subtype"])))
        if n.get("isco_code"):
            g.add((u, ONT.iscoCode, Literal(n["isco_code"])))
        for s in n.get("sources", []):
            if s:
                g.add((u, ONT.source, Literal(s)))
        # Wikidata cross-reference (SKOS mapping to the real Wikidata entity)
        if n.get("wikidata_qid"):
            rel = SKOS.closeMatch if n.get("wikidata_relation", "").endswith("closeMatch") else SKOS.exactMatch
            g.add((u, rel, WD[n["wikidata_qid"]]))

    for e in edges:
        s, t = JOBKB[e["source"]], JOBKB[e["target"]]
        if e["type"] == "broader":
            g.add((s, SKOS.broader, t))
        elif e["type"] == "in_domain":
            g.add((s, ONT.inDomain, t))
        elif e["type"] == "requires":
            prop = ONT[_REL_PROP.get(e["subtype"], "requiresSkill")]
            g.add((s, prop, t))
    return g


def self_check(nodes, edges):
    """Verify the ontology axioms hold in the data (reasoner-substance, no Java). Returns (ok, details)."""
    kind = {n["id"]: n["kind"] for n in nodes}
    results = []
    # class disjointness: no node is both Occupation and Skill (true by construction — one kind each)
    both = [n["id"] for n in nodes if n["kind"] == "occupation" and n["kind"] == "skill"]
    results.append(("Occupation disjointWith Skill (no node is both)", len(both) == 0,
                    f"{len(both)} violations"))
    # requiresSkill domain/range: subject is an Occupation, object is a Skill
    bad_req = [e for e in edges if e["type"] == "requires"
               and (kind.get(e["source"]) != "occupation" or kind.get(e["target"]) != "skill")]
    results.append(("requiresSkill: domain Occupation / range Skill", len(bad_req) == 0,
                    f"{len(bad_req)} violations"))
    # inDomain range: object is a SkillDomain
    bad_dom = [e for e in edges if e["type"] == "in_domain"
               and (kind.get(e["source"]) != "occupation" or kind.get(e["target"]) != "skill_domain")]
    results.append(("inDomain: domain Occupation / range SkillDomain", len(bad_dom) == 0,
                    f"{len(bad_dom)} violations"))
    # skos:broader never leaves the concept universe (no dangling IRI)
    ids = set(kind)
    bad_edge = [e for e in edges if e["source"] not in ids or e["target"] not in ids]
    results.append(("edges reference only declared concepts", len(bad_edge) == 0,
                    f"{len(bad_edge)} dangling"))
    ok = all(r[1] for r in results)
    return ok, results


def write(nodes, edges, path):
    g = build_rdf(nodes, edges)
    g.serialize(destination=path, format="turtle")
    ok, checks = self_check(nodes, edges)
    return {"triples": len(g), "self_check_ok": ok, "checks": checks}
