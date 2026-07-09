"""The reflecting self (v4 P4) — the Ralph-loop cognitive act that makes the mind EVOLVE.

Periodically (budget-gated, slow cadence) Opus reads the durable self + what's been learned (top
beliefs, live contradictions, topics recently read) and rewrites the self: it reweights interests,
SPAWNS NEW interests it was never seeded with, forms new questions from contradictions and gaps,
records strategies/taste, updates its identity, and picks priority reads. Fresh context each time;
all state lives in the self files. This is where genuine interests, ideas, and autonomy come from.
"""
from __future__ import annotations

from .. import config, selfmind
from ..budget import budget
from ..events import log

_TOOL = {
    "name": "evolve_self",
    "description": "Rewrite the researcher's evolving self after reflecting on what it has learned.",
    "input_schema": {
        "type": "object",
        "properties": {
            "interests": {"type": "array", "description": "the FULL evolved interest list "
                          "(keep what still matters, drop what's exhausted, ADD new curiosities "
                          "the reading opened up)",
                          "items": {"type": "object", "properties": {
                              "name": {"type": "string"}, "weight": {"type": "number"},
                              "reason": {"type": "string"}}, "required": ["name", "weight"]}},
            "open_questions": {"type": "array", "items": {"type": "string"},
                               "description": "the questions most worth answering next (from "
                               "contradictions, gaps, surprises)"},
            "priority_reads": {"type": "array", "items": {"type": "string"},
                               "description": "specific topics/queries to go read next"},
            "strategy_note": {"type": "string", "description": "a reading/analysis strategy that's working (or not)"},
            "taste_note": {"type": "string", "description": "what surprised me or feels important"},
            "identity_update": {"type": "string", "description": "one sentence on how I've changed"},
            "changelog": {"type": "string", "description": "one-line summary of this reflection"},
        },
        "required": ["interests", "open_questions", "priority_reads", "changelog"],
    },
}

_SYSTEM = ("You are a persistent, autonomous research mind reflecting on your own progress. You "
           "were spawned as a blank slate with a few seed interests; you have been reading at scale "
           "and building a belief graph. Reflect like a real scientist deciding what to pursue: "
           "follow contradictions and surprises, spawn genuinely NEW interests the reading opened "
           "up (not just the seeds), sharpen your questions, and be honest about what you don't yet "
           "know. Keep interests focused (5-9). Return the evolved self via the tool.")


def _kg_summary(kg, n: int = 25) -> str:
    if kg is None:
        return "(knowledge graph unavailable)"
    beliefs = kg.beliefs(min_independent=1, limit=n)
    contra = kg.contradictions(limit=15)
    bl = "\n".join(f"- {b['subject']} [{b['effect_sign']}] {b['object']} "
                   f"({b['independent_sources']} labs, p={b['confidence']:.2f})" for b in beliefs) or "(none yet)"
    cl = "\n".join(f"- {c['subject']} → {c['object']}: +{c['pos_sources']} vs −{c['neg_sources']} labs"
                   for c in contra) or "(none yet)"
    return f"TOP BELIEFS:\n{bl}\n\nLIVE CONTRADICTIONS:\n{cl}"


def deliberate(kg=None, *, parent_id=None) -> dict:
    """Run one reflection. Returns {ok, priority_reads, new_interests}. Applies the self-rewrite."""
    if not config.have_key():
        return {"ok": False, "reason": "no-key"}
    if not budget().can_spend():
        return {"ok": False, "reason": "budget"}
    from anthropic import Anthropic
    client = Anthropic(api_key=config.ANTHROPIC_API_KEY)
    s = selfmind.read_self()
    directives = (s.get('directives.md', '') or '').strip()
    dir_block = (f"## STANDING DIRECTIVES FROM THE HUMAN (weigh these heavily)\n{directives}\n\n"
                 if directives else "")
    prompt = (f"MY CURRENT SELF:\n\n## identity\n{s.get('identity.md','')}\n\n"
              f"{dir_block}"
              f"## interests\n{s.get('interests.md','')}\n\n## open questions\n{s.get('open_questions.md','')}\n\n"
              f"## strategies\n{s.get('strategies.md','')[:1500]}\n\n"
              f"## what I've learned so far\n{_kg_summary(kg)}\n\n"
              f"Reflect and evolve. Honor the human's standing directives first, then follow the "
              f"contradictions and surprises; spawn new interests the reading opened up.")
    resp = client.messages.create(
        model=config.MODEL_SELF, max_tokens=2048, system=_SYSTEM, tools=[_TOOL],
        tool_choice={"type": "tool", "name": "evolve_self"},
        messages=[{"role": "user", "content": prompt}])
    u = resp.usage
    budget().add((u.input_tokens * 15.0 + u.output_tokens * 75.0) / 1_000_000)   # Opus $/Mtok
    out = {}
    for b in resp.content:
        if b.type == "tool_use":
            out = b.input
    if not out:
        return {"ok": False, "reason": "no-output"}

    from .. import coherence
    prev_pairs = selfmind.interests()
    prev_interests = {n.lower() for n, _ in prev_pairs}
    prev_sig = coherence.interest_signature()
    new_pairs = [(i["name"], i.get("weight", 1.0)) for i in out.get("interests", [])
                 if isinstance(i, dict) and i.get("name")]
    THETA = 0.7          # E-DRIFT: above this the interest set is being wholesale-replaced = a spiral
    applied_pairs = prev_pairs
    if new_pairs:
        new_sig = {w for name, _ in new_pairs for w in name.lower().split() if len(w) > 3}
        pdrift = coherence.drift(prev_sig, new_sig)
        if pdrift > THETA and prev_pairs:
            # GUARD THAT ACTS (v6 P6): one reflection may not replace the whole self. Keep the
            # existing focus and admit at most 2 genuinely-new interests (bounded, healthy growth).
            fresh = [(n, w) for n, w in new_pairs if n.lower() not in prev_interests][:2]
            applied_pairs = (list(prev_pairs) + fresh)[:9]
            selfmind.set_interests(applied_pairs)
            log().emit("coherence", f"throttled a large interest shift (drift={pdrift:.2f}) — kept my "
                       f"focus, admitted {len(fresh)} new interest(s) instead of spiraling",
                       actor="self", parent_id=parent_id)
        else:
            selfmind.set_interests(new_pairs)
            applied_pairs = new_pairs
    if out.get("open_questions"):
        selfmind.set_open_questions(out["open_questions"])
    selfmind.append_section("strategies.md", out.get("strategy_note", ""))
    selfmind.append_section("taste.md", out.get("taste_note", ""))
    selfmind.append_section("identity.md", out.get("identity_update", ""))
    selfmind.append_changelog(out.get("changelog", "reflected"))

    # anti-degradation: keep the self bounded (memory-blocks); the drift guard above already ACTED
    coherence.enforce_caps()

    spawned = [n for n, _ in applied_pairs if n.lower() not in prev_interests]
    log().emit("thought",
               f"reflected (Opus): {out.get('changelog','')[:120]}"
               + (f" · spawned new interest(s): {', '.join(spawned[:4])}" if spawned else ""),
               actor="self", parent_id=parent_id, spawned=spawned)
    return {"ok": True, "priority_reads": out.get("priority_reads", []),
            "new_interests": spawned}
