#!/usr/bin/env python
"""CLI entry point for the JobKB build.

    python run_pipeline.py                 # full build (ingest -> hierarchy -> align -> merge)
    python run_pipeline.py --no-align      # ingest + hierarchy only (skip HF models)
    python run_pipeline.py --keep          # do not wipe kb/ before building
"""

from __future__ import annotations
import argparse

from src import pipeline


def main():
    ap = argparse.ArgumentParser(description="Build the JobKB knowledge base.")
    ap.add_argument("--no-align", action="store_true",
                    help="skip alignment + unified merge (no HF model downloads)")
    ap.add_argument("--keep", action="store_true",
                    help="keep existing kb/ files instead of rebuilding clean")
    args = ap.parse_args()

    pipeline.run_all(clean=not args.keep, do_align=not args.no_align)


if __name__ == "__main__":
    main()
