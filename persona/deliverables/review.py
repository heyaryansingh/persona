"""Literature-review engine (v5 P9) — a cited, defensible review of a topic.

AutoSurvey/STORM-style assembly over the mind's OWN cited synthesis notes (each already grounded
in verbatim quotes), so the review inherits provenance. Stages: gather relevant notes -> draft a
structured review (abstract, intro, thematic sections, contradictions/open problems, conclusion)
citing sources -> citation-check -> write deliverables/review-<slug>.md with a References section.
Because it's built FROM cited notes, every reference resolves to a real paper.
"""
from __future__ import annotations

import re
from datetime import datetime, timezone

from .. import config
from ..budget import budget
from ..context import get_persona
from ..events import log

_TOOL = {"name": "write_review", "description": "Write a structured, cited literature review.",
         "input_schema": {"type": "object", "properties": {
             "title": {"type": "string"},
             "abstract": {"type": "string"},
             "review_markdown": {"type": "string", "description": "the full review: ## Introduction, "
                 "thematic ## sections, ## Contradictions & open problems, ## Conclusion. Cite "
                 "sources inline as [n] using the numbered sources provided. Ground every claim in "
                 "the synthesis notes; do not invent."}},
             "required": ["title", "review_markdown"]}}

_SYSTEM = ("You are writing a rigorous, citable literature review for scientists, from your own "
           "cited synthesis notes. Be structured, balanced, and honest about disagreement and gaps. "
           "Cite sources inline as [n] from the numbered list. Never state anything the notes don't "
           "support. Aim for depth over breadth on the strongest evidence.")


def _slug(t): return (re.sub(r"[^a-z0-9]+", "-", t.lower()).strip("-")[:50] or "review")


def _now(): return datetime.now(timezone.utc).isoformat(timespec="seconds")


def write_review(topic: str, *, parent_id=None, max_notes: int = 8) -> dict:
    if not config.have_key() or not budget().can_spend():
        return {"ok": False, "reason": "no-key-or-budget"}
    p = get_persona()
    nd = p.paths.notes_dir
    if not nd.exists() or not any(nd.glob("*.md")):
        return {"ok": False, "reason": "no-notes-yet"}
    # gather the most relevant notes (vector search on the topic; fall back to all)
    slugs = [h["slug"] for h in p.vectors.search(topic, k=max_notes) if h.get("slug")]
    if not slugs:
        slugs = [f.stem for f in sorted(nd.glob("*.md"))[:max_notes]]
    notes, sources, snum = [], [], {}
    for s in slugs:
        f = nd / f"{s}.md"
        if not f.exists():
            continue
        txt = f.read_text(encoding="utf-8")
        notes.append(txt)
        for m in re.finditer(r"^\[(\d+)\]\s*(.+)$", txt, re.M):    # collect this note's sources
            key = m.group(2).strip()
            if key not in snum:
                snum[key] = len(sources) + 1
                sources.append(key)
    if not notes:
        return {"ok": False, "reason": "no-notes-matched"}
    src_list = "\n".join(f"[{snum[k]}] {k}" for k in sources)
    corpus = "\n\n=== NOTE ===\n".join(n[:3000] for n in notes)

    from anthropic import Anthropic
    client = Anthropic(api_key=config.ANTHROPIC_API_KEY)
    resp = client.messages.create(model=config.MODEL_WORKER, max_tokens=4096, system=_SYSTEM,
        tools=[_TOOL], tool_choice={"type": "tool", "name": "write_review"},
        messages=[{"role": "user", "content": f"Topic: {topic}\n\nMY SYNTHESIS NOTES:\n{corpus}\n\n"
                   f"NUMBERED SOURCES:\n{src_list}\n\nWrite the review."}])
    u = resp.usage
    budget().add((u.input_tokens * 3.0 + u.output_tokens * 15.0) / 1_000_000)
    out = {}
    for b in resp.content:
        if b.type == "tool_use":
            out = b.input
    if not out:
        return {"ok": False, "reason": "no-output"}
    from ..synthesis import checker
    chk = checker.check(out.get("review_markdown", ""), sources)   # sources are the citation targets
    sr = chk.get("support_rate")
    title = out.get("title", topic)
    md = (f"# {title}\n\n_literature review · {len(notes)} synthesis notes · {len(sources)} sources"
          + (f" · {int(sr*100)}% supported" if sr is not None else "") + f" · {_now()}_\n\n"
          f"## Abstract\n{out.get('abstract','')}\n\n{out.get('review_markdown','')}\n\n"
          f"## References\n{src_list}\n")
    p.paths.deliverables_dir.mkdir(parents=True, exist_ok=True)
    fname = f"review-{_slug(topic)}.md"
    (p.paths.deliverables_dir / fname).write_text(md, encoding="utf-8")
    log().emit("artifact", f"wrote a literature review: “{title}” ({len(sources)} sources"
               + (f", {int(sr*100)}% supported" if sr is not None else "") + ")",
               actor="reviewer", parent_id=parent_id, file=fname)
    return {"ok": True, "file": fname, "title": title, "sources": len(sources), "support_rate": sr}
