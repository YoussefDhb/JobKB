"""Neutral skill hierarchy — a source-equal, data-oriented skill ontology.

Every skill from every source (ESCO/ONET/ROME) is classified into a **type**
(Hard / Soft) and an **IT sub-domain** (programming, data, networks, security, cloud,
web, AI/ML, systems, IT management, methodology, ...), and placed in one shared tree:

    skill -> sub-domain -> type

This replaces the previous ESCO-only skill-group hierarchy (which left all ONET/ROME
skills flat). The ESCO transversal collection is still added as the soft-skill
vocabulary. Type/sub-domain nodes are stored as `TAXONOMY` skill rows so the graph is
self-contained; edges are tagged `SKILL_ONTO`.
"""

from __future__ import annotations
import os
import re
from collections import defaultdict

from . import config as C
from . import common as K

TRANSVERSAL = os.path.join(C.ESCO_EN_DIR, "transversalSkillsCollection_en.csv")
EDGE_SRC = "SKILL_ONTO"
TAXO_SRC = "TAXONOMY"

# Top-level types and IT sub-domains (sub-domain -> (type, display label)).
TYPES = {"hard": "Hard skill", "soft": "Soft skill"}
SUBDOMAINS = {
    "security": ("hard", "Security & cybersecurity"),
    "ai_ml": ("hard", "AI & machine learning"),
    "data_databases": ("hard", "Data & databases"),
    "cloud_devops": ("hard", "Cloud & DevOps"),
    "web": ("hard", "Web development"),
    "networks": ("hard", "Networks & telecom"),
    "programming_languages": ("hard", "Programming & software development"),
    "systems_infrastructure": ("hard", "Systems & infrastructure"),
    "it_management": ("hard", "IT management & governance"),
    "methodology": ("hard", "Methodologies & practices"),
    "knowledge_general": ("hard", "General IT knowledge"),
    "other_hard": ("hard", "Other technical"),
    "soft_transversal": ("soft", "Soft & transversal"),
}


def _rx(p):
    return re.compile(p)


# Ordered rules (checked on the accent-folded, lower-cased label). First match wins.
_RULES = [
    ("security", _rx(r"\b(secur|cyber|crypto|encryption|penetration|pentest|vulnerab|"
                     r"firewall|malware|forensic|rgpd|gdpr|iso 27|siem|owasp)")),
    ("ai_ml", _rx(r"(machine learning|deep learning|neural network|artificial intelligence|"
                  r"apprentissage automatique|intelligence artificielle|\bnlp\b|computer vision|"
                  r"tensorflow|pytorch|data science|datascience|data mining)")),
    ("data_databases", _rx(r"(database|data warehouse|base de donnee|\bsql\b|nosql|\betl\b|"
                           r"big data|bigdata|hadoop|spark|analytics|donnee|business intelligence|"
                           r"\bbdd\b|datastage|oracle|mongodb|postgres)")),
    ("cloud_devops", _rx(r"(\bcloud\b|\baws\b|azure|\bgcp\b|docker|kubernetes|devops|ci/cd|"
                         r"jenkins|terraform|ansible|conteneur|serverless|microservice)")),
    ("web", _rx(r"(\bweb\b|html|\bcss\b|javascript|typescript|react|angular|\bvue\b|node\.?js|"
                r"django|flask|\bphp\b|frontend|backend|front-end|back-end|\bcms\b|drupal|wordpress)")),
    ("networks", _rx(r"(network|reseau|telecom|routing|\btcp\b|\blan\b|\bwan\b|cisco|\bvoip\b|"
                     r"fibre|switch|\bdns\b|protocol)")),
    ("programming_languages", _rx(r"\b(python|java|c\+\+|c#|\.net|ruby|perl|golang|rust|kotlin|"
                                  r"swift|scala|matlab|bash|powershell|programming language|"
                                  r"langage de programmation|programmation|algorithm|coding|"
                                  r"software|logiciel|application|applicati|develop|api\b|sdk|"
                                  r"framework|compil|debug|version control|\bgit\b)")),
    ("systems_infrastructure", _rx(r"(operating system|\blinux\b|unix|windows server|"
                                   r"systeme d exploitation|\bserver\b|serveur|virtualiz|"
                                   r"infrastructure|storage|stockage|backup|sauvegarde|"
                                   r"datacenter|data center|hardware|materiel)")),
    ("it_management", _rx(r"(project management|gestion de projet|governance|gouvernance|\bitil\b|"
                          r"it service|strateg|budget|risk management|gestion des risques|"
                          r"portfolio|business analysis|compliance)")),
    ("methodology", _rx(r"(\bagile\b|scrum|kanban|\blean\b|devsecops|methodolog|methode|\buml\b|"
                        r"design pattern|test driven|\btdd\b)")),
]


def classify_subdomain(text, hard_soft, esco_type):
    if hard_soft == "soft":
        return "soft_transversal"
    t = " " + K.normalize_label(text) + " "
    for sub, rx in _RULES:
        if rx.search(t):
            return sub
    if (esco_type or "") == "knowledge":
        return "knowledge_general"
    return "other_hard"


def _add_transversal(esco, esco_ids, label_rows):
    """Add the ESCO transversal collection as soft skills (the soft vocabulary)."""
    if not os.path.isfile(TRANSVERSAL):
        return 0
    tdf = K.read_csv_smart(TRANSVERSAL)
    transv_ids = {K.uri_tail((r.get("conceptUri") or "").strip()) for _, r in tdf.iterrows()}
    for r in esco:
        if r["source_id"] in transv_ids:
            r["hard_soft_provisional"] = "soft"
            r["hard_soft_method"] = "esco_transversal_collection"
    added = 0
    for _, r in tdf.iterrows():
        tail = K.uri_tail((r.get("conceptUri") or "").strip())
        if not tail or tail in esco_ids:
            continue
        eid = K.mint_id("SKL_", C.SRC_ESCO, tail)
        pref = (r.get("preferredLabel") or "").strip()
        alts = K.split_multi(r.get("altLabels", ""))
        esco.append({
            "entity_id": eid, "source": C.SRC_ESCO, "source_id": tail,
            "pref_label_en": pref, "pref_label_fr": "",
            "alt_labels_en": " | ".join(alts), "alt_labels_fr": "",
            "description_en": (r.get("description") or "").strip(), "description_fr": "",
            "esco_skill_type": (r.get("skillType") or "").strip(),
            "esco_reuse_level": (r.get("reuseLevel") or "transversal").strip(),
            "hard_soft_provisional": "soft", "hard_soft_method": "esco_transversal_collection",
            "it_subtype": "",
        })
        esco_ids.add(tail)
        label_rows.extend(K.make_label_rows(eid, "skill", C.SRC_ESCO,
                                            preferred={"en": [pref]}, alts={"en": alts}))
        added += 1
    return added


def _taxonomy_nodes():
    """Return (rows, type_id, domain_id) — the ontology nodes as TAXONOMY skill rows."""
    rows, type_id, domain_id = [], {}, {}

    def _row(prefix, sid, label, hard_soft, marker):
        eid = K.mint_id(prefix, TAXO_SRC, sid)
        rows.append({
            "entity_id": eid, "source": TAXO_SRC, "source_id": sid,
            "pref_label_en": label, "pref_label_fr": "",
            "alt_labels_en": "", "alt_labels_fr": "",
            "description_en": "", "description_fr": "",
            "esco_skill_type": marker, "esco_reuse_level": "",
            "hard_soft_provisional": hard_soft, "hard_soft_method": "ontology",
            "it_subtype": marker.replace("skill_", ""),
        })
        return eid

    for tkey, label in TYPES.items():
        type_id[tkey] = _row("SKT_", f"type:{tkey}", label, tkey, "skill_type")
    for skey, (tkey, label) in SUBDOMAINS.items():
        domain_id[skey] = _row("SKD_", f"domain:{skey}", label, tkey, "skill_domain")
    return rows, type_id, domain_id


def run():
    all_skills = [r for r in K.read_all(C.SKILLS_CSV)
                  if r.get("esco_skill_type") not in ("skill_type", "skill_domain")]
    esco = [r for r in all_skills if r["source"] == C.SRC_ESCO]
    others = [r for r in all_skills if r["source"] != C.SRC_ESCO]
    esco_ids = {r["source_id"] for r in esco}

    label_rows = []
    n_soft_added = _add_transversal(esco, esco_ids, label_rows)

    taxo_rows, type_id, domain_id = _taxonomy_nodes()

    # Classify every skill and wire skill -> sub-domain edges.
    hier_edges = []
    for r in esco + others:
        text = r.get("pref_label_en") or r.get("pref_label_fr") or ""
        sub = classify_subdomain(text, r.get("hard_soft_provisional"), r.get("esco_skill_type"))
        r["it_subtype"] = sub
        hier_edges.append({
            "parent_entity_id": domain_id[sub], "child_entity_id": r["entity_id"],
            "entity_kind": "skill", "relation_type": "broader_than", "source": EDGE_SRC,
        })
    # sub-domain -> type edges.
    for skey, (tkey, _lbl) in SUBDOMAINS.items():
        hier_edges.append({
            "parent_entity_id": type_id[tkey], "child_entity_id": domain_id[skey],
            "entity_kind": "skill", "relation_type": "broader_than", "source": EDGE_SRC,
        })

    # Write back: ESCO skills (incl. added transversal), other sources, taxonomy nodes.
    K.replace_source_rows(C.SKILLS_CSV, C.SKILL_FIELDS, C.SRC_ESCO, esco)
    by_source = defaultdict(list)
    for r in others:
        by_source[r["source"]].append(r)
    for src, rows in by_source.items():
        K.replace_source_rows(C.SKILLS_CSV, C.SKILL_FIELDS, src, rows)
    K.replace_source_rows(C.SKILLS_CSV, C.SKILL_FIELDS, TAXO_SRC, taxo_rows)
    K.replace_source_rows(C.HIERARCHY_CSV, C.HIERARCHY_FIELDS, EDGE_SRC, hier_edges)
    K.upsert_labels(label_rows)

    n_soft = sum(1 for r in esco + others if r["hard_soft_provisional"] == "soft")
    K.log_provenance(EDGE_SRC, [{
        "entity_id": EDGE_SRC, "source": EDGE_SRC, "source_version": "-",
        "retrieved_at": K.now_iso(), "retrieval_method": "neutral_skill_ontology",
        "notes": f"{len(esco)+len(others)} skills classified, {n_soft} soft, "
                 f"{len(SUBDOMAINS)} sub-domains, {len(hier_edges)} edges",
    }])
    print(f"[HIER] classified {len(esco)+len(others)} skills into {len(SUBDOMAINS)} "
          f"sub-domains ({n_soft} soft, +{n_soft_added} transversal); {len(hier_edges)} edges.")
