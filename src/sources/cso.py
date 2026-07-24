"""CSO 3.5: a curated IT subset of the Computer Science Ontology (~14.6k CS research topics). Keeps only
the shallow IT-relevant part as knowledge skills: BFS from CSO_ROOTS over superTopicOf to CSO_MAX_DEPTH,
capped, each topic classified by its root branch (CSO_BRANCH_SUBDOMAIN). De-noised (canonical
preferentialEquivalent + a fold key, drop >6-word phrases; relatedEquivalent -> alt-labels). The topic
hierarchy is used only to select/classify, never persisted as skill->skill edges.
"""

from __future__ import annotations

import csv
import os
from collections import defaultdict, deque
from urllib.parse import unquote

from .. import config as C
from .. import common as K
from ..relevance import is_structural_noise
from .base import StructuredSource

_CSO_CSV = os.path.join(C.CSO_EN_DIR, "CSO.3.5.csv")

_P_SUPER = "superTopicOf"
_P_RELATED = "relatedEquivalent"
_P_PREF = "preferentialEquivalent"

# Redundant trailing words that make a topic a near-duplicate of its base concept
# (e.g. "reinforcement learning approach" -> "reinforcement learning"). Kept deliberately
# small/safe — no "system/model/algorithm" (they carry meaning: "operating system").
_GENERIC_TAIL = {"approach", "approaches", "method", "methods", "methodology",
                 "methodologies", "technique", "techniques"}


def _slug(x: str) -> str:
    return unquote((x or "").strip())


def _clean_label(obj: str) -> str:
    o = (obj or "").strip()
    if o.endswith(" ."):
        o = o[:-2].strip()
    if "@" in o:                      # drop the @en / @xx language tag
        o = o.rsplit("@", 1)[0]
    return unquote(o.strip().strip('"')).strip()


def _humanize(slug: str) -> str:
    s = slug.replace("_", " ").strip()
    return s[:1].upper() + s[1:] if s else s


def _dedup_key(label: str) -> str:
    """Normalized key folding 'X' / 'X approach' / simple plurals to one representative."""
    words = K.normalize_label(label).split()
    while len(words) > 1 and words[-1] in _GENERIC_TAIL:
        words.pop()
    if words:
        w = words[-1]
        if w.endswith("ies") and len(w) > 4:
            w = w[:-3] + "y"
        elif w.endswith(("ses", "xes", "zes", "ches", "shes")):
            w = w[:-2]
        elif w.endswith("s") and not w.endswith("ss") and len(w) > 3:
            w = w[:-1]
        words[-1] = w
    return " ".join(words)


class CsoSource(StructuredSource):
    name = C.SRC_CSO
    contributes_occupations = False      # CSO has no occupations
    needs_attach = False                 # ... so nothing to attach to ISCO
    builtin = True                       # permanent member of a full build
    version = "cso-3.5"
    retrieval_method = "cso_curated_subset"

    def _parse(self):
        """Return (labels, super_map, canonical, related) from the CSO triples."""
        labels = {}                       # slug -> human label
        super_map = defaultdict(set)      # parent slug -> {child slugs}
        canonical = {}                    # slug -> canonical (preferential) slug
        related = defaultdict(set)        # slug -> {synonym slugs}
        with open(_CSO_CSV, encoding="utf-8", newline="") as f:
            reader = csv.reader(f)
            next(reader, None)            # header: Topic1,Schema,Topic2
            for row in reader:
                if len(row) < 3:
                    continue
                s, p, o = row[0], row[1], row[2]
                if p == _P_SUPER:
                    super_map[_slug(s)].add(_slug(o))
                elif p == _P_RELATED:
                    a, b = _slug(s), _slug(o)
                    related[a].add(b)
                    related[b].add(a)
                elif p == _P_PREF:
                    canonical[_slug(s)] = _slug(o)
                elif p.endswith("#label"):
                    labels[_slug(s)] = _clean_label(o)
        return labels, super_map, canonical, related

    def _curate(self, super_map):
        """BFS from CSO_ROOTS (specific->generic) to CSO_MAX_DEPTH; return (order, branch)
        where branch[slug] is the root the slug descends from (shallowest / most-specific root)."""
        branch, order = {}, []
        q = deque()
        for root in C.CSO_ROOTS:
            if root not in branch:
                branch[root] = root
                q.append((root, 0))
        while q:
            slug, depth = q.popleft()
            order.append(slug)
            if depth < C.CSO_MAX_DEPTH:
                for child in sorted(super_map.get(slug, ())):
                    if child not in branch:
                        branch[child] = branch[slug]
                        q.append((child, depth + 1))
        return order, branch

    def skills(self):
        labels, super_map, canonical, related = self._parse()
        order, branch = self._curate(super_map)

        def _lab(s):
            return labels.get(s) or _humanize(s)

        seen_canon, seen_key, n = set(), set(), 0
        per_branch = defaultdict(int)                # topics kept per sub-domain (balance)
        for slug in order:
            if n >= C.CSO_MAX_TOPICS:
                break
            sub = C.CSO_BRANCH_SUBDOMAIN.get(branch.get(slug, ""), "")
            if not sub or per_branch[sub] >= C.CSO_MAX_PER_BRANCH:
                continue                             # branch already full -> drop deep tail
            canon = canonical.get(slug, slug)
            if canon in seen_canon:
                continue                             # canonical duplicate
            label = _lab(canon)
            if len(label.split()) > 6 or is_structural_noise(label):
                continue                             # over-specific phrase / malformed slug
            key = _dedup_key(label)
            if key in seen_key:
                continue                             # near-duplicate ("X" vs "X approach")
            seen_canon.add(canon)
            seen_key.add(key)
            per_branch[sub] += 1
            n += 1

            alts = set()
            for syn in related.get(slug, set()) | related.get(canon, set()):
                alts.add(_lab(syn))
            alts.discard(label)
            yield {
                "source_id": canon,
                "label_en": label,
                "alt_en": sorted(a for a in alts if a),
                "skill_type": "knowledge",
                "method": "cso_topic",
                "it_subtype": sub,
            }
