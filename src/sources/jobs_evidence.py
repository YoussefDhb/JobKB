"""JOBS source — mined IT job-posting evidence relations (enrichment).

`resources/OTHERS/en/JobsDatasetProcessed.csv` is 2,999 LLM-processed IT postings, each tagged with
a role (`Query`) and pre-extracted `IT Skills` / `Soft Skills` (free-text surface forms). We mine it
as **evidence relations only**: match each posting's role to an EXISTING occupation and each extracted
skill to an EXISTING skill (by normalized label), then add weighted `demand` relations for
(occupation, skill) pairs seen in at least `JOBS_MIN_FREQ` postings.

No new occupation/skill nodes are created — topic-only queries ("Statistics", "Deep Learning") find
no occupation match and drop out, so the LLM-extraction noise self-filters. Relation-only source.
"""

from __future__ import annotations

import csv
import os
from collections import defaultdict

from .. import config as C
from .. import common as K
from .base import Source
from . import evidence

_CSV = os.path.join(C.OTHERS_EN_DIR, "JobsDatasetProcessed.csv")


class JobsEvidenceSource(Source):
    name = C.SRC_JOBS
    contributes_occupations = False
    needs_attach = False
    builtin = True
    version = "jobs-processed"
    retrieval_method = "job_postings_mined"

    def ingest(self) -> None:
        occ_map = evidence.occ_index()
        skl_map = evidence.skill_index()
        pair = defaultdict(int)
        n_post = 0
        roles_matched = set()
        with open(_CSV, encoding="utf-8", newline="") as f:
            for row in csv.DictReader(f):
                n_post += 1
                occ_id = occ_map.get(evidence.match_key(row.get("Query") or ""))
                if not occ_id:
                    continue                          # role is not an existing occupation -> skip
                roles_matched.add(row.get("Query"))
                skills = set()
                for col in ("IT Skills", "Soft Skills"):
                    for surface in (row.get(col) or "").split(","):
                        sid = skl_map.get(evidence.match_key(surface))
                        if sid:
                            skills.add(sid)
                for sid in skills:
                    pair[(occ_id, sid)] += 1

        rows = [evidence.relation_row(o, s, self.name, weight=c)
                for (o, s), c in pair.items() if c >= C.JOBS_MIN_FREQ]
        evidence.write_relations(self.name, rows)
        K.log_provenance(self.name, [{
            "entity_id": self.name, "source": self.name, "source_version": self.version,
            "retrieved_at": K.now_iso(), "retrieval_method": self.retrieval_method,
            "notes": f"{len(rows)} evidence relations from {n_post} postings, "
                     f"{len(roles_matched)} roles matched to existing occupations",
        }])
        print(f"[{self.name}] {len(rows)} evidence relations from {n_post} postings "
              f"({len(roles_matched)} roles matched, {len({o for o, _ in pair})} occupations).")
