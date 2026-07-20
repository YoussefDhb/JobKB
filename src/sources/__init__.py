"""Pluggable data-source framework for JobKB.

A `Source` ingests ONE data source into the KB's per-source, idempotent CSV layer,
standardized to the English-primary schema. Existing taxonomies (ESCO/ISCO/ONET/NOC/
ROME) are wrapped as sources in `registry.py`; new datasets subclass `StructuredSource`
and implement only field-mapping hooks. See `base.py` and `registry.py`.
"""
