"""EMERGING source — curated emerging IT roles observed in the labor market but absent from the standard taxonomies"""

from __future__ import annotations

from .. import config as C
from .base import StructuredSource

# Each: source_id, canonical label, description, alt labels, and the raw job-title regex.
EMERGING_ROLES = [
    {
        "source_id": "analytics_engineer",
        "label": "analytics engineer",
        "desc": ("An analytics engineer builds, tests and documents clean, reliable data models and "
                 "analysis-ready datasets — typically with SQL and transformation tools such as dbt — "
                 "transforming raw data warehouse data into curated tables that data analysts and "
                 "business users consume. The role bridges data engineering and data analysis, applying "
                 "software-engineering practices (version control, testing, CI/CD) to analytics."),
        "alts": ["analytics developer", "dbt developer", "data analytics engineer"],
        "pattern": r"analytics engineer|\bdbt (developer|engineer)",
    },
    {
        "source_id": "mlops_engineer",
        "label": "MLOps engineer",
        "desc": ("An MLOps engineer designs and operates the infrastructure, pipelines and tooling to "
                 "deploy, serve, monitor, version and scale machine-learning models in production. The "
                 "role combines machine learning, software engineering, DevOps and cloud practices to "
                 "automate the machine-learning lifecycle (training, deployment, monitoring, retraining)."),
        "alts": ["machine learning operations engineer", "ML operations engineer", "ML platform engineer"],
        "pattern": r"\bml ?ops\b|machine learning operations",
    },
    {
        "source_id": "bi_developer",
        "label": "business intelligence developer",
        "desc": ("A business intelligence developer designs, builds and maintains BI solutions — data "
                 "models, ETL/ELT processes, reports and interactive dashboards — using tools such as "
                 "Power BI, Tableau, SSRS, SSIS and SQL, to deliver reporting and analytics to an "
                 "organisation. Distinct from a BI analyst, the role focuses on building the BI systems."),
        "alts": ["BI developer", "BI engineer", "business intelligence engineer", "reporting developer"],
        "pattern": r"\bbi (developer|engineer)\b|business intelligence (developer|engineer)",
    },
    {
        "source_id": "data_governance_analyst",
        "label": "data governance analyst",
        "desc": ("A data governance analyst defines, implements and enforces data policies, standards, "
                 "quality rules, lineage, cataloguing, ownership and regulatory compliance across an "
                 "organisation's data assets, ensuring data is trustworthy, well-documented and used "
                 "responsibly."),
        "alts": ["data governance manager", "data governance specialist", "data governance lead"],
        "pattern": r"data governance",
    },
    {
        "source_id": "full_stack_developer",
        "label": "full stack developer",
        "desc": ("A full-stack developer designs, builds and maintains both the front-end (user "
                 "interface, client-side) and the back-end (server-side application logic, APIs, "
                 "databases) of web and software applications, working across the entire technology "
                 "stack from the browser to the database."),
        "alts": ["full-stack developer", "full stack engineer", "full-stack engineer",
                 "full stack software developer", "full stack web developer"],
        "pattern": r"full[- ]?stack",
    },
    {
        "source_id": "backend_developer",
        "label": "back-end developer",
        "desc": ("A back-end developer designs, builds and maintains the server-side of web and "
                 "software applications — the application logic, APIs, services, business rules and "
                 "database access that run on the server rather than in the browser. The role works "
                 "with server languages and frameworks, data stores and integration, and is the "
                 "counterpart to the front-end developer; distinct from a full-stack developer, who "
                 "spans both tiers."),
        "alts": ["backend developer", "back end developer", "back-end engineer",
                 "backend engineer", "server-side developer", "back-end software developer"],
        "pattern": r"back[- ]?end",
    },
]


class EmergingRolesSource(StructuredSource):
    name = C.SRC_EMERGING
    contributes_occupations = True
    needs_attach = True
    builtin = True
    version = "curated-emerging-2026"
    retrieval_method = "labor_market_gap_curation"

    def occupations(self):
        for r in EMERGING_ROLES:
            yield {
                "source_id": r["source_id"],
                "label_en": r["label"],
                "alt_en": r["alts"],
                "desc_en": r["desc"],
            }
