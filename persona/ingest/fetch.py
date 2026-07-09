"""Fetch + parse a work's text (v4). Prefers open-access full-text PDF (PyMuPDF); falls back to
the abstract, then the title. Bounded (pages/chars) so one huge PDF can't stall the reader.
Docling + structure-aware chunking for the full pipeline lands in P3; P1 gets real text now.
"""
from __future__ import annotations

_MAX_PAGES = 18
_MAX_CHARS = 45000


def _fetch_pdf_text(url: str) -> str:
    from .service import service
    data = service().get_bytes(url, accept="application/pdf")   # cached + rate-limited + backoff
    if b"<fullTextXML" in data[:200] or b"<article" in data[:400]:   # Europe PMC full-text XML
        import re
        txt = re.sub(r"<[^>]+>", " ", data.decode("utf-8", "replace"))
        return re.sub(r"\s+", " ", txt).strip()
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
