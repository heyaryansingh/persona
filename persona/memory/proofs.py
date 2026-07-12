"""Pending formal proofs (v8) — async Lean 4 proving via Harmonic Aristotle.

Aristotle proving takes minutes, so Persona SUBMITS (fast) and COLLECTS later — the same submit-then-
drain pattern as the reading Batch API, so a slow formal proof never blocks a worker or a team. A
submitted proof is tracked here with its Aristotle task_id; a periodic `collect_proofs` pass polls
each, and a kernel-verified COMPLETE lands in the verification ledger as a **lean**-verified TESTED
belief (the strongest possible tier). This lets the teams keep proving formally in the background while
the human-facing Studio "verify" gets a real formal answer when it's ready.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone

from ..context import get_persona
from ..events import log


def _path():
    return get_persona().paths.ops_dir / "proofs_pending.jsonl"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def pending() -> list[dict]:
    f = _path()
    if not f.exists():
        return []
    out = []
    for line in f.read_text(encoding="utf-8").splitlines():
        if line.strip():
            try:
                out.append(json.loads(line))
            except Exception:
                pass
    return out


def _write(items: list[dict]) -> None:
    get_persona().paths.ops_dir.mkdir(parents=True, exist_ok=True)
    _path().write_text("\n".join(json.dumps(x, ensure_ascii=False) for x in items)
                       + ("\n" if items else ""), encoding="utf-8")


def add_pending(task_id: str, statement: str) -> None:
    items = pending()
    if any(x.get("task_id") == task_id for x in items):
        return
    items.append({"task_id": task_id, "statement": statement[:400], "submitted_at": _now(), "checks": 0})
    _write(items)


def submit_and_track(statement: str) -> dict:
    """Submit a formal Lean 4 proof to Aristotle and track it. Returns {ok, task_id, reason}."""
    from ..tools import aristotle
    r = aristotle.submit(statement)
    if r.get("task_id"):
        add_pending(r["task_id"], statement)
        log().emit("thought", f"submitted a formal Lean 4 proof to Aristotle: “{statement[:56]}” "
                   "(kernel-checking, ~minutes)…", actor="prove")
        return {"ok": True, "task_id": r["task_id"]}
    return {"ok": False, "reason": r.get("error") or ("no-key" if not r.get("available") else "submit-failed")}


def poll() -> dict:
    """Poll pending proofs; record kernel-verified ones to the ledger; drop resolved. Returns counts."""
    from ..tools import aristotle
    from . import verified as vled
    items = pending()
    if not items:
        return {"checked": 0, "verified": 0, "still_pending": 0}
    keep, nver = [], 0
    for it in items:
        r = aristotle.check(it["task_id"])
        it["checks"] = it.get("checks", 0) + 1
        if r.get("done"):
            if r.get("verified"):
                nver += 1
                vled.record(it["statement"], "lean", "verified",
                            evidence=f"aristotle:{it['task_id'][:8]}", source="formal")
                log().emit("belief_update", f"Aristotle formally VERIFIED (Lean 4): "
                           f"“{it['statement'][:56]}”", actor="prove")
            else:
                log().emit("thought", f"formal proof did not verify ({r.get('status', '?')}): "
                           f"“{it['statement'][:50]}”", actor="prove")
        elif it["checks"] < 200:          # keep polling (proving can take a while); give up after ~long
            keep.append(it)
    _write(keep)
    return {"checked": len(items), "verified": nver, "still_pending": len(keep)}
