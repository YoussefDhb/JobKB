"""LINKEDIN_SWE source — kaggle LinkedIn software-engineering postings."""

from __future__ import annotations

import csv
import re
from collections import defaultdict

from .. import config as C
from .. import common as K
from .base import Source
from . import evidence
from .data_jobs import _augmented_skill_index
from .emerging_roles import EMERGING_ROLES

_SENIORITY = re.compile(
    r"\b(senior|sr|junior|jr|lead|principal|staff|mid|middle|entry[- ]?level|intern|"
    r"i{1,3}|iv|v)\b\.?", re.I)


class LinkedInSweSource(Source):
    name = C.SRC_LINKEDIN_SWE
    contributes_occupations = False
    needs_attach = False
    builtin = True
    version = "kaggle-linkedin-swe"
    retrieval_method = "job_postings_mined"

    def ingest(self) -> None:
        occ_map = evidence.occ_index()
        skill_idx = _augmented_skill_index(exclude_source=self.name)
        emerging = [(re.compile(r["pattern"], re.I), occ_map.get(evidence.match_key(r["label"])))
                    for r in EMERGING_ROLES]
        emerging = [(rx, oid) for rx, oid in emerging if oid]
        soft_dev = occ_map.get(evidence.match_key("software developer"))
        embedded = occ_map.get(evidence.match_key("embedded systems designer"))

        def resolve_role(title):
            t = title or ""
            oid = next((oid for rx, oid in emerging if rx.search(t)), None)
            if oid:
                return oid
            base = re.sub(r"\s+", " ", _SENIORITY.sub(" ", t)).strip(" -/,")
            oid = occ_map.get(evidence.match_key(base))
            if oid:
                return oid
            tl = t.lower()
            if "embedded" in tl and embedded:
                return embedded
            if ("developer" in tl or "engineer" in tl or "programmer" in tl) and soft_dev:
                return soft_dev
            return None

        pair = defaultdict(int)
        n_post = 0
        roles_matched = set()
        with open(C.LINKEDIN_SWE_CSV, encoding="utf-8", errors="replace", newline="") as f:
            csv.field_size_limit(2 ** 31 - 1)
            for row in csv.DictReader(f):
                n_post += 1
                occ_id = resolve_role(row.get("job_title") or "")
                if not occ_id:
                    continue
                raw = (row.get("job_skills") or "").strip()
                if not raw:
                    continue
                roles_matched.add((row.get("job_title") or "").strip())
                for t in {t.strip().lower() for t in raw.split(",") if t.strip()}:
                    sid = skill_idx.get(evidence.match_key(t))
                    if sid:
                        pair[(occ_id, sid)] += 1

        rel_rows = [evidence.relation_row(o, s, self.name, weight=w)
                    for (o, s), w in pair.items() if w >= C.LINKEDIN_SWE_MIN_FREQ]
        evidence.write_relations(self.name, rel_rows)

        K.log_provenance(self.name, [{
            "entity_id": self.name, "source": self.name, "source_version": self.version,
            "retrieved_at": K.now_iso(), "retrieval_method": self.retrieval_method,
            "notes": f"{len(rel_rows)} demand relations from {n_post} postings, "
                     f"{len(roles_matched)} titles matched",
        }])
        print(f"[{self.name}] {len(rel_rows)} demand relations from {n_post} postings "
              f"({len(roles_matched)} distinct titles matched, "
              f"{len({o for o, _ in pair})} occupations).")
