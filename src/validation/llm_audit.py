"""LLM-connection accuracy audit (Track 3, objective 2).

The only genuine LLM-*created* connections in the graph are the `llm_inferred` occupation->skill links
(gated at creation by embedding cosine only) and the `llm` skill descriptions (length + NLI). This
re-validates them independently and read-only:
  - links: (a) NLI re-verification (occupation definition |= "requires {skill}") and (b) DEMAND
    CORROBORATION — does the occupation actually demand that skill (or a semantically-near one) in its
    real posting profile? An independent, held-out real-world signal.
  - descriptions: NLI re-verify "This text describes {label}."
"""

from __future__ import annotations

from collections import defaultdict

from .. import config as C
from .. import common as K


def _occ_def(o):
    return (o.get("description_en") or o.get("description_fr") or o.get("pref_label_en")
            or o.get("pref_label_fr") or "")


def _label(r):
    return (r.get("pref_label_en") or r.get("pref_label_fr") or "")


def audit(embedder=None, verifier=None):
    """Return {"links": {...summary}, "link_rows": [...], "descriptions": {...}, "desc_rows": [...]}."""
    rels = K.read_all(C.OCC_SKILL_REL_CSV)
    occ = {r["entity_id"]: r for r in K.read_all(C.OCCUPATIONS_CSV)}
    skl = {r["entity_id"]: r for r in K.read_all(C.SKILLS_CSV)}
    links = [r for r in rels if r.get("relation_type") == "llm_inferred"]

    demand = defaultdict(set)                       # occupation -> demanded skill ids (real postings)
    for r in rels:
        if r.get("relation_type") == "demand":
            demand[r["occupation_entity_id"]].add(r["skill_entity_id"])

    if verifier is None:
        from ..align.verify import Verifier
        verifier = Verifier()

    # NLI: occupation definition |= "This occupation requires {skill}."
    nli_pairs = []
    for l in links:
        o = occ.get(l["occupation_entity_id"], {})
        s = skl.get(l["skill_entity_id"], {})
        nli_pairs.append((_occ_def(o), f"This occupation requires {_label(s)}."))
    nli_scores = verifier.entail_batch(nli_pairs) if links else []

    # Semantic demand corroboration: encode the linked skill + each occupation's demanded-skill labels
    # once, then per link take the max cosine of the linked skill against that occ's demand profile.
    sem_corr = [None] * len(links)
    if embedder is not None and embedder.mode == "st":
        import numpy as np
        from ..align import candidates as cand
        needed = set()
        for l in links:
            needed.add(l["skill_entity_id"])
            needed |= demand.get(l["occupation_entity_id"], set())
        needed = [sid for sid in needed if sid in skl and _label(skl[sid])]
        vec = {}
        if needed:
            arr = cand.encode_cached(embedder, [_label(skl[sid]) for sid in needed])
            vec = {sid: arr[i] for i, sid in enumerate(needed)}
        for i, l in enumerate(links):
            sid = l["skill_entity_id"]
            prof = [d for d in demand.get(l["occupation_entity_id"], set()) if d in vec and d != sid]
            if sid in vec and prof:
                sims = np.asarray([float(vec[sid] @ vec[d]) for d in prof])
                sem_corr[i] = round(float(sims.max()), 3)

    link_rows, nli_ok, dem_exact_ok, dem_sem_ok = [], 0, 0, 0
    for i, l in enumerate(links):
        oid, sid = l["occupation_entity_id"], l["skill_entity_id"]
        nli = nli_scores[i] if i < len(nli_scores) else None
        nli_pass = nli is not None and nli >= C.VALIDATION_LINK_NLI_MIN
        d_exact = sid in demand.get(oid, set())
        d_sem = sem_corr[i] is not None and sem_corr[i] >= C.VALIDATION_DEMAND_SEMANTIC_MIN
        corroborated = d_exact or d_sem
        nli_ok += int(nli_pass)
        dem_exact_ok += int(d_exact)
        dem_sem_ok += int(corroborated)
        link_rows.append({
            "occupation": _label(occ.get(oid, {})), "skill": _label(skl.get(sid, {})),
            "creation_cosine": l.get("weight", ""),
            "nli": "" if nli is None else round(float(nli), 3), "nli_pass": nli_pass,
            "demand_exact": d_exact, "demand_semantic": "" if sem_corr[i] is None else sem_corr[i],
            "corroborated": corroborated,
            # a link the LLM proposed that BOTH NLI and real demand back is high-confidence
            "verdict": "strong" if (nli_pass and corroborated) else
                       ("corroborated" if corroborated else ("nli_only" if nli_pass else "weak")),
        })

    n = len(links)
    links_summary = {"n": n,
                     "nli_pass": nli_ok, "nli_pass_pct": round(100 * nli_ok / n, 1) if n else 0.0,
                     "demand_exact": dem_exact_ok,
                     "demand_corroborated": dem_sem_ok,
                     "demand_corroborated_pct": round(100 * dem_sem_ok / n, 1) if n else 0.0}

    # LLM descriptions: NLI re-verify "This text describes {label}." (same hypothesis as creation).
    uskl = K.read_all(C.UNIFIED_SKILLS_CSV)
    uocc = K.read_all(C.UNIFIED_OCCUPATIONS_CSV)
    llm_desc = [r for r in uskl + uocc
                if r.get("description_source") == "llm" and (r.get("description") or "").strip()]
    dpairs = [(r["description"], f"This text describes {r.get('primary_label_en')}.") for r in llm_desc]
    dscores = verifier.entail_batch(dpairs) if dpairs else []
    desc_rows, dpass = [], 0
    for i, r in enumerate(llm_desc):
        sc = dscores[i] if i < len(dscores) else None
        ok = sc is not None and sc >= C.LLM_DESC_NLI_MIN
        dpass += int(ok)
        desc_rows.append({"label": r.get("primary_label_en"),
                          "nli": "" if sc is None else round(float(sc), 3), "pass": ok,
                          "description": (r.get("description") or "")[:160]})
    desc_summary = {"n": len(llm_desc), "nli_pass": dpass,
                    "nli_pass_pct": round(100 * dpass / len(llm_desc), 1) if llm_desc else 0.0}

    return {"links": links_summary, "link_rows": link_rows,
            "descriptions": desc_summary, "desc_rows": desc_rows}
