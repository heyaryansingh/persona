"""Arbitrary web / online source connector (v4 P3) — read any URL, not just papers.

trafilatura extracts the main content (dropping nav/ads/boilerplate). Produces a Work-shaped
record so the same read→extract→membrane pipeline applies. Independence unit for the web is the
domain (a proxy for "source"), so ten pages from one site don't count as ten independent labs.
"""
from __future__ import annotations

import hashlib
import urllib.parse

from .openalex import Work


def fetch_url(url: str) -> Work | None:
    """Fetch + main-content-extract a URL into a Work. None if nothing substantive."""
    import trafilatura
    downloaded = trafilatura.fetch_url(url)
    if not downloaded:
        return None
    text = trafilatura.extract(downloaded, include_comments=False, include_tables=True,
                               favor_recall=True) or ""
    if len(text) < 200:
        return None
    meta = trafilatura.extract_metadata(downloaded)
    title = (getattr(meta, "title", None) or url)[:300]
    domain = urllib.parse.urlparse(url).netloc.replace("www.", "")
    wid = "web_" + hashlib.sha1(url.encode()).hexdigest()[:12]   # clean filesystem slug
    year = None
    date = getattr(meta, "date", None)
    if date and len(str(date)) >= 4 and str(date)[:4].isdigit():
        year = int(str(date)[:4])
    return Work(id=wid, title=title, abstract=text, year=year, doi=None,
                authors=[getattr(meta, "author", None) or domain], affiliations=[domain],
                pdf_url=None, landing_url=url, venue=domain, cited_by=0)
