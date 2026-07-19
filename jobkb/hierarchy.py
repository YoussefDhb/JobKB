"""Skill hierarchy + hard/soft refinement + IT sub-typing (English).

- ESCO transversal-collection members are reclassified hard -> soft.
- ESCO skill groups (broaderRelationsSkillPillar) become group nodes with
  child -> group ``broader_than`` edges (edge source tag ``ESCO_SKILLS`` so it does
  not clobber ESCO's occupation->ISCO attachment edges tagged ``ESCO``).
- Every hard skill gets an ``it_subtype`` (named tech / programming / data / network /
  security / development / other), using tech tokens plus ESCO group labels.
"""

from __future__ import annotations
import os
import re
from collections import defaultdict

from . import config as C
from . import common as K

TRANSVERSAL = os.path.join(C.ESCO_EN_DIR, "transversalSkillsCollection_en.csv")
BROADER = os.path.join(C.ESCO_EN_DIR, "broaderRelationsSkillPillar_en.csv")

EDGE_SRC = "ESCO_SKILLS"

TECH_RE = re.compile(
    r"\b(python|java|javascript|typescript|c\+\+|c#|\.net|php|ruby|perl|go|golang|rust|"
    r"kotlin|swift|scala|r|matlab|sql|nosql|html|css|bash|powershell|kubernetes|docker|"
    r"tensorflow|pytorch|hadoop|spark|kafka|aws|azure|gcp|linux|unix|git|jenkins|"
    r"react|angular|vue|node\.?js|django|flask|spring|\.js)\b", re.I)


def _tails(path, col="conceptUri"):
    if not os.path.isfile(path):
        return set()
    df = K.read_csv_smart(path)
    return {K.uri_tail((v or "").strip()) for v in df[col]}


def _subtype_from_group(labels):
    for lbl in labels:
        l = (lbl or "").lower()
        if "program" in l:
            return "programmation"
        if "database" in l or "data " in l or l.endswith("data") or "data and" in l:
            return "donnees_bdd"
        if "network" in l:
            return "reseau"
        if "security" in l or "protect" in l or "penetration" in l or "cyber" in l:
            return "securite"
        if "develop" in l or "design" in l:
            return "developpement_conception"
    return None


def run():
    all_skills = K.read_all(C.SKILLS_CSV)
    esco = [r for r in all_skills if r["source"] == C.SRC_ESCO]
    others = [r for r in all_skills if r["source"] != C.SRC_ESCO]
    esco_ids = {r["source_id"] for r in esco}
    label_rows = []

    # 1) Transversal collection -> soft. IT occupations barely link transversal
    #    skills, so we both reclassify any that are present and add the rest of the
    #    collection as standalone soft nodes (the ESCO soft-skill vocabulary), which
    #    then dedup against ROME savoir-etre / ONET abilities during alignment.
    added_transv = 0
    if os.path.isfile(TRANSVERSAL):
        tdf = K.read_csv_smart(TRANSVERSAL)
        transv_ids = {K.uri_tail((r.get("conceptUri") or "").strip()) for _, r in tdf.iterrows()}
        for r in esco:
            if r["source_id"] in transv_ids:
                r["hard_soft_provisional"] = "soft"
                r["hard_soft_method"] = "esco_transversal_collection"
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
                "hard_soft_provisional": "soft",
                "hard_soft_method": "esco_transversal_collection",
                "it_subtype": "soft_transversale",
            })
            esco_ids.add(tail)
            label_rows.extend(K.make_label_rows(eid, "skill", C.SRC_ESCO,
                                                preferred={"en": [pref]}, alts={"en": alts}))
            added_transv += 1

    # 2) Skill-group hierarchy.
    group_nodes, hier_edges = {}, []
    parent_labels = defaultdict(list)
    if os.path.isfile(BROADER):
        broader = K.read_csv_smart(BROADER)
        for _, r in broader.iterrows():
            child_tail = K.uri_tail((r.get("conceptUri") or "").strip())
            if child_tail not in esco_ids:
                continue
            btype = (r.get("broaderType") or "").strip()
            parent_tail = K.uri_tail((r.get("broaderUri") or "").strip())
            blabel = (r.get("broaderLabel") or "").strip()
            parent_labels[child_tail].append(blabel)
            child_eid = K.mint_id("SKL_", C.SRC_ESCO, child_tail)
            if btype == "SkillGroup":
                gid = K.mint_id("SKL_", C.SRC_ESCO, parent_tail)
                if parent_tail not in group_nodes:
                    group_nodes[parent_tail] = {
                        "entity_id": gid, "source": C.SRC_ESCO, "source_id": parent_tail,
                        "pref_label_en": blabel, "pref_label_fr": "",
                        "alt_labels_en": "", "alt_labels_fr": "",
                        "description_en": "", "description_fr": "",
                        "esco_skill_type": "skill_group", "esco_reuse_level": "",
                        "hard_soft_provisional": "group",
                        "hard_soft_method": "esco_skill_group", "it_subtype": "groupe",
                    }
                    label_rows.extend(K.make_label_rows(gid, "skill", C.SRC_ESCO,
                                                        preferred={"en": [blabel]}))
                parent_eid = gid
            elif parent_tail in esco_ids:
                parent_eid = K.mint_id("SKL_", C.SRC_ESCO, parent_tail)
            else:
                continue
            hier_edges.append({
                "parent_entity_id": parent_eid, "child_entity_id": child_eid,
                "entity_kind": "skill", "relation_type": "broader_than", "source": EDGE_SRC,
            })

    # 3) IT sub-typing.
    def subtype_esco(r):
        if r["hard_soft_provisional"] == "soft":
            return "soft_transversale"
        if r["esco_skill_type"] == "skill_group" or r["hard_soft_provisional"] == "group":
            return "groupe"
        label = r["pref_label_en"] or r["pref_label_fr"]
        if TECH_RE.search(label or ""):
            return "langage_ou_techno_nommee"
        return _subtype_from_group(parent_labels.get(r["source_id"], [])) or "autre_hard"

    for r in esco:
        r["it_subtype"] = subtype_esco(r)

    for r in others:
        if r["hard_soft_provisional"] == "soft":
            r["it_subtype"] = "soft_transversale"
        elif r["it_subtype"]:
            pass  # e.g. ONET software already tagged
        elif TECH_RE.search(r["pref_label_en"] or r["pref_label_fr"] or ""):
            r["it_subtype"] = "langage_ou_techno_nommee"
        else:
            r["it_subtype"] = "autre_hard"

    # 4) Write back.
    esco_out = esco + list(group_nodes.values())
    K.replace_source_rows(C.SKILLS_CSV, C.SKILL_FIELDS, C.SRC_ESCO, esco_out)
    by_source = defaultdict(list)
    for r in others:
        by_source[r["source"]].append(r)
    for src, rows in by_source.items():
        K.replace_source_rows(C.SKILLS_CSV, C.SKILL_FIELDS, src, rows)
    K.replace_source_rows(C.HIERARCHY_CSV, C.HIERARCHY_FIELDS, EDGE_SRC, hier_edges)
    K.upsert_labels(label_rows)

    n_soft = sum(1 for r in esco if r["hard_soft_provisional"] == "soft")
    K.log_provenance(EDGE_SRC, [{
        "entity_id": EDGE_SRC, "source": EDGE_SRC, "source_version": "ESCO v1.2 (en)",
        "retrieved_at": K.now_iso(), "retrieval_method": "derived",
        "notes": f"{n_soft} soft, {len(group_nodes)} groups, {len(hier_edges)} skill edges",
    }])
    print(f"[HIER] {n_soft} soft skills, {len(group_nodes)} skill groups, "
          f"{len(hier_edges)} skill-hierarchy edges.")
