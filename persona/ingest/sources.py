"""Multi-source scholarly search (v5 P1) — fail over instead of dying on one host's 429.

One `search_multi(query, limit)` tries OpenAlex → Crossref → Europe PMC → arXiv, returning the
first source that yields results (and logging which). Cross-source dedup by DOI (same paper from
any source gets the same slug). All requests go through the shared IngestService (cache + rate
limit + backoff). Never returns [] silently — the caller learns which sources were tried + why.
"""
from __future__ import annotations

import hashlib
import re
import urllib.parse
import xml.etree.ElementTree as ET

from .openalex import Work
from .service import service


def _doi_norm(doi) -> str:
    if not doi:
        return ""
    return re.sub(r"^https?://(dx\.)?doi\.org/", "", str(doi)).strip().lower()


def _mk(id_fallback: str, *, title, abstract, year, doi, authors, affiliations,
        pdf_url=None, landing_url=None, venue=None) -> Work:
    dn = _doi_norm(doi)
    wid = ("doi_" + hashlib.sha1(dn.encode()).hexdigest()[:12]) if dn else id_fallback
    return Work(id=wid, title=(title or "").strip(), abstract=(abstract or "").strip(),
                year=year, doi=(dn or None), authors=[a for a in authors if a],
                affiliations=list(dict.fromkeys([a for a in affiliations if a])),
                pdf_url=pdf_url, landing_url=landing_url or (f"https://doi.org/{dn}" if dn else None),
                venue=venue, cited_by=0)


# ------------------------------------------------------------------ OpenAlex
def _reconstruct_abstract(inv):
    if not inv:
        return ""
    pos = [(i, w) for w, idxs in inv.items() for i in idxs]
    pos.sort()
    return " ".join(w for _, w in pos)


def openalex_search(query: str, limit: int, page: int = 1) -> list[Work]:
    d = service().get_json("https://api.openalex.org/works", {
        "search": query, "per_page": max(1, min(limit, 50)), "page": page,
        "mailto": "persona-researcher@example.org", "sort": "relevance_score:desc"})
    out = []
    for r in d.get("results", []):
        affs = [inst.get("display_name") for a in r.get("authorships", [])
                for inst in (a.get("institutions") or []) if inst.get("display_name")]
        boa = r.get("best_oa_location") or {}
        ploc = r.get("primary_location") or {}
        out.append(_mk(r.get("id", "").rsplit("/", 1)[-1],
                       title=r.get("title"), abstract=_reconstruct_abstract(r.get("abstract_inverted_index")),
                       year=r.get("publication_year"), doi=r.get("doi"),
                       authors=[a.get("author", {}).get("display_name", "") for a in r.get("authorships", [])],
                       affiliations=affs, pdf_url=boa.get("pdf_url") or ploc.get("pdf_url"),
                       landing_url=boa.get("landing_page_url") or ploc.get("landing_page_url"),
                       venue=((ploc.get("source") or {}).get("display_name"))))
    return out


# ------------------------------------------------------------------ Crossref
def crossref_search(query: str, limit: int) -> list[Work]:
    d = service().get_json("https://api.crossref.org/works",
                           {"query": query, "rows": max(1, min(limit, 40)),
                            "select": "DOI,title,abstract,author,issued,container-title,link"})
    out = []
    for it in d.get("message", {}).get("items", []):
        title = (it.get("title") or [""])[0]
        abstract = re.sub(r"<[^>]+>", " ", it.get("abstract", "") or "")   # strip JATS tags
        year = None
        dp = (it.get("issued", {}).get("date-parts") or [[None]])[0]
        if dp and dp[0]:
            year = dp[0]
        authors = [f"{a.get('given','')} {a.get('family','')}".strip() for a in it.get("author", [])]
        affs = [aff.get("name") for a in it.get("author", []) for aff in (a.get("affiliation") or [])]
        pdf = next((l.get("URL") for l in it.get("link", [])
                    if l.get("content-type") == "application/pdf"), None)
        out.append(_mk("cr_" + _doi_norm(it.get("DOI")), title=title, abstract=abstract, year=year,
                       doi=it.get("DOI"), authors=authors, affiliations=affs, pdf_url=pdf,
                       venue=(it.get("container-title") or [None])[0]))
    return out


# ------------------------------------------------------------------ Europe PMC
def europepmc_search(query: str, limit: int) -> list[Work]:
    d = service().get_json("https://www.ebi.ac.uk/europepmc/webservices/rest/search",
                           {"query": query, "format": "json", "pageSize": max(1, min(limit, 40)),
                            "resultType": "core"})
    out = []
    for r in d.get("resultList", {}).get("result", []):
        auths = [a.get("fullName", "") for a in
                 (r.get("authorList", {}) or {}).get("author", [])] or \
                [s.strip() for s in (r.get("authorString", "") or "").split(",")]
        affs = []
        for a in (r.get("authorList", {}) or {}).get("author", []):
            for aff in (a.get("authorAffiliationDetailsList", {}) or {}).get("authorAffiliation", []):
                if aff.get("affiliation"):
                    affs.append(aff["affiliation"])
        src, ext = r.get("source", "MED"), r.get("id", "")
        pmcid = r.get("pmcid")
        pdf = (f"https://www.ebi.ac.uk/europepmc/webservices/rest/{pmcid}/fullTextXML"
               if pmcid else None)
        out.append(_mk(f"epmc_{src}_{ext}", title=r.get("title"), abstract=r.get("abstractText", ""),
                       year=int(r["pubYear"]) if str(r.get("pubYear", "")).isdigit() else None,
                       doi=r.get("doi"), authors=auths, affiliations=affs, pdf_url=pdf,
                       landing_url=(f"https://europepmc.org/article/{src}/{ext}"),
                       venue=(r.get("journalInfo", {}) or {}).get("journal", {}).get("title")))
    return out


# ------------------------------------------------------------------ arXiv
_ATOM = "{http://www.w3.org/2005/Atom}"


def arxiv_search(query: str, limit: int) -> list[Work]:
    xml = service().get_bytes("https://export.arxiv.org/api/query?" + urllib.parse.urlencode(
        {"search_query": f"all:{query}", "max_results": max(1, min(limit, 40)),
         "sortBy": "relevance"}))
    root = ET.fromstring(xml)
    out = []
    for e in root.findall(f"{_ATOM}entry"):
        aid = (e.findtext(f"{_ATOM}id") or "").rsplit("/", 1)[-1]
        title = (e.findtext(f"{_ATOM}title") or "").strip()
        summ = (e.findtext(f"{_ATOM}summary") or "").strip()
        yr = (e.findtext(f"{_ATOM}published") or "")[:4]
        authors = [a.findtext(f"{_ATOM}name") for a in e.findall(f"{_ATOM}author")]
        doi = e.findtext("{http://arxiv.org/schemas/atom}doi")
        pdf = next((l.get("href") for l in e.findall(f"{_ATOM}link")
                    if l.get("title") == "pdf"), None)
        out.append(_mk(f"arxiv_{aid.replace('/', '_')}", title=title, abstract=summ,
                       year=int(yr) if yr.isdigit() else None, doi=doi, authors=authors,
                       affiliations=[], pdf_url=pdf,
                       landing_url=f"https://arxiv.org/abs/{aid}", venue="arXiv"))
    return out


_SOURCES = [("openalex", openalex_search), ("crossref", crossref_search),
            ("europepmc", europepmc_search), ("arxiv", arxiv_search)]


def search_multi(query: str, limit: int = 25, *, log=None) -> tuple[list[Work], str]:
    """Try each source in order; return (works, source_used). Fails over on error/empty; only
    returns ([], 'none') if ALL sources fail. `log(msg)` optional for surfacing which source hit."""
    tried = []
    for name, fn in _SOURCES:
        try:
            works = fn(query, limit)
        except Exception as e:
            tried.append(f"{name}:err")
            if log:
                log(f"source {name} failed ({str(e)[:60]}) — failing over")
            continue
        if works:
            if log and tried:
                log(f"used {name} (after {', '.join(tried)})")
            return works, name
        tried.append(f"{name}:0")
    if log:
        log(f"all sources empty/failed: {', '.join(tried)}")
    return [], "none"
