"""KAGGLE_JOBS source — kaggle "job skill set" dataset, IT subset."""

from __future__ import annotations

import ast
import csv
from collections import defaultdict

from .. import config as C
from .. import common as K
from .base import Source
from . import evidence
from .data_jobs import _augmented_skill_index

# Ordered (keyword-in-title -> occupation probe) rules.
_TITLE_RULES = [
    (("help desk", "helpdesk", "support"), "ict help desk agent"),
    (("project manager", "project coordinator", "program manager", "delivery manager"), "ict project manager"),
    (("business analyst",), "ict business analyst"),
    (("system administrator", "systems administrator", "sysadmin"), "ict system administrator"),
    (("security",), "information security analyst"),
    (("database", "dba"), "database administrator"),
    (("developer", "programmer", "software engineer"), "software developer"),
    (("technician",), "ict technician"),
    (("manager", "director", "operations", "head of"), "ict operations manager"),
]


class KaggleJobsSource(Source):
    name = C.SRC_KAGGLE_JOBS
    contributes_occupations = False
    needs_attach = False
    builtin = True
    version = "kaggle-job-skill-set-it"
    retrieval_method = "job_postings_mined"

    def ingest(self) -> None:
        occ_map = evidence.occ_index()
        skill_idx = _augmented_skill_index(exclude_source=self.name)

        def resolve_role(title):
            t = (title or "").lower()
            for kws, probe in _TITLE_RULES:
                if any(kw in t for kw in kws):
                    return occ_map.get(evidence.match_key(probe))
            return None

        pair = defaultdict(int)
        n_it = 0
        roles_matched = set()
        with open(C.KAGGLE_JOBS_CSV, encoding="utf-8", errors="replace", newline="") as f:
            csv.field_size_limit(2 ** 31 - 1)
            for row in csv.DictReader(f):
                if (row.get("category") or "").strip() != "INFORMATION-TECHNOLOGY":
                    continue
                n_it += 1
                occ_id = resolve_role(row.get("job_title") or "")
                if not occ_id:
                    continue
                try:
                    skills = ast.literal_eval(row.get("job_skill_set") or "[]")
                except (ValueError, SyntaxError):
                    continue
                roles_matched.add(occ_id)
                seen = set()
                for s in skills:
                    sid = skill_idx.get(evidence.match_key(str(s)))
                    if sid and sid not in seen:
                        seen.add(sid)
                        pair[(occ_id, sid)] += 1

        rel_rows = [evidence.relation_row(o, s, self.name, weight=w)
                    for (o, s), w in pair.items() if w >= C.KAGGLE_JOBS_MIN_FREQ]
        evidence.write_relations(self.name, rel_rows)

        K.log_provenance(self.name, [{
            "entity_id": self.name, "source": self.name, "source_version": self.version,
            "retrieved_at": K.now_iso(), "retrieval_method": self.retrieval_method,
            "notes": f"{len(rel_rows)} demand relations from {n_it} IT postings, "
                     f"{len(roles_matched)} occupations",
        }])
        print(f"[{self.name}] {len(rel_rows)} demand relations from {n_it} IT postings "
              f"({len(roles_matched)} occupations).")
