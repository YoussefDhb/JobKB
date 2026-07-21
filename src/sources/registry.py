"""Source registry — the single place that lists every ingestable source.

The built-in taxonomies (ISCO/ESCO/ONET/NOC/ROME) are wrapped so they share one interface
with plugin sources. Adding a new source = append one `register(...)` line here (or import
and register from elsewhere); the incremental orchestrator, `attach` and the CLI all read
this registry, so no other file needs editing.
"""

from __future__ import annotations

from .. import config as C
from ..ingest import isco, esco, onet, noc, rome
from .base import Source
from .demo_dataset import DemoSource
from .sfia import SfiaSource
from .cso import CsoSource
from .lightcast import LightcastSource
from .kaggle_skills import KaggleSkillsSource
from .ecf import EcfSource
from .adem_demand import AdemDemandSource
from .jobs_evidence import JobsEvidenceSource


class _WrappedIngest(Source):
    """Adapt an existing `ingest.<module>.run` function to the Source interface."""

    def __init__(self, name, run_fn, *, contributes_occupations, needs_attach, version="-"):
        self.name = name
        self._run = run_fn
        self.contributes_occupations = contributes_occupations
        self.needs_attach = needs_attach
        self.builtin = True   # the wrapped taxonomies are the base build set
        self.version = version

    def ingest(self) -> None:
        self._run()


REGISTRY: dict[str, Source] = {}


def register(src: Source) -> Source:
    REGISTRY[src.name] = src
    return src


# --- built-in taxonomies ---------------------------------------------------------------
# ISCO is the neutral backbone (its nodes are ISCO groups, not aligned occupations).
register(_WrappedIngest(C.SRC_ISCO, isco.run, contributes_occupations=False, needs_attach=False))
# ESCO carries a native ISCO code (self-attaches during ingest).
register(_WrappedIngest(C.SRC_ESCO, esco.run, contributes_occupations=True, needs_attach=False))
# ONET / NOC / ROME have no native ISCO code -> the attach stage assigns one.
register(_WrappedIngest(C.SRC_ONET, onet.run, contributes_occupations=True, needs_attach=True))
register(_WrappedIngest(C.SRC_NOC, noc.run, contributes_occupations=True, needs_attach=True))
register(_WrappedIngest(C.SRC_ROME, rome.run, contributes_occupations=True, needs_attach=True))

# --- built-in skills-only frameworks ---------------------------------------------------
# SFIA/CSO/Lightcast/Kaggle contribute skills but no occupations; they classify + align/merge
# into the shared skill layer and reach occupations transitively via unified skills.
register(SfiaSource())
register(CsoSource())
register(LightcastSource())
register(KaggleSkillsSource())
# e-CF: the European e-Competence Framework — 41 authoritative EU ICT competences.
register(EcfSource())

# --- built-in relation-only enrichment (must run after ESCO/ROME/skills exist) ---------
# ADEM (real vacancy demand) and JOBS (mined postings) add weighted occupation->skill edges
# between entities that already exist in the KB — no new nodes.
register(AdemDemandSource())
register(JobsEvidenceSource())

# --- plugin sources --------------------------------------------------------------------
register(DemoSource())


def get(name: str) -> Source:
    if name not in REGISTRY:
        raise KeyError(f"Unknown source '{name}'. Known: {', '.join(sorted(REGISTRY))}")
    return REGISTRY[name]


def names() -> tuple[str, ...]:
    return tuple(REGISTRY)


def builtin_sources() -> tuple[str, ...]:
    """The base taxonomy sources built by a full ingest, in registration order."""
    return tuple(n for n, s in REGISTRY.items() if getattr(s, "builtin", False))


def occ_sources() -> tuple[str, ...]:
    """Sources contributing real (non ISCO-group) occupations that get aligned."""
    return tuple(n for n, s in REGISTRY.items() if s.contributes_occupations)


def needs_attach_sources() -> tuple[str, ...]:
    """Sources whose occupations need alignment-based ISCO attachment."""
    return tuple(n for n, s in REGISTRY.items() if s.needs_attach)
