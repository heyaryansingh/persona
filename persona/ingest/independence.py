"""Evidential-independence keys (v3 T1.1).

Audit #4: convergence counted distinct JOURNALS, which the citation-echo attack the code cites
as motivation defeats trivially — one lab republishes/cites its own finding across several
journals and the membrane sees "many independent sources". The real independence unit in
biomedicine is the LAB, and the cheapest high-signal proxy for a lab is the **senior (last)
author**. Grouping by senior author collapses a lab's self-echo to one vote; distinct senior
authors is a far better independence count than distinct journals.

Deterministic + cross-batch stable (a function of the author string only), so beliefs accrued
across separate reads share group ids without relational clustering. Last-name collisions between
truly independent labs UNDER-count independence -> the SAFE direction for an anti-slop membrane
(harder to converge), not the dangerous one. Author-set overlap / citation-graph screens are a
future refinement; senior-author is the load-bearing core (validated: experiments/exp_e14_independence.py).
"""
from __future__ import annotations

import re


def _norm(s: str) -> str:
    return re.sub(r"[^a-z ]", "", s.lower()).strip()


def author_list(authors: str) -> list:
    """Split an Europe PMC authorString ('Smith AB, Jones CD, Brown EF.') into raw name tokens."""
    if not authors:
        return []
    parts = [p.strip().rstrip(".") for p in authors.split(",")]
    return [p for p in parts if p and "et al" not in p.lower()]


def senior_author(authors: str) -> str:
    """The last author's 'surname + first initial', normalized (the lab-head / PI proxy)."""
    names = author_list(authors)
    if not names:
        return ""
    last = names[-1].split()
    if not last:
        return ""
    surname = _norm(last[0])
    initial = _norm(last[1])[:1] if len(last) > 1 else ""
    return f"{surname} {initial}".strip()


def independence_group(doc) -> str:
    """Independence key for a Document: senior author if known, else journal, else source.
    This is the `group` the membrane counts distinct copies of for convergence."""
    meta = getattr(doc, "meta", None) or {}
    sr = senior_author(meta.get("authors", ""))
    if sr:
        return f"lab:{sr}"
    if getattr(doc, "group", None):
        return f"jrnl:{_norm(doc.group)}"
    return f"src:{getattr(doc, 'source', 'unknown')}"
