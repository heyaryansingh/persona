"""Source-agnostic ingestion primitives: Document, SourceAdapter, DiskCache (stdlib)."""
from __future__ import annotations

import hashlib
import json
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional


@dataclass
class Document:
    """A normalized unit of reading, source-agnostic (paper, dataset card, web page, repo)."""
    doc_id: str
    title: str
    text: str                       # abstract / body / description
    source: str                     # adapter name, e.g. "europepmc"
    url: Optional[str] = None
    year: Optional[int] = None
    group: Optional[str] = None     # independence group (journal / lab / dataset) for convergence
    meta: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)


class DiskCache:
    """Content-addressed JSON cache. Keeps live-early ingestion from breaking the demo."""

    def __init__(self, root: str | Path = ".cache/ingest"):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def _key(self, *parts: str) -> Path:
        h = hashlib.sha1("\x1f".join(parts).encode("utf-8")).hexdigest()[:20]
        return self.root / f"{h}.json"

    def get(self, *parts: str):
        p = self._key(*parts)
        if p.exists():
            return json.loads(p.read_text(encoding="utf-8"))["value"]
        return None

    def put(self, value, *parts: str) -> None:
        p = self._key(*parts)
        p.write_text(json.dumps({"cached_at": time.time(), "value": value}, indent=2),
                     encoding="utf-8")


class SourceAdapter(ABC):
    """One bounded job: given a query, return normalized Documents. Cached by default."""

    name: str = "base"

    def __init__(self, cache: Optional[DiskCache] = None):
        self.cache = cache if cache is not None else DiskCache()

    @abstractmethod
    def search(self, query: str, limit: int = 10) -> list[Document]:
        ...
