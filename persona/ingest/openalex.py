"""OpenAlex Work model (v4) — the shared result record.

Live searching now goes through `ingest/sources.py` + the rate-limited/cached `IngestService`
(multi-source failover). This module keeps only the `Work` dataclass those adapters build; the
old keyless urllib search path was removed (it bypassed the limiter/cache and carried a fake
polite-pool mailto — a ban risk). Abstracts arrive as an inverted index; `sources._reconstruct_abstract`
rebuilds them.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Work:
    id: str                      # OpenAlex id (short, e.g. W1234)
    title: str
    abstract: str
    year: Optional[int]
    doi: Optional[str]
    authors: list = field(default_factory=list)          # display names
    affiliations: list = field(default_factory=list)     # institution names (independence)
    pdf_url: Optional[str] = None
    landing_url: Optional[str] = None
    venue: Optional[str] = None
    cited_by: int = 0
    field: Optional[str] = None       # OpenAlex primary_topic.field display name (e.g. "Mathematics")
    field_id: Optional[str] = None    # short field id (e.g. "26") — the relevance/routing key

    @property
    def slug(self) -> str:
        return self.id.rsplit("/", 1)[-1]

    def to_dict(self) -> dict:
        return {"id": self.id, "title": self.title, "abstract": self.abstract, "year": self.year,
                "doi": self.doi, "authors": self.authors, "affiliations": self.affiliations,
                "pdf_url": self.pdf_url, "landing_url": self.landing_url, "venue": self.venue,
                "cited_by": self.cited_by, "field": self.field, "field_id": self.field_id}

    @classmethod
    def from_dict(cls, d: dict) -> "Work":
        return cls(**{k: d.get(k) for k in ("id", "title", "abstract", "year", "doi", "authors",
                                            "affiliations", "pdf_url", "landing_url", "venue",
                                            "cited_by", "field", "field_id")})
