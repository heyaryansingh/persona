"""Director (v8) — the orchestrator that keeps research teams on NON-OVERLAPPING problems.

Persona runs many investigations in parallel; the Director is the agent that keeps them distinct.
It surveys the open questions and hands each new team a problem that is NOT already being worked, NOT
already finalized, and NOT already verified — so N teams cover N different questions rather than
duplicating effort. Every assignment is logged to self/director.md so a human can see who is on what.
"""
from __future__ import annotations

import re
from datetime import datetime, timezone

from ..context import get_persona
from ..events import log


def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", (s or "").lower()).strip()


def _taken() -> set[str]:
    """Normalized questions already covered — active/finalized investigations + verified results."""
    taken = set()
    try:
        from ..research.investigation import Investigation
        for i in Investigation.list_all():
            n = _norm(i.question)
            if n:
                taken.add(n)
    except Exception:
        pass
    try:
        from ..memory import verified as vled
        for e in vled.entries():
            n = _norm(e.get("statement", ""))
            if n:
                taken.add(n)
    except Exception:
        pass
    return taken


def assign_question(open_questions, specialization: str = "") -> str | None:
    """Pick the next open question a team should take, distinct from everything already covered
    (fuzzy substring dedup catches near-duplicates). Logs the assignment. Returns the question or None."""
    taken = _taken()
    for q in open_questions:
        nq = _norm(q)
        if not nq:
            continue
        if nq in taken:
            continue
        if any(nq in t or t in nq for t in taken if t):   # near-duplicate of an existing problem
            continue
        _log_assignment(q, specialization)
        return q
    return None


def _log_assignment(q: str, specialization: str) -> None:
    p = get_persona()
    p.paths.self_dir.mkdir(parents=True, exist_ok=True)
    f = p.paths.self_dir / "director.md"
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    header = ("# director — team assignments\n\n_The orchestrator keeps every team on a different "
              "problem: what's assigned, and what it skipped as already-done._\n\n")
    prev = f.read_text(encoding="utf-8") if f.exists() else header
    f.write_text(prev + f"- {now} — assigned a team → “{q[:90]}”"
                 + (f"  ({specialization})" if specialization else "") + "\n", encoding="utf-8")
    log().emit("schedule", f"director: assigned a team to a new problem — “{q[:64]}”", actor="director")
