#!/usr/bin/env python
"""CLI entry point for the JobKB build.

Full build:
    python run_pipeline.py                 # full clean build (all stages)
    python run_pipeline.py --no-align      # ingest + hierarchy only (skip HF models)
    python run_pipeline.py --keep          # do not wipe kb/ before the full build

Run only specific stages (against the existing kb/, never wiped unless --clean):
    stages = ingest -> hierarchy -> align -> attach -> merge -> qa
    python run_pipeline.py --stages merge              # re-derive unified concepts (seconds)
    python run_pipeline.py --stages attach,merge       # re-attach + re-merge (after tuning attach)
    python run_pipeline.py --from align                # align -> attach -> merge -> qa
    python run_pipeline.py --to hierarchy              # ingest + hierarchy only
    python run_pipeline.py --stages ingest --source ESCO   # re-ingest just one source
    python run_pipeline.py --stages qa                 # integrity report only
    python run_pipeline.py --list-stages

Incremental sources:
    python run_pipeline.py --add NAME      # incrementally add one registered source
    python run_pipeline.py --remove NAME   # incrementally remove one source
    python run_pipeline.py --list-sources  # list registered sources
"""

from __future__ import annotations
import argparse
import sys

from src import pipeline


def _resolve_stages(args):
    """Return the explicit list of stages requested, or None for a full build."""
    order = pipeline.STAGE_ORDER
    if args.stages and (args.stage_from or args.stage_to):
        sys.exit("error: use either --stages or --from/--to, not both.")

    if args.stages:
        req = [s.strip() for s in args.stages.split(",") if s.strip()]
        unknown = [s for s in req if s not in order]
        if unknown:
            sys.exit(f"error: unknown stage(s): {', '.join(unknown)}. "
                     f"Valid: {', '.join(order)}")
        return req

    if args.stage_from or args.stage_to:
        for label, val in (("--from", args.stage_from), ("--to", args.stage_to)):
            if val and val not in order:
                sys.exit(f"error: unknown stage for {label}: {val}. Valid: {', '.join(order)}")
        start = order.index(args.stage_from) if args.stage_from else 0
        end = order.index(args.stage_to) if args.stage_to else len(order) - 1
        if start > end:
            sys.exit("error: --from stage comes after --to stage.")
        return order[start:end + 1]

    return None


def main():
    ap = argparse.ArgumentParser(
        description="Build the JobKB knowledge base (whole or by stage).",
        formatter_class=argparse.RawDescriptionHelpFormatter, epilog=__doc__)
    # full-build switches
    ap.add_argument("--no-align", action="store_true",
                    help="full build without alignment/attach/merge (no HF model downloads)")
    ap.add_argument("--keep", action="store_true",
                    help="full build without wiping kb/ first")
    # stage selection
    ap.add_argument("--stages", metavar="A,B,C",
                    help="run only these comma-separated stages (in canonical order)")
    ap.add_argument("--from", dest="stage_from", metavar="STAGE",
                    help="run from this stage to the end")
    ap.add_argument("--to", dest="stage_to", metavar="STAGE",
                    help="run from the start up to (and including) this stage")
    ap.add_argument("--source", metavar="NAME",
                    help="scope ingest/align/attach to a single registered source")
    ap.add_argument("--clean", action="store_true",
                    help="wipe kb/ before a selective run (default: keep it)")
    ap.add_argument("--list-stages", action="store_true", help="list the stages and exit")
    # incremental sources
    ap.add_argument("--add", metavar="NAME",
                    help="incrementally add one registered source to the existing KB")
    ap.add_argument("--remove", metavar="NAME",
                    help="incrementally remove one source from the existing KB")
    ap.add_argument("--list-sources", action="store_true",
                    help="list the registered sources and exit")
    # wikidata enrichment (network read-only; snapshotted for offline reproducibility)
    ap.add_argument("--wikidata", action="store_true",
                    help="anchor tech-skills + occupations to Wikidata QIDs (kb/wikidata_links.csv)")
    ap.add_argument("--refresh-wikidata", action="store_true",
                    help="re-query Wikidata ignoring the resolutions snapshot")
    # LLM enrichment (pillar 3): generation is snapshotted; validated; fail-open on no credits/offline
    ap.add_argument("--llm", nargs="?", const="all", metavar="TASKS",
                    help="run LLM enrichment after merge; optional comma-list of tasks "
                         "(descriptions,hardsoft,links,emerging); default all")
    ap.add_argument("--translate", nargs="?", const="all", metavar="DIRS",
                    help="fill empty EN/FR labels after merge (Wikidata labels + validated MT); "
                         "optional comma-list of directions (wikidata,en_fr,fr_en); default all")
    args = ap.parse_args()

    if args.list_stages:
        print("stages (canonical order):", " -> ".join(pipeline.STAGE_ORDER))
        return

    if args.list_sources:
        from src.sources import registry
        for n, s in registry.REGISTRY.items():
            print(f"  {n:6}  builtin={s.builtin}  occupations={s.contributes_occupations}  "
                  f"needs_attach={s.needs_attach}")
        return

    if args.wikidata or args.refresh_wikidata:
        from src import wikidata
        wikidata.run(refresh=args.refresh_wikidata)
        return

    if args.llm:
        from src import llm
        tasks = llm.ALL_TASKS if args.llm == "all" else tuple(t.strip() for t in args.llm.split(","))
        llm.run(tasks=tasks)
        return

    if args.translate:
        from src import translate
        translate.run(directions=args.translate)
        return

    if args.add:
        from src import incremental
        incremental.add_source(args.add)
        return
    if args.remove:
        from src import incremental
        incremental.remove_source(args.remove)
        return

    selected = _resolve_stages(args)

    if selected is not None:
        pipeline.run_stages(selected, source=args.source, clean=args.clean)
        return

    # full build
    if args.source:
        sys.exit("error: --source only applies to a stage selection "
                 "(--stages/--from/--to) or --add/--remove.")
    pipeline.run_all(clean=not args.keep, do_align=not args.no_align)


if __name__ == "__main__":
    main()
