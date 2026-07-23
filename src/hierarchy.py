"""Neutral skill + occupation taxonomy — a source-equal, faceted, graph-oriented ontology.

Two connected structures share one **functional-domain** vocabulary:

  * **Skills** — every skill from every source is placed in a 4-level tree
        skill -> category -> domain -> type   (type = Hard / Soft)
    22 fine **categories** roll up into 10 broad **domains**, which roll up into 2 **types**.
  * **Occupations** — the authoritative ISCO-08 backbone (occupation -> unit -> minor -> sub-major ->
    ICT root, built in `ingest/isco.py`) is enriched with a **functional-domain facet**: each real
    occupation is also linked (`in_domain`) to one of the SAME 10 domain nodes, so the graph is
    navigable end-to-end: `occupation <-> domain <-> category <-> skill`.

Type/domain/category nodes are stored as `TAXONOMY` skill rows (markers in `esco_skill_type`, see
`config.TAXONOMY_SKILL_MARKERS`) so the graph is self-contained; skill-ontology edges are tagged
`SKILL_ONTO`, the occupation facet `DOMAIN_FACET`. The ESCO transversal collection is still added as the
soft-skill vocabulary.
"""

from __future__ import annotations
import os
import re
from collections import defaultdict

from . import config as C
from . import common as K

TRANSVERSAL = os.path.join(C.ESCO_EN_DIR, "transversalSkillsCollection_en.csv")
EDGE_SRC = "SKILL_ONTO"
FACET_SRC = "DOMAIN_FACET"
TAXO_SRC = "TAXONOMY"

# --- the three taxonomy tiers ---------------------------------------------------------------------
TYPES = {"hard": "Technical skills", "soft": "Soft & transversal skills"}

# domain key -> (type, display label). 9 hard IT domains + 1 soft family; shared by skills+occupations.
DOMAINS = {
    "dom_software":      ("hard", "Software Development"),
    "dom_web_mobile":    ("hard", "Web & Mobile Development"),
    "dom_data_ai":       ("hard", "Data, Analytics & AI"),
    "dom_infra_cloud":   ("hard", "Infrastructure, Systems & Cloud"),
    "dom_networks":      ("hard", "Networks & Telecommunications"),
    "dom_security":      ("hard", "Cybersecurity"),
    "dom_it_mgmt":       ("hard", "IT Management, Governance & Support"),
    "dom_emerging":      ("hard", "Emerging Technologies"),
    "dom_cross":         ("hard", "General & Cross-cutting IT"),
    "dom_soft":          ("soft", "Soft & Transversal Skills"),
}

# category key -> (domain, display label). The 19 legacy keys (unchanged, so the self-classified source
# maps keep working) + 3 new fine categories (mobile_development, data_engineering, hardware_embedded).
CATEGORIES = {
    "programming_languages":  ("dom_software", "Programming & software development"),
    "methodology":            ("dom_software", "Methodologies & practices"),
    "web":                    ("dom_web_mobile", "Web development"),
    "mobile_development":     ("dom_web_mobile", "Mobile development"),
    "data_databases":         ("dom_data_ai", "Databases & data management"),
    "data_engineering":       ("dom_data_ai", "Big data & data engineering"),
    "ai_ml":                  ("dom_data_ai", "AI & machine learning"),
    "systems_infrastructure": ("dom_infra_cloud", "Systems & infrastructure"),
    "cloud_devops":           ("dom_infra_cloud", "Cloud & DevOps"),
    "hardware_embedded":      ("dom_infra_cloud", "Hardware & embedded systems"),
    "networks":               ("dom_networks", "Networks & telecom"),
    "security":               ("dom_security", "Security & cybersecurity"),
    "it_management":          ("dom_it_mgmt", "IT management & governance"),
    "emerging_tech":          ("dom_emerging", "Emerging tech (IoT, AR/VR, blockchain)"),
    "knowledge_general":      ("dom_cross", "General IT knowledge"),
    "other_hard":             ("dom_cross", "Other technical"),
    "soft_cognitive":         ("dom_soft", "Cognitive: creativity & problem-solving"),
    "soft_self_management":   ("dom_soft", "Self-management, resilience & dependability"),
    "soft_collaboration":     ("dom_soft", "Communication & collaboration"),
    "soft_leadership":        ("dom_soft", "Leadership & social influence"),
    "soft_learning":          ("dom_soft", "Curiosity & lifelong learning"),
    "soft_transversal":       ("dom_soft", "Soft & transversal (other)"),
}

# Back-compat alias: some sources/docs still say "sub-domain". A category IS the (fine) sub-domain.
SUBDOMAINS = CATEGORIES
SOFT_SUBDOMAINS = tuple(k for k, (d, _l) in CATEGORIES.items() if d == "dom_soft")


def _cat_type(cat):
    """The hard/soft type of a category (via its domain)."""
    return DOMAINS[CATEGORIES[cat][0]][0]


def skill_type(cat):
    """Authoritative hard/soft type for a skill from its category (a category belongs to one domain,
    and a domain is hard or soft). Returns "hard"/"soft", or "" if `cat` is not a known category — so
    a skill's `hard_soft` is a deterministic function of its taxonomy placement, never a separate
    (and possibly contradictory) guess. This is the single source of truth used by `merge`."""
    c = CATEGORIES.get(cat)
    return DOMAINS[c[0]][0] if c else ""


def _rx(p):
    return re.compile(p)


# High-precision FINE categories — applied FIRST to every hard skill (overriding even self-classified
# sources: these categories didn't exist when those maps were written). Kept tight to avoid false hits.
_FINE_RULES = [
    ("mobile_development", _rx(r"(\bandroid\b|\bios\b|ipados|kotlin|\bswiftui\b|\bswift\b|flutter|"
                              r"react native|xamarin|objective-?c|mobile app|mobile develop|"
                              r"mobile application|\bcordova\b|\bionic\b|jetpack compose|\bapk\b|"
                              r"play store|app store|application mobile)")),
    ("data_engineering", _rx(r"(apache spark|\bspark\b|hadoop|\bkafka\b|airflow|\betl\b|\belt\b|"
                             r"data pipeline|data warehouse|data lake|databricks|big data|bigdata|"
                             r"\bhive\b|\bflink\b|snowflake|redshift|\bdbt\b|data engineering|"
                             r"data ingestion|stream processing|entrepot de donnee|kinesis|\bflume\b|"
                             r"\bsqoop\b|\bnifi\b|apache beam|informatica)")),
    ("hardware_embedded", _rx(r"(embedded system|systeme embarque|\bfirmware\b|microcontroller|"
                              r"micro-controller|\bfpga\b|\bplc\b|integrated circuit|circuit board|"
                              r"electronic circuit|\belectronics\b|computer hardware|\bhardware\b|"
                              r"\bsensor\b|arduino|raspberry|semiconductor|soldering|robotic|\brtos\b|"
                              r"\bvhdl\b|verilog|\bcan bus\b|mechatronic|materiel informatique)")),
]

# Ordered coarse rules (checked on the accent-folded, lower-cased label). First match wins.
_RULES = [
    ("security", _rx(r"\b(secur|cyber|crypto|encryption|penetration|pentest|vulnerab|"
                     r"firewall|malware|forensic|rgpd|gdpr|iso 27|siem|owasp|wireshark|"
                     r"authentication|\biam\b|identity management|\bnmap\b|intrusion detection|"
                     r"\bids\b|\bips\b|identity and access|acces et.*identite)")),
    ("ai_ml", _rx(r"(machine learning|deep learning|neural network|artificial intelligence|"
                  r"apprentissage automatique|intelligence artificielle|\bnlp\b|computer vision|"
                  r"tensorflow|pytorch|data science|datascience|data mining|image recognition|"
                  r"evolutionary algorithm|generative ai|\bllm\b|reinforcement learning)")),
    ("emerging_tech", _rx(r"(internet of things|\biot\b|augmented reality|virtual reality|"
                          r"\bar/vr\b|\bvr\b headset|blockchain|distributed ledger|smart contract|"
                          r"quantum comput|metaverse|wearable|\bnft\b|tokeniz)")),
    ("data_databases", _rx(r"(database|data warehouse|base de donnee|\bsql\b|nosql|analytics|"
                           r"donnee|business intelligence|\bbdd\b|\bbi\b|datastage|oracle|mongodb|"
                           r"postgres|mysql|mariadb|\bdb2\b|matplotlib|seaborn|plotly|ggplot|bokeh|"
                           r"data visuali|\btableau\b|power bi|data model|data governance|data quality|"
                           r"data reporting|decisionnel)")),
    ("cloud_devops", _rx(r"(\bcloud\b|\baws\b|azure|\bgcp\b|docker|kubernetes|devops|ci/cd|"
                         r"jenkins|terraform|ansible|conteneur|serverless|microservice|"
                         r"continuous integration|continuous deployment|helm\b|openshift)")),
    ("web", _rx(r"(\bweb\b|html|\bcss\b|\bsass\b|\bless\b|javascript|typescript|react|angular|\bvue\b|"
                r"node\.?js|django|flask|\bphp\b|frontend|backend|front-end|back-end|\bcms\b|drupal|"
                r"wordpress|webpack|bootstrap|jquery|rest api|graphql)")),
    ("networks", _rx(r"(network|reseau|telecom|routing|\btcp\b|\blan\b|\bwan\b|cisco|\bvoip\b|"
                     r"fibre|switch|\bdns\b|protocol|\bvpn\b|load balanc|\bsd-wan\b|broadcast)")),
    ("programming_languages", _rx(r"\b(python|java|c\+\+|c#|\.net|ruby|perl|golang|rust|kotlin|"
                                  r"swift|scala|matlab|bash|powershell|pascal|\bvyper\b|solidity|"
                                  r"programming language|langage de programmation|programmation|"
                                  r"algorithm|coding|software|logiciel|application|applicati|develop|"
                                  r"api\b|sdk|framework|compil|debug|version control|\bgit\b|"
                                  r"object-oriented|functional programming|design pattern|"
                                  r"integrated development|\bide\b|\bscript\b|versioning|"
                                  r"typescript|node\.?js)")),
    ("systems_infrastructure", _rx(r"(operating system|\blinux\b|unix|windows server|"
                                   r"systeme d exploitation|\bserver\b|serveur|virtualiz|virtual machine|"
                                   r"hypervisor|vmware|citrix|infrastructure|storage|stockage|backup|"
                                   r"sauvegarde|datacenter|data center|active directory|sharepoint|"
                                   r"terminal service|remote desktop|middleware|mainframe|\bsan\b|\bnas\b|"
                                   r"disaster recovery|reprise.*sinistre|recovery system|systeme "
                                   r"informatique|informatique industrielle|administration systeme)")),
    ("it_management", _rx(r"(project management|gestion de projet|governance|gouvernance|\bitil\b|"
                          r"it service|service desk|help desk|helpdesk|user support|strateg|budget|"
                          r"risk management|gestion des risques|portfolio|business analysis|compliance|"
                          r"stakeholder|service management|gestion des incident|incident management|"
                          r"veille (technolog|reglementaire)|support technique|demarche qualite)")),
    ("methodology", _rx(r"(\bagile\b|scrum|kanban|\blean\b|devsecops|methodolog|methode|\buml\b|"
                        r"test driven|\btdd\b|\bbdd test\b|waterfall|\bsafe\b framework)")),
]

# Soft classifier — routes any soft skill into a WEF-aligned category. Ordered; first match wins.
_SOFT_RULES = [
    ("soft_leadership", _rx(r"(leader|lead others|lead a|manage a team|mentor|coach|teach|instruct|"
                            r"train|persuas|negotiat|influence|delegat|networking|liais|build.*trust|"
                            r"stakeholder|motivat.*(team|other))")),
    ("soft_collaboration", _rx(r"(team|collaborat|cooperat|communicat|\bempath|listen|feedback|"
                               r"interpersonal|co-?worker|colleague|service orient|customer|assist|"
                               r"support.*(other|co)|address an audience|moderate|consideration|"
                               r"relationship|social skill|work.*with.*people)")),
    ("soft_learning", _rx(r"(curiosit|lifelong|willing.*learn|eager to learn|open.?mind|"
                          r"self.?develop|upskill|continuous learning)")),
    ("soft_cognitive", _rx(r"(creativ|critical think|analytical|analyse|systems think|system thinking|"
                           r"problem.solv|problem solving|reasoning|innovat|ideation|conceptual|"
                           r"decision|judgement|judgment)")),
    ("soft_self_management", _rx(r"(self.?aware|self.?control|self.?regulat|initiative|independ|"
                                 r"motivat|responsib|accountab|commit|deadline|\btime\b|priorit|"
                                 r"attention to detail|\bdetail|quality|stress|frustrat|resilien|"
                                 r"adapt|flexib|agilit|persist|persever|conscientious|\bgrit\b|"
                                 r"mindset|reliab|dependab|determination|discipline|proactiv|organi[sz])")),
]


def _fine_category(text):
    """High-precision mobile/data-engineering/hardware category, or None."""
    t = " " + K.normalize_label(text) + " "
    for cat, rx in _FINE_RULES:
        if rx.search(t):
            return cat
    return None


def classify_subdomain(text, hard_soft, esco_type):
    """Classify a skill into one of the 22 categories (a.k.a. sub-domain)."""
    if hard_soft == "soft":
        t = " " + K.normalize_label(text) + " "
        for cat, rx in _SOFT_RULES:
            if rx.search(t):
                return cat
        return "soft_transversal"
    fine = _fine_category(text)
    if fine:
        return fine
    t = " " + K.normalize_label(text) + " "
    for cat, rx in _RULES:
        if rx.search(t):
            return cat
    if (esco_type or "") == "knowledge":
        return "knowledge_general"
    return "other_hard"


# --- occupation -> functional domain facet --------------------------------------------------------
# Ordered label-keyword rules (specific first), then an ISCO-code fallback, then dom_cross.
_OCC_DOMAIN_KEYWORDS = [
    (_rx(r"(data scien|machine learning|\bml\b|\bai\b|artificial intel|deep learning|data analyst|"
         r"data engineer|analytics|business intelligence|\bbi\b developer|data governance)"), "dom_data_ai"),
    (_rx(r"(database|\bdba\b)"), "dom_data_ai"),
    (_rx(r"(security|cyber|infosec|penetration|forensic)"), "dom_security"),
    (_rx(r"(network|telecom|\bvoip\b|broadcast|radio|audiovisual)"), "dom_networks"),
    (_rx(r"(mobile|android|\bios\b)"), "dom_web_mobile"),
    (_rx(r"(\bweb\b|front.?end|multimedia|\bui\b|\bux\b|user interface)"), "dom_web_mobile"),
    (_rx(r"(embedded|firmware|hardware)"), "dom_infra_cloud"),
    (_rx(r"(devops|\bcloud\b|site reliability|\bsre\b|system admin|systems admin|infrastructure|"
         r"operations tech)"), "dom_infra_cloud"),
    (_rx(r"(support|help desk|helpdesk|user support)"), "dom_it_mgmt"),
    (_rx(r"(manager|officer|governance|head of|director|scrum master|project manag|product manag|"
         r"business analyst)"), "dom_it_mgmt"),
    (_rx(r"(\btest\b|\bqa\b|quality assurance|tester)"), "dom_software"),
    (_rx(r"(game|games develop)"), "dom_software"),
    (_rx(r"(developer|programmer|software|systems analyst|analyst programmer)"), "dom_software"),
]
_OCC_DOMAIN_ISCO = {
    "2511": "dom_software", "2512": "dom_software", "2514": "dom_software", "2519": "dom_software",
    "2513": "dom_web_mobile", "3514": "dom_web_mobile",
    "2521": "dom_data_ai",
    "2522": "dom_infra_cloud", "3511": "dom_infra_cloud", "2529": "dom_infra_cloud",
    "2523": "dom_networks", "3513": "dom_networks", "3521": "dom_networks", "3522": "dom_networks",
    "133": "dom_it_mgmt", "1330": "dom_it_mgmt", "3512": "dom_it_mgmt",
    "25": "dom_software", "35": "dom_infra_cloud",
}


def _occupation_domain(occ):
    text = K.normalize_label(occ.get("pref_label_en") or occ.get("pref_label_fr")
                             or occ.get("alt_labels_en") or "")
    for rx, dom in _OCC_DOMAIN_KEYWORDS:
        if rx.search(text):
            return dom
    code = (occ.get("isco_code") or "").strip()
    for k in (code, code[:3], code[:2]):
        if k in _OCC_DOMAIN_ISCO:
            return _OCC_DOMAIN_ISCO[k]
    return "dom_cross"


def _add_transversal(esco, esco_ids, label_rows):
    """Add the ESCO transversal collection as soft skills (the soft vocabulary). Non-IT "life skills"
    (health / physical / civic / environmental / cultural) are pruned via the curated soft-relevance
    filter, so the soft branch stays IT-focused."""
    if not os.path.isfile(TRANSVERSAL):
        return 0
    from . import relevance as R  # lazy: relevance pulls in the align models
    tdf = K.read_csv_smart(TRANSVERSAL)
    transv_ids = {K.uri_tail((r.get("conceptUri") or "").strip()) for _, r in tdf.iterrows()}
    for r in esco:
        if r["source_id"] in transv_ids and not R.is_non_it_soft(r.get("pref_label_en", "")):
            r["hard_soft_provisional"] = "soft"
            r["hard_soft_method"] = "esco_transversal_collection"
    added = 0
    for _, r in tdf.iterrows():
        tail = K.uri_tail((r.get("conceptUri") or "").strip())
        if not tail or tail in esco_ids:
            continue
        pref = (r.get("preferredLabel") or "").strip()
        if R.is_non_it_soft(pref):      # prune non-IT transversal life-skills
            continue
        eid = K.mint_id("SKL_", C.SRC_ESCO, tail)
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
    """Return (rows, type_id, domain_id, category_id) — the 3-tier ontology as TAXONOMY skill rows."""
    rows, type_id, domain_id, category_id = [], {}, {}, {}

    def _row(prefix, sid, label, hard_soft, marker, subtype):
        eid = K.mint_id(prefix, TAXO_SRC, sid)
        rows.append({
            "entity_id": eid, "source": TAXO_SRC, "source_id": sid,
            "pref_label_en": label, "pref_label_fr": "",
            "alt_labels_en": "", "alt_labels_fr": "",
            "description_en": "", "description_fr": "",
            "esco_skill_type": marker, "esco_reuse_level": "",
            "hard_soft_provisional": hard_soft, "hard_soft_method": "ontology",
            "it_subtype": subtype,
        })
        return eid

    for tkey, label in TYPES.items():
        type_id[tkey] = _row("SKT_", f"type:{tkey}", label, tkey, "skill_type", tkey)
    for dkey, (tkey, label) in DOMAINS.items():
        domain_id[dkey] = _row("SKD_", f"domain:{dkey}", label, tkey, "skill_domain", dkey)
    for ckey, (dkey, label) in CATEGORIES.items():
        category_id[ckey] = _row("SKC_", f"category:{ckey}", label, DOMAINS[dkey][0],
                                 "skill_category", ckey)
    return rows, type_id, domain_id, category_id


def run():
    all_skills = [r for r in K.read_all(C.SKILLS_CSV)
                  if r.get("esco_skill_type") not in C.TAXONOMY_SKILL_MARKERS]
    esco = [r for r in all_skills if r["source"] == C.SRC_ESCO]
    others = [r for r in all_skills if r["source"] != C.SRC_ESCO]
    esco_ids = {r["source_id"] for r in esco}

    label_rows = []
    n_soft_added = _add_transversal(esco, esco_ids, label_rows)

    taxo_rows, type_id, domain_id, category_id = _taxonomy_nodes()

    # --- classify every skill -> category, then wire skill -> category -------------------
    hier_edges = []
    for r in esco + others:
        text = r.get("pref_label_en") or r.get("pref_label_fr") or ""
        hs = r.get("hard_soft_provisional")
        existing = r.get("it_subtype")
        # A high-precision fine category (mobile/data-eng/hardware) wins for ANY hard source, since
        # these categories post-date the self-classified source maps; otherwise trust a self-classified
        # source's own category; otherwise derive it from the label classifier.
        fine = _fine_category(text) if hs != "soft" else None
        if fine:
            sub = fine
        elif r["source"] in C.SELF_CLASSIFIED_SUBDOMAIN_SOURCES and existing in CATEGORIES:
            sub = existing
        else:
            sub = classify_subdomain(text, hs, r.get("esco_skill_type"))
        r["it_subtype"] = sub
        hier_edges.append({
            "parent_entity_id": category_id[sub], "child_entity_id": r["entity_id"],
            "entity_kind": "skill", "relation_type": "broader_than", "source": EDGE_SRC,
        })
    # category -> domain, domain -> type.
    for ckey, (dkey, _l) in CATEGORIES.items():
        hier_edges.append({
            "parent_entity_id": domain_id[dkey], "child_entity_id": category_id[ckey],
            "entity_kind": "skill", "relation_type": "broader_than", "source": EDGE_SRC,
        })
    for dkey, (tkey, _l) in DOMAINS.items():
        hier_edges.append({
            "parent_entity_id": type_id[tkey], "child_entity_id": domain_id[dkey],
            "entity_kind": "skill", "relation_type": "broader_than", "source": EDGE_SRC,
        })

    # --- occupation -> domain facet (shared domain nodes; navigable occ <-> domain <-> skill) ---
    facet_edges, facet_by_dom = [], defaultdict(int)
    for o in K.read_all(C.OCCUPATIONS_CSV):
        if o.get("occupation_type") == "isco_group":
            continue
        dom = _occupation_domain(o)
        facet_by_dom[dom] += 1
        facet_edges.append({
            "parent_entity_id": domain_id[dom], "child_entity_id": o["entity_id"],
            "entity_kind": "occupation", "relation_type": "in_domain", "source": FACET_SRC,
        })

    # Write back: ESCO skills (incl. added transversal), other sources, taxonomy nodes, edges.
    K.replace_source_rows(C.SKILLS_CSV, C.SKILL_FIELDS, C.SRC_ESCO, esco)
    by_source = defaultdict(list)
    for r in others:
        by_source[r["source"]].append(r)
    for src, rows in by_source.items():
        K.replace_source_rows(C.SKILLS_CSV, C.SKILL_FIELDS, src, rows)
    K.replace_source_rows(C.SKILLS_CSV, C.SKILL_FIELDS, TAXO_SRC, taxo_rows)
    K.replace_source_rows(C.HIERARCHY_CSV, C.HIERARCHY_FIELDS, EDGE_SRC, hier_edges)
    K.replace_source_rows(C.HIERARCHY_CSV, C.HIERARCHY_FIELDS, FACET_SRC, facet_edges)
    K.upsert_labels(label_rows)

    n_soft = sum(1 for r in esco + others if r["hard_soft_provisional"] == "soft")
    K.log_provenance(EDGE_SRC, [{
        "entity_id": EDGE_SRC, "source": EDGE_SRC, "source_version": "-",
        "retrieved_at": K.now_iso(), "retrieval_method": "neutral_faceted_ontology",
        "notes": f"{len(esco)+len(others)} skills -> {len(CATEGORIES)} categories / {len(DOMAINS)} "
                 f"domains / {len(TYPES)} types; {n_soft} soft; {len(hier_edges)} skill edges, "
                 f"{len(facet_edges)} occupation-domain facet edges",
    }])
    print(f"[HIER] {len(esco)+len(others)} skills -> {len(CATEGORIES)} categories / {len(DOMAINS)} "
          f"domains / {len(TYPES)} types ({n_soft} soft, +{n_soft_added} transversal); "
          f"{len(hier_edges)} skill edges + {len(facet_edges)} occupation-domain facet edges.")
