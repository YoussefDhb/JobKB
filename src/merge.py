"""Unified concept merge / de-duplication.

Clusters occupations (and separately skills) into unified concepts by taking the
connected components of the ``exactMatch`` alignment graph. Each unified concept
carries an English-primary label (French secondary), merged synonyms, the hub ISCO
code, and back-links to its source members (provenance preserved).
"""

from __future__ import annotations
import hashlib

from . import config as C
from collections import Counter

from . import common as K
from . import wikidata as W


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


def _majority(members, field):
    """Source-neutral majority value of `field` (ties: shorter, then alphabetical)."""
    vals = [(m.get(field) or "").strip() for m in members if (m.get(field) or "").strip()]
    if not vals:
        return ""
    counts = Counter(vals)
    top = max(counts.values())
    return sorted([v for v, c in counts.items() if c == top], key=lambda s: (len(s), s))[0]


def _consensus_label(members, lang):
    """Source-neutral primary label for a language: the most shared *preferred* label
    across members (ties: most frequent normalized form, then shortest, then alphabetical).
    Falls back to alternative labels only when no member has a preferred label in that
    language (e.g. an all-ROME cluster for English). No source ranking."""
    pref_field, alt_field = f"pref_label_{lang}", f"alt_labels_{lang}"

    def _vote(get_forms):
        norm_count, surfaces = Counter(), {}
        for m in members:
            for f in get_forms(m):
                f = (f or "").strip()
                n = K.normalize_label(f)
                if not n:
                    continue
                norm_count[n] += 1
                surfaces.setdefault(n, []).append(f)
        if not norm_count:
            return ""
        best = sorted([n for n, c in norm_count.items()
                       if c == max(norm_count.values())])[0]
        return sorted(set(surfaces[best]), key=lambda s: (len(s), s))[0]

    return _vote(lambda m: [m.get(pref_field)]) or _vote(lambda m: _split(m.get(alt_field)))


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


def _merge_edges(kind_prefix):
    """Cross-source pairs flagged for merge, as (a, b, kind) with kind in {label, semantic}."""
    edges = []
    for a in K.read_all(C.ALIGNMENTS_CSV):
        ea, eb, kind = a.get("entity_id_a", ""), a.get("entity_id_b", ""), a.get("merge", "")
        if kind in ("label", "semantic") and ea.startswith(kind_prefix) and eb.startswith(kind_prefix):
            edges.append((ea, eb, kind))
    return edges


def _merge_occupations():
    occ = [r for r in K.read_all(C.OCCUPATIONS_CSV)
           if r.get("occupation_type") != "isco_group"]
    by_id = {r["entity_id"]: r for r in occ}
    isco = {e: (r.get("isco_code") or "").strip() for e, r in by_id.items()}
    # Label merges always apply; semantic merges only within the same ISCO group.
    edges = [(a, b) for a, b, kind in _merge_edges("OCC_")
             if kind == "label" or (a in isco and isco[a] and isco[a] == isco.get(b))]
    comps = _components(list(by_id), edges)

    rows = []
    for comp in comps:
        members = [by_id[e] for e in comp]
        primary_en = _consensus_label(members, "en")
        primary_fr = _consensus_label(members, "fr")
        alt_en, alt_fr = _merged_alts(members, primary_en, primary_fr)
        rows.append({
            "unified_id": _unified_id("UOCC_", comp),
            "primary_label_en": primary_en, "primary_label_fr": primary_fr,
            "alt_labels_en": alt_en, "alt_labels_fr": alt_fr,
            "isco_code": _majority(members, "isco_code"),
            "occupation_type": "unified_occupation",
            "sources": " | ".join(sorted({m["source"] for m in members})),
            "member_entity_ids": " | ".join(sorted(comp)),
        })
    W.enrich_rows(rows, "occupation")  # weave in Wikidata anchors if the side table exists
    K.write_csv(C.UNIFIED_OCCUPATIONS_CSV, C.UNIFIED_OCC_FIELDS, rows)
    return rows


def _merge_skills():
    skl = [r for r in K.read_all(C.SKILLS_CSV)
           if r.get("esco_skill_type") not in C.TAXONOMY_SKILL_MARKERS]
    by_id = {r["entity_id"]: r for r in skl}
    comps = _components(list(by_id), [(a, b) for a, b, _k in _merge_edges("SKL_")])

    rows = []
    for comp in comps:
        members = [by_id[e] for e in comp]
        primary_en = _consensus_label(members, "en")
        primary_fr = _consensus_label(members, "fr")
        alt_en, alt_fr = _merged_alts(members, primary_en, primary_fr)
        rows.append({
            "unified_id": _unified_id("USKL_", comp),
            "primary_label_en": primary_en, "primary_label_fr": primary_fr,
            "alt_labels_en": alt_en, "alt_labels_fr": alt_fr,
            "hard_soft": _majority(members, "hard_soft_provisional"),
            "it_subtype": _majority(members, "it_subtype"),
            "sources": " | ".join(sorted({m["source"] for m in members})),
            "member_entity_ids": " | ".join(sorted(comp)),
        })
    W.enrich_rows(rows, "skill")  # weave in Wikidata anchors if the side table exists
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
