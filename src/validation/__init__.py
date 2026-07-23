"""KB validation (read-only over the graph): logical-consistency suite + external gold benchmark +
LLM-connection audit.

`run(tracks)` orchestrates the three tracks, loading the shared bge-m3 embedder / mDeBERTa verifier
once, writes a human-readable `validation/report.md` plus per-track CSVs, and prints a console summary.
`consistency.check()` additionally runs inside `pipeline.qa()` so every build self-certifies.
"""

from __future__ import annotations

import csv
import os

from .. import config as C
from .. import common as K
from . import consistency, coverage, llm_audit

ALL_TRACKS = ("consistency", "coverage", "llm")


def _write_csv(name, fields, rows):
    path = os.path.join(C.VALIDATION_OUT_DIR, name)
    with open(path, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow(r)


def run(tracks=ALL_TRACKS):
    os.makedirs(C.VALIDATION_OUT_DIR, exist_ok=True)
    rep = ["# JobKB validation report", f"_generated {K.now_iso()}_", ""]
    embedder = None
    if "coverage" in tracks or "llm" in tracks:
        from ..align import candidates as cand
        embedder = cand.get_embedder()

    # -------- Track 1: logical consistency --------
    if "consistency" in tracks:
        res = consistency.check()
        _write_csv("consistency.csv", ["invariant", "status", "detail"],
                   [{"invariant": n, "status": "PASS" if ok else "FAIL", "detail": d}
                    for n, ok, d in res])
        npass = sum(1 for _, ok, _ in res if ok)
        rep.append(f"## 1. Logical consistency — {npass}/{len(res)} invariants PASS")
        for n, ok, d in res:
            rep.append(f"- {'PASS' if ok else '**FAIL**'} — {n}" + (f" ({d})" if d else ""))
        rep.append("")
        print(f"[VALIDATE] consistency: {npass}/{len(res)} invariants PASS")

    # -------- Track 2: external coverage benchmark --------
    if "coverage" in tracks:
        rep.append("## 2. External coverage benchmark (KB skill-vocabulary recall vs expert gold)")
        rep.append("Gold skill mentions pooled across all splits; coverage = a mention's normalized "
                   "`match_key` hits a KB primary/alt label (exact) or its nearest KB skill label is "
                   f"within {C.VALIDATION_SEMANTIC_MIN} bge-m3 cosine (semantic).\n")
        rep.append("| dataset | slice | gold | exact% | +semantic% | covered% |")
        rep.append("|---|---|--:|--:|--:|--:|")
        summary_rows, detail_fields = [], ["surface", "layer", "subset", "category", "count",
                                           "exact", "exact_uid", "sem_score", "sem_uid", "semantic"]
        for ds in C.VALIDATION_DATASETS:
            golds = coverage.evaluate(ds, embedder)
            _write_csv(f"coverage_{ds}_detail.csv", detail_fields, golds)
            for row in coverage.aggregate(ds, golds):
                summary_rows.append(row)
                slc = row["layer"] + ("/" + row["subset"] if row["subset"] else "")
                rep.append(f"| {row['dataset']} | {slc} | {row['gold']} | {row['exact_pct']} | "
                           f"{row['semantic_pct']} | {row['covered_pct']} |")
            # top uncovered examples (neither exact nor semantic), most frequent first
            unc = sorted([g for g in golds if not g["exact"] and not g["semantic"]],
                         key=lambda g: -g["count"])[:15]
            print(f"[VALIDATE] coverage {ds}: {len(golds)} unique gold mentions")
        _write_csv("coverage_summary.csv",
                   ["dataset", "layer", "subset", "gold", "exact_n", "exact_pct",
                    "semantic_n", "semantic_pct", "covered_pct"], summary_rows)
        rep.append("")
        # Sayfullina synonym-normalization test
        norm = coverage.normalization_test(embedder)
        if norm:
            s, rows = norm
            _write_csv("normalization.csv",
                       ["cluster_id", "cluster_size", "resolved", "distinct_kb_nodes",
                        "collapsed", "example"], rows)
            rep.append("### Synonym-normalization (Sayfullina 234-cluster reference)")
            rep.append(f"Of {s['clusters_evaluable']} clusters with ≥2 phrasings the KB contains, "
                       f"**{s['clusters_collapsed']} ({s['collapse_rate_pct']}%)** resolve all their "
                       f"phrasings to a single KB node (correct normalization).\n")
            print(f"[VALIDATE] normalization: {s['clusters_collapsed']}/{s['clusters_evaluable']} "
                  f"clusters collapse to one node ({s['collapse_rate_pct']}%)")
        else:
            rep.append("### Synonym-normalization: cluster list unavailable (corpus-only coverage).\n")

    # -------- Track 3: LLM-connection accuracy --------
    if "llm" in tracks:
        from ..align.verify import Verifier
        res = llm_audit.audit(embedder, Verifier())
        _write_csv("llm_links_audit.csv",
                   ["occupation", "skill", "creation_cosine", "nli", "nli_pass", "demand_exact",
                    "demand_semantic", "corroborated", "verdict"], res["link_rows"])
        _write_csv("llm_descriptions_audit.csv", ["label", "nli", "pass", "description"],
                   res["desc_rows"])
        L, Dz = res["links"], res["descriptions"]
        rep.append("## 3. LLM-connection accuracy audit")
        rep.append(f"**{L['n']} `llm_inferred` occupation→skill links** (created with a cosine≥0.45 "
                   f"gate only) re-validated independently:")
        rep.append(f"- NLI (occupation definition ⊨ \"requires {{skill}}\"): "
                   f"**{L['nli_pass']}/{L['n']} ({L['nli_pass_pct']}%)** pass ≥{C.VALIDATION_LINK_NLI_MIN}.")
        rep.append(f"- Demand corroboration (occupation really demands the skill or a near one in its "
                   f"posting profile): **{L['demand_corroborated']}/{L['n']} "
                   f"({L['demand_corroborated_pct']}%)** ({L['demand_exact']} exact).")
        strong = sum(1 for r in res["link_rows"] if r["verdict"] == "strong")
        rep.append(f"- Both signals agree (high-confidence): **{strong}/{L['n']}**.")
        rep.append(f"\n**{Dz['n']} `llm` descriptions** re-verified by NLI: "
                   f"**{Dz['nli_pass']}/{Dz['n']} ({Dz['nli_pass_pct']}%)** pass ≥{C.LLM_DESC_NLI_MIN}.\n")
        print(f"[VALIDATE] llm links: NLI {L['nli_pass']}/{L['n']}, demand-corroborated "
              f"{L['demand_corroborated']}/{L['n']}; descriptions NLI {Dz['nli_pass']}/{Dz['n']}")

    with open(os.path.join(C.VALIDATION_OUT_DIR, "report.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(rep) + "\n")
    print(f"[VALIDATE] report written to {os.path.join(C.VALIDATION_OUT_DIR, 'report.md')}")
