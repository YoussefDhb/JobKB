"""ADEM source — real labor-market demand relations (enrichment)."""

from __future__ import annotations

import csv
import os
from collections import defaultdict

from .. import config as C
from .. import common as K
from .base import Source
from . import evidence

_CSV = os.path.join(C.OTHERS_EN_DIR, "datasc-skills-vacancies-2025-2027.csv")


class AdemDemandSource(Source):
    name = C.SRC_ADEM
    contributes_occupations = False
    needs_attach = False
    builtin = True
    version = "adem-2025"
    retrieval_method = "adem_vacancies"

    def ingest(self) -> None:
        rome_map = evidence.rome_occ_by_code()
        esco_map = evidence.esco_skill_by_uuid()
        agg = defaultdict(int)
        rows_scanned = 0
        with open(_CSV, encoding="utf-8", newline="") as f:
            for row in csv.DictReader(f):
                rows_scanned += 1
                oc = (row.get("occupation_code") or "").strip()
                uri = (row.get("skill_uri") or "").strip()
                if not uri or not oc.startswith(C.ADEM_ROME_PREFIX):
                    continue
                occ_id = rome_map.get(oc)
                skill_id = esco_map.get(uri.rsplit("/", 1)[-1])
                if not occ_id or not skill_id:
                    continue                         
                try:
                    positions = int(float(row.get("positions") or 1))
                except ValueError:
                    positions = 1
                agg[(occ_id, skill_id)] += max(positions, 1)

        rows = [evidence.relation_row(o, s, self.name, weight=w) for (o, s), w in agg.items()]
        evidence.write_relations(self.name, rows)
        K.log_provenance(self.name, [{
            "entity_id": self.name, "source": self.name, "source_version": self.version,
            "retrieved_at": K.now_iso(), "retrieval_method": self.retrieval_method,
            "notes": f"{len(rows)} demand relations ({C.ADEM_ROME_PREFIX}* IT vacancies)",
        }])
        print(f"[{self.name}] {len(rows)} demand relations from {rows_scanned} vacancy-skill rows "
              f"({len({o for o, _ in agg})} occupations, {len({s for _, s in agg})} skills).")
