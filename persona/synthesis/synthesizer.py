"""Synthesizer (v5 P5) — one community's claims+quotes -> a cited synthesis NOTE.

Grounded generation: the writer sees ONLY this subtopic's claims with their VERBATIM QUOTES and
source labels, and writes a concise synthesis citing sources inline as [n]. Because it generates
FROM stored quotes (not free recall), citations can't be fabricated (the P6 citation-checker
verifies). The note is written to notes/<slug>.md, linked in the KG (SynthesisNote-[:SYNTHESIZES]->
Claim), and embedded for retrieval. This is durable, cited UNDERSTANDING — not triples.
"""
from __future__ import annotations

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


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


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
    sources_md = "\n".join(f"[{src_num[s['slug']]}] {s.get('title') or s['slug']} — "
                           f"{s.get('lab','')}" + (f" (doi:{s['doi']})" if s.get('doi') else "")
                           for s in src_list)
    prompt = (f"Subtopic entities: {', '.join(community['entities'][:12])}\n\n"
              f"CLAIMS (with independent-lab counts, [n]=source, and a quote):\n"
              + "\n".join(claim_lines) + f"\n\nNUMBERED SOURCES:\n{sources_md}\n\n"
              f"Write the cited synthesis.")

    from anthropic import Anthropic
    client = Anthropic(api_key=config.ANTHROPIC_API_KEY)
    resp = client.messages.create(model=config.MODEL_WORKER, max_tokens=2048, system=_SYSTEM,
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
    body = out.get("synthesis_markdown", "")
    oq = out.get("open_questions", []) or []
    contra = out.get("contradictions", []) or []
    # eval-in-the-loop: verify the synthesis is actually supported by the quotes (defensibility)
    from . import checker
    allquotes = [s.get("quote") for c in claims for s in (c.get("sources") or []) if s.get("quote")]
    chk = checker.check(body, allquotes)
    sr = chk.get("support_rate")
    sr_str = f" · {int(sr*100)}% quote-supported" if sr is not None else ""
    md = (f"# {title}\n\n_synthesis · {len(claims)} claims · {len(src_list)} sources{sr_str} · updated {_now()}_\n\n"
          f"{body}\n\n" + ("## open questions\n" + "\n".join(f"- {q}" for q in oq) + "\n\n" if oq else "")
          + ("## contradictions\n" + "\n".join(f"- {q}" for q in contra) + "\n\n" if contra else "")
          + "## sources\n" + sources_md + "\n")
    p.paths.notes_dir.mkdir(parents=True, exist_ok=True)
    (p.paths.notes_dir / f"{slug}.md").write_text(md, encoding="utf-8")
    kg.add_synthesis_note(slug, title, community["entities"], [c["claim_id"] for c in claims])
    try:
        p.vectors.upsert(f"note:{slug}", f"{title}\n{body}", {"title": title, "slug": slug, "kind": "note"})
    except Exception:
        pass
    log().emit("synthesis", f"synthesized “{title}” ({len(claims)} claims, {len(src_list)} sources"
               + (f", {int(sr*100)}% quote-supported" if sr is not None else "") + ")",
               actor="synthesizer", parent_id=parent_id, slug=slug, support_rate=sr)
    return {"ok": True, "slug": slug, "title": title, "n_claims": len(claims), "support_rate": sr}
