"""Consolidator (v5 P5) — the sleep-time pass that turns accumulated claims into understanding.

Runs off the hot read path (on a cadence): detect the subtopic communities, (re)synthesize the
largest ones into cited notes, and refresh a field-overview index. Budget-capped per run. Because
notes are regenerated from the current graph, they stay current as evidence accrues. (A-MEM-style
incremental evolution + citation-checking are P6.)
"""
from __future__ import annotations

from ..budget import budget
from ..context import get_persona
from ..events import log
from . import communities, synthesizer


def consolidate(max_notes: int = 6, parent_id=None) -> dict:
    p = get_persona()
    kg = p.kg
    if kg is None:
        return {"ok": False, "reason": "no-kg"}
    comms = communities.detect(kg, min_size=3)
    if not comms:
        return {"ok": True, "communities": 0, "synthesized": 0}
    log().emit("thought", f"consolidating — found {len(comms)} subtopic(s) in what I've read; "
               f"synthesizing the largest.", actor="consolidator", parent_id=parent_id)
    done = 0
    for c in comms[:max_notes]:
        if not budget().can_spend():
            break
        r = synthesizer.synthesize(c, parent_id=parent_id)
        if r.get("ok"):
            done += 1
    return {"ok": True, "communities": len(comms), "synthesized": done}
