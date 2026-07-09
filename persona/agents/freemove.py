"""Free move (v6 P4) — the persona chooses WHAT KIND of thing to do next.

Not a router rebuild: a single Opus step whose tool schema is an ENUM of vetted registry actions.
It picks one action + a topic from what it can ALREADY do (read, investigate, synthesize, review,
paper, diagram, page, art, code), grounded in its self + graph + standing directives, and logs its
rationale. The worker enqueues the chosen task. The mind chooses freely among reviewed capabilities;
it can never invent a new one. Bounded by budget + coherence + workspace-jail.
"""
from __future__ import annotations

from .. import config, selfmind
from ..budget import budget
from ..events import log

ACTIONS = ["scout", "investigate", "review", "paper", "diagram", "page", "art", "code", "consolidate"]

_TOOL = {"name": "choose", "description": "Choose your single highest-value next move.",
         "input_schema": {"type": "object", "properties": {
             "action": {"type": "string", "enum": ACTIONS},
             "topic": {"type": "string", "description": "the topic / question / argument the action "
                       "operates on"},
             "rationale": {"type": "string", "description": "one sentence: why this is the highest-"
                           "value move right now"}},
             "required": ["action", "topic", "rationale"]}}

_SYSTEM = ("You are a persistent researcher with a FREE mind and real tools. Choose your single "
           "highest-value next move from your available actions: read more (scout), run a real "
           "computational investigation/experiment (investigate), synthesize what you've read "
           "(consolidate), write a cited review or a compiled paper, build an explanatory diagram, "
           "an interactive explorable page, generative data-art of your own knowledge, or a small "
           "useful code tool. Follow your curiosity AND the human's standing directives; prefer moves "
           "that resolve a contradiction, fill a real gap, make your knowledge legible, or produce "
           "something genuinely useful. Be honest about what's most worth doing right now.")


def free_move(kg=None, *, parent_id=None) -> dict:
    if not config.have_key() or not budget().can_spend():
        return {"ok": False, "reason": "no-key-or-budget"}
    from anthropic import Anthropic
    from .deliberate import _kg_summary
    client = Anthropic(api_key=config.ANTHROPIC_API_KEY)
    s = selfmind.read_self()
    prompt = (f"## my interests\n{s.get('interests.md', '')}\n\n"
              f"## open questions\n{s.get('open_questions.md', '')[:800]}\n\n"
              f"## standing directives from the human\n{s.get('directives.md', '')[:600]}\n\n"
              f"## what I know\n{_kg_summary(kg)}\n\nChoose your next move.")
    resp = client.messages.create(model=config.MODEL_SELF, max_tokens=700, system=_SYSTEM,
                                  tools=[_TOOL], tool_choice={"type": "tool", "name": "choose"},
                                  messages=[{"role": "user", "content": prompt}])
    u = resp.usage
    budget().add((u.input_tokens * 15.0 + u.output_tokens * 75.0) / 1_000_000)
    out = next((b.input for b in resp.content if b.type == "tool_use"), {})
    if not out.get("action"):
        return {"ok": False, "reason": "no-choice"}
    log().emit("thought", f"free move → {out['action']}: {out.get('rationale', '')}",
               actor="self", parent_id=parent_id)
    return {"ok": True, "action": out["action"], "topic": out.get("topic", ""),
            "rationale": out.get("rationale", "")}
