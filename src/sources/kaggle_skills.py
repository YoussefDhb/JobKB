"""KAGGLE source — a small curated IT technical-skills taxonomy."""

from __future__ import annotations

import os

from .. import config as C
from .. import common as K
from .base import StructuredSource

_CSV = os.path.join(C.OTHERS_EN_DIR, "kaggle-dataset_technical_skills.csv")

_KAGGLE_SUBDOMAIN = {
    "Programming Languages": "programming_languages",
    "DevOps & Cloud": "cloud_devops",
    "Machine Learning & AI": "ai_ml",
    "Web Frameworks": "web",
    "Databases": "data_databases",
    "Networking & Security": "networks",
    "Mobile Development": "programming_languages",
    "Testing & QA": "methodology",
    "Development Practices": "methodology",
}


class KaggleSkillsSource(StructuredSource):
    name = C.SRC_KAGGLE
    contributes_occupations = False
    needs_attach = False
    builtin = True
    version = "kaggle-technical-skills"
    retrieval_method = "kaggle_csv"

    def skills(self):
        for _, r in K.read_csv_smart(_CSV).iterrows():
            sid = (r.get("Skill ID") or "").strip()
            label = (r.get("Skill Name") or "").strip()
            if not sid or not label:
                continue
            cat = (r.get("Category") or "").strip()
            yield {
                "source_id": sid,
                "label_en": label,
                "method": "kaggle_skill",
                "it_subtype": _KAGGLE_SUBDOMAIN.get(cat, ""), 
            }
