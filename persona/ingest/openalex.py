"""OpenAlex connector (v4) — keyless, domain-neutral scholarly search over ~250M works.

Chosen as the first connector because it is (a) free/keyless, (b) every field of science (not
just biomed), (c) gives author AFFILIATIONS (→ lab-independence for the membrane) and open-access
full-text URLs. Abstracts arrive as an inverted index; we reconstruct them.
"""
from __future__ import annotations

import re
import urllib.parse
import urllib.request
import json
from dataclasses import dataclass, field
from typing import Optional

_BASE = "https://api.openalex.org/works"
_MAILTO = "persona-researcher@example.org"     # polite pool
_UA = "persona-researcher/4.0 (mailto:persona-researcher@example.org)"


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

    @property
    def slug(self) -> str:
        return self.id.rsplit("/", 1)[-1]


def _reconstruct_abstract(inv: Optional[dict]) -> str:
    if not inv:
        return ""
    positions = []
    for word, idxs in inv.items():
        for i in idxs:
            positions.append((i, word))
    positions.sort()
    return " ".join(w for _, w in positions)


def _get(url: str, timeout: float = 25.0) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": _UA})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


def search(query: str, limit: int = 5, *, oa_only: bool = False,
           min_year: Optional[int] = None) -> list[Work]:
    """Search works by relevance. `oa_only` restricts to open-access (fetchable full text)."""
    filters = []
    if oa_only:
        filters.append("open_access.is_oa:true")
    if min_year:
        filters.append(f"from_publication_date:{min_year}-01-01")
    params = {"search": query, "per_page": max(1, min(limit, 50)),
              "mailto": _MAILTO, "sort": "relevance_score:desc"}
    if filters:
        params["filter"] = ",".join(filters)
    data = _get(f"{_BASE}?{urllib.parse.urlencode(params)}")
    out: list[Work] = []
    for r in data.get("results", []):
        auths = [a.get("author", {}).get("display_name", "") for a in r.get("authorships", [])]
        affs = []
        for a in r.get("authorships", []):
            for inst in a.get("institutions", []) or []:
                if inst.get("display_name"):
                    affs.append(inst["display_name"])
        boa = r.get("best_oa_location") or {}
        ploc = r.get("primary_location") or {}
        out.append(Work(
            id=r.get("id", ""),
            title=(r.get("title") or "").strip(),
            abstract=_reconstruct_abstract(r.get("abstract_inverted_index")),
            year=r.get("publication_year"),
            doi=(r.get("doi") or None),
            authors=[a for a in auths if a],
            affiliations=list(dict.fromkeys(affs)),      # dedup, keep order
            pdf_url=boa.get("pdf_url") or ploc.get("pdf_url"),
            landing_url=boa.get("landing_page_url") or ploc.get("landing_page_url"),
            venue=((ploc.get("source") or {}).get("display_name")),
            cited_by=r.get("cited_by_count", 0),
        ))
    return out
