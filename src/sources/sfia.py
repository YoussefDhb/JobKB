"""SFIA source — the Skills Framework for the Information Age, version 9.

SFIA is a curated professional competency framework for digital, data and technology work.
It contributes **skills only** (no occupations): its skills flow into the neutral skill
ontology, align/merge against the existing skill vocabulary (ESCO/ONET/...), and reach
occupations transitively wherever a SFIA skill merges into a unified skill that already
carries occupation relations.

Data: `resources/SFIA/en/sfia9_skills.csv` (147 skills; the sibling category / subcategory /
mapping tables are NOT used — this export's `subcategory_id` and `sfia9_skill_mappings.csv`
are unreliable, e.g. they file "Systems integration" under "Security Investigation" and
"Accessibility" under AI). Only the skill titles/descriptions are genuine, so we ship our own
hand-curated `_SFIA_SUBDOMAIN` map: it (a) **scopes** SFIA to IT + IT-management — a code
absent from the map is a general business / HR / marketing / finance / facilities competency
and is **dropped as out of scope** — and (b) places each kept skill into one of the 13 neutral
sub-domains (kept by `hierarchy.run` because SFIA is in `config.SELF_CLASSIFIED_SUBDOMAIN_SOURCES`).
Deprecated skills are skipped.
"""

from __future__ import annotations

import os

from .. import config as C
from .. import common as K
from .base import StructuredSource

_SKILLS_CSV = os.path.join(C.SFIA_EN_DIR, "sfia9_skills.csv")

# Kept SFIA skill codes -> neutral sub-domain. Codes NOT listed are out of IT scope (dropped):
# marketing/sales/customer, facilities, finance, HR/L&D, generic business, physical safety.
_SFIA_SUBDOMAIN = {
    # security & cybersecurity
    "SCTY": "security", "SCAD": "security", "PENT": "security", "VUAS": "security",
    "VURE": "security", "THIN": "security", "IAMT": "security", "INAS": "security",
    "DGFS": "security", "CRIM": "security", "OCOP": "security",
    # AI & machine learning
    "MLNG": "ai_ml", "DATS": "ai_ml",
    # data & databases
    "DAAN": "data_databases", "DENG": "data_databases", "DATM": "data_databases",
    "DTAN": "data_databases", "VISL": "data_databases", "DBAD": "data_databases",
    "DBDS": "data_databases", "BINT": "data_databases", "IRMG": "data_databases",
    # programming & software development
    "PROG": "programming_languages", "SWDN": "programming_languages",
    "RESD": "programming_languages", "ADEV": "programming_languages",
    "ANCC": "programming_languages", "ASUP": "programming_languages",
    # web / UX & design
    "HCEV": "web", "UNAN": "web", "USEV": "web", "URCH": "web", "INCA": "web",
    "GRDN": "web", "ACIN": "web",
    # cloud & devops
    "DEPL": "cloud_devops", "PORT": "cloud_devops", "CFMG": "cloud_devops",
    # networks & telecom
    "NTDS": "networks", "NTAS": "networks", "RFEN": "networks",
    # systems & infrastructure
    "ARCH": "systems_infrastructure", "DESN": "systems_infrastructure",
    "SINT": "systems_infrastructure", "STPL": "systems_infrastructure",
    "IFDN": "systems_infrastructure", "ITOP": "systems_infrastructure",
    "STMG": "systems_infrastructure", "SYSP": "systems_infrastructure",
    "HPCC": "systems_infrastructure", "CPMG": "systems_infrastructure",
    # methodologies & practices (testing, requirements, change)
    "TEST": "methodology", "NFTS": "methodology", "PRTS": "methodology",
    "BPTS": "methodology", "REQM": "methodology", "METL": "methodology",
    "FEAS": "methodology", "CHMG": "methodology",
    # IT management & governance
    "GOVN": "it_management", "PEDP": "it_management", "AUDT": "it_management",
    "POMG": "it_management", "PROF": "it_management", "PGMG": "it_management",
    "PRMG": "it_management", "BURM": "it_management", "ITSP": "it_management",
    "QUMG": "it_management", "QUAS": "it_management", "RMGT": "it_management",
    "KNOW": "it_management", "ISCO": "it_management", "EMRG": "it_management",
    "CSOP": "it_management", "DEMG": "it_management", "DEMM": "it_management",
    "PROD": "it_management", "INOV": "it_management", "BENM": "it_management",
    "BUDF": "it_management", "COMG": "it_management", "ITCM": "it_management",
    "SUPP": "it_management", "SCMG": "it_management", "SLMO": "it_management",
    "ITMG": "it_management", "USUP": "it_management", "PBMG": "it_management",
    "AVMT": "it_management", "COPL": "it_management", "ASMG": "it_management",
    # general IT knowledge
    "RSCH": "knowledge_general", "NUAN": "knowledge_general", "MEAS": "knowledge_general",
}


class SfiaSource(StructuredSource):
    name = C.SRC_SFIA
    contributes_occupations = False      # SFIA has no occupations
    needs_attach = False                 # ... so nothing to attach to ISCO
    builtin = True                       # permanent member of a full build
    version = "sfia-9"
    retrieval_method = "sfia_csv"

    def skills(self):
        for _, r in K.read_csv_smart(_SKILLS_CSV).iterrows():
            if (r.get("is_deprecated") or "").strip().lower() == "true":
                continue
            code = (r.get("code") or "").strip()
            title = (r.get("title") or "").strip()
            sub = _SFIA_SUBDOMAIN.get(code)
            if not code or not title or sub is None:
                continue                 # drop deprecated / out-of-scope business skills
            yield {
                "source_id": code,
                "label_en": title,
                "alt_en": [code],        # keep the SFIA short code searchable
                "desc_en": (r.get("description") or "").strip(),
                "method": "sfia_skill",
                "it_subtype": sub,
            }
