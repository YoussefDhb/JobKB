"""ZENODO 3906955 (Montandon et al. 2019): ~17.9k English Stack Overflow postings with clean roles +
extracted hard/soft skills. Hybrid like DATAJOBS: (1) harvests absent frequent tools as new skills
(gate-screened, self-classified via the high-level category); (2) weighted demand edges for both hard
skills and the SOFTSKILLS vocabulary (linking noun-form soft skills to occupations). Skills-only; roles
resolve to existing occupations (the one gap, back-end developer, comes from EMERGING).
"""

from __future__ import annotations

import csv
from collections import Counter, defaultdict

from .. import config as C
from .. import common as K
from .base import Source
from . import evidence
from .data_jobs import _augmented_skill_index
from .soft_skills import SOFT_SKILLS

# The 14 clean Zenodo role tokens -> candidate occupation phrases (first that resolves against the
# current KB wins). All resolve via `occ_index` (pref+alt labels); back-end developer resolves to the
# EMERGING occupation once that source is ingested. Kept explicit so a KB label change can't silently
# mis-route a role's demand.
ROLE_PROBES = {
    "SystemAdministrator":   ["ict system administrator", "system administrator", "systems administrator"],
    "FullStackDeveloper":    ["full stack developer", "full-stack developer"],
    "BackendDeveloper":      ["back-end developer", "backend developer", "back end developer"],
    "FrontendDeveloper":     ["front end developer", "front-end developer", "user interface developer"],
    "MobileDeveloper":       ["mobile application developer", "mobile developer", "mobile app developer"],
    "DatabaseAdministrator": ["database administrator"],
    "QATestDeveloper":       ["software tester", "qa engineer", "test automation developer"],
    "DevOpsDeveloper":       ["devops engineer", "cloud devops engineer", "dev ops engineer"],
    "DesktopDeveloper":      ["software developer", "application developer"],
    "DataScientist":         ["data scientist"],
    "EmbeddedDeveloper":     ["embedded systems designer", "embedded software developer", "embedded developer"],
    "ProductManager":        ["ict product manager", "product manager"],
    "GameDeveloper":         ["digital games developer", "digital games designer", "game developer"],
    "Designer":              ["ui designer", "user interface designer", "ux designer"],
}

# Signals in the (tokenized) `soft_skills` column -> SOFTSKILLS source_id. The column uses a tiny
# fixed vocabulary; multi-word terms arrive split ("work ethic" -> "work" "ethic"), so we detect by
# the distinctive token rather than by whole-phrase match.
ZENODO_SOFT_TRIGGERS = {
    "teamwork": "teamwork",
    "communication": "communication",
    "responsibility": "responsibility",
    "flexibility": "flexibility",
    "ethic": "work_ethic",
    "interpersonal": "interpersonal_skills",
    "integrity": "integrity",
    "positive": "positive_attitude",
    "attitude": "positive_attitude",
    "professionalism": "professionalism",
    "courtesy": "professionalism",
}


def _hl_categories():
    """{hard-skill tag -> high-level category} from the companion taxonomy CSV."""
    cats = {}
    with open(C.ZENODO_HL_CSV, encoding="utf-8-sig", errors="replace", newline="") as f:
        for r in csv.DictReader(f):
            tag = (r.get("tag") or "").strip().lower()
            cat = (r.get("João + Luciana") or r.get("Joao + Luciana") or "").strip()
            if tag:
                cats[tag] = cat
    return cats


class ZenodoSource(Source):
    name = C.SRC_ZENODO
    contributes_occupations = False
    needs_attach = False
    builtin = True
    version = "zenodo-3906955-montandon2019"
    retrieval_method = "job_postings_mined"

    def ingest(self) -> None:
        occ_map = evidence.occ_index()
        skill_idx = _augmented_skill_index(exclude_source=self.name)
        hl_cat = _hl_categories()

        # Resolve the 14 roles to occupations once (first probe that hits the current KB).
        role_occ, unresolved = {}, []
        for role, probes in ROLE_PROBES.items():
            oid = next((occ_map[k] for k in (evidence.match_key(p) for p in probes) if k in occ_map), None)
            if oid:
                role_occ[role] = oid
            else:
                unresolved.append(role)

        # Curated soft-skill entity ids are deterministic (minted by SoftSkillsSource the same way).
        soft_valid = {s["source_id"] for s in SOFT_SKILLS}
        soft_eid = {sid: K.mint_id("SKL_", C.SRC_SOFTSKILLS, sid) for sid in soft_valid}

        # --- one streaming pass: token stats + (role, token) co-occurrence -------------------
        hard_pair = defaultdict(int)      # (occ_id, hard token) -> #postings
        soft_pair = defaultdict(int)      # (occ_id, soft source_id) -> #postings
        tok_freq = Counter()              # hard token -> #postings mentioning it
        n_post = n_en = 0
        roles_matched = set()
        with open(C.ZENODO_JOBS_CSV, encoding="utf-8", errors="replace", newline="") as f:
            csv.field_size_limit(2 ** 31 - 1)
            for row in csv.DictReader(f, delimiter=";"):
                n_post += 1
                if (row.get("language") or "").strip().lower() != "en":
                    continue
                n_en += 1
                occ_ids = [role_occ[r] for r in (row.get("roles") or "").split() if r in role_occ]
                roles_matched.update(r for r in (row.get("roles") or "").split() if r in role_occ)

                hard = {t.strip().lower() for t in (row.get("hard_skills") or "").split() if t.strip()}
                for t in hard:
                    tok_freq[t] += 1

                soft_ids = {ZENODO_SOFT_TRIGGERS[t] for t in (row.get("soft_skills") or "").lower().split()
                            if t in ZENODO_SOFT_TRIGGERS}

                for occ_id in occ_ids:
                    for t in hard:
                        hard_pair[(occ_id, t)] += 1
                    for sid in soft_ids:
                        soft_pair[(occ_id, sid)] += 1

        # --- harvest genuinely-absent, frequent IT tools as new skill nodes -----------------
        candidates = [t for t, c in tok_freq.items()
                      if c >= C.ZENODO_MIN_SKILL_FREQ and t not in skill_idx]
        skill_rows, label_rows = [], []
        for t in candidates:
            eid = K.mint_id("SKL_", self.name, t)
            skill_rows.append({
                "entity_id": eid, "source": self.name, "source_id": t,
                "pref_label_en": t, "pref_label_fr": "",
                "alt_labels_en": "", "alt_labels_fr": "",
                "description_en": "", "description_fr": "",
                "esco_skill_type": "", "esco_reuse_level": "",
                "hard_soft_provisional": "hard", "hard_soft_method": "zenodo_skill",
                "it_subtype": C.ZENODO_HL_SUBDOMAIN.get(hl_cat.get(t, ""), ""),
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
        def resolve_hard(token):
            return skill_idx.get(evidence.match_key(token)) or harvested.get(token)

        agg = defaultdict(int)
        for (occ_id, token), c in hard_pair.items():
            sid = resolve_hard(token)
            if sid and c >= C.ZENODO_MIN_FREQ:
                agg[(occ_id, sid)] += c
        rel_rows = [evidence.relation_row(o, s, self.name, weight=w) for (o, s), w in agg.items()]

        soft_kept = 0
        for (occ_id, ssid), c in soft_pair.items():
            if ssid in soft_eid and c >= C.ZENODO_MIN_SOFT_FREQ:
                rel_rows.append(evidence.relation_row(occ_id, soft_eid[ssid], self.name, weight=c))
                soft_kept += 1
        evidence.write_relations(self.name, rel_rows)

        gate_note = ""
        if gstats:
            gate_note = (f"; gate blocked {gstats['malformed'] + gstats['non_it']} "
                         f"(non-IT {gstats['non_it']}, malformed {gstats['malformed']})")
        unresolved_note = f"; unresolved roles: {', '.join(unresolved)}" if unresolved else ""
        K.log_provenance(self.name, [{
            "entity_id": self.name, "source": self.name, "source_version": self.version,
            "retrieved_at": K.now_iso(), "retrieval_method": self.retrieval_method,
            "notes": f"{len(skill_rows)} harvested tool skills, {len(rel_rows)} demand relations "
                     f"({soft_kept} soft) from {n_en} English postings, "
                     f"{len(roles_matched)} roles matched{gate_note}{unresolved_note}",
        }])
        print(f"[{self.name}] {len(skill_rows)} new tool skills, {len(rel_rows)} demand relations "
              f"({soft_kept} soft) from {n_en}/{n_post} English postings "
              f"({len(roles_matched)} roles matched).{gate_note}{unresolved_note}")
