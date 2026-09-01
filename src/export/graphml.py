"""GraphML (Gephi / Cytoscape / yEd) and nodes/edges JSON (Neo4j / web viz) serialization."""

from __future__ import annotations

import json
from xml.sax.saxutils import escape, quoteattr

# GraphML node/edge attribute schema: (key_id, target, name, type)
_NODE_KEYS = [
    ("label", "label_en", "string"), ("label_fr", "label_fr", "string"),
    ("kind", "kind", "string"), ("hard_soft", "hard_soft", "string"),
    ("it_subtype", "it_subtype", "string"), ("isco_code", "isco_code", "string"),
    ("wikidata_qid", "wikidata_qid", "string"), ("sources", "sources", "string"),
    ("description", "description", "string"),
]
_EDGE_KEYS = [("etype", "type", "string"), ("subtype", "subtype", "string"),
              ("weight", "weight", "string"), ("prov", "prov", "string")]


def _node_val(n, field):
    v = n.get(field, "")
    if isinstance(v, list):
        return " | ".join(x for x in v if x)
    return v or ""


def write_graphml(nodes, edges, path):
    lines = ['<?xml version="1.0" encoding="UTF-8"?>',
             '<graphml xmlns="http://graphml.graphdrawing.org/xmlns">']
    for kid, _f, typ in _NODE_KEYS:
        lines.append(f'  <key id="{kid}" for="node" attr.name="{kid}" attr.type="{typ}"/>')
    for kid, _f, typ in _EDGE_KEYS:
        lines.append(f'  <key id="{kid}" for="edge" attr.name="{kid}" attr.type="{typ}"/>')
    lines.append('  <graph id="jobkb" edgedefault="directed">')
    for n in nodes:
        lines.append(f'    <node id={quoteattr(n["id"])}>')
        for kid, field, _t in _NODE_KEYS:
            val = _node_val(n, field)
            if val != "":
                lines.append(f'      <data key="{kid}">{escape(str(val))}</data>')
        lines.append('    </node>')
    for i, e in enumerate(edges):
        lines.append(f'    <edge id="e{i}" source={quoteattr(e["source"])} target={quoteattr(e["target"])}>')
        for kid, field, _t in _EDGE_KEYS:
            val = e.get(field, "")
            if val != "":
                lines.append(f'      <data key="{kid}">{escape(str(val))}</data>')
        lines.append('    </edge>')
    lines.append('  </graph>')
    lines.append('</graphml>')
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    return {"nodes": len(nodes), "edges": len(edges)}


def write_json(nodes, edges, path):
    out = {
        "meta": {"nodes": len(nodes), "edges": len(edges),
                 "node_kinds": sorted({n["kind"] for n in nodes}),
                 "edge_types": sorted({(e["type"] + ":" + e["subtype"]).rstrip(":") for e in edges})},
        "nodes": [{
            "id": n["id"], "label": n.get("label_en") or n.get("label_fr"), "label_fr": n.get("label_fr", ""),
            "kind": n["kind"], "hard_soft": n.get("hard_soft", ""), "it_subtype": n.get("it_subtype", ""),
            "isco_code": n.get("isco_code", ""), "wikidata_qid": n.get("wikidata_qid", ""),
            "sources": n.get("sources", []), "description": n.get("description", ""),
        } for n in nodes],
        "edges": [{"source": e["source"], "target": e["target"], "type": e["type"],
                   "subtype": e["subtype"], "weight": e["weight"], "prov": e["prov"]} for e in edges],
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False)
    return {"nodes": len(nodes), "edges": len(edges)}
