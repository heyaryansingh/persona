"""The reader (v4 P1): interest -> a real paper -> structured claims on disk.

Blank-slate → first read. Picks the top not-yet-read work for an interest, fetches its full text
(OA PDF) or abstract, extracts auditable claims with Claude, and writes them into the workspace
under sources/<slug>/. Idempotent: a work already in sources/ is skipped. Emits real READ/CLAIM
events so the live stream shows an actual read happening.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone

from .. import config
from ..events import log
from ..ingest import openalex, fetch
from . import extract


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _claim_id(subject: str, relation: str, obj: str, sign: str) -> str:
    key = f"{subject.strip().lower()}|{relation.strip().lower()}|{obj.strip().lower()}|{sign}"
    return "clm_" + hashlib.sha1(key.encode()).hexdigest()[:12]


def _already_read(slug: str) -> bool:
    return (config.SOURCES_DIR / slug / "claims.jsonl").exists()


def read_interest(interest: str, *, parent_id=None, limit: int = 6) -> dict:
    """Read one unread paper for `interest`. Returns a summary dict."""
    config.ensure_workspace()
    try:
        works = openalex.search(interest, limit=limit, oa_only=False)
    except Exception as e:
        log().emit("error", f"OpenAlex search failed for “{interest}”: {str(e)[:160]}",
                   actor="reader", parent_id=parent_id)
        return {"ok": False, "error": str(e)[:160]}
    work = next((w for w in works if w.slug and not _already_read(w.slug)), None)
    if work is None:
        log().emit("thought", f"already read the top results for “{interest}”; nothing new here yet.",
                   actor="reader", parent_id=parent_id)
        return {"ok": True, "read": False, "reason": "all-read"}

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
    (src_dir / "meta.json").write_text(json.dumps(meta, indent=2, ensure_ascii=False),
                                       encoding="utf-8")

    read_ev = log().emit("read",
                         f"read “{work.title[:80]}” ({kind}, {work.year}) — {len(work.authors)} "
                         f"authors, {len(work.affiliations)} affiliations",
                         actor="reader", parent_id=parent_id, slug=work.slug, kind=kind,
                         interest=interest)

    claims, usage = extract.extract_claims(text, work.title)
    lines = []
    for c in claims:
        cid = _claim_id(c.get("subject", ""), c.get("relation", ""),
                        c.get("object", ""), c.get("effect_sign", "na"))
        rec = {"claim_id": cid, "source_id": work.slug, "subject": c.get("subject", ""),
               "relation": c.get("relation", ""), "object": c.get("object", ""),
               "effect_sign": c.get("effect_sign", "na"), "quote": c.get("quote", ""),
               "confidence": c.get("confidence", 0.6), "provenance": "READ",
               "affiliations": work.affiliations, "extracted_at": _now()}
        lines.append(json.dumps(rec, ensure_ascii=False))
    (src_dir / "claims.jsonl").write_text("\n".join(lines) + ("\n" if lines else ""),
                                          encoding="utf-8")

    for c in claims[:8]:
        sign = c.get("effect_sign", "na")
        arrow = {"+": "↑", "-": "↓", "0": "∅"}.get(sign, "·")
        log().emit("claim",
                   f"{c.get('subject','?')} {arrow} {c.get('object','?')} "
                   f"({c.get('relation','?')})", actor="reader", parent_id=read_ev,
                   source=work.slug, effect_sign=sign)
    if not config.have_key():
        log().emit("thought", "stored the text; claim extraction needs an API key (none set).",
                   actor="reader", parent_id=read_ev)
    return {"ok": True, "read": True, "slug": work.slug, "title": work.title,
            "n_claims": len(claims), "cost": usage.get("cost", 0.0), "kind": kind}
