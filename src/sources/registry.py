"""Source registry — the place that lists every ingestable source."""

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
from .soft_skills import SoftSkillsSource
from .soft_taxonomy import SoftTaxonomySource
from .wef import WefSource
from .emerging_roles import EmergingRolesSource
from .adem_demand import AdemDemandSource
from .jobs_evidence import JobsEvidenceSource
from .data_jobs import DataJobsSource
from .zenodo import ZenodoSource
from .djinni import DjinniSource
from .linkedin_swe import LinkedInSweSource
from .kaggle_jobs import KaggleJobsSource
from .scraper import ScraperSource


class _WrappedIngest(Source):
    """Adapt an existing `ingest.<module>.run` function to the Source interface."""

    def __init__(self, name, run_fn, *, contributes_occupations, needs_attach, version="-"):
        self.name = name
        self._run = run_fn
        self.contributes_occupations = contributes_occupations
        self.needs_attach = needs_attach
        self.builtin = True   
        self.version = version

    def ingest(self) -> None:
        self._run()


REGISTRY: dict[str, Source] = {}


def register(src: Source) -> Source:
    REGISTRY[src.name] = src
    return src


# --- built-in taxonomies ---------------------------------------------------------------
# ISCO is the neutral backbone.
register(_WrappedIngest(C.SRC_ISCO, isco.run, contributes_occupations=False, needs_attach=False))
# ESCO carries a native ISCO code.
register(_WrappedIngest(C.SRC_ESCO, esco.run, contributes_occupations=True, needs_attach=False))
# ONET / NOC / ROME have no native ISCO code -> the attach stage assigns one.
register(_WrappedIngest(C.SRC_ONET, onet.run, contributes_occupations=True, needs_attach=True))
register(_WrappedIngest(C.SRC_NOC, noc.run, contributes_occupations=True, needs_attach=True))
register(_WrappedIngest(C.SRC_ROME, rome.run, contributes_occupations=True, needs_attach=True))

# --- built-in skills-only frameworks ---------------------------------------------------
register(SfiaSource())
register(CsoSource())
register(LightcastSource())
register(KaggleSkillsSource())
# e-CF: the European e-Competence Framework
register(EcfSource())
# SOFTSKILLS: curated noun-form soft/transversal skills used in IT hiring
register(SoftSkillsSource())
# WEF Global Skills Taxonomy: structured soft skills
register(WefSource())
# Comprehensive curated IT soft-skills taxonomy: genuinely-new soft skills self-classified into the 5 soft sub-domains.
register(SoftTaxonomySource())

# --- curated emerging IT roles -----
# Registered before DATAJOBS so its occupations exist when data_jobs attributes demand to them.
register(EmergingRolesSource())

# --- built-in relation-only enrichment ---------
register(AdemDemandSource())
register(JobsEvidenceSource())
# DATAJOBS resolves endpoints against the existing KB at ingest, so it registers after the taxonomies/skills.
register(DataJobsSource())
# ZENODO is a hybrid like DATAJOBS
register(ZenodoSource())
# Three more job-posting demand sources
register(DjinniSource())
register(LinkedInSweSource())
register(KaggleJobsSource())

# --- plugin sources --------------------------------------------------------------------
# SCRAPER: web-scraping enrichment.
register(ScraperSource())
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
    """Sources contributing real occupations that get aligned."""
    return tuple(n for n, s in REGISTRY.items() if s.contributes_occupations)


def needs_attach_sources() -> tuple[str, ...]:
    """Sources whose occupations need alignment-based ISCO attachment."""
    return tuple(n for n, s in REGISTRY.items() if s.needs_attach)
