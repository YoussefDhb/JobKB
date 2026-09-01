"""Bilingual label completion: fill empty EN/FR labels on the unified tables."""
from __future__ import annotations

import csv
import hashlib
import os
import re

from . import config as C
from . import common as K


# Snapshots (resumable / reproducible)
def _hash(text: str) -> str:
    return hashlib.sha1(text.encode("utf-8")).hexdigest()[:16]


def _load_snapshot() -> dict:
    """Load the MT snapshot (direction, src_hash) -> {src,out,guard_ok,validated,score,reason}."""
    snap = {}
    if os.path.isfile(C.TRANSLATE_SNAPSHOT_CSV):
        with open(C.TRANSLATE_SNAPSHOT_CSV, encoding="utf-8", newline="") as f:
            for r in csv.DictReader(f):
                snap[(r["direction"], r["src_hash"])] = r
    return snap


def _save_snapshot(snap: dict) -> None:
    os.makedirs(C.TRANSLATE_RETRIEVED_DIR, exist_ok=True)
    rows = sorted(snap.values(), key=lambda r: (r["direction"], r["src_hash"]))
    with open(C.TRANSLATE_SNAPSHOT_CSV, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=C.TRANSLATE_SNAPSHOT_FIELDS)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in C.TRANSLATE_SNAPSHOT_FIELDS})


def _load_wd_labels() -> dict:
    """qid -> {"en","fr"} authoritative Wikidata labels."""
    out = {}
    if os.path.isfile(C.TRANSLATE_WD_LABELS_CSV):
        with open(C.TRANSLATE_WD_LABELS_CSV, encoding="utf-8", newline="") as f:
            for r in csv.DictReader(f):
                out[r["qid"]] = {"en": r.get("label_en", ""), "fr": r.get("label_fr", "")}
    return out


def _save_wd_labels(labels: dict) -> None:
    os.makedirs(C.TRANSLATE_RETRIEVED_DIR, exist_ok=True)
    with open(C.TRANSLATE_WD_LABELS_CSV, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=C.TRANSLATE_WD_LABELS_FIELDS)
        w.writeheader()
        for qid in sorted(labels):
            w.writerow({"qid": qid, "label_en": labels[qid].get("en", ""),
                        "label_fr": labels[qid].get("fr", "")})


# Tech-term preservation guard
_CAMEL = re.compile(r"[a-z][A-Z]")
_STRIP = " ,.;:()[]{}\"'/’"


def _is_protected_token(tok: str) -> bool:
    """True for a technology proper-noun / acronym / version token that MT must not translate."""
    core = tok.strip(_STRIP)
    if not core:
        return False
    low = core.lower()
    if low in C.TRANSLATE_TECH_LEXICON:
        return True
    if core.isupper() and len(core) >= 2 and any(ch.isalpha() for ch in core):
        return True                      # acronym: SQL, API, ML, AWS, S3, EC2
    if _CAMEL.search(core):
        return True                      # CamelCase: PyTorch, JavaScript, TensorFlow
    if any(ch.isdigit() for ch in core) or any(ch in "+#" for ch in core):
        return True                      # version / symbol: C++, C#, Python3, .NET, ISO27001
    if "." in core and not core.endswith("."):
        return True                      # dotted tech: .NET, Node.js, asp.net
    return False


def _is_fully_protected(label: str) -> bool:
    """The whole label is a single technology term → keep verbatim in both languages, no MT."""
    lab = label.strip()
    if not lab:
        return False
    if len(lab) <= 2:                             
        return True
    if lab.lower() in C.TRANSLATE_TECH_LEXICON:   
        return True
    alnum_tokens = [t for t in lab.split() if any(ch.isalnum() for ch in t)]
    return bool(alnum_tokens) and all(_is_protected_token(t) for t in alnum_tokens)


_PH = re.compile(r"^Zt\d+z$")
_LEX_PHRASES = None


def _lex_phrases():
    """Multi-word tech-lexicon entries, longest first."""
    global _LEX_PHRASES
    if _LEX_PHRASES is None:
        _LEX_PHRASES = sorted((p for p in C.TRANSLATE_TECH_LEXICON if " " in p),
                              key=len, reverse=True)
    return _LEX_PHRASES


def _protect(text: str):
    """Mask multi-word lexicon phrases and any protected tokens with placeholders, so MT never translates them."""
    mapping = {}
    masked = text
    for phrase in _lex_phrases():
        def _sub(m):
            ph = f"Zt{len(mapping)}z"
            mapping[ph] = m.group(0)
            return ph
        masked = re.compile(re.escape(phrase), re.IGNORECASE).sub(_sub, masked)
    out = []
    for tok in masked.split():
        core = tok.strip(_STRIP)
        if _PH.match(core):           
            out.append(tok)
        elif core and _is_protected_token(tok):
            ph = f"Zt{len(mapping)}z"
            mapping[ph] = tok
            out.append(ph)
        else:
            out.append(tok)
    return " ".join(out), mapping


def _restore(text: str, mapping: dict):
    """Restore masked tokens. Returns (restored_text, ok) — ok=False if any placeholder was lost."""
    ok = True
    for ph, orig in mapping.items():
        if ph in text:
            text = text.replace(ph, orig)
        else:
            ok = False
    return text, ok


# MT engine (local HuggingFace NLLB)
class Translator:
    """Local NLLB MT engine (HuggingFace) with a tech-term guard. Fail-open: if the model is missing or unavailable"""

    def __init__(self):
        self.ok = False
        self._tok = None
        self._model = None
        try:
            import torch
            from transformers import AutoModelForSeq2SeqLM, AutoTokenizer
            from transformers.utils import logging as _hf_logging
            _hf_logging.set_verbosity_error()
            try:
                os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
                import os as _os
                torch.set_num_threads(_os.cpu_count() or 1)
            except Exception:
                pass
            self._torch = torch
            self._tok = AutoTokenizer.from_pretrained(C.TRANSLATE_MT_MODEL, token=C.HF_TOKEN or None)
            self._model = AutoModelForSeq2SeqLM.from_pretrained(C.TRANSLATE_MT_MODEL,
                                                                token=C.HF_TOKEN or None)
            self._model.eval()
            self.ok = True
            print(f"[TRANSLATE] MT model = {C.TRANSLATE_MT_MODEL}", flush=True)
        except Exception as e:  
            print(f"[TRANSLATE] MT unavailable ({type(e).__name__}: {e}); "
                  f"install sentencepiece / check the model. MT-dependent fills skipped.", flush=True)

    def _generate(self, texts, src_code, tgt_code, num_beams):
        tok, model, torch = self._tok, self._model, self._torch
        tok.src_lang = src_code
        bos = tok.convert_tokens_to_ids(tgt_code)
        outs = []
        bs = C.TRANSLATE_BATCH_SIZE
        for i in range(0, len(texts), bs):
            chunk = texts[i:i + bs]
            enc = tok(chunk, return_tensors="pt", padding=True, truncation=True, max_length=128)
            with torch.no_grad():
                gen = model.generate(**enc, forced_bos_token_id=bos, num_beams=num_beams,
                                     max_new_tokens=C.TRANSLATE_MAX_NEW_TOKENS)
            outs.extend(tok.batch_decode(gen, skip_special_tokens=True))
        return outs

    def translate_many(self, texts, src, tgt, num_beams=4, protect=True):
        """Translate a batch of texts from `src` to `tgt`. Returns list of (output, guard_ok) tuples."""
        if not self.ok or not texts:
            return [("", False) for _ in texts]
        src_code, tgt_code = C.TRANSLATE_LANG_CODES[src], C.TRANSLATE_LANG_CODES[tgt]
        masked, maps = [], []
        for t in texts:
            m, mp = _protect(t) if protect else (t, {})
            masked.append(m)
            maps.append(mp)
        raw = self._generate(masked, src_code, tgt_code, num_beams)
        results = []
        for out, mp in zip(raw, maps):
            restored, ok = _restore(out.strip(), mp)
            results.append((restored, ok))
        return results


# Validation (pillar 4)
class Validator:
    """Validate MT output with a lenient cross-lingual semantic floor (bge-m3) + structural filters. Rejects are logged."""

    def __init__(self, translator: Translator = None):
        self._t = translator
        self._embedder = None
        self.rejects = []

    def _xling_cosines(self, pairs):
        """Cross-lingual cosine for (src, out) pairs via bge-m3."""
        if not pairs:
            return []
        from sklearn.metrics.pairwise import cosine_similarity
        if self._embedder is None:
            from .align.candidates import get_embedder
            self._embedder = get_embedder()
        flat = [x for p in pairs for x in p]
        vecs = self._embedder.encode(flat)
        return [float(cosine_similarity(vecs[2 * i:2 * i + 1], vecs[2 * i + 1:2 * i + 2])[0][0])
                for i in range(len(pairs))]

    @staticmethod
    def _looks_like_sentence(src, out):
        """MT sometimes describes a term instead of naming it. Flag when a short source yields sentence-like output."""
        low = out.lower().lstrip("\"'([ ")
        if any(low.startswith(s) for s in C.TRANSLATE_SENTENCE_STARTS):
            return True
        return (len(src.split()) <= 3 and out.rstrip().endswith(".")
                and len(out) > 2.0 * len(src) and "." not in src)

    def _sanity(self, src, out, guard_ok):
        if not out.strip():
            return False, "empty"
        if not guard_ok or re.search(r"Zt\d+z", out):
            return False, "lost_protected_token"
        r = len(out) / max(len(src), 1)
        if r < C.TRANSLATE_LEN_RATIO_MIN or r > C.TRANSLATE_LEN_RATIO_MAX:
            return False, f"len_ratio={r:.2f}"
        if self._looks_like_sentence(src, out):
            return False, "sentence_not_label"
        if K.normalize_label(out) == K.normalize_label(src):
            # Output identical to source
            return True, "verbatim"
        return True, ""

    def validate_batch(self, direction, items):
        """items: list of dict(unified_id, src, out, guard_ok). Returns list of (ok, score, reason)."""
        results = [None] * len(items)
        to_check = []
        for idx, it in enumerate(items):
            ok, reason = self._sanity(it["src"], it["out"], it["guard_ok"])
            if not ok:
                results[idx] = (False, 0.0, reason)
            elif reason == "verbatim":
                results[idx] = (True, 1.0, "verbatim")
            else:
                to_check.append(idx)
        # Lenient cross-lingual floor for the survivors
        cos = self._xling_cosines([(items[i]["src"], items[i]["out"]) for i in to_check])
        for j, idx in enumerate(to_check):
            score = cos[j]
            ok = score >= C.TRANSLATE_XLING_MIN
            results[idx] = (ok, score, "" if ok else f"xling={score:.2f}")
        for idx, it in enumerate(items):
            ok, score, reason = results[idx]
            if not ok:
                self.rejects.append({"direction": direction, "unified_id": it["unified_id"],
                                     "src_text": it["src"], "output": it["out"],
                                     "reason": reason, "score": f"{score:.3f}"})
        return results

    def dump_rejects(self):
        """Write the rejected MT outputs to a CSV for inspection."""
        os.makedirs(C.KB_DIR, exist_ok=True)
        snap = _load_snapshot()
        rows = sorted((r for r in snap.values() if r.get("validated") == "0"),
                      key=lambda r: (r.get("direction", ""), r.get("src_text", "")))
        with open(C.TRANSLATE_REJECTED_CSV, "w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=C.TRANSLATE_REJECTED_FIELDS)
            w.writeheader()
            for r in rows:
                w.writerow({k: r.get(k, "") for k in C.TRANSLATE_REJECTED_FIELDS})


# L1 — Wikidata authoritative labels + aliases
def _wd_links_by_uid() -> dict:
    """unified_id -> {"qid","aliases_en","aliases_fr"} from the Wikidata side table."""
    out = {}
    if not os.path.isfile(C.WIKIDATA_LINKS_CSV):
        return out
    for r in K.read_all(C.WIKIDATA_LINKS_CSV):
        uid = r.get("unified_id", "")
        if uid:
            out[uid] = {"qid": r.get("qid", ""),
                        "aliases_en": r.get("wd_aliases_en", ""),
                        "aliases_fr": r.get("wd_aliases_fr", "")}
    return out


def _fetch_wd_labels(qids, cache):
    """Fetch Wikidata @en/@fr labels for `qids` (cached). Returns qid -> {"en","fr"}."""
    todo = [q for q in dict.fromkeys(qids) if q and q not in cache]
    if not todo:
        return cache
    from . import wikidata as W
    for i in range(0, len(todo), 180):
        batch = todo[i:i + 180]
        values = " ".join(f"wd:{q}" for q in batch)
        query = (
            "SELECT ?item ?en ?fr WHERE { "
            f"VALUES ?item {{ {values} }} "
            'OPTIONAL { ?item rdfs:label ?en FILTER(lang(?en)="en") } '
            'OPTIONAL { ?item rdfs:label ?fr FILTER(lang(?fr)="fr") } }'
        )
        js = W._http_get(C.WIKIDATA_SPARQL_URL, {"query": query, "format": "json"})
        got = {q: {"en": "", "fr": ""} for q in batch} 
        if js:
            for b in js.get("results", {}).get("bindings", []):
                qid = b.get("item", {}).get("value", "").rsplit("/", 1)[-1]
                if qid in got:
                    if b.get("en"):
                        got[qid]["en"] = b["en"]["value"]
                    if b.get("fr"):
                        got[qid]["fr"] = b["fr"]["value"]
        cache.update(got)
        print(f"[TRANSLATE] wikidata labels fetched: {min(i + 180, len(todo))}/{len(todo)}", flush=True)
    return cache


# Apply — fill empty label cells from Wikidata (L1) then the MT snapshot (L2).
def _first_alias(pipe_joined: str) -> str:
    for part in (pipe_joined or "").split(" | "):
        part = part.strip()
        if part:
            return part
    return ""


def apply_enrichment(rows, kind):
    """Fill empty ``primary_label_en/fr`` (Wikidata → MT snapshot) and empty ``alt_labels_en/fr`` """
    snap = _load_snapshot()
    wd_labels = _load_wd_labels()
    wd_links = _wd_links_by_uid()
    if not (snap or wd_labels or wd_links):
        return rows

    def _mt(direction, src_text):
        cell = snap.get((direction, _hash(src_text)))
        if cell and cell.get("validated") == "1":
            return cell.get("output", "")
        return ""

    for r in rows:
        uid = r.get("unified_id", "")
        link = wd_links.get(uid, {})
        qid = (r.get("wikidata_qid") or link.get("qid") or "").strip()
        wl = wd_labels.get(qid, {}) if qid else {}
        en = (r.get("primary_label_en") or "").strip()
        fr = (r.get("primary_label_fr") or "").strip()

        # French primary: Wikidata @fr → first FR alias → validated en->fr MT of the English label.
        if not fr:
            cand = wl.get("fr") or _first_alias(link.get("aliases_fr", ""))
            if not cand and en:
                cand = _mt("en_fr", en)
            if cand:
                r["primary_label_fr"] = cand
        # English primary: Wikidata @en → first EN alias → validated fr->en MT.
        if not en:
            cand = wl.get("en") or _first_alias(link.get("aliases_en", ""))
            if not cand and fr and C.TRANSLATE_ROME_EN_ENABLED:
                cand = _mt("fr_en", fr)
            if cand:
                r["primary_label_en"] = cand

        # Alt labels: Wikidata aliases only (per project decision, no bulk MT of aliases).
        if not (r.get("alt_labels_en") or "").strip() and link.get("aliases_en"):
            r["alt_labels_en"] = link["aliases_en"]
        if not (r.get("alt_labels_fr") or "").strip() and link.get("aliases_fr"):
            r["alt_labels_fr"] = link["aliases_fr"]
    return rows


# Generation orchestration
_UNIFIED = {
    "occupation": (C.UNIFIED_OCCUPATIONS_CSV,),
    "skill": (C.UNIFIED_SKILLS_CSV,),
}


def _mt_targets(direction, wd_labels, wd_links):
    """Collect (unified_id, src_text) needing MT for `direction`. Dedups identical source texts."""
    src_lang, tgt_lang = direction.split("_")
    src_col, tgt_col = f"primary_label_{src_lang}", f"primary_label_{tgt_lang}"
    seen, targets = set(), []
    for path in (C.UNIFIED_OCCUPATIONS_CSV, C.UNIFIED_SKILLS_CSV):
        if not os.path.isfile(path):
            continue
        for r in K.read_all(path):
            if (r.get(tgt_col) or "").strip():
                continue                      
            src_text = (r.get(src_col) or "").strip()
            if not src_text:
                continue
            uid = r.get("unified_id", "")
            link = wd_links.get(uid, {})
            qid = (r.get("wikidata_qid") or link.get("qid") or "").strip()
            wl = wd_labels.get(qid, {}) if qid else {}
            if wl.get(tgt_lang) or _first_alias(link.get(f"aliases_{tgt_lang}", "")):
                continue                     
            key = src_text
            if key in seen:
                continue
            seen.add(key)
            targets.append((uid, src_text))
    return targets


def _translate_direction(direction, translator, validator, snap, wd_labels, wd_links, save=None):
    """Generate + validate MT for one direction, writing only validated outputs into `snap`. """
    targets = _mt_targets(direction, wd_labels, wd_links)
    # Skip anything already attempted.
    pending = [(uid, s) for uid, s in targets if (direction, _hash(s)) not in snap]
    if C.TRANSLATE_MAX_TARGETS:
        pending = pending[:C.TRANSLATE_MAX_TARGETS]
    stats = {"targets": len(targets), "attempted": len(pending), "verbatim": 0,
             "validated": 0, "rejected": 0}
    if not pending:
        return stats

    src_lang, tgt_lang = direction.split("_")
    model = C.TRANSLATE_MT_MODEL
    chunk = 200
    for start in range(0, len(pending), chunk):
        batch = pending[start:start + chunk]
        # Fully-protected labels (pure tech terms) are kept verbatim.
        verbatim = [(uid, s) for uid, s in batch if _is_fully_protected(s)]
        mt_items = [(uid, s) for uid, s in batch if not _is_fully_protected(s)]
        for uid, s in verbatim:
            snap[(direction, _hash(s))] = {"direction": direction, "src_hash": _hash(s), "src_text": s,
                                           "output": s, "model": "verbatim", "validated": "1",
                                           "score": "1.000", "created_at": K.now_iso()}
            stats["verbatim"] += 1
        if mt_items and translator.ok:
            outs = translator.translate_many([s for _u, s in mt_items], src_lang, tgt_lang, num_beams=4)
            items = [{"unified_id": uid, "src": s, "out": o, "guard_ok": g}
                     for (uid, s), (o, g) in zip(mt_items, outs)]
            verdicts = validator.validate_batch(direction, items)
            for (uid, s), it, (ok, score, reason) in zip(mt_items, items, verdicts):
                # Keep the rejected text too; apply_enrichment only ever reads validated=="1".
                snap[(direction, _hash(s))] = {
                    "direction": direction, "src_hash": _hash(s), "src_text": s,
                    "output": it["out"], "model": model,
                    "validated": "1" if ok else "0", "score": f"{score:.3f}",
                    "reason": "" if ok else reason, "created_at": K.now_iso()}
                stats["validated" if ok else "rejected"] += 1
        elif mt_items:
            stats["rejected"] += len(mt_items)
        if save:
            save()
        print(f"[TRANSLATE] {direction}: {min(start + chunk, len(pending))}/{len(pending)} "
              f"(validated={stats['validated']} verbatim={stats['verbatim']} "
              f"rejected={stats['rejected']})", flush=True)
    return stats


ALL_DIRECTIONS = ("wikidata", "en_fr", "fr_en")


def _parse_directions(directions):
    if directions in (None, "all", "", ("all",)):
        return list(ALL_DIRECTIONS)
    if isinstance(directions, str):
        directions = [d.strip() for d in re.split(r"[,\s]+", directions) if d.strip()]
    picked = [d for d in directions if d in ALL_DIRECTIONS]
    return picked or list(ALL_DIRECTIONS)


def run(directions="all") -> dict:
    """Fill empty EN/FR labels: L1 Wikidata (authoritative) + L2 validated MT, then re-weave via merge. """
    dirs = _parse_directions(directions)
    print(f"[TRANSLATE] directions = {dirs}", flush=True)

    wd_links = _wd_links_by_uid()
    wd_labels = _load_wd_labels()

    # L1 — authoritative Wikidata labels for anchored rows missing a FR (or EN) primary.
    if "wikidata" in dirs and wd_links:
        need = set()
        for path in (C.UNIFIED_OCCUPATIONS_CSV, C.UNIFIED_SKILLS_CSV):
            if not os.path.isfile(path):
                continue
            for r in K.read_all(path):
                uid = r.get("unified_id", "")
                qid = (r.get("wikidata_qid") or wd_links.get(uid, {}).get("qid") or "").strip()
                if qid and (not (r.get("primary_label_fr") or "").strip()
                            or not (r.get("primary_label_en") or "").strip()):
                    need.add(qid)
        wd_labels = _fetch_wd_labels(sorted(need), wd_labels)
        _save_wd_labels(wd_labels)

    # L2 — MT for the primary labels Wikidata cannot supply.
    snap = _load_snapshot()
    stats = {}
    mt_dirs = [d for d in dirs if d in ("en_fr", "fr_en")]
    if mt_dirs:
        translator = Translator()
        validator = Validator(translator)
        save = lambda: (_save_snapshot(snap), validator.dump_rejects())  # checkpoint each chunk
        for d in mt_dirs:
            stats[d] = _translate_direction(d, translator, validator, snap, wd_labels, wd_links, save)
            _save_snapshot(snap)
            print(f"[TRANSLATE] {d}: {stats[d]}", flush=True)
        validator.dump_rejects()
        print(f"[TRANSLATE] rejects logged: {len(validator.rejects)}", flush=True)

    # Weave the filled labels into the unified tables.
    from . import merge
    merge.run()

    K.log_provenance("TRANSLATE", [{
        "entity_id": "TRANSLATE", "source": "TRANSLATE",
        "source_version": f"wd+mt={C.TRANSLATE_MT_MODEL}",
        "retrieved_at": K.now_iso(),
        "retrieval_method": "wikidata-labels + nllb-mt + backtranslation-validation",
        "notes": ("; ".join(f"{k}={v}" for k, v in stats.items()) or "wikidata-only")[:500],
    }])
    print(f"[TRANSLATE] done. {stats}", flush=True)
    return stats
