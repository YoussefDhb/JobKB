"""Source plugin base classes.

A `Source` knows how to ingest one data source into the KB's per-source, idempotent CSV
layer (occupations / skills / occupation-skill relations / labels / provenance), already
standardized to the KB schema. Because every write goes through
`common.replace_source_rows` (keyed by the `source` tag), a source only ever touches its
own rows — so a new source can be added or removed without rebuilding the others.

Subclass `StructuredSource` for a dataset with structured fields: implement the
`occupations()`, `skills()`, `relations()` generators returning plain normalized dicts;
the base mints deterministic ids, builds label rows, applies English-primary
standardization (`label_language_status`), and persists everything. Downstream stages then
enrich each source uniformly: `hierarchy` classifies skills (hard/soft + IT sub-domain),
`attach` assigns an ISCO group (NLI-verified) when the source has no native code, and
`merge` folds duplicates into unified concepts — so a new source ends up structurally
identical to the built-in taxonomies.

`ExtractionSource` adds a text->records extraction step for unstructured inputs (e.g.
scraped job postings); the extractor itself is a documented stub to be wired to an HF
skill-extraction model.

Normalized record shape (all keys optional unless noted):
  occupation: {source_id (required, unique in source), label_en, label_fr,
               alt_en:[...], alt_fr:[...], desc_en, desc_fr, isco_code, source_code}
  skill:      {source_id (required), label_en, label_fr, alt_en:[...], alt_fr:[...],
               desc_en, desc_fr, hard_soft ("hard"|"soft"|""), method, skill_type, it_subtype}
  relation:   {occupation_source_id (required), skill_source_id (required), relation_type}
"""

from __future__ import annotations

from .. import config as C
from .. import common as K


def _lang_status(label_en: str, label_fr: str) -> str:
    """English-primary standardization: an EN-only source is `en_native`, a bilingual one
    `en_plus_fr`, and a French-only source `fr_only` (it gains an EN label later, only via
    validated cross-lingual alignment — never machine translation), exactly like ROME."""
    if label_en and label_fr:
        return "en_plus_fr"
    if label_en:
        return "en_native"
    if label_fr:
        return "fr_only"
    return "en_native"


def _join(values) -> str:
    return " | ".join(v.strip() for v in (values or []) if v and v.strip())


class Source:
    """Base source descriptor. `name` is the `source` tag written into every KB row."""

    name: str = ""
    #: contributes real (non ISCO-group) occupations that get aligned across sources
    contributes_occupations: bool = True
    #: has no native ISCO code -> the `attach` stage assigns one
    needs_attach: bool = True
    #: part of the base taxonomy set built by a full `ingest` (plugins are False)
    builtin: bool = False
    version: str = "-"
    retrieval_method: str = "plugin"

    def ingest(self) -> None:
        raise NotImplementedError


class StructuredSource(Source):
    """A source whose records are already structured. Subclasses implement the generators
    below; this base handles id minting, label rows, standardization and persistence."""

    # --- hooks (override) -------------------------------------------------------------
    def occupations(self):
        return []

    def skills(self):
        return []

    def relations(self):
        return []

    # --- row builders -----------------------------------------------------------------
    def _occ_row(self, rec):
        sid = str(rec["source_id"]).strip()
        eid = K.mint_id("OCC_", self.name, sid)
        en, fr = (rec.get("label_en") or "").strip(), (rec.get("label_fr") or "").strip()
        alt_en, alt_fr = rec.get("alt_en") or [], rec.get("alt_fr") or []
        row = {
            "entity_id": eid, "source": self.name, "source_id": sid,
            "isco_code": (rec.get("isco_code") or "").strip(),
            "source_code": (rec.get("source_code") or "").strip(),
            "pref_label_en": en, "pref_label_fr": fr,
            "alt_labels_en": _join(alt_en), "alt_labels_fr": _join(alt_fr),
            "description_en": (rec.get("desc_en") or "").strip(),
            "description_fr": (rec.get("desc_fr") or "").strip(),
            "occupation_type": f"{self.name.lower()}_occupation",
            "label_language_status": _lang_status(en, fr),
        }
        labels = K.make_label_rows(eid, "occupation", self.name,
                                   preferred={"en": [en], "fr": [fr]},
                                   alts={"en": alt_en, "fr": alt_fr})
        return row, labels

    def _skill_row(self, rec):
        sid = str(rec["source_id"]).strip()
        eid = K.mint_id("SKL_", self.name, sid)
        en, fr = (rec.get("label_en") or "").strip(), (rec.get("label_fr") or "").strip()
        alt_en, alt_fr = rec.get("alt_en") or [], rec.get("alt_fr") or []
        row = {
            "entity_id": eid, "source": self.name, "source_id": sid,
            "pref_label_en": en, "pref_label_fr": fr,
            "alt_labels_en": _join(alt_en), "alt_labels_fr": _join(alt_fr),
            "description_en": (rec.get("desc_en") or "").strip(),
            "description_fr": (rec.get("desc_fr") or "").strip(),
            "esco_skill_type": (rec.get("skill_type") or "").strip(),
            "esco_reuse_level": "",
            "hard_soft_provisional": (rec.get("hard_soft") or "").strip(),
            "hard_soft_method": (rec.get("method") or f"{self.name.lower()}_skill").strip(),
            "it_subtype": (rec.get("it_subtype") or "").strip(),
        }
        labels = K.make_label_rows(eid, "skill", self.name,
                                   preferred={"en": [en], "fr": [fr]},
                                   alts={"en": alt_en, "fr": alt_fr})
        return row, labels

    def _rel_row(self, rec):
        return {
            "occupation_entity_id": K.mint_id("OCC_", self.name, str(rec["occupation_source_id"]).strip()),
            "skill_entity_id": K.mint_id("SKL_", self.name, str(rec["skill_source_id"]).strip()),
            "relation_type": (rec.get("relation_type") or "essential").strip(),
            "source": self.name,
        }

    # --- driver -----------------------------------------------------------------------
    def ingest(self) -> None:
        occ_rows, skill_rows, rel_rows, label_rows = [], [], [], []
        for rec in self.occupations():
            row, labels = self._occ_row(rec)
            occ_rows.append(row)
            label_rows.extend(labels)
        for rec in self.skills():
            row, labels = self._skill_row(rec)
            skill_rows.append(row)
            label_rows.extend(labels)
        for rec in self.relations():
            rel_rows.append(self._rel_row(rec))

        # Relevance / noise gate: screen before persisting, so blocked (non-IT / malformed)
        # entities never enter the KB. Also drop their labels + relations. (Lazy import to
        # keep ingest cheap and avoid loading the align models unless the gate runs.)
        from .. import relevance
        occ_rows, skill_rows, blocked, gstats = relevance.filter_rows(occ_rows, skill_rows, self.name)
        if blocked:
            label_rows = [l for l in label_rows if l["entity_id"] not in blocked]
            rel_rows = [r for r in rel_rows if r["occupation_entity_id"] not in blocked
                        and r["skill_entity_id"] not in blocked]

        K.replace_source_rows(C.OCCUPATIONS_CSV, C.OCCUPATION_FIELDS, self.name, occ_rows)
        K.replace_source_rows(C.SKILLS_CSV, C.SKILL_FIELDS, self.name, skill_rows)
        K.replace_source_rows(C.OCC_SKILL_REL_CSV, C.REL_FIELDS, self.name, rel_rows)
        K.upsert_labels(label_rows)
        gate_note = ""
        if gstats:
            gate_note = (f"; gate blocked {gstats['malformed'] + gstats['non_it']} "
                         f"(malformed {gstats['malformed']}, non-IT {gstats['non_it']}), "
                         f"borderline-kept {gstats['borderline']}")
        K.log_provenance(self.name, [{
            "entity_id": self.name, "source": self.name, "source_version": self.version,
            "retrieved_at": K.now_iso(), "retrieval_method": self.retrieval_method,
            "notes": f"{len(occ_rows)} occ, {len(skill_rows)} skills, {len(rel_rows)} relations{gate_note}",
        }])
        print(f"[{self.name}] {len(occ_rows)} occupations, {len(skill_rows)} skills, "
              f"{len(rel_rows)} occ-skill relations.{gate_note}")


class ExtractionSource(StructuredSource):
    """A source of unstructured documents (e.g. scraped job postings). Override
    `documents()` to yield raw texts and `extract(text)` to turn each into structured
    records; the base then standardizes + persists them exactly like a structured source.

    `extract` is a deliberate stub: wire it to an HF skill-extractor (the repo already
    caches `TechWolf/ConTeXT-Skill-Extraction-base` and `TechWolf/JobBERT-v3`) plus an
    occupation-title normalizer. Return shape:
        {"occupation": {occupation-record} | None,
         "skills":     [skill-record, ...],
         "relations":  [{"skill_source_id": ...}, ...]}  # occupation_source_id inferred
    """

    def documents(self):
        return []

    def extract(self, text):
        raise NotImplementedError(
            "ExtractionSource.extract() is a stub. Implement it with an HF skill-extraction "
            "model (e.g. TechWolf/ConTeXT-Skill-Extraction-base) to turn a posting into "
            "{'occupation': {...}, 'skills': [...], 'relations': [...]} records.")

    def _extracted(self):
        if getattr(self, "_cache", None) is None:
            occs, skills, rels = [], [], []
            for doc in self.documents():
                res = self.extract(doc) or {}
                occ = res.get("occupation")
                if occ:
                    occs.append(occ)
                for s in res.get("skills", []):
                    skills.append(s)
                for r in res.get("relations", []):
                    if occ and "occupation_source_id" not in r:
                        r = {**r, "occupation_source_id": occ["source_id"]}
                    rels.append(r)
            self._cache = (occs, skills, rels)
        return self._cache

    def occupations(self):
        return self._extracted()[0]

    def skills(self):
        return self._extracted()[1]

    def relations(self):
        return self._extracted()[2]
