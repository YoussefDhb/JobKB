"""SOFTTAXO: a curated IT soft-skills taxonomy filling gaps ESCO/SOFTSKILLS/WEF leave."""
from __future__ import annotations

from .. import common as K
from .. import config as C
from .base import StructuredSource
from . import evidence


# Each: source_id, label, subdomain, core, alts, desc.
SOFT_TAXONOMY = [
    # ---- soft_cognitive ---------------------------------------------------------------------------
    {"source_id": "critical_thinking", "label": "critical thinking", "subdomain": "soft_cognitive",
     "core": True, "alts": ["think critically", "critical analysis", "evaluate arguments critically",
                            "critically evaluate information"],
     "desc": ("The ability to objectively analyse facts, evidence and assumptions to form a reasoned "
              "judgement, questioning claims rather than accepting them at face value.")},
    {"source_id": "systems_thinking", "label": "systems thinking", "subdomain": "soft_cognitive",
     "core": True, "alts": ["think in systems", "holistic thinking", "systems-level thinking"],
     "desc": ("The ability to understand how components of a system interrelate and influence one "
              "another, reasoning about the whole rather than isolated parts — key to architecture and "
              "debugging complex systems.")},
    {"source_id": "logical_reasoning", "label": "logical reasoning", "subdomain": "soft_cognitive",
     "core": False, "alts": ["logical thinking", "reason logically", "structured reasoning"],
     "desc": ("The ability to reason step by step from premises to sound conclusions, essential for "
              "algorithm design, debugging and formal problem solving.")},
    {"source_id": "root_cause_analysis", "label": "root cause analysis", "subdomain": "soft_cognitive",
     "core": False, "alts": ["root-cause analysis", "identify root causes", "diagnose root causes"],
     "desc": ("The disciplined practice of tracing a problem or incident back to its underlying cause "
              "rather than treating symptoms — central to troubleshooting and incident response.")},
    {"source_id": "design_thinking", "label": "design thinking", "subdomain": "soft_cognitive",
     "core": False, "alts": ["human-centred design", "design-thinking approach", "user-centred design"],
     "desc": ("A human-centred, iterative approach to problem solving that empathises with users, frames "
              "problems, ideates and prototypes solutions.")},
    {"source_id": "research_skills", "label": "research skills", "subdomain": "soft_cognitive",
     "core": False, "alts": ["technical research", "information gathering", "conduct research"],
     "desc": ("The ability to systematically investigate, gather and synthesise information — evaluating "
              "documentation, prior art and options before building.")},
    {"source_id": "data_driven_decision_making", "label": "data-driven decision making",
     "subdomain": "soft_cognitive", "core": True,
     "alts": ["data-driven thinking", "evidence-based decision making", "use data to decide"],
     "desc": ("Basing decisions on measured evidence, metrics and experimentation rather than intuition "
              "alone — a core habit in modern engineering and product work.")},
    {"source_id": "business_acumen", "label": "business acumen", "subdomain": "soft_cognitive",
     "core": True, "alts": ["commercial awareness", "business understanding", "business sense"],
     "desc": ("Understanding how technology decisions create business value — connecting engineering "
              "work to cost, revenue, risk and customer outcomes.")},
    {"source_id": "product_thinking", "label": "product thinking", "subdomain": "soft_cognitive",
     "core": False, "alts": ["product mindset", "product-oriented thinking", "user-value focus"],
     "desc": ("Framing technical work in terms of the user value and product outcomes it delivers, not "
              "just the implementation.")},
    {"source_id": "strategic_thinking", "label": "strategic thinking", "subdomain": "soft_cognitive",
     "core": False, "alts": ["strategic mindset", "think strategically", "big-picture thinking"],
     "desc": ("The ability to see the bigger picture and long-term implications, aligning day-to-day "
              "technical choices with broader goals.")},
    {"source_id": "estimation", "label": "estimation", "subdomain": "soft_cognitive",
     "core": False, "alts": ["effort estimation", "work estimation", "estimate tasks"],
     "desc": ("The ability to reason about the effort, time and uncertainty of tasks and produce useful "
              "estimates for planning — a chronic challenge in software delivery.")},

    # ---- soft_collaboration -----------------------------------------------------------------------
    {"source_id": "active_listening", "label": "active listening", "subdomain": "soft_collaboration",
     "core": True, "alts": ["listen actively", "attentive listening", "listen and clarify"],
     "desc": ("Fully concentrating on, understanding and responding to what others say — confirming "
              "understanding before reacting, essential for requirements and teamwork.")},
    {"source_id": "technical_communication", "label": "technical communication",
     "subdomain": "soft_collaboration", "core": True,
     "alts": ["communicate technical concepts", "explain technical topics",
              "translate technical to non-technical"],
     "desc": ("The ability to explain complex technical concepts clearly to both technical and "
              "non-technical audiences, adapting depth and language to the listener.")},
    {"source_id": "written_communication", "label": "written communication",
     "subdomain": "soft_collaboration", "core": False,
     "alts": ["writing skills", "clear writing", "business writing"],
     "desc": ("The ability to convey information clearly and concisely in writing — issues, proposals, "
              "chat and asynchronous updates that distributed teams rely on.")},
    {"source_id": "cross_functional_collaboration", "label": "cross-functional collaboration",
     "subdomain": "soft_collaboration", "core": True,
     "alts": ["work across teams", "cross-team collaboration", "interdisciplinary collaboration"],
     "desc": ("Working effectively with people from different functions (product, design, data, ops, "
              "business) toward a shared outcome.")},
    {"source_id": "remote_collaboration", "label": "remote collaboration",
     "subdomain": "soft_collaboration", "core": False,
     "alts": ["distributed teamwork", "asynchronous collaboration", "virtual teamwork"],
     "desc": ("Collaborating productively in distributed and asynchronous settings — clear written "
              "updates, documentation and considerate communication across time zones.")},
    {"source_id": "cross_cultural_competence", "label": "cross-cultural competence",
     "subdomain": "soft_collaboration", "core": False,
     "alts": ["intercultural competence", "cultural awareness", "work across cultures"],
     "desc": ("The ability to work respectfully and effectively with people from diverse cultural and "
              "linguistic backgrounds, common in global IT teams.")},
    {"source_id": "customer_orientation", "label": "customer orientation",
     "subdomain": "soft_collaboration", "core": True,
     "alts": ["customer focus", "client focus", "customer-centricity", "service orientation"],
     "desc": ("Keeping the needs and experience of the end user or client at the centre of technical "
              "decisions and delivery.")},
    {"source_id": "stakeholder_management", "label": "stakeholder management",
     "subdomain": "soft_collaboration", "core": True,
     "alts": ["manage stakeholders", "stakeholder engagement", "stakeholder communication"],
     "desc": ("Identifying, engaging and aligning the people affected by or invested in a technical "
              "initiative, managing expectations and communication.")},
    {"source_id": "knowledge_sharing", "label": "knowledge sharing", "subdomain": "soft_collaboration",
     "core": False, "alts": ["share knowledge", "knowledge transfer", "share expertise"],
     "desc": ("Proactively sharing information, expertise and lessons learned with the team, reducing "
              "bus-factor and raising collective capability.")},
    {"source_id": "technical_writing", "label": "technical writing", "subdomain": "soft_collaboration",
     "core": False, "alts": ["documentation writing", "write documentation", "technical documentation"],
     "desc": ("Producing clear, accurate documentation — READMEs, design docs, runbooks and API docs — "
              "that others can act on.")},
    {"source_id": "code_review_etiquette", "label": "code review etiquette",
     "subdomain": "soft_collaboration", "core": False,
     "alts": ["constructive code review", "giving code feedback", "respectful code review"],
     "desc": ("Reviewing others' code constructively and receiving reviews gracefully — focusing on the "
              "work, being specific and kind, and keeping the team moving.")},
    {"source_id": "facilitation", "label": "facilitation", "subdomain": "soft_collaboration",
     "core": False, "alts": ["facilitate meetings", "workshop facilitation", "facilitate discussions"],
     "desc": ("Guiding a group through a discussion or workshop so it reaches a productive outcome, "
              "keeping it focused, inclusive and time-boxed.")},
    {"source_id": "storytelling", "label": "storytelling", "subdomain": "soft_collaboration",
     "core": False, "alts": ["data storytelling", "narrative communication", "storytelling with data"],
     "desc": ("Framing information and results as a clear, compelling narrative so an audience "
              "understands, remembers and acts on it.")},
    {"source_id": "diplomacy", "label": "diplomacy", "subdomain": "soft_collaboration",
     "core": False, "alts": ["tactfulness", "tact", "political awareness"],
     "desc": ("Handling sensitive situations and differing interests with tact and discretion, "
              "preserving relationships while moving work forward.")},

    # ---- soft_leadership --------------------------------------------------------------------------
    {"source_id": "technical_leadership", "label": "technical leadership", "subdomain": "soft_leadership",
     "core": True, "alts": ["tech lead skills", "lead technically", "technical direction"],
     "desc": ("Guiding a team's technical direction and decisions, setting standards and unblocking "
              "others — leadership grounded in engineering judgement rather than formal authority.")},
    {"source_id": "delegation", "label": "delegation", "subdomain": "soft_leadership",
     "core": False, "alts": ["delegate tasks", "delegate responsibilities", "distribute work"],
     "desc": ("Assigning tasks and authority to the right people and trusting them to deliver, freeing "
              "oneself for higher-leverage work and growing the team.")},
    {"source_id": "influence", "label": "influence", "subdomain": "soft_leadership",
     "core": False, "alts": ["influencing", "influence without authority", "build buy-in"],
     "desc": ("Persuading and aligning others toward a direction or decision without relying on formal "
              "authority — through reasoning, credibility and relationships.")},
    {"source_id": "change_management", "label": "change management", "subdomain": "soft_leadership",
     "core": False, "alts": ["manage change", "lead change", "change leadership"],
     "desc": ("Guiding people and teams through change — new tools, processes or architectures — "
              "addressing resistance and easing adoption.")},
    {"source_id": "ownership", "label": "ownership", "subdomain": "soft_leadership",
     "core": True, "alts": ["taking ownership", "end-to-end ownership", "take ownership"],
     "desc": ("Taking end-to-end responsibility for outcomes — not just one's assigned task — following "
              "problems through to resolution and caring about the result.")},
    {"source_id": "team_building", "label": "team building", "subdomain": "soft_leadership",
     "core": False, "alts": ["build teams", "foster team cohesion", "team development"],
     "desc": ("Fostering trust, cohesion and psychological safety within a team so it collaborates and "
              "performs well.")},
    {"source_id": "servant_leadership", "label": "servant leadership", "subdomain": "soft_leadership",
     "core": False, "alts": ["servant-leader", "supportive leadership", "enabling leadership"],
     "desc": ("A leadership style that prioritises removing obstacles and supporting the growth and "
              "effectiveness of the team over personal authority — common in agile teams.")},
    {"source_id": "vision_setting", "label": "vision setting", "subdomain": "soft_leadership",
     "core": False, "alts": ["set vision", "articulate vision", "provide direction"],
     "desc": ("Articulating a clear, motivating direction and purpose that aligns and energises a team "
              "around shared goals.")},

    # ---- soft_self_management ---------------------------------------------------------------------
    {"source_id": "resilience", "label": "resilience", "subdomain": "soft_self_management",
     "core": True, "alts": ["professional resilience", "bounce back", "emotional resilience"],
     "desc": ("The capacity to recover quickly from setbacks, failures and pressure — incidents, "
              "outages, rejected work — and keep performing constructively.")},
    {"source_id": "self_discipline", "label": "self-discipline", "subdomain": "soft_self_management",
     "core": False, "alts": ["discipline", "disciplined work", "self-regulation"],
     "desc": ("The ability to stay focused and consistent on important work, resisting distraction and "
              "maintaining good practices without external pressure.")},
    {"source_id": "dependability", "label": "dependability", "subdomain": "soft_self_management",
     "core": False, "alts": ["dependable", "reliable delivery", "follow through"],
     "desc": ("Being consistently reliable — doing what one commits to, on time and to standard, so the "
              "team can count on it.")},
    {"source_id": "dealing_with_ambiguity", "label": "dealing with ambiguity",
     "subdomain": "soft_self_management", "core": False,
     "alts": ["tolerate ambiguity", "comfort with uncertainty", "navigate ambiguity"],
     "desc": ("Staying effective and making progress when requirements, priorities or information are "
              "incomplete or shifting — a constant in fast-moving technology work.")},
    {"source_id": "patience", "label": "patience", "subdomain": "soft_self_management",
     "core": False, "alts": ["patient", "composure", "even-temperedness"],
     "desc": ("Remaining calm and steady through slow progress, repetition or difficult debugging and "
              "support situations.")},
    {"source_id": "goal_orientation", "label": "goal orientation", "subdomain": "soft_self_management",
     "core": False, "alts": ["goal-setting", "results orientation", "outcome focus"],
     "desc": ("Setting clear goals and staying focused on delivering measurable outcomes and results.")},

    # ---- soft_learning ----------------------------------------------------------------------------
    {"source_id": "self_directed_learning", "label": "self-directed learning",
     "subdomain": "soft_learning", "core": True,
     "alts": ["self-learning", "learn independently", "autodidactic learning"],
     "desc": ("Taking initiative to identify learning needs and acquire new skills and knowledge "
              "independently — indispensable in a field that changes constantly.")},
    {"source_id": "learning_agility", "label": "learning agility", "subdomain": "soft_learning",
     "core": True, "alts": ["agile learning", "quick to learn", "adapt and learn"],
     "desc": ("The ability to learn quickly from experience and apply lessons to new, unfamiliar "
              "situations — picking up new languages, tools and domains rapidly.")},
    {"source_id": "staying_current_with_technology", "label": "staying current with technology",
     "subdomain": "soft_learning", "core": True,
     "alts": ["keep up with technology", "tech trend awareness", "continuous upskilling",
              "stay up to date"],
     "desc": ("Actively following and evaluating new tools, languages and practices to keep skills "
              "relevant as the technology landscape evolves.")},
    {"source_id": "experimentation", "label": "experimentation", "subdomain": "soft_learning",
     "core": False, "alts": ["experimental mindset", "willingness to experiment", "prototyping mindset"],
     "desc": ("A willingness to try, prototype and test ideas, learning from what works and what fails "
              "rather than seeking certainty first.")},
    {"source_id": "openness_to_feedback", "label": "openness to feedback", "subdomain": "soft_learning",
     "core": False, "alts": ["receptive to feedback", "coachability", "act on feedback"],
     "desc": ("Actively seeking, welcoming and acting on feedback — treating criticism as information "
              "for growth rather than a threat.")},
    {"source_id": "reflective_practice", "label": "reflective practice", "subdomain": "soft_learning",
     "core": False, "alts": ["self-reflection", "retrospective mindset", "reflective learning"],
     "desc": ("Regularly reviewing one's own work and decisions — retrospectives, post-mortems — to "
              "extract lessons and continuously improve.")},

    # ---- soft_transversal (cross-cutting professional attitudes) ----------------------------------
    {"source_id": "ethical_judgment", "label": "ethical judgment", "subdomain": "soft_transversal",
     "core": False, "alts": ["professional ethics", "ethical decision making", "ethical awareness"],
     "desc": ("Recognising the ethical dimensions of technical work — privacy, security, bias, "
              "sustainability — and making responsible choices.")},
    {"source_id": "customer_empathy", "label": "customer empathy", "subdomain": "soft_transversal",
     "core": False, "alts": ["user empathy", "empathise with users", "understand user needs"],
     "desc": ("Genuinely understanding the needs, frustrations and context of the people who use what "
              "one builds, and letting that guide the work.")},
]


class SoftTaxonomySource(StructuredSource):
    name = C.SRC_SOFTTAXO
    contributes_occupations = False
    needs_attach = False
    builtin = True
    screen_relevance = False   
    version = "curated-soft-taxonomy-2026"
    retrieval_method = "soft_skill_taxonomy_curation"

    def _surviving(self):
        """The curated entries that are genuinely new (their normalized label does not already name an
        existing skill from any OTHER source). Cached so `skills()` and `ingest()` agree."""
        if getattr(self, "_cache", None) is None:
            existing = set()
            for r in K.read_all(C.SKILLS_CSV):
                if r.get("source") == self.name:
                    continue                       
                for field in ("pref_label_en", "pref_label_fr", "alt_labels_en", "alt_labels_fr"):
                    for lbl in (r.get(field) or "").split(" | "):
                        k = evidence.match_key(lbl)
                        if k:
                            existing.add(k)
            kept, skipped = [], []
            for e in SOFT_TAXONOMY:
                if evidence.match_key(e["label"]) in existing:
                    skipped.append(e["label"])
                else:
                    kept.append(e)
            self._cache = kept
            if skipped:
                print(f"[{self.name}] dedup: {len(skipped)} already-covered terms skipped "
                      f"(e.g. {', '.join(skipped[:5])})", flush=True)
        return self._cache

    def skills(self):
        for e in self._surviving():
            yield {
                "source_id": e["source_id"],
                "label_en": e["label"],
                "alt_en": e["alts"],
                "desc_en": e["desc"],
                "hard_soft": "soft",
                "method": "curated_soft_taxonomy",
                "it_subtype": e["subdomain"],     
            }

    def ingest(self) -> None:
        super().ingest()   

        # Universal transversal attach
        core_ids = [K.mint_id("SKL_", self.name, e["source_id"])
                    for e in self._surviving() if e["core"]]
        occ_ids = [r["entity_id"] for r in K.read_all(C.OCCUPATIONS_CSV)
                   if r.get("occupation_type") != "isco_group"]
        rel_rows = [evidence.relation_row(o, sid, self.name, weight="", relation_type="transversal")
                    for o in occ_ids for sid in core_ids]
        evidence.write_relations(self.name, rel_rows)
        print(f"[{self.name}] transversal attach: {len(core_ids)} universal soft skills × "
              f"{len(occ_ids)} occupations = {len(rel_rows)} edges.", flush=True)
