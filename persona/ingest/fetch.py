"""Fetch + parse a work's text (v4). Prefers open-access full-text PDF (PyMuPDF); falls back to
the abstract, then the title. Bounded (pages/chars) so one huge PDF can't stall the reader.
Docling + structure-aware chunking for the full pipeline lands in P3; P1 gets real text now.
"""
from __future__ import annotations

import urllib.request

_UA = "persona-researcher/4.0 (mailto:persona-researcher@example.org)"
_MAX_PAGES = 18
_MAX_CHARS = 45000


def _fetch_pdf_text(url: str, timeout: float = 30.0) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": _UA, "Accept": "application/pdf"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        data = r.read()
    import fitz  # PyMuPDF
    doc = fitz.open(stream=data, filetype="pdf")
    parts = []
    for i, page in enumerate(doc):
        if i >= _MAX_PAGES:
            break
        parts.append(page.get_text())
    doc.close()
    return "\n".join(parts).strip()


def fulltext(work) -> tuple[str, str]:
    """Return (text, kind) where kind in {'pdf','abstract','title'}."""
    if getattr(work, "pdf_url", None):
        try:
            text = _fetch_pdf_text(work.pdf_url)
            if len(text) > 400:                    # got real body text
                return text[:_MAX_CHARS], "pdf"
        except Exception:
            pass                                   # fall through to abstract
    if getattr(work, "abstract", "") and len(work.abstract) > 40:
        return work.abstract, "abstract"
    return work.title, "title"
