"""Unified concept merge / de-duplication.

Clusters occupations (and separately skills) into unified concepts by taking the
connected components of the ``exactMatch`` alignment graph. Each unified concept
carries an English-primary label (French secondary), merged synonyms, the hub ISCO
code, and back-links to its source members (provenance preserved).
"""

from __future__ import annotations
import hashlib

from . import config as C
from . import common as K

SOURCE_ORDER = {C.SRC_ESCO: 0, C.SRC_ONET: 1, C.SRC_NOC: 2, C.SRC_ROME: 3, C.SRC_ISCO: 4}


class _UF:
    def __init__(self):
        self.p = {}

    def find(self, x):
        self.p.setdefault(x, x)
        root = x
        while self.p[root] != root:
            root = self.p[root]
        while self.p[x] != root:
            self.p[x], x = root, self.p[x]
        return root

    def union(self, a, b):
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.p[ra] = rb


def _components(nodes, edges):
    uf = _UF()
    for n in nodes:
        uf.find(n)
    for a, b in edges:
        if a in uf.p and b in uf.p:
            uf.union(a, b)
    comps = {}
    for n in nodes:
        comps.setdefault(uf.find(n), []).append(n)
    return list(comps.values())


def _unified_id(prefix, member_ids):
    h = hashlib.sha1("|".join(sorted(member_ids)).encode("utf-8")).hexdigest()[:12]
    return f"{prefix}{h}"


def _split(value):
    return [p.strip() for p in (value or "").split(" | ") if p.strip()]


def _by_order(members, field):
    """First non-empty value of `field` across members, by source priority."""
    for m in sorted(members, key=lambda r: SOURCE_ORDER.get(r["source"], 9)):
        if (m.get(field) or "").strip():
            return m[field].strip()
    return ""


def _merged_alts(members, primary_en, primary_fr):
    en, fr = [], []
    for m in members:
        for v in [m.get("pref_label_en")] + _split(m.get("alt_labels_en")):
            v = (v or "").strip()
            if v and v != primary_en and v not in en:
                en.append(v)
        for v in [m.get("pref_label_fr")] + _split(m.get("alt_labels_fr")):
            v = (v or "").strip()
            if v and v != primary_fr and v not in fr:
                fr.append(v)
    return " | ".join(en), " | ".join(fr)


def _exact_edges(kind_prefix):
    edges = []
    for a in K.read_all(C.ALIGNMENTS_CSV):
        ea, eb = a.get("entity_id_a", ""), a.get("entity_id_b", "")
        if (ea.startswith(kind_prefix) and eb.startswith(kind_prefix)
                and a.get("relation") == "skos:exactMatch"):
            edges.append((ea, eb))
    return edges


def _merge_occupations():
    occ = [r for r in K.read_all(C.OCCUPATIONS_CSV)
           if r.get("occupation_type") != "isco_group"]
    by_id = {r["entity_id"]: r for r in occ}
    comps = _components(list(by_id), _exact_edges("OCC_"))

    rows = []
    for comp in comps:
        members = [by_id[e] for e in comp]
        primary_en = _by_order(members, "pref_label_en")
        primary_fr = _by_order(members, "pref_label_fr")
        alt_en, alt_fr = _merged_alts(members, primary_en, primary_fr)
        rows.append({
            "unified_id": _unified_id("UOCC_", comp),
            "primary_label_en": primary_en, "primary_label_fr": primary_fr,
            "alt_labels_en": alt_en, "alt_labels_fr": alt_fr,
            "isco_code": _by_order(members, "isco_code"),
            "occupation_type": "unified_occupation",
            "sources": " | ".join(sorted({m["source"] for m in members})),
            "member_entity_ids": " | ".join(sorted(comp)),
        })
    K.write_csv(C.UNIFIED_OCCUPATIONS_CSV, C.UNIFIED_OCC_FIELDS, rows)
    return rows


def _merge_skills():
    skl = [r for r in K.read_all(C.SKILLS_CSV)
           if r.get("hard_soft_provisional") != "group"]
    by_id = {r["entity_id"]: r for r in skl}
    comps = _components(list(by_id), _exact_edges("SKL_"))

    rows = []
    for comp in comps:
        members = [by_id[e] for e in comp]
        primary_en = _by_order(members, "pref_label_en")
        primary_fr = _by_order(members, "pref_label_fr")
        alt_en, alt_fr = _merged_alts(members, primary_en, primary_fr)
        hs = [m.get("hard_soft_provisional") for m in members
              if m.get("hard_soft_provisional")]
        hard_soft = max(set(hs), key=hs.count) if hs else ""
        rows.append({
            "unified_id": _unified_id("USKL_", comp),
            "primary_label_en": primary_en, "primary_label_fr": primary_fr,
            "alt_labels_en": alt_en, "alt_labels_fr": alt_fr,
            "hard_soft": hard_soft, "it_subtype": _by_order(members, "it_subtype"),
            "sources": " | ".join(sorted({m["source"] for m in members})),
            "member_entity_ids": " | ".join(sorted(comp)),
        })
    K.write_csv(C.UNIFIED_SKILLS_CSV, C.UNIFIED_SKILL_FIELDS, rows)
    return rows


def run():
    occ_rows = _merge_occupations()
    skl_rows = _merge_skills()
    n_occ_multi = sum(1 for r in occ_rows if " | " in r["member_entity_ids"])
    n_skl_multi = sum(1 for r in skl_rows if " | " in r["member_entity_ids"])
    K.log_provenance("MERGE", [{
        "entity_id": "MERGE", "source": "MERGE", "source_version": "-",
        "retrieved_at": K.now_iso(), "retrieval_method": "connected_components(exactMatch)",
        "notes": f"{len(occ_rows)} unified occ ({n_occ_multi} merged), "
                 f"{len(skl_rows)} unified skills ({n_skl_multi} merged)",
    }])
    print(f"[MERGE] {len(occ_rows)} unified occupations ({n_occ_multi} multi-source), "
          f"{len(skl_rows)} unified skills ({n_skl_multi} multi-source).")
