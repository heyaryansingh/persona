"""Source-agnostic ingestion (planning/PHASE0_PLAN.md Decisions: live-early, cached).

Persona's curiosity is not fenced to one corpus: reader/scout agents pull through a
single `SourceAdapter` interface. Biomedical APIs are the first adapters; web / dataset
/ repo adapters follow with the same interface. Every adapter caches to disk so the
demo can't break on a live outage (§9.7 resilience backstop).
"""
from .base import Document, SourceAdapter, DiskCache
from .europepmc import EuropePMCAdapter

_REGISTRY: dict[str, type[SourceAdapter]] = {
    "europepmc": EuropePMCAdapter,
}


def get_adapter(name: str, **kwargs) -> SourceAdapter:
    if name not in _REGISTRY:
        raise KeyError(f"unknown source {name!r}; have {sorted(_REGISTRY)}")
    return _REGISTRY[name](**kwargs)


__all__ = ["Document", "SourceAdapter", "DiskCache", "EuropePMCAdapter", "get_adapter"]
