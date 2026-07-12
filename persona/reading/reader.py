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
from ..context import get_persona
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
    return (get_persona().paths.sources_dir / slug / "meta.json").exists()


# ---- objective-relevance gate --------------------------------------------------------------------
# Reading used to fan out with ZERO relevance filtering, so a math persona pulled ~59% off-topic
# papers (biomed/physics) that then polluted the belief graph. The gate anchors every scouted paper
# to the DURABLE objective (the persona's top-weighted interests), NOT the transient interest
# sentence, using free local bge-small embeddings. tau=0.70 = 0.939 balanced accuracy on 646 real
# Erdos titles (keeps 94% on-topic, drops 94% off-topic). See experiments/exp_rq_e14_relevance_gate.py.
_ANCHOR_CACHE: dict = {"key": None, "vecs": None}


def _objective_anchor() -> list[str]:
    """The persona's durable objective = its strongly-held interests. Empty for a blank slate."""
    try:
        from ..selfmind import interests
        ints = interests()
        if not ints:
            return []
        mx = max((w for _, w in ints), default=1.0) or 1.0
        return [n for n, w in sorted(ints, key=lambda x: -x[1]) if w >= 0.6 * mx][:12]
    except Exception:
        return []


def _relevance_filter(works: list, tau: float) -> tuple[list, int]:
    """Keep only works whose title is on-objective (max cosine to the anchor >= tau). Returns
    (kept, n_dropped). Fails OPEN (keeps everything) with no anchor or if embedding is unavailable —
    a blank-slate or embedding hiccup must never silently stop a mind from reading."""
    anchor = _objective_anchor()
    if not anchor or not works:
        return works, 0
    try:
        from ..memory.embed import encode
        key = tuple(anchor)
        if _ANCHOR_CACHE["key"] != key:
            _ANCHOR_CACHE["key"], _ANCHOR_CACHE["vecs"] = key, encode(anchor)
        av = _ANCHOR_CACHE["vecs"]
        sims = (encode([w.title or "" for w in works]) @ av.T).max(axis=1)
        kept = [w for w, s in zip(works, sims) if s >= tau]
        return kept, len(works) - len(kept)
    except Exception:
        return works, 0


def scout(interest: str, want: int = 20, max_pages: int = 3, per_page: int = 25) -> list[dict]:
    """Return up to `want` UNREAD works for an interest, via multi-source failover (OpenAlex →
    Crossref → Europe PMC → arXiv). Cached + rate-limited + backed-off by the IngestService, so a
    single host's 429 no longer starves discovery."""
    from ..ingest.sources import search_multi
    # FIELD gate at the source: constrain the primary index to the persona's declared fields so
    # off-field papers (education/biomed for a math mind) are never even fetched (exp_rq_e15).
    field_ids = []
    if config.RELEVANCE_GATE:
        try:
            from .. import selfmind
            field_ids = selfmind.allowed_field_ids()
        except Exception:
            field_ids = []
    works, src = search_multi(interest, max(want, per_page), field_ids=field_ids,
                              log=lambda m: log().emit("thought", m, actor="scout", interest=interest))
    # objective-relevance gate BEFORE the want cap: read only the on-objective few, not `want` fakes.
    if config.RELEVANCE_GATE:
        works, dropped = _relevance_filter(works, config.RELEVANCE_TAU)
        if dropped:
            log().emit("control", f"objective filter: skipped {dropped} off-topic paper(s) for "
                       f"“{interest[:60]}”", actor="scout", interest=interest, dropped=dropped)
    seen, out = set(), []
    for w in works:
        if w.slug and w.slug not in seen and not _already_read(w.slug):
            seen.add(w.slug)
            out.append(w.to_dict())
            if len(out) >= want:
                break
    if not out and src == "none":
        log().emit("error", f"no source returned results for “{interest}” (all rate-limited/empty)",
                   actor="scout")
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
    get_persona().paths.ensure()
    work = openalex.Work.from_dict(work_dict)
    if not work.slug or _already_read(work.slug):
        return {"ok": True, "read": False, "reason": "already-read"}

    text, kind = fetch.fulltext(work)
    src_dir = get_persona().paths.sources_dir / work.slug
    src_dir.mkdir(parents=True, exist_ok=True)
    (src_dir / "clean.md").write_text(f"# {work.title}\n\n_{kind} · {work.venue or ''} · "
                                      f"{work.year or ''}_\n\n{text}\n", encoding="utf-8")
    meta = {"id": work.id, "slug": work.slug, "title": work.title, "year": work.year,
            "doi": work.doi, "authors": work.authors, "affiliations": work.affiliations,
            "venue": work.venue, "cited_by": work.cited_by, "field": work.field,
            "field_id": work.field_id, "url": work.landing_url or work.pdf_url, "text_kind": kind,
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

    raw_claims, usage = extract.extract_claims(text, work.title)
    budget().add(usage.get("cost", 0.0))
    claims, rejected = extract.validate_claims(raw_claims, text)
    if rejected:
        (src_dir / "claims_rejected.jsonl").write_text(
            "\n".join(json.dumps(r, ensure_ascii=False) for r in rejected) + "\n", encoding="utf-8")
        # the verbatim gate firing is the membrane WORKING (discipline of believing), not a failure —
        # emit it as a neutral funnel event, not a red error.
        log().emit("control", f"held back {len(rejected)} claim(s) lacking verbatim support",
                   actor="membrane", parent_id=read_ev, slug=work.slug)
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
            "rejected_claims": len(rejected), "cost": usage.get("cost", 0.0), "kind": kind}
