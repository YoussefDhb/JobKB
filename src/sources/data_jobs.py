"""DATAJOBS source — lukebarousse/data_jobs (785k postings): tool harvest + large-scale demand.

`resources/OTHERS/en/data_jobs.csv` is 785,741 real job postings across 10 data/IT roles, each with a
pre-extracted, normalized `job_skills` list and a `job_type_skills` category grouping. We exploit it
two ways (no salary — not needed):

  1. **Harvest** the few genuinely-absent, high-frequency IT tools (e.g. databricks, matplotlib, dax,
     golang) as **new skill nodes** — gate-screened (non-IT/office noise blocked) and self-classified
     via `job_type_skills` category -> sub-domain.
  2. **Demand relations**: aggregate `(role, skill)` co-occurrence over all postings into weighted
     `demand` occupation->skill edges, keeping robust pairs (>= DATAJOBS_MIN_FREQ postings).

Both endpoints are resolved against the CURRENT kb/: roles -> existing occupations, skills -> existing
skills via an **augmented matcher** (exact/alias key PLUS parenthetical acronyms and vendor/suffix
stripping, so short tokens like `gcp`/`power bi`/`kafka` match verbose KB labels — never substring
matching, which would confuse e.g. `airflow` the tool with computational-fluid-dynamics airflow).
Tokens that neither resolve nor get harvested simply drop out. Contributes skills-only
(`contributes_occupations=False`, `needs_attach=False`).
"""

from __future__ import annotations

import ast
import csv
import os
import re
from collections import Counter, defaultdict

from .. import config as C
from .. import common as K
from .base import Source
from . import evidence
from .emerging_roles import EMERGING_ROLES

_CSV = os.path.join(C.OTHERS_EN_DIR, "data_jobs.csv")

# Conservative token sets for the augmented matcher (stripped from KB labels to build extra keys).
_VENDOR = {"microsoft", "apache", "google", "amazon", "aws", "ibm", "oracle", "adobe", "apple"}
_TRAIL = {"software", "framework", "platform", "statistics", "language", "db", "database"}
_PAREN = re.compile(r"\(([^)]+)\)")


def _variant_keys(label: str):
    """Yield match_key variants for a KB skill label so short posting tokens resolve to verbose
    KB names: the base key, any parenthetical acronym, and a vendor/suffix-stripped key."""
    yield evidence.match_key(label)
    for m in _PAREN.findall(label):
        k = evidence.match_key(m)
        if k:
            yield k
    toks = K.normalize_label(_PAREN.sub("", label)).split()
    while toks and toks[0] in _VENDOR:
        toks = toks[1:]
    while toks and toks[-1] in _TRAIL:
        toks = toks[:-1]
    if toks:
        yield evidence.match_key(" ".join(toks))


def _augmented_skill_index(exclude_source=None):
    """{match_key variant -> skill entity_id} over real KB skills (exact keys win over stripped).
    `exclude_source` drops that source's own rows so a re-ingest re-harvests idempotently (else its
    previously-harvested skills look 'already present' and get deleted by the replace)."""
    skl = [r for r in K.read_all(C.SKILLS_CSV)
           if r.get("esco_skill_type") not in ("skill_type", "skill_domain")
           and r.get("source") != exclude_source]
    idx = {}
    for r in skl:
        for field in ("pref_label_en", "pref_label_fr", "alt_labels_en", "alt_labels_fr"):
            for lbl in (r.get(field) or "").split(" | "):
                for k in _variant_keys(lbl):
                    if k:
                        idx.setdefault(k, r["entity_id"])
    return idx


class DataJobsSource(Source):
    name = C.SRC_DATAJOBS
    contributes_occupations = False
    needs_attach = False
    builtin = True
    version = "lukebarousse/data_jobs"
    retrieval_method = "job_postings_mined"

    def ingest(self) -> None:
        occ_map = evidence.occ_index()
        skill_idx = _augmented_skill_index(exclude_source=self.name)

        # Emerging roles (Analytics Engineer, MLOps, …) are recognized from the RAW job title and
        # take precedence over the coarse job_title_short, so their demand profile is attributed to
        # the specific occupation (present only if EMERGING was ingested first).
        emerging = [(re.compile(r["pattern"], re.I), occ_map.get(evidence.match_key(r["label"])))
                    for r in EMERGING_ROLES]
        emerging = [(rx, oid) for rx, oid in emerging if oid]

        # --- one streaming pass: token stats + (role, token) co-occurrence -------------------
        pair = defaultdict(int)           # (occ_id, token) -> #postings
        tok_freq = Counter()              # token -> #postings mentioning it
        tok_cat = defaultdict(Counter)    # token -> {job_type_skills category: count}
        n_post = 0
        roles_matched = set()
        with open(_CSV, encoding="utf-8", errors="replace", newline="") as f:
            for row in csv.DictReader(f):
                n_post += 1
                raw_title = row.get("job_title") or ""
                occ_id = next((oid for rx, oid in emerging if rx.search(raw_title)), None)
                if not occ_id:                       # fall back to the coarse normalized role
                    occ_id = occ_map.get(evidence.match_key((row.get("job_title_short") or "")
                                                            .replace("Senior ", "").strip()))
                raw = row.get("job_skills") or ""
                if not raw:
                    continue
                try:
                    tokens = ast.literal_eval(raw)
                except (ValueError, SyntaxError):
                    continue
                tokens = {str(t).strip().lower() for t in tokens if str(t).strip()}
                for t in tokens:
                    tok_freq[t] += 1
                cats = {}
                try:
                    for cat, toks in (ast.literal_eval(row.get("job_type_skills") or "{}") or {}).items():
                        for t in toks:
                            cats[str(t).strip().lower()] = cat
                except (ValueError, SyntaxError):
                    pass
                for t in tokens:
                    if t in cats:
                        tok_cat[t][cats[t]] += 1
                if occ_id:
                    roles_matched.add(row.get("job_title_short"))
                    for t in tokens:
                        pair[(occ_id, t)] += 1

        # --- harvest genuinely-absent, frequent IT tools as new skill nodes -----------------
        candidates = [t for t, c in tok_freq.items()
                      if c >= C.DATAJOBS_MIN_SKILL_FREQ and t not in skill_idx]
        skill_rows, label_rows = [], []
        for t in candidates:
            eid = K.mint_id("SKL_", self.name, t)
            cat = tok_cat[t].most_common(1)[0][0] if tok_cat[t] else ""
            skill_rows.append({
                "entity_id": eid, "source": self.name, "source_id": t,
                "pref_label_en": t, "pref_label_fr": "",
                "alt_labels_en": "", "alt_labels_fr": "",
                "description_en": "", "description_fr": "",
                "esco_skill_type": "", "esco_reuse_level": "",
                "hard_soft_provisional": "hard", "hard_soft_method": "datajobs_skill",
                "it_subtype": C.DATAJOBS_TYPE_SUBDOMAIN.get(cat, ""),
            })
            label_rows.extend(K.make_label_rows(eid, "skill", self.name, preferred={"en": [t]}))

        # relevance gate: block non-IT / office noise before the tokens become nodes.
        from .. import relevance
        _, skill_rows, blocked, gstats = relevance.filter_rows([], skill_rows, self.name)
        if blocked:
            label_rows = [l for l in label_rows if l["entity_id"] not in blocked]
        harvested = {r["source_id"]: r["entity_id"] for r in skill_rows}   # token -> new skill id

        K.replace_source_rows(C.SKILLS_CSV, C.SKILL_FIELDS, self.name, skill_rows)
        K.upsert_labels(label_rows)

        # --- resolve every (role, token) into weighted demand relations ---------------------
        def resolve(token):
            return skill_idx.get(evidence.match_key(token)) or harvested.get(token)

        agg = defaultdict(int)
        for (occ_id, token), c in pair.items():
            sid = resolve(token)
            if sid:
                agg[(occ_id, sid)] += c
        rel_rows = [evidence.relation_row(o, s, self.name, weight=w)
                    for (o, s), w in agg.items() if w >= C.DATAJOBS_MIN_FREQ]
        evidence.write_relations(self.name, rel_rows)

        gate_note = ""
        if gstats:
            gate_note = (f"; gate blocked {gstats['malformed'] + gstats['non_it']} "
                         f"(non-IT {gstats['non_it']}, malformed {gstats['malformed']})")
        K.log_provenance(self.name, [{
            "entity_id": self.name, "source": self.name, "source_version": self.version,
            "retrieved_at": K.now_iso(), "retrieval_method": self.retrieval_method,
            "notes": f"{len(skill_rows)} harvested tool skills, {len(rel_rows)} demand relations "
                     f"from {n_post} postings, {len(roles_matched)} roles matched{gate_note}",
        }])
        print(f"[{self.name}] {len(skill_rows)} new tool skills, {len(rel_rows)} demand relations "
              f"from {n_post} postings ({len(roles_matched)} roles matched, "
              f"{len({o for o, _ in agg})} occupations).{gate_note}")
