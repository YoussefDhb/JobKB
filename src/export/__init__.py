"""Graph export — materialize the unified concept graph for external tools and visualization.

`run(formats=ALL_FORMATS)` (CLI: `run_pipeline.py --export [formats]`) builds the shared concept-graph
model once (`graph.build_graph`) and serializes it to the requested targets, all read-only over `kb/` and
writing only to `export/`:
  * rdf     -> jobkb.ttl     (RDF/OWL Turtle: SKOS concepts + a light JobKB ontology; reasoner-ready)
  * graphml -> jobkb.graphml (Gephi / Cytoscape / yEd)
  * json    -> jobkb.json    (nodes/edges for Neo4j / web viz)
  * viz     -> jobkb.html    (self-contained interactive backbone overview)
"""

from __future__ import annotations

import os

from .. import config as C

ALL_FORMATS = C.EXPORT_FORMATS


def run(formats=ALL_FORMATS) -> dict:
    formats = [f for f in formats if f in C.EXPORT_FORMATS]
    if not formats:
        print(f"[EXPORT] no valid formats in {formats!r}; valid: {C.EXPORT_FORMATS}", flush=True)
        return {}
    os.makedirs(C.EXPORT_OUT_DIR, exist_ok=True)
    from . import graph as G
    nodes, edges = G.build_graph()
    print(f"[EXPORT] concept graph: {len(nodes)} nodes, {len(edges)} edges "
          f"(formats: {', '.join(formats)})", flush=True)
    stats = {"nodes": len(nodes), "edges": len(edges)}

    if "rdf" in formats:
        from . import rdf
        r = rdf.write(nodes, edges, C.EXPORT_TTL)
        stats["rdf"] = r
        print(f"[EXPORT] RDF/Turtle -> {C.EXPORT_TTL} ({r['triples']} triples); "
              f"axiom self-check: {'PASS' if r['self_check_ok'] else 'FAIL'}", flush=True)
        for name, ok, detail in r["checks"]:
            print(f"    {'ok ' if ok else 'FAIL'} {name} ({detail})", flush=True)
    if "graphml" in formats:
        from . import graphml
        stats["graphml"] = graphml.write_graphml(nodes, edges, C.EXPORT_GRAPHML)
        print(f"[EXPORT] GraphML -> {C.EXPORT_GRAPHML}", flush=True)
    if "json" in formats:
        from . import graphml
        stats["json"] = graphml.write_json(nodes, edges, C.EXPORT_JSON)
        print(f"[EXPORT] JSON -> {C.EXPORT_JSON}", flush=True)
    if "viz" in formats:
        from . import viz
        v = viz.write_html(nodes, edges, C.EXPORT_HTML)
        stats["viz"] = v
        print(f"[EXPORT] interactive HTML -> {C.EXPORT_HTML} "
              f"({v['viz_nodes']} backbone nodes, {v['viz_edges']} edges)", flush=True)
    print("[EXPORT] done.", flush=True)
    return stats
