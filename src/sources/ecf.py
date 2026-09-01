"""ECF source — the European e-Competence Framework."""

from __future__ import annotations

import csv
import os

from .. import config as C
from .base import StructuredSource

_CSV = os.path.join(C.OTHERS_EN_DIR, "e-Cf_ESCO.csv")


def _fix(text):
    """Repair the source CSV."""
    return (text or "").replace("�", "'")

# e-CF competence ID -> neutral sub-domain
_ECF_SUBDOMAIN = {
    # A — Plan
    "A.1": "it_management", "A.2": "it_management", "A.3": "it_management",
    "A.4": "it_management", "A.5": "systems_infrastructure", "A.6": "programming_languages",
    "A.7": "emerging_tech", "A.8": "it_management", "A.9": "it_management", "A.10": "web",
    # B — Build
    "B.1": "programming_languages", "B.2": "systems_infrastructure", "B.3": "methodology",
    "B.4": "cloud_devops", "B.5": "methodology", "B.6": "networks",
    # C — Run
    "C.1": "it_management", "C.2": "methodology", "C.3": "it_management",
    "C.4": "it_management", "C.5": "systems_infrastructure",
    # D — Enable
    "D.1": "security", "D.2": "methodology", "D.3": "it_management", "D.4": "it_management",
    "D.5": "it_management", "D.6": "it_management", "D.7": "ai_ml", "D.8": "it_management",
    "D.9": "it_management", "D.10": "data_databases", "D.11": "methodology",
    # E — Manage
    "E.1": "it_management", "E.2": "it_management", "E.3": "it_management",
    "E.4": "it_management", "E.5": "methodology", "E.6": "methodology",
    "E.7": "it_management", "E.8": "security", "E.9": "it_management",
}


class EcfSource(StructuredSource):
    name = C.SRC_ECF
    contributes_occupations = False
    needs_attach = False
    builtin = True
    version = "e-CF 4.0"
    retrieval_method = "ecf_csv"

    def skills(self):
        with open(_CSV, encoding="utf-8-sig", errors="replace", newline="") as fh:
            for r in csv.DictReader(fh, delimiter=";"):
                cid = (r.get("Dimension 2 (ID)") or "").strip()
                label = _fix((r.get("Dimension 2 (Title)") or "").strip())
                if not cid or not label:
                    continue
                yield {
                    "source_id": cid,
                    "label_en": label,
                    "desc_en": _fix((r.get("Dimension 2 (Generic Description)") or "").strip()),
                    "hard_soft": "hard",
                    "method": "ecf_competence",
                    "it_subtype": _ECF_SUBDOMAIN.get(cid, ""),  
                }
