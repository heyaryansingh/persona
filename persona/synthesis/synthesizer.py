"""Synthesizer (v5 P5) — one community's claims+quotes -> a cited synthesis NOTE.

Grounded generation: the writer sees ONLY this subtopic's claims with their VERBATIM QUOTES and
source labels, and writes a concise synthesis citing sources inline as [n]. Because it generates
FROM stored quotes (not free recall), citations can't be fabricated (the P6 citation-checker
verifies). The note is written to notes/<slug>.md, linked in the KG (SynthesisNote-[:SYNTHESIZES]->
Claim), and embedded for retrieval. This is durable, cited UNDERSTANDING — not triples.
"""
from __future__ import annotations

import difflib
import re
from datetime import datetime, timezone

from .. import config
from ..budget import budget
from ..context import get_persona
from ..events import log

_TOOL = {
    "name": "write_synthesis",
    "description": "Write a cited synthesis of what is known about this subtopic.",
    "input_schema": {"type": "object", "properties": {
        "title": {"type": "string", "description": "a specific subtopic title"},
        "synthesis_markdown": {"type": "string", "description": "3-6 short paragraphs synthesizing "
            "the evidence; cite sources inline as [n] using the numbered list; be honest about "
            "disagreement and gaps. Do NOT invent claims beyond the evidence."},
        "open_questions": {"type": "array", "items": {"type": "string"}},
        "contradictions": {"type": "array", "items": {"type": "string"}},
    }, "required": ["title", "synthesis_markdown"]}}

_SYSTEM = ("You synthesize a subtopic of a research field from EXTRACTED CLAIMS and their verbatim "
           "quotes. Write a tight, cited synthesis a scientist could trust: what the evidence shows, "
           "where labs disagree, and what's open. Cite sources inline as [n] from the numbered list. "
           "Ground every statement in the provided quotes — never add claims not supported by them.")


def _slug(entities: list) -> str:
    s = "-".join(re.sub(r"[^a-z0-9]+", "", e.lower())[:14] for e in entities[:3] if e)
    return (s or "topic")[:60]


def substance_tier(support_rate: float | None, n_claims: int) -> str:
    """Objective substance grade for a synthesis, from the two signals we actually measure:
    what fraction of the prose traces back to a stored verbatim quote, and how many claims back it.
    Thresholds are deliberately conservative so a thin/ungrounded note reads as a DRAFT, not a finding
    — this is the substance gate that stops 'unverified reports with no substance' from looking authoritative."""
    if support_rate is None:
        return "unverified"
    if support_rate >= 0.7 and n_claims >= 4:
        return "verified"
    if support_rate >= 0.4:
        return "provisional"
    return "draft"


_TIER_BANNER = {
    "verified": "> **verified synthesis** · {pct}% of statements trace to a stored quote across {n} claims.",
    "provisional": "> **provisional** · {pct}% quote-supported across {n} claims — treat as tentative.",
    "draft": "> **draft** · only {pct}% quote-supported — not yet a reliable synthesis, do not cite as settled.",
    "unverified": "> **unverified** · quote-support not checked ({n} claims).",
}


def _tier_banner(tier: str, support_rate: float | None, n_claims: int) -> str:
    return _TIER_BANNER[tier].format(pct=int((support_rate or 0) * 100), n=n_claims)


def demo() -> None:  # ponytail: one runnable check on the branchy gate
    assert substance_tier(0.9, 6) == "verified"
    assert substance_tier(0.9, 2) == "provisional"   # high support but too few claims
    assert substance_tier(0.5, 10) == "provisional"
    assert substance_tier(0.2, 10) == "draft"
    assert substance_tier(None, 10) == "unverified"
    print("substance_tier ok")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def note_diff(old: str, new: str) -> str:
    """Deterministic line-level diff between two synthesis revisions (stdlib difflib, no model/network).
    Returns a unified diff of the changed lines (file-header lines dropped); '' when nothing changed."""
    old_lines = (old or "").splitlines()
    new_lines = (new or "").splitlines()
    diff = difflib.unified_diff(old_lines, new_lines, lineterm="", n=1)
    return "\n".join(l for l in diff if not l.startswith(("---", "+++")))


def record_revision(notes_dir, slug: str, title: str, old: str, new: str) -> str:
    """When a synthesis note is rewritten, append what changed to a `<slug>.history.md` sidecar so the
    note's evolution is auditable. No-op (returns '') when the body is unchanged. Deterministic diff;
    only the revision timestamp is wall-clock."""
    diff = note_diff(old, new)
    if not diff.strip():
        return ""
    hist = notes_dir / f"{slug}.history.md"
    hist.parent.mkdir(parents=True, exist_ok=True)
    with hist.open("a", encoding="utf-8") as fh:
        fh.write(f"## revision {_now()} — {title}\n\n```diff\n{diff}\n```\n\n")
    return diff


def synthesize(community: dict, *, parent_id=None) -> dict:
    """Synthesize one community into a cited note. Returns {ok, slug, title, n_claims}."""
    if not config.have_key() or not budget().can_spend():
        return {"ok": False, "reason": "no-key-or-budget"}
    p = get_persona()
    kg = p.kg
    claims = kg.claims_in(community["entities"], limit=50)
    if len(claims) < 2:
        return {"ok": False, "reason": "too-few-claims"}

    # numbered, deduped source list (the citation targets) + the grounded claim block
    src_num, src_list = {}, []
    for c in claims:
        for s in (c.get("sources") or []):
            if s.get("slug") and s["slug"] not in src_num:
                src_num[s["slug"]] = len(src_list) + 1
                src_list.append(s)
    arrow = {"+": "increases", "-": "decreases", "0": "no effect"}
    claim_lines = []
    for c in claims:
        cites = sorted({src_num[s["slug"]] for s in (c.get("sources") or []) if s.get("slug") in src_num})
        q = next((s.get("quote") for s in (c.get("sources") or []) if s.get("quote")), "")
        claim_lines.append(f"- {c['subject']} {arrow.get(c['effect_sign'],'~')} {c['object']} "
                           f"({c['independent_sources']} labs) {['['+str(n)+']' for n in cites]}"
                           + (f'  quote: "{q[:180]}"' if q else ""))
    _st = lambda x: re.sub(r"<[^>]+>", "", str(x or "")).strip()   # strip leaked <i>/<b>… from titles
    sources_md = "\n".join(f"[{src_num[s['slug']]}] {_st(s.get('title')) or s['slug']} — "
                           f"{_st(s.get('lab'))}" + (f" (doi:{s['doi']})" if s.get('doi') else "")
                           for s in src_list)
    prompt = (f"Subtopic entities: {', '.join(community['entities'][:12])}\n\n"
              f"CLAIMS (with independent-lab counts, [n]=source, and a quote):\n"
              + "\n".join(claim_lines) + f"\n\nNUMBERED SOURCES:\n{sources_md}\n\n"
              f"Write the cited synthesis.")

    from ..providers import anthropic_client
    client = anthropic_client()
    resp = client.messages.create(model=config.MODEL_WORKER, max_tokens=4096, system=_SYSTEM,
                                  tools=[_TOOL], tool_choice={"type": "tool", "name": "write_synthesis"},
                                  messages=[{"role": "user", "content": prompt}])
    u = resp.usage
    budget().add((u.input_tokens * 3.0 + u.output_tokens * 15.0) / 1_000_000)
    out = {}
    for b in resp.content:
        if b.type == "tool_use":
            out = b.input
    if not out:
        return {"ok": False, "reason": "no-output"}

    slug = _slug(community["entities"])
    title = out.get("title", slug)
    from ..deliverables.document import sanitize_markdown
    body = sanitize_markdown(out.get("synthesis_markdown", ""))
    # substance floor: a note whose body is empty/near-empty (the forced-tool JSON truncated, or the
    # community was incoherent) is just a citation list with no synthesis — never save that as a note.
    if len(body.strip()) < 200:
        log().emit("control", f"skipped an empty synthesis for {slug} (no substance, {len(claims)} claims)",
                   actor="synthesizer", parent_id=parent_id, slug=slug)
        return {"ok": False, "reason": "empty-synthesis"}
    def _clean(s):
        s = re.sub(r"</?item>", "", str(s))       # leaked XML wrapper the model sometimes emits
        s = re.sub(r"<[^>]+>", "", s)               # any stray tag (<i>, <b>, …)
        return s.strip()

    def _aslist(v):
        # the model sometimes returns a STRING (or a "<item>a</item><item>b</item>" blob) where a list
        # is expected; iterating that char-by-char was the single-letter-bullet bug. Split on item tags
        # (NOT characters), strip tags, drop empties/1-char noise.
        if isinstance(v, str):
            parts = [_clean(p) for p in re.split(r"</?item>", v)]
            items = [p for p in parts if len(p) > 1]
            return items if items else ([_clean(v)] if len(_clean(v)) > 1 else [])
        if isinstance(v, list):
            return [_clean(x) for x in v if len(_clean(x)) > 1]
        return []
    oq = _aslist(out.get("open_questions"))
    contra = _aslist(out.get("contradictions"))
    # eval-in-the-loop: verify the synthesis is actually supported by the quotes (defensibility)
    from . import checker
    allquotes = [s.get("quote") for c in claims for s in (c.get("sources") or []) if s.get("quote")]
    chk = checker.check(body, allquotes)
    sr = chk.get("support_rate")
    sr_str = f" · {int(sr*100)}% quote-supported" if sr is not None else ""
    tier = substance_tier(sr, len(claims))
    banner = _tier_banner(tier, sr, len(claims))
    md = (f"# {title}\n\n_synthesis · {len(claims)} claims · {len(src_list)} sources{sr_str} · updated {_now()}_\n\n"
          f"{banner}\n\n"
          f"{body}\n\n" + ("## open questions\n" + "\n".join(f"- {q}" for q in oq) + "\n\n" if oq else "")
          + ("## contradictions\n" + "\n".join(f"- {q}" for q in contra) + "\n\n" if contra else "")
          + "## sources\n" + sources_md + "\n")
    p.paths.notes_dir.mkdir(parents=True, exist_ok=True)
    note_path = p.paths.notes_dir / f"{slug}.md"
    prev = note_path.read_text(encoding="utf-8") if note_path.exists() else None
    note_path.write_text(md, encoding="utf-8")
    if prev is not None:  # a revision — log what changed to the .history sidecar
        record_revision(p.paths.notes_dir, slug, title, prev, md)
    kg.add_synthesis_note(slug, title, community["entities"], [c["claim_id"] for c in claims])
    try:
        p.vectors.upsert(f"note:{slug}", f"{title}\n{body}", {"title": title, "slug": slug, "kind": "note"})
    except Exception:
        pass
    log().emit("synthesis", f"synthesized “{title}” [{tier}] ({len(claims)} claims, {len(src_list)} sources"
               + (f", {int(sr*100)}% quote-supported" if sr is not None else "") + ")",
               actor="synthesizer", parent_id=parent_id, slug=slug, support_rate=sr, tier=tier)
    return {"ok": True, "slug": slug, "title": title, "n_claims": len(claims),
            "support_rate": sr, "tier": tier}
