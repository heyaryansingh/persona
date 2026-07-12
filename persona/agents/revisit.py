"""Revisit / re-verify (v8) — the mind re-tests its own past work.

The self-correcting half of the verified loop. Periodically re-examine a past TESTED result against
what the mind knows NOW: re-run its machine check (re-prove), or re-review its report. Then update
the ledger — still-verified / weakened / refuted. No other researcher tool re-checks its own past
conclusions; this is what makes Persona a scientist rather than a one-shot generator.
"""
from __future__ import annotations

from ..budget import budget
from ..context import get_persona
from ..events import log
from ..memory import verified as vled


def revisit(*, parent_id=None) -> dict:
    """Re-test the least-recently-checked past result. Returns {ok, statement, old, new, note}."""
    if not budget().can_spend():
        return {"ok": False, "reason": "no-budget"}
    ents = vled.entries()
    # re-test the least-recently-revisited still-standing result (verified or weakened), oldest first
    cand = sorted([e for e in ents if e.get("status") in ("verified", "weakened")],
                  key=lambda e: (e.get("revisits", 0), e.get("last_revisit", ""), e.get("at", "")))
    if not cand:
        return {"ok": True, "revisited": 0, "reason": "nothing-to-revisit"}
    e = cand[0]
    stmt, method = e["statement"], e.get("method")
    log().emit("thought", f"revisiting a past result to re-verify it: “{stmt[:60]}”",
               actor="revisit", parent_id=parent_id)

    if method in ("sympy", "lean"):
        # re-run the machine check — a real proof re-verifies; if it no longer checks, it's weakened/refuted
        from . import reason
        r = reason.prove(stmt, parent_id=parent_id)
        v, t = r.get("verified", 0), r.get("checks", 0)
        new = "verified" if (t > 0 and v == t) else ("weakened" if v > 0 else "refuted")
        note = f"re-proved: {v}/{t} checks passed" if t else "no machine-checkable steps on re-test"
    else:
        # analyst/other — re-review the report against current evidence
        from . import critic
        cr = critic.critique(stmt, parent_id=parent_id)
        new = "verified" if cr.get("verdict") == "solid" else "weakened"
        note = f"re-reviewed: verdict {cr.get('verdict', '?')}"

    vled.update_status(e["key"], new, note)
    arrow = "held" if new == e["status"] else f"{e['status']}→{new}"
    log().emit("belief_update", f"re-verified “{stmt[:52]}”: {arrow} ({note})", actor="revisit",
               parent_id=parent_id)
    return {"ok": True, "statement": stmt, "old": e["status"], "new": new, "note": note,
            "method": method}
