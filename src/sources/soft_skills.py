"""SOFTSKILLS source — curated canonical soft / transversal skills used in IT hiring."""

from __future__ import annotations

from .. import config as C
from .base import StructuredSource

# Each: source_id, canonical noun-form label, alt labels, and a description.
SOFT_SKILLS = [
    {
        "source_id": "teamwork",
        "label": "teamwork",
        "alts": ["team player", "team collaboration", "collaboration", "work in a team",
                 "team work", "build team spirit", "work in teams"],
        "desc": ("The ability to work effectively and cooperatively within a team towards a shared "
                 "goal, contributing, sharing knowledge and supporting colleagues — central to "
                 "agile software delivery."),
    },
    {
        "source_id": "communication",
        "label": "communication",
        "alts": ["communication skills", "verbal communication", "written communication",
                 "excellent communication skills", "communicate effectively", "address an audience"],
        "desc": ("The ability to convey information, ideas and technical concepts clearly and "
                 "effectively in speech and writing to both technical and non-technical audiences."),
    },
    {
        "source_id": "leadership",
        "label": "leadership",
        "alts": ["leadership skills", "lead a team", "team leadership", "display leadership",
                 "lead others"],
        "desc": ("The ability to guide, motivate and coordinate a team or technical initiative, "
                 "setting direction, making decisions and taking ownership of outcomes."),
    },
    {
        "source_id": "problem_solving",
        "label": "problem solving",
        "alts": ["problem-solving", "problem solving skills", "analytical problem solving",
                 "solving problems", "troubleshooting"],
        "desc": ("The ability to analyse a problem, identify root causes and design and implement "
                 "effective solutions — the core cognitive skill of engineering and debugging."),
    },
    {
        "source_id": "time_management",
        "label": "time management",
        "alts": ["manage time", "meet deadlines", "prioritisation", "prioritization",
                 "manage workload"],
        "desc": ("The ability to plan, prioritise and organise one's work to meet deadlines and "
                 "deliver on commitments across concurrent tasks and projects."),
    },
    {
        "source_id": "flexibility",
        "label": "flexibility",
        "alts": ["adaptability", "adaptable", "flexible", "adapt to change", "versatility"],
        "desc": ("The ability to adjust readily to changing requirements, technologies, priorities "
                 "and environments — essential in fast-moving technology work."),
    },
    {
        "source_id": "creativity",
        "label": "creativity",
        "alts": ["creative", "creative thinking", "innovation", "think creatively",
                 "express yourself creatively"],
        "desc": ("The ability to generate original ideas and novel approaches to design, "
                 "architecture and problem solving."),
    },
    {
        "source_id": "emotional_intelligence",
        "label": "emotional intelligence",
        "alts": ["emotional quotient", "self-awareness", "empathy", "social awareness"],
        "desc": ("The ability to recognise, understand and manage one's own emotions and those of "
                 "others, supporting effective collaboration and communication."),
    },
    {
        "source_id": "work_ethic",
        "label": "work ethic",
        "alts": ["strong work ethic", "professional work ethic", "diligence", "dedication",
                 "commitment"],
        "desc": ("A disciplined, reliable and committed approach to work, taking pride in "
                 "delivering high-quality results."),
    },
    {
        "source_id": "attention_to_detail",
        "label": "attention to detail",
        "alts": ["detail-oriented", "detail oriented", "attention to details", "meticulous",
                 "attend to detail"],
        "desc": ("Thoroughness and accuracy in completing work, catching errors and edge cases — "
                 "critical in coding, testing and configuration."),
    },
    {
        "source_id": "interpersonal_skills",
        "label": "interpersonal skills",
        "alts": ["interpersonal", "interpersonal communication", "people skills",
                 "relationship building", "build networks"],
        "desc": ("The ability to build and maintain positive working relationships and interact "
                 "effectively with colleagues, stakeholders and clients."),
    },
    {
        "source_id": "decision_making",
        "label": "decision making",
        "alts": ["decision-making", "make decisions", "sound judgement", "judgement"],
        "desc": ("The ability to evaluate options and make timely, well-reasoned decisions, often "
                 "under uncertainty or technical trade-offs."),
    },
    {
        "source_id": "responsibility",
        "label": "responsibility",
        "alts": ["accountability", "sense of responsibility", "take responsibility", "reliability",
                 "assume responsibility", "ownership"],
        "desc": ("Taking ownership of one's tasks, decisions and their outcomes, and being "
                 "dependable and accountable to the team."),
    },
    {
        "source_id": "professionalism",
        "label": "professionalism",
        "alts": ["professional attitude", "professional conduct", "courtesy", "integrity at work"],
        "desc": ("Conducting oneself with competence, respect, reliability and ethical standards in "
                 "the workplace."),
    },
    {
        "source_id": "conflict_resolution",
        "label": "conflict resolution",
        "alts": ["resolve conflict", "resolving conflict", "conflict management",
                 "manage disagreements"],
        "desc": ("The ability to mediate and resolve disagreements constructively, keeping a team "
                 "productive and collaborative."),
    },
    {
        "source_id": "presentation_skills",
        "label": "presentation skills",
        "alts": ["presentation", "presenting", "present to stakeholders", "public speaking"],
        "desc": ("The ability to prepare and deliver clear, engaging presentations of technical "
                 "work and results to varied audiences."),
    },
    {
        "source_id": "self_motivation",
        "label": "self-motivation",
        "alts": ["self-motivated", "self-starter", "highly motivated", "proactive", "proactivity",
                 "autonomy", "ability to work independently"],
        "desc": ("The drive to take initiative and work productively and autonomously without close "
                 "supervision."),
    },
    {
        "source_id": "stress_management",
        "label": "stress management",
        "alts": ["work under pressure", "cope with stress", "manage pressure", "resilience",
                 "composure"],
        "desc": ("The ability to stay calm, focused and effective under pressure, tight deadlines "
                 "and incident situations."),
    },
    {
        "source_id": "positive_attitude",
        "label": "positive attitude",
        "alts": ["positive", "enthusiasm", "enthusiastic", "optimism", "can-do attitude"],
        "desc": ("A constructive, optimistic and enthusiastic approach to work and challenges."),
    },
    {
        "source_id": "integrity",
        "label": "integrity",
        "alts": ["honesty", "trustworthiness", "ethics", "demonstrate trustworthiness"],
        "desc": ("Adherence to strong moral and ethical principles — honesty, trustworthiness and "
                 "consistency between values and actions."),
    },
    {
        "source_id": "organization",
        "label": "organization",
        "alts": ["organisation", "organized", "organised", "organizational skills",
                 "organisational skills", "planning"],
        "desc": ("The ability to structure work, information and resources systematically to keep "
                 "tasks and projects on track."),
    },
    {
        "source_id": "continuous_learning",
        "label": "continuous learning",
        "alts": ["willingness to learn", "eager to learn", "fast learner", "self-learning",
                 "demonstrate willingness to learn", "curiosity"],
        "desc": ("A commitment to continuously acquiring new skills, tools and knowledge to keep "
                 "pace with rapidly evolving technology."),
    },
]


class SoftSkillsSource(StructuredSource):
    name = C.SRC_SOFTSKILLS
    contributes_occupations = False
    needs_attach = False
    builtin = True
    screen_relevance = False  
    version = "curated-softskills-2026"
    retrieval_method = "soft_skill_curation"

    def skills(self):
        for s in SOFT_SKILLS:
            yield {
                "source_id": s["source_id"],
                "label_en": s["label"],
                "alt_en": s["alts"],
                "desc_en": s["desc"],
                "hard_soft": "soft",
                "method": "curated_soft_skill",
                "it_subtype": "soft_transversal",
            }
