"""DJINNI source (djinni.com) - IT recruitment postings."""

from __future__ import annotations

import csv
import re
from collections import defaultdict

from .. import config as C
from .. import common as K
from .base import Source
from . import evidence

# Djinni Primary Keyword -> candidate occupation phrases.
DJINNI_ROLE_OCC = {
    "JavaScript": ["software developer"], "Java": ["software developer"], ".NET": ["software developer"],
    "Node.js": ["software developer"], "PHP": ["software developer"], "Python": ["software developer"],
    "C++": ["software developer"], "Ruby": ["software developer"], "Golang": ["software developer"],
    "Scala": ["software developer"], "Rust": ["software developer"], "React": ["software developer"],
    "Salesforce": ["software developer"], "SAP": ["software developer"],
    "DevOps": ["cloud devops engineer", "devops engineer"],
    "QA": ["software tester"], "QA Automation": ["software tester"],
    "Android": ["mobile application developer"], "iOS": ["mobile application developer"],
    "Flutter": ["mobile application developer"],
    "Data Science": ["data scientist"], "Data Engineer": ["data engineer"],
    "Data Analyst": ["data analyst"],
    "Sysadmin": ["ict system administrator"],
    "Security": ["information security analyst", "cybersecurity specialist", "ict security administrator"],
    "SQL": ["database administrator"], "Unity": ["digital games developer"],
    "Project Manager": ["ict project manager"], "Scrum Master": ["ict project manager"],
    "Product Manager": ["ict product manager"], "Product Owner": ["ict product manager"],
    "Business Analyst": ["ict business analyst"], "Support": ["ict help desk agent"],
    "Block-chain": ["software developer"],
}

_WORD = re.compile(r"[a-z0-9+.#]+")


def _concrete_skill_index():
    """{full-label match_key -> skill entity_id} over concrete-tech KB skills, safe for free-text."""
    idx = {}
    for r in K.read_all(C.SKILLS_CSV):
        if r.get("it_subtype") not in C.DJINNI_CONCRETE_SUBDOMAINS:
            continue
        for field in ("pref_label_en", "alt_labels_en"):
            for lbl in (r.get(field) or "").split(" | "):
                key = evidence.match_key(lbl)
                if not key or key in C.DJINNI_TEXT_DENY:
                    continue
                toks = key.split()
                if len(toks) >= 2 or (len(toks) == 1 and len(key) >= 4):
                    idx.setdefault(key, r["entity_id"])
    return idx


class DjinniSource(Source):
    name = C.SRC_DJINNI
    contributes_occupations = False
    needs_attach = False
    builtin = True
    version = "djinni-recruitment-en"
    retrieval_method = "job_postings_text_mined"

    def ingest(self) -> None:
        occ_map = evidence.occ_index()
        skill_idx = _concrete_skill_index()
        # Resolve the role tags to occupations once.
        role_occ = {}
        for kw, probes in DJINNI_ROLE_OCC.items():
            oid = next((occ_map[k] for k in (evidence.match_key(p) for p in probes) if k in occ_map), None)
            if oid:
                role_occ[kw] = oid
        max_n = max((len(k.split()) for k in skill_idx), default=1)
        max_n = min(max_n, 4)

        def extract(text):
            toks = _WORD.findall(K.normalize_label(text))
            found = set()
            for i in range(len(toks)):
                for n in range(1, max_n + 1):
                    if i + n <= len(toks):
                        key = evidence.match_key(" ".join(toks[i:i + n]))
                        sid = skill_idx.get(key)
                        if sid:
                            found.add(sid)
            return found

        pair = defaultdict(int)          
        n_post = n_used = 0
        roles_matched = set()
        with open(C.DJINNI_CSV, encoding="utf-8", errors="replace", newline="") as f:
            csv.field_size_limit(2 ** 31 - 1)
            for row in csv.DictReader(f):
                n_post += 1
                if (row.get("Long Description_lang") or "").strip().lower() not in ("en", ""):
                    continue
                occ_id = role_occ.get((row.get("Primary Keyword") or "").strip())
                if not occ_id:
                    continue
                n_used += 1
                roles_matched.add((row.get("Primary Keyword") or "").strip())
                for sid in extract(row.get("Long Description") or ""):
                    pair[(occ_id, sid)] += 1

        rel_rows = [evidence.relation_row(o, s, self.name, weight=w)
                    for (o, s), w in pair.items() if w >= C.DJINNI_MIN_FREQ]
        evidence.write_relations(self.name, rel_rows)

        K.log_provenance(self.name, [{
            "entity_id": self.name, "source": self.name, "source_version": self.version,
            "retrieved_at": K.now_iso(), "retrieval_method": self.retrieval_method,
            "notes": f"{len(rel_rows)} demand relations from {n_used}/{n_post} IT postings "
                     f"({len(roles_matched)} roles, {len({o for o, _ in pair})} occupations)",
        }])
        print(f"[{self.name}] {len(rel_rows)} demand relations from {n_used}/{n_post} IT postings "
              f"({len(roles_matched)} role tags matched, {len({o for o, _ in pair})} occupations).")
