"""Europe PMC adapter — live, cached, stdlib-only (no API key required).

REST: https://europepmc.org/RestfulWebService . We use the search endpoint with
resultType=core to get abstracts. Journal is used as the independence `group` so the
membrane's convergence gate can count evidential independence (planning/LITERATURE.md §D).
"""
from __future__ import annotations

import json
import urllib.parse
import urllib.request
from typing import Optional

from .base import Document, SourceAdapter, DiskCache

_BASE = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"
_UA = "persona-researcher/0.0.1 (research prototype)"


class EuropePMCAdapter(SourceAdapter):
    name = "europepmc"

    def __init__(self, cache: Optional[DiskCache] = None, timeout: float = 20.0):
        super().__init__(cache)
        self.timeout = timeout

    def _fetch(self, query: str, limit: int) -> dict:
        params = urllib.parse.urlencode({
            "query": query,
            "format": "json",
            "pageSize": max(1, min(limit, 100)),
            "resultType": "core",
        })
        req = urllib.request.Request(f"{_BASE}?{params}", headers={"User-Agent": _UA})
        with urllib.request.urlopen(req, timeout=self.timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))

    def search(self, query: str, limit: int = 10) -> list[Document]:
        cached = self.cache.get(self.name, query, str(limit))
        if cached is not None:
            return [Document(**d) for d in cached]
        data = self._fetch(query, limit)
        docs: list[Document] = []
        for r in data.get("resultList", {}).get("result", []):
            src = r.get("source", "MED")
            ext = r.get("id", "")
            year = r.get("pubYear")
            docs.append(Document(
                doc_id=f"{src}:{ext}",
                title=r.get("title", "").strip(),
                text=(r.get("abstractText") or "").strip(),
                source=self.name,
                url=(f"https://doi.org/{r['doi']}" if r.get("doi")
                     else f"https://europepmc.org/article/{src}/{ext}"),
                year=int(year) if year and str(year).isdigit() else None,
                group=(r.get("journalInfo", {}) or {}).get("journal", {}).get("title")
                      or r.get("source"),
                meta={"authors": r.get("authorString", ""),
                      "cited_by": r.get("citedByCount", 0),
                      "is_open_access": r.get("isOpenAccess", "N")},
            ))
        self.cache.put([d.to_dict() for d in docs], self.name, query, str(limit))
        return docs
