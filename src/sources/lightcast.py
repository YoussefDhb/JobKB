"""LIGHTCAST source — Lightcast Open Skills, IT slice.

Lightcast Open Skills is a large, cleanly-categorized skills taxonomy (31 categories → 442
subcategories → ~32k skills) in one flat CSV: `resources/LIGHTCAST/en/lightcast_data_formatted.csv`
(`id, description, hierarchy_levels, type`). We ingest the **Information Technology** category
(`17.0`) — 5,244 skills across 70 authoritative IT subcategories — as a **skills-only** source.

Unlike SFIA's export, Lightcast's categorisation is reliable, so each skill self-classifies into
one of the 14 neutral sub-domains via its subcategory (`_LIGHTCAST_SUBDOMAIN`, kept by
`hierarchy.run` since LIGHTCAST is in `config.SELF_CLASSIFIED_SUBDOMAIN_SOURCES`). Skills align/merge
with the existing vocabulary and reach occupations transitively; the relevance gate screens them at
ingest (≈0 blocks — they are already IT-scoped).
"""

from __future__ import annotations

import ast
import os

from .. import config as C
from .. import common as K
from .base import StructuredSource

_CSV = os.path.join(C.LIGHTCAST_EN_DIR, "lightcast_data_formatted.csv")
_IT_CATEGORY = "17.0"

# Lightcast IT subcategory code -> one of the 14 neutral sub-domains (hierarchy.SUBDOMAINS).
_LIGHTCAST_SUBDOMAIN = {
    "17.0.474.0": "programming_languages", "17.0.442.0": "programming_languages",
    "17.0.369.0": "programming_languages", "17.0.456.0": "programming_languages",
    "17.0.476.0": "programming_languages", "17.0.471.0": "programming_languages",
    "17.0.470.0": "programming_languages", "17.0.428.0": "programming_languages",
    "17.0.437.0": "programming_languages", "17.0.379.0": "programming_languages",
    "17.0.415.0": "programming_languages", "17.0.447.0": "programming_languages",
    "17.0.434.0": "programming_languages",
    "17.0.426.0": "security", "17.0.451.0": "security", "17.0.392.0": "security",
    "17.0.367.0": "security", "17.0.387.0": "security",
    "17.0.372.0": "ai_ml",
    "17.0.479.0": "data_databases", "17.0.416.0": "data_databases", "17.0.464.0": "data_databases",
    "17.0.395.0": "data_databases", "17.0.393.0": "data_databases", "17.0.411.0": "data_databases",
    "17.0.396.0": "data_databases", "17.0.400.0": "data_databases", "17.0.422.0": "data_databases",
    "17.0.382.0": "cloud_devops", "17.0.486.0": "cloud_devops", "17.0.389.0": "cloud_devops",
    "17.0.406.0": "cloud_devops", "17.0.488.0": "cloud_devops", "17.0.435.0": "cloud_devops",
    "17.0.381.0": "cloud_devops",
    "17.0.495.0": "networks", "17.0.452.0": "networks", "17.0.483.0": "networks",
    "17.0.450.0": "networks", "17.0.453.0": "networks", "17.0.421.0": "networks",
    "17.0.491.0": "web", "17.0.391.0": "web", "17.0.490.0": "web", "17.0.494.0": "web",
    "17.0.438.0": "web", "17.0.472.0": "web",
    "17.0.480.0": "systems_infrastructure", "17.0.386.0": "systems_infrastructure",
    "17.0.375.0": "systems_infrastructure", "17.0.481.0": "systems_infrastructure",
    "17.0.440.0": "systems_infrastructure", "17.0.446.0": "systems_infrastructure",
    "17.0.473.0": "systems_infrastructure", "17.0.455.0": "systems_infrastructure",
    "17.0.445.0": "systems_infrastructure", "17.0.419.0": "systems_infrastructure",
    "17.0.409.0": "it_management", "17.0.436.0": "it_management", "17.0.482.0": "it_management",
    "17.0.384.0": "it_management", "17.0.487.0": "it_management",
    "17.0.477.0": "methodology", "17.0.365.0": "methodology", "17.0.484.0": "methodology",
    "17.0.363.0": "knowledge_general", "17.0.376.0": "knowledge_general",
    "17.0.374.0": "emerging_tech", "17.0.430.0": "emerging_tech", "17.0.378.0": "emerging_tech",
}


class LightcastSource(StructuredSource):
    name = C.SRC_LIGHTCAST
    contributes_occupations = False
    needs_attach = False
    builtin = True
    version = "lightcast-open-skills"
    retrieval_method = "lightcast_csv"

    def skills(self):
        for _, r in K.read_csv_smart(_CSV).iterrows():
            if (r.get("type") or "").strip() != "skill":
                continue
            raw = (r.get("hierarchy_levels") or "").strip()
            if not raw:
                continue                              # unmapped (certs) -> skip
            try:
                pairs = ast.literal_eval(raw)
            except (ValueError, SyntaxError):
                continue
            if not pairs or pairs[0][0] != _IT_CATEGORY:
                continue                              # keep only the IT category (17.0)
            subcat = pairs[0][1] if len(pairs[0]) > 1 else ""
            label = (r.get("description") or "").strip()
            sid = (r.get("id") or "").strip()
            if not sid or not label:
                continue
            yield {
                "source_id": sid,
                "label_en": label,
                "method": "lightcast_skill",
                "it_subtype": _LIGHTCAST_SUBDOMAIN.get(subcat, ""),   # "" -> regex fallback
            }
