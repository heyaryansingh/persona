"""The reader (v4 P1/P3): interest -> many real papers -> structured claims on disk.

P3 splits discovery from reading so one interest fans out into MANY atomic reads (that's how
claims recur across independent labs and beliefs converge):
- `scout(interest)` pages OpenAlex for the top UNREAD works and returns slim dicts to enqueue.
- `read_work(work)` fetches ONE paper's full text, extracts auditable claims (budget-gated), and
  writes sources/<slug>/{meta.json, clean.md, claims.jsonl}. Idempotent per work.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone

from .. import config
from ..budget import budget
from ..events import log
from ..ingest import openalex, fetch
from . import extract


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _claim_id(subject: str, relation: str, obj: str, sign: str) -> str:
    key = f"{subject.strip().lower()}|{relation.strip().lower()}|{obj.strip().lower()}|{sign}"
    return "clm_" + hashlib.sha1(key.encode()).hexdigest()[:12]


def _already_read(slug: str) -> bool:
    # keyed on meta.json: a source is "seen" once fetched+stored (before extraction), so a paper
    # submitted to a pending batch isn't re-scouted. Harvest still skips sources with no claims.jsonl.
    return (config.SOURCES_DIR / slug / "meta.json").exists()


def scout(interest: str, want: int = 20, max_pages: int = 3, per_page: int = 25) -> list[dict]:
    """Return up to `want` UNREAD works for an interest (paged). Slim dicts (for task params)."""
    out, page = [], 1
    seen = set()
    while len(out) < want and page <= max_pages:
        try:
            works = openalex.search(interest, limit=per_page, page=page)
        except Exception as e:
            log().emit("error", f"scout failed for “{interest}” p{page}: {str(e)[:140]}", actor="scout")
            break
        if not works:
            break
        for w in works:
            if w.slug and w.slug not in seen and not _already_read(w.slug):
                seen.add(w.slug)
                out.append(w.to_dict())
                if len(out) >= want:
                    break
        page += 1
    return out


def read_url(url: str, interest: str = "web", *, parent_id=None) -> dict:
    """Read an ARBITRARY web page (not just a paper) through the same pipeline."""
    from ..ingest import web
    try:
        w = web.fetch_url(url)
    except Exception as e:
        log().emit("error", f"web fetch failed for {url}: {str(e)[:120]}", actor="reader",
                   parent_id=parent_id)
        return {"ok": False, "error": str(e)[:120]}
    if w is None:
        log().emit("thought", f"nothing substantive at {url}", actor="reader", parent_id=parent_id)
        return {"ok": True, "read": False, "reason": "empty"}
    return read_work(w.to_dict(), interest, parent_id=parent_id)


def read_work(work_dict: dict, interest: str = "", *, parent_id=None) -> dict:
    """Read one specific paper -> claims on disk. Budget-gated extraction."""
    config.ensure_workspace()
    work = openalex.Work.from_dict(work_dict)
    if not work.slug or _already_read(work.slug):
        return {"ok": True, "read": False, "reason": "already-read"}

    text, kind = fetch.fulltext(work)
    src_dir = config.SOURCES_DIR / work.slug
    src_dir.mkdir(parents=True, exist_ok=True)
    (src_dir / "clean.md").write_text(f"# {work.title}\n\n_{kind} · {work.venue or ''} · "
                                      f"{work.year or ''}_\n\n{text}\n", encoding="utf-8")
    meta = {"id": work.id, "slug": work.slug, "title": work.title, "year": work.year,
            "doi": work.doi, "authors": work.authors, "affiliations": work.affiliations,
            "venue": work.venue, "cited_by": work.cited_by,
            "url": work.landing_url or work.pdf_url, "text_kind": kind,
            "interest": interest, "read_at": _now()}
    (src_dir / "meta.json").write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")

    read_ev = log().emit("read",
                         f"read “{work.title[:80]}” ({kind}, {work.year}) — {len(work.affiliations)} "
                         f"affiliation(s)", actor="reader", parent_id=parent_id, slug=work.slug,
                         kind=kind, interest=interest)

    # budget gate: store the text regardless; only spend on extraction if we can afford it
    if not budget().can_spend():
        log().emit("thought", "daily budget reached — stored the text, deferring claim extraction.",
                   actor="reader", parent_id=read_ev)
        (src_dir / "claims.jsonl").write_text("", encoding="utf-8")   # marks read; harvest skips empties
        return {"ok": True, "read": True, "slug": work.slug, "n_claims": 0, "deferred": True}

    claims, usage = extract.extract_claims(text, work.title)
    budget().add(usage.get("cost", 0.0))
    claims = [c for c in claims if isinstance(c, dict)]      # model sometimes emits a bare string
    lines = []
    for c in claims:
        cid = _claim_id(c.get("subject", ""), c.get("relation", ""),
                        c.get("object", ""), c.get("effect_sign", "na"))
        lines.append(json.dumps({"claim_id": cid, "source_id": work.slug,
            "subject": c.get("subject", ""), "relation": c.get("relation", ""),
            "object": c.get("object", ""), "effect_sign": c.get("effect_sign", "na"),
            "quote": c.get("quote", ""), "confidence": c.get("confidence", 0.6),
            "provenance": "READ", "affiliations": work.affiliations, "extracted_at": _now()},
            ensure_ascii=False))
    (src_dir / "claims.jsonl").write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")
    for c in claims[:6]:
        a = {"+": "↑", "-": "↓", "0": "∅"}.get(c.get("effect_sign", "na"), "·")
        log().emit("claim", f"{c.get('subject','?')} {a} {c.get('object','?')}",
                   actor="reader", parent_id=read_ev, effect_sign=c.get("effect_sign", "na"))
    return {"ok": True, "read": True, "slug": work.slug, "n_claims": len(claims),
            "cost": usage.get("cost", 0.0), "kind": kind}
