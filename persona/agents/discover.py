"""Discovery / action (v5 P8) — see what's known, then ACT to advance it.

Reads the mind's own knowledge (contradictions, open questions, converged beliefs) and generates
falsifiable HYPOTHESES / leads, each grounded in evidence. Then routes each:
- testable computationally  -> enqueues a real sandbox investigation (the analyst)
- needs a physical/wet-lab test or human judgment -> an evidence-backed HUMAN escalation (Persona
  sees all, tests what it can, and hands the rest to a human — the design's division of labor)
All leads are curated into a readable idea log (deliverables/ideas.md) — the "ideas it found
interesting" deliverable.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone

from .. import config
from ..budget import budget
from ..context import get_persona
from ..events import log

_TOOL = {"name": "propose", "description": "Propose falsifiable hypotheses / research leads from "
         "the current knowledge, each grounded in evidence and routed to compute or a human.",
         "input_schema": {"type": "object", "properties": {"ideas": {"type": "array", "items": {
             "type": "object", "properties": {
                 "title": {"type": "string"},
                 "hypothesis": {"type": "string", "description": "a specific, falsifiable statement"},
                 "rationale": {"type": "string", "description": "why the current evidence motivates it"},
                 "evidence": {"type": "string", "description": "the beliefs/contradictions it builds on"},
                 "testable_computationally": {"type": "boolean",
                     "description": "true if it could be tested with public data + code in a sandbox"},
                 "human_action": {"type": "string", "description": "if it needs a physical/wet-lab "
                     "test or expert judgment, what specifically a human must do"},
                 "novelty": {"type": "integer"}, "value": {"type": "integer"}},
             "required": ["title", "hypothesis", "rationale", "testable_computationally"]}}},
             "required": ["ideas"]}}

_SYSTEM = ("You are a creative but rigorous researcher generating your next moves. From the "
           "knowledge below (converged beliefs, live contradictions, open questions), propose 3-5 "
           "FALSIFIABLE hypotheses or high-value leads. Prefer ones that resolve a contradiction, "
           "fill a gap, or bridge subtopics. For each, judge honestly whether it is testable with "
           "public data + code (you can run that yourself) or needs a physical/wet-lab experiment or "
           "expert judgment (route that to a human). Rank by novelty × testability × value.")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def discover(*, parent_id=None, max_investigations: int = 1) -> dict:
    if not config.have_key() or not budget().can_spend():
        return {"ok": False, "reason": "no-key-or-budget"}
    p = get_persona()
    kg = p.kg
    if kg is None:
        return {"ok": False, "reason": "no-kg"}
    beliefs = kg.beliefs(min_independent=2, limit=20)
    contra = kg.contradictions(limit=12)
    from .. import selfmind
    qs = selfmind.open_questions()[:8]
    if not beliefs and not contra and not qs:
        return {"ok": True, "ideas": 0, "reason": "not-enough-knowledge"}
    arrow = {"+": "raises", "-": "lowers", "0": "no effect on"}
    kb = ("CONVERGED BELIEFS:\n" + "\n".join(f"- {b['subject']} {arrow.get(b['effect_sign'],'~')} "
          f"{b['object']} ({b['independent_sources']} labs)" for b in beliefs) +
          "\n\nLIVE CONTRADICTIONS:\n" + "\n".join(f"- {c['subject']} → {c['object']}: "
          f"+{c['pos_sources']} vs −{c['neg_sources']} labs" for c in contra) +
          "\n\nOPEN QUESTIONS:\n" + "\n".join(f"- {q}" for q in qs))

    from anthropic import Anthropic
    client = Anthropic(api_key=config.ANTHROPIC_API_KEY)
    resp = client.messages.create(model=config.MODEL_SELF, max_tokens=2048, system=_SYSTEM,
                                  tools=[_TOOL], tool_choice={"type": "tool", "name": "propose"},
                                  messages=[{"role": "user", "content": kb + "\n\nPropose."}])
    u = resp.usage
    budget().add((u.input_tokens * 15.0 + u.output_tokens * 75.0) / 1_000_000)
    ideas = []
    for b in resp.content:
        if b.type == "tool_use":
            ideas = b.input.get("ideas", []) or []
    ideas = [i for i in ideas if isinstance(i, dict) and i.get("title")]
    if not ideas:
        return {"ok": False, "reason": "no-output"}

    # append to the curated idea log (a real deliverable) + structured jsonl
    p.paths.deliverables_dir.mkdir(parents=True, exist_ok=True)
    log_md = p.paths.deliverables_dir / "ideas.md"
    prev = log_md.read_text(encoding="utf-8") if log_md.exists() else "# ideas & leads\n\n_hypotheses and leads I've found worth pursuing, with why._\n"
    jl = p.paths.deliverables_dir / "ideas.jsonl"
    queued, escalated = 0, 0
    with jl.open("a", encoding="utf-8") as f, log_md.open("w", encoding="utf-8") as lm:
        lm.write(prev.rstrip() + "\n")
        for i in ideas:
            rec = {**i, "at": _now()}
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            route = "run it myself" if i.get("testable_computationally") else "→ human"
            lm.write(f"\n## {i['title']}\n**Hypothesis:** {i.get('hypothesis','')}\n\n"
                     f"_{i.get('rationale','')}_\n\nEvidence: {i.get('evidence','')}\n\n"
                     f"Route: **{route}**"
                     + (f" — needs: {i.get('human_action','')}" if not i.get('testable_computationally') else "") + "\n")
        lm.write("\n")

    # route: test the top computable one; escalate the physical ones to a human
    q = p.queue()
    for i in ideas:
        if i.get("testable_computationally") and queued < max_investigations:
            q.enqueue("investigate", priority=4, params={"question": i.get("hypothesis", i["title"])},
                      parent_id=parent_id)
            queued += 1
        elif not i.get("testable_computationally") and i.get("human_action"):
            log().emit("escalate", f"needs a human: {i['title']} — {i.get('human_action','')[:120]}",
                       actor="discover", parent_id=parent_id)
            escalated += 1
    log().emit("thought", f"generated {len(ideas)} lead(s) → queued {queued} experiment(s), "
               f"flagged {escalated} for a human", actor="discover", parent_id=parent_id)
    return {"ok": True, "ideas": len(ideas), "queued": queued, "escalated": escalated}
