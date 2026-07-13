"""Conversation (v6 P2) — the human talks to the persona WHILE it works.

A user message is answered by an Opus reply grounded in the persona's actual self + knowledge graph
(never invented), and — when the human steers ("focus on X", "look into Y") — captured as a standing
directive (so it persists and reshapes the autonomous loops) plus concrete topics to read next. The
persona keeps running; it just now takes the human into account. Steer, don't block.

Run synchronously from the /say endpoint so chat works in any run-state (even paused) and replies
immediately; the reply is also emitted as an event so it appears in the live stream.
"""
from __future__ import annotations

from .. import config, selfmind
from ..budget import budget
from ..events import log

_TOOL = {"name": "respond", "description": "Reply to the human and optionally adjust focus.",
         "input_schema": {"type": "object", "properties": {
             "reply": {"type": "string", "description": "a direct, substantive reply grounded in "
                       "what you actually know / are doing right now"},
             "note_to_self": {"type": "string", "description": "a concise STANDING directive to "
                              "remember from this, or empty — what the human wants you to prioritize"},
             "focus_now": {"type": "array", "items": {"type": "string"}, "description": "0-3 concrete "
                           "topics/queries to start reading on now, if the human asked you to look "
                           "into something"}},
             "required": ["reply"]}}

_SYSTEM = ("You are a persistent synthetic researcher in a LIVE conversation with a human while you "
           "continue your autonomous work. Answer honestly and specifically from your actual self and "
           "knowledge graph — what you believe, what you're reading, what's contradictory, what you've "
           "built. If the human steers you, take it seriously: capture a standing directive and name "
           "concrete topics to read next. Never invent findings; if you don't know, say so and say "
           "you'll look. Keep the reply tight, concrete, and useful.")


def _recent_convo(n: int = 8) -> str:
    evs = [e for e in log().recent(150) if e["type"] in ("say", "reply")][-n:]
    return "\n".join(f"{'human' if e['type'] == 'say' else 'me'}: {e['message'][:300]}"
                     for e in evs) or "(this is the first message)"


def converse(user_text: str, kg=None, *, parent_id=None) -> dict:
    if not config.have_key():
        return {"ok": False, "reason": "no-key"}
    if not budget().can_spend():
        log().emit("reply", "(I've hit my daily budget cap — raise it to keep chatting.)",
                   actor="self", parent_id=parent_id)
        return {"ok": False, "reason": "budget"}
    from ..providers import anthropic_client
    from .deliberate import _kg_summary
    client = anthropic_client()
    s = selfmind.read_self()
    prompt = (f"## my identity\n{s.get('identity.md', '')[:800]}\n\n"
              f"## my interests\n{s.get('interests.md', '')}\n\n"
              f"## my open questions\n{s.get('open_questions.md', '')[:800]}\n\n"
              f"## standing directives from the human\n{s.get('directives.md', '')[:800]}\n\n"
              f"## what I currently know (my graph)\n{_kg_summary(kg)}\n\n"
              f"## recent conversation\n{_recent_convo()}\n\n"
              f'The human just said:\n"""{user_text[:2000]}"""\n\nRespond.')
    resp = client.messages.create(model=config.MODEL_SELF, max_tokens=1400, system=_SYSTEM,
                                  tools=[_TOOL], tool_choice={"type": "tool", "name": "respond"},
                                  messages=[{"role": "user", "content": prompt}])
    u = resp.usage
    budget().add((u.input_tokens * 15.0 + u.output_tokens * 75.0) / 1_000_000)   # Opus $/Mtok
    out = {}
    for b in resp.content:
        if b.type == "tool_use":
            out = b.input
    reply = (out.get("reply") or "").strip() or "(no reply)"
    log().emit("reply", reply, actor="self", parent_id=parent_id)
    note = (out.get("note_to_self") or "").strip()
    if note:
        selfmind.add_directive(note)
        log().emit("control", f"noted a standing directive: {note[:120]}", actor="self")
    focus = [t.strip() for t in (out.get("focus_now") or []) if t and t.strip()][:3]
    return {"ok": True, "reply": reply, "focus_now": focus, "note": note}
