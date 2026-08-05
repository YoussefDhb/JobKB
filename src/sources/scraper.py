"""SCRAPER: opt-in web-scraping enrichment (emerging occupations, skills, technologies).

Ingests the offline snapshot written by `src/scrape.py` (RESOURCES/SCRAPED/**). Hybrid extraction like
DATAJOBS/DJINNI but over scraped free-text postings:
  * occupations — each posting title is cleaned (seniority/contract/gender tokens stripped), routed
    through the EMERGING patterns, and resolved against the current KB; a title that recurs, is genuinely
    new and clears the relevance gate is minted as an occupation (needs_attach -> ISCO via `attach`).
  * skills — dictionary matching of the posting text against the KB's own skill labels (EN+FR) yields
    demand relations to existing skills (the DJINNI-safe path for prose); an optional HF skill-span
    extractor adds genuinely-novel spans, which must still clear a frequency floor AND the relevance/noise
    gate before they are minted. Cross-source `merge` folds scraped skills into their unified concepts.

Everything is offline/deterministic/idempotent (source-scoped writes keyed by SCRAPER); a re-ingest
re-derives from the snapshot with no double counting.
"""

from __future__ import annotations

import csv
import datetime as _dt
import glob
import os
import re
from collections import Counter, defaultdict

from .. import config as C
from .. import common as K
from .base import ExtractionSource
from . import evidence
from .emerging_roles import EMERGING_ROLES

_SEP = re.compile(r"\s*[,|]\s*|\s+[-–—/]\s+|\s+(?:chez|at|@)\s+", re.I)  # role / company / team boundary
_PAREN = re.compile(r"\([^)]*\)")
_GENDER = re.compile(r"\b[hfmw]\s*/\s*[hfmw]\b", re.I)          # H/F, F/H, M/W, …
# Occupational head nouns: a scraped title is only *minted* as an occupation if it ends in one of these
# (drops generic "manager"/"lead" and prose), and the title is truncated to the head to collapse the
# team-suffixed ATS variants ("ML Engineer, Relevance & Personalization" -> "machine learning engineer").
_ROLE_HEAD = re.compile(r"\b(engineer|developer|scientist|analyst|architect|administrator|programmer|"
                        r"technician|specialist|designer|researcher|sre|devops|dba|"
                        r"ing[eé]nieur|d[eé]veloppeur|analyste|architecte|technicien|concepteur)\b", re.I)
_TOKEN = re.compile(r"[A-Za-z0-9][A-Za-z0-9+.#-]*")
# A well-formed skill span (starts with a letter) — rejects WordPiece fragments ("##al", "#x") the NER emits.
_CLEAN_SPAN = re.compile(r"^[A-Za-z][A-Za-z0-9+.#/&' -]*$")

# Single-token skill matches on free prose are unsafe (DJINNI's lesson: "react"/"application"/"go" are
# ambiguous). A 1-gram is accepted only if it is a concrete-tech skill AND not in this denylist; multi-word
# matches are specific enough to trust. Reuses the DJINNI denylist plus a few generic prose words.
_TEXT_DENY = frozenset(C.DJINNI_TEXT_DENY) | {
    "api", "service", "services", "solution", "solutions", "application", "applications",
    "stack", "team", "teams", "chef", "data", "experience", "production",
}


def _clean_title(raw: str) -> str:
    """Fold a raw posting title to a bare role phrase: drop parentheticals, gender/contract markers, and
    the company/team tail (after a comma/pipe/dash), strip seniority stopwords, and truncate to the ≤N
    words ending at the occupational head noun so team-suffixed ATS variants collapse to the core role."""
    t = _GENDER.sub(" ", _PAREN.sub(" ", raw or ""))
    for seg in _SEP.split(t):
        words = [w.strip(" \t,.;:·•!?\"'()[]{}") for w in seg.split()]
        words = [w for w in words if w and K.normalize_label(w) not in C.SCRAPER_TITLE_STOPWORDS]
        if not words:
            continue
        phrase = " ".join(words)
        m = _ROLE_HEAD.search(phrase)
        if m:                                   # keep the ≤N words ending at the role head
            return " ".join(phrase[:m.end()].split()[-C.SCRAPER_TITLE_MAX_WORDS:])
        return " ".join(words[:C.SCRAPER_TITLE_MAX_WORDS])
    return ""


def _ngrams(tokens, n):
    for i in range(len(tokens) - n + 1):
        yield i, " ".join(tokens[i:i + n])


# Generic / employment tags that arrive in the `tags[]` arrays but are not skills.
_TAG_STOP = {K.normalize_label(x) for x in (list(C.SCRAPER_TITLE_STOPWORDS) + [
    "remote", "hybrid", "onsite", "full time", "part time", "contract", "internship", "entry level",
    "mid level", "senior level", "freelance", "startup", "english", "worldwide", "anywhere", "usa",
    "uk", "europe", "b2b", "saas", "fintech", "featured", "visa", "relocation", "equity", "salary",
    "benefits", "engineering", "design", "marketing", "sales", "finance", "hr", "recruiting",
    # role words are occupations, not skills; plus generic job-board tag noise
    "engineer", "developer", "dev", "analyst", "architect", "scientist", "designer", "manager",
    "chat", "digital nomad", "marketplace", "technical", "research", "documentation", "prototyping",
    "people management", "engineering management", "business", "product", "commercial", "ops",
    "non tech", "growth", "operations", "support", "consulting", "education", "medical", "legal",
])}


def _parse_date(s):
    """Parse an ISO-8601 or RFC-822 (RSS) date string to an aware datetime, or None."""
    s = (s or "").strip()
    if not s:
        return None
    if "," in s and re.search(r"[A-Za-z]{3}", s):          # RFC-822: "Wed, 22 Jul 2026 07:00:51 +0000"
        try:
            from email.utils import parsedate_to_datetime
            return parsedate_to_datetime(s)
        except (TypeError, ValueError, IndexError):
            pass
    try:
        return _dt.datetime.fromisoformat(s.replace("Z", "+00:00"))
    except ValueError:
        return None


def _recency_weight(posted_at):
    """Exponential recency decay so `demand` tracks the current market (missing date -> 1.0)."""
    dt = _parse_date(posted_at)
    if not dt:
        return 1.0
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=_dt.timezone.utc)
    age = max(0.0, (_dt.datetime.now(_dt.timezone.utc) - dt).total_seconds() / 86400.0)
    return 0.5 ** (age / C.SCRAPER_RECENCY_HALFLIFE_DAYS)


class ScraperSource(ExtractionSource):
    name = C.SRC_SCRAPER
    contributes_occupations = True
    needs_attach = True
    builtin = False                 # opt-in only (network-gated); never part of a full build
    screen_relevance = True         # scraped free text is noisy -> the IT/noise gate is essential
    version = "web-scraper-2026"
    retrieval_method = "network_scraped"

    # --- snapshot documents ------------------------------------------------------------
    def documents(self):
        for path in sorted(glob.glob(os.path.join(C.SCRAPED_DIR, "**", "*.csv"), recursive=True)):
            with open(path, encoding="utf-8", newline="") as f:
                for r in csv.DictReader(f):
                    if (r.get("title") or "").strip():
                        yield r

    # --- per-posting extraction (the ExtractionSource hook) ----------------------------
    def extract(self, doc):
        """Turn one posting into {occupation, skills}: a cleaned/resolved title + the skills mentioned
        (existing KB skills matched in the text, plus novel neural spans). Corpus-level frequency and
        the relevance gate are applied later, in `ingest`."""
        occ_index = self._occ_index()
        skill_index = self._skill_index()

        title = _clean_title(doc.get("title", ""))
        occ = None
        if title and 1 <= len(title.split()) <= C.SCRAPER_TITLE_MAX_WORDS:
            key = evidence.match_key(title)
            if key:
                occ = {"key": key, "label": title.lower(), "lang": (doc.get("lang") or "en").strip(),
                       "existing_id": self._resolve_occ(doc.get("title", ""), key, occ_index)}

        text = doc.get("text", "")
        skills, covered = [], set()
        norm_tokens = _TOKEN.findall(K.normalize_label(text))
        for n in (3, 2, 1):                                    # longest match wins, mark covered spans
            for i, gram in _ngrams(norm_tokens, n):
                if any((i + j) in covered for j in range(n)):
                    continue
                mk = evidence.match_key(gram)
                hit = skill_index.get(mk)
                if not hit:
                    continue
                sid, subtype = hit
                if subtype not in C.DJINNI_CONCRETE_SUBDOMAINS:
                    continue            # concrete tech only — generic/soft ESCO verb-phrases are prose noise
                if n == 1 and (gram in _TEXT_DENY or mk in _TEXT_DENY):
                    continue            # ambiguous bare token (also catches plurals: "makes" -> "make")
                skills.append({"key": mk, "label": gram, "existing_id": sid, "src": "dict"})
                covered.update(range(i, i + n))
        for span in self._neural_spans(text):                 # NER strengthens demand to EXISTING skills
            mk = evidence.match_key(span)
            if not mk:
                continue
            hit = skill_index.get(mk)
            skills.append({"key": mk, "label": span.strip().lower(),
                           "existing_id": hit[0] if hit else None, "src": "ner"})
        # Pre-extracted skill tags (Remotive/RemoteOK/The Muse/GitHub): curated keywords, not prose, so
        # they bypass the concrete-subtype/denylist prose guards — the highest-precision skill signal.
        for tag in (doc.get("tags") or "").split("|"):
            tag = tag.strip()
            if not tag or K.normalize_label(tag) in _TAG_STOP:
                continue
            mk = evidence.match_key(tag)
            if not mk:
                continue
            hit = skill_index.get(mk)
            skills.append({"key": mk, "label": tag.lower(), "existing_id": hit[0] if hit else None,
                           "src": "tag"})     # curated -> the only source allowed to MINT a novel skill
        return {"occupation": occ, "skills": skills}

    # --- corpus-level ingest (frequency + gate + resolve-to-existing + mint) ------------
    def ingest(self) -> None:
        docs = list(self.documents())

        title_freq, title_label, title_existing = Counter(), {}, {}
        title_skilled = set()                                  # titles whose postings mention IT skills
        tok_freq, tok_label, tok_existing = Counter(), {}, {}
        tok_taggable = set()                                   # skills seen from a curated `tags[]` source
        pair = defaultdict(int)                                # (title_key, skill_key) -> posting count
        pair_wt = defaultdict(float)                           # ... -> recency-weighted demand
        for doc in docs:
            res = self.extract(doc)
            occ = res.get("occupation")
            okey = occ["key"] if occ else None
            skills_here = res.get("skills", [])
            w = _recency_weight(doc.get("posted_at"))          # recent postings weigh more
            if occ:
                title_freq[okey] += 1
                title_label.setdefault(okey, (occ["label"], occ["lang"]))
                if occ["existing_id"]:
                    title_existing[okey] = occ["existing_id"]
                if skills_here:
                    title_skilled.add(okey)
            seen_keys = set()
            for s in skills_here:
                skey = s["key"]
                if skey in seen_keys:
                    continue                                   # count a skill once per posting
                seen_keys.add(skey)
                tok_freq[skey] += 1
                tok_label.setdefault(skey, s["label"])
                if s["existing_id"]:
                    tok_existing[skey] = s["existing_id"]
                if s.get("src") == "tag":
                    tok_taggable.add(skey)
                if okey:
                    pair[(okey, skey)] += 1
                    pair_wt[(okey, skey)] += w

        # Mint genuinely-new occupations (recurring, unresolved) and novel skills (recurring, unmatched).
        # Mint a new occupation only if the title recurs, is genuinely new, AND its postings mention IT
        # skills — the strongest noise filter for scraped titles (a non-IT job's postings have no IT tools).
        occ_recs, occ_sid = [], {}
        for key, freq in title_freq.items():
            label, lang = title_label[key]
            # Mint only a genuine emerging role: recurs, unresolved, IT-skilled, ends in an occupational
            # head noun, and >=2 words (a bare "engineer"/"developer" is too generic to be an occupation).
            if (freq >= C.SCRAPER_MIN_OCC_FREQ and key not in title_existing and key in title_skilled
                    and _ROLE_HEAD.search(label) and len(label.split()) >= 2):
                sid = K.normalize_label(label).replace(" ", "_")[:60]
                occ_sid[key] = sid
                # A truthful description from the role's most-demanded skills — gives the ISCO `attach`
                # NLI real signal (scraped titles otherwise have no definition, forcing low-confidence).
                top = sorted((sk for (o, sk) in pair if o == key),
                             key=lambda sk: pair[(key, sk)], reverse=True)[:8]
                skills_txt = ", ".join(tok_label[sk] for sk in top)
                desc = (f"An information-technology role ({label}); job postings for it commonly require "
                        f"{skills_txt}." if skills_txt else "")
                occ_recs.append({"source_id": sid, "lang": lang, "label": label, "desc": desc})
        # Mint a novel skill only from a curated `tags[]`/GitHub-topic source (clean emerging-tech signal);
        # NER/dictionary matches on free prose only strengthen demand to EXISTING skills, never mint.
        skill_recs, skill_sid = [], {}
        for key, freq in tok_freq.items():
            if freq >= C.SCRAPER_MIN_SKILL_FREQ and key not in tok_existing and key in tok_taggable:
                label = tok_label[key]
                sid = K.normalize_label(label).replace(" ", "_")[:60] or key.replace(" ", "_")
                skill_sid[key] = sid
                skill_recs.append({"source_id": sid, "lang": "en", "label": label})

        occ_rows, skill_rows, label_rows = [], [], []
        for rec in occ_recs:
            en = rec["label"] if rec["lang"] == "en" else ""
            fr = rec["label"] if rec["lang"] == "fr" else ""
            row, labels = self._occ_row({"source_id": rec["source_id"], "label_en": en, "label_fr": fr,
                                         "desc_en": rec.get("desc", "")})   # skills-derived def -> better attach
            occ_rows.append(row)
            label_rows.extend(labels)
        for rec in skill_recs:
            row, labels = self._skill_row({
                "source_id": rec["source_id"], "label_en": rec["label"],
                "hard_soft": "hard", "method": "scraper_skill",
                "it_subtype": C.SCRAPER_SUBDOMAIN.get(K.normalize_label(rec["label"]), ""),
            })
            skill_rows.append(row)
            label_rows.extend(labels)

        # Relevance / noise gate — the same acceptance criteria every source passes (blocked rows are
        # logged to kb/blocked_entities.csv and never enter the KB).
        blocked, gstats = set(), None
        from .. import relevance
        occ_rows, skill_rows, blocked, gstats = relevance.filter_rows(occ_rows, skill_rows, self.name)
        if blocked:
            label_rows = [l for l in label_rows if l["entity_id"] not in blocked]
        kept_occ = {r["entity_id"] for r in occ_rows}
        kept_skill = {r["entity_id"] for r in skill_rows}

        K.replace_source_rows(C.OCCUPATIONS_CSV, C.OCCUPATION_FIELDS, self.name, occ_rows)
        K.replace_source_rows(C.SKILLS_CSV, C.SKILL_FIELDS, self.name, skill_rows)
        K.upsert_labels(label_rows)

        # Resolve each (title, skill) pair to entity ids (existing KB entity, or a kept minted one) and
        # write weighted demand relations.
        def occ_endpoint(key):
            if key in title_existing:
                return title_existing[key]
            eid = K.mint_id("OCC_", self.name, occ_sid[key]) if key in occ_sid else None
            return eid if eid in kept_occ else None

        def skill_endpoint(key):
            if key in tok_existing:
                return tok_existing[key]
            eid = K.mint_id("SKL_", self.name, skill_sid[key]) if key in skill_sid else None
            return eid if eid in kept_skill else None

        # Keep an edge if the (occ, skill) pair recurs >= the floor (posting count); weight it by the
        # recency-decayed sum so the graph reflects *current* demand.
        agg_cnt, agg_wt = defaultdict(int), defaultdict(float)
        for (okey, skey), c in pair.items():
            oid, sid = occ_endpoint(okey), skill_endpoint(skey)
            if oid and sid:
                agg_cnt[(oid, sid)] += c
                agg_wt[(oid, sid)] += pair_wt[(okey, skey)]
        rel_rows = [evidence.relation_row(o, s, self.name, weight=round(agg_wt[(o, s)], 1),
                                          relation_type="demand")
                    for (o, s), c in agg_cnt.items() if c >= C.SCRAPER_MIN_DEMAND_FREQ]
        evidence.write_relations(self.name, rel_rows)

        gate_note = ""
        if gstats:
            gate_note = (f"; gate blocked {gstats['malformed'] + gstats['non_it']} "
                         f"(non-IT {gstats['non_it']}, malformed {gstats['malformed']})")
        K.log_provenance(self.name, [{
            "entity_id": self.name, "source": self.name, "source_version": self.version,
            "retrieved_at": K.now_iso(), "retrieval_method": self.retrieval_method,
            "notes": f"{len(occ_rows)} new occupations, {len(skill_rows)} new skills, "
                     f"{len(rel_rows)} demand relations from {len(docs)} scraped postings{gate_note}",
        }])
        print(f"[{self.name}] {len(occ_rows)} new occupations, {len(skill_rows)} new skills, "
              f"{len(rel_rows)} demand relations from {len(docs)} scraped postings.{gate_note}")

    # --- lazily-built indices + optional neural extractor ------------------------------
    def _occ_index(self):
        """{match_key -> occupation entity_id} for real occupations, EXCLUDING this source's own rows so
        a re-ingest re-mints its titles to the same deterministic ids (idempotent) instead of resolving
        to the rows it is about to replace."""
        if getattr(self, "_occ_idx", None) is None:
            occ = [r for r in K.read_all(C.OCCUPATIONS_CSV)
                   if r.get("occupation_type") != "isco_group" and r.get("source") != self.name]
            self._occ_idx = evidence._label_index(
                occ, ("pref_label_en", "pref_label_fr", "alt_labels_en", "alt_labels_fr"))
            self._emerging = [(re.compile(r["pattern"], re.I),
                               K.mint_id("OCC_", C.SRC_EMERGING, r["source_id"])) for r in EMERGING_ROLES]
        return self._occ_idx

    def _skill_index(self):
        """{match_key(label) -> (skill entity_id, it_subtype)} over real KB skills (exact labels only —
        the vendor-strip matcher is unsafe on prose). Excludes taxonomy nodes and this source's own rows
        so a re-ingest re-derives cleanly."""
        if getattr(self, "_skill_idx", None) is None:
            idx = {}
            for r in K.read_all(C.SKILLS_CSV):
                if (r.get("source") == self.name
                        or r.get("esco_skill_type") in C.TAXONOMY_SKILL_MARKERS):
                    continue
                val = (r["entity_id"], r.get("it_subtype", ""))
                for field in ("pref_label_en", "pref_label_fr", "alt_labels_en", "alt_labels_fr"):
                    for lbl in (r.get(field) or "").split(" | "):
                        k = evidence.match_key(lbl)
                        if k and k not in idx:
                            idx[k] = val
            self._skill_idx = idx
        return self._skill_idx

    def _resolve_occ(self, raw_title, key, occ_index):
        """Existing occupation entity id for a title, via KB label match or an EMERGING pattern."""
        if key in occ_index:
            return occ_index[key]
        for rx, eid in getattr(self, "_emerging", []):
            if rx.search(raw_title or ""):
                return eid
        return None

    def _neural_spans(self, text):
        """Best-effort HF skill-span extraction (novel spans). Fail-open: any load/inference error, or
        the feature disabled, yields nothing and the deterministic dictionary path still runs."""
        if not C.SCRAPER_EXTRACTOR_ENABLED or not (text or "").strip():
            return []
        nlp = getattr(self, "_nlp", None)
        if nlp is None:
            try:
                from transformers import pipeline
                nlp = pipeline("token-classification", model=C.SCRAPER_EXTRACTOR_MODEL,
                               aggregation_strategy="simple")
            except Exception:  # noqa: BLE001 — model unavailable/incompatible/offline -> disable neural path
                nlp = False
            self._nlp = nlp
        if not nlp:
            return []
        try:                                        # keep typed skill spans; drop O/BUS + WordPiece junk
            keep = {"TECHNOLOGY", "TECHNICAL", "SOFT", "SKILL", "KNOWLEDGE"}
            out = []
            for e in nlp(text[:2000]):
                if e.get("entity_group") not in keep and e.get("entity_group") != "B":
                    continue
                w = (e.get("word") or "").strip()
                if 2 <= len(w) <= 40 and _CLEAN_SPAN.match(w):   # drops "##al"/"#x" subword fragments
                    out.append(w)
            return out
        except Exception:  # noqa: BLE001
            return []
