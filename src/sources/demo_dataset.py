"""DEMO source — a tiny synthetic IT dataset to validate incremental add/remove."""

from __future__ import annotations

from .base import StructuredSource

_OCCUPATIONS = [
    {"source_id": "dev-soft", "label_en": "Software Developer",
     "alt_en": ["Application Developer", "Programmer"],
     "desc_en": "Designs, builds, tests and maintains software applications and systems."},
    {"source_id": "dev-web-fr", "label_fr": "Développeur web",
     "alt_fr": ["Développeuse web", "Intégrateur web"],
     "desc_fr": "Conçoit, développe et maintient des sites et des applications web."},
    {"source_id": "prompt-eng", "label_en": "Prompt Engineer",
     "alt_en": ["LLM Prompt Engineer"],
     "desc_en": "Designs, tests and optimizes prompts and pipelines for large language models."},
]

_SKILLS = [
    {"source_id": "python", "label_en": "Python", "hard_soft": "hard",
     "desc_en": "General-purpose programming language widely used in software and data work."},
    {"source_id": "kubernetes", "label_en": "Kubernetes", "hard_soft": "hard",
     "desc_en": "Open-source container-orchestration platform for deploying and scaling services."},
    {"source_id": "teamwork", "label_en": "Teamwork", "hard_soft": "soft",
     "desc_en": "Working effectively and collaboratively within a team to reach shared goals."},
]

_RELATIONS = [
    {"occupation_source_id": "dev-soft", "skill_source_id": "python", "relation_type": "essential"},
    {"occupation_source_id": "dev-soft", "skill_source_id": "teamwork", "relation_type": "optional"},
    {"occupation_source_id": "dev-web-fr", "skill_source_id": "python", "relation_type": "essential"},
    {"occupation_source_id": "prompt-eng", "skill_source_id": "python", "relation_type": "essential"},
    {"occupation_source_id": "prompt-eng", "skill_source_id": "kubernetes", "relation_type": "optional"},
]


class DemoSource(StructuredSource):
    name = "DEMO"
    contributes_occupations = True
    needs_attach = True              
    version = "demo-1"
    retrieval_method = "synthetic_demo"

    def occupations(self):
        return _OCCUPATIONS

    def skills(self):
        return _SKILLS

    def relations(self):
        return _RELATIONS
