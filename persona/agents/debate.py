"""Gated debate step (Lane 1 · F1.4) — fires ONLY when the membrane reports low convergence or high
stakes (unconditional multi-agent debate is expensive noise; conditional debate helps on hard items,
hurts on easy ones). Positions are DE-IDENTIFIED (no author identity) to curb sycophancy, rounds are
capped, the raw `agreement` fraction is ALWAYS surfaced beside the verdict (guarding the "deliberative
illusion"), and low agreement ESCALATES to a human handoff (FC-2) rather than outvoting a grounded
minority.

The debate rounds themselves are PAID model calls — gated on key/budget, so at $0 `debate` returns an
unresolved, non-escalating result WITHOUT spending. The de-identification, agreement tally, resolve
gate, and escalation-to-handoff are deterministic and $0. See PRD-01 F1.4 + FC-2.
"""
from __future__ import annotations

MAX_ROUNDS = 3
TAU = 0.67                     # agreement fraction required to call a debate resolved
_STANCES = ("+", "-", "0", "na")


def _result(*, resolved: bool, verdict: str, agreement: float, rounds_used: int = 0,
            transcript_ref: str = "", escalate: bool = False) -> dict:
    # FROZEN F1.4 shape — exactly these 7 keys (Lane 2's membrane consumes it; no extra fields).
    return {"ok": True, "resolved": resolved, "verdict": verdict, "agreement": round(float(agreement), 3),
            "rounds_used": rounds_used, "transcript_ref": transcript_ref, "escalate": escalate}


def _deidentify(positions) -> list[dict]:
    """Strip every author/identity field — the debater only ever sees a verbatim span and a stance, so
    it cannot anchor on WHO said it (arXiv:2510.07517). Keeps claim_id for the escalation dossier only;
    that is never put into the debate prompt."""
    clean = []
    for p in (positions or []):
        if not isinstance(p, dict):
            continue
        span = str(p.get("span", "")).strip()
        stance = p.get("stance") if p.get("stance") in _STANCES else "na"
        if span:
            clean.append({"span": span, "stance": stance, "claim_id": str(p.get("claim_id", "")),
                          "qualifiers": p.get("qualifiers") if isinstance(p.get("qualifiers"), dict) else {}})
    return clean


def _tally(votes: list[str]) -> tuple[float, str]:
    """Majority stance + the fraction of the panel converging on it at the final round (the
    self-consistency signal — always surfaced, never hidden behind the verdict)."""
    votes = [v for v in votes if v in _STANCES]
    if not votes:
        return 0.0, ""
    counts: dict[str, int] = {}
    for v in votes:
        counts[v] = counts.get(v, 0) + 1
    verdict, top = max(counts.items(), key=lambda kv: kv[1])
    return top / len(votes), verdict


def _run_rounds(claim: str, positions: list[dict], rounds: int, parent_id) -> list[str]:
    """PAID: run up to `rounds` de-identified debate turns, return the final-round panel stances.
    Gated on key/budget — returns [] at $0 (caller then reports unresolved without spending). The
    prompt is built ONLY from spans + stances (no author identity)."""
    try:
        from .. import config
        from ..budget import budget
        if not config.have_key() or not budget().can_spend():
            return []
    except Exception:
        return []
    # NOTE: the real multi-turn debate exchange is wired here (de-identified prompt → panel stances),
    # budget-gated. Left unimplemented until a budget greenlight — never spend from motion.
    return []


def _escalate(claim: str, positions: list[dict], agreement: float, parent_id) -> str:
    """Low agreement → file a human handoff (FC-2), never outvote a grounded minority. Best-effort:
    a dossier-schema mismatch must not crash the debate."""
    try:
        from .. import inbox
        dossier = {
            "decision_requested": f"Resolve the contested claim: {claim[:200]}",
            "why_unresolvable": f"debate did not converge (agreement {agreement:.2f} < {TAU})",
            "disagreeing": [{"claim_id": p["claim_id"], "span": p["span"], "qualifiers": p["qualifiers"]}
                            for p in positions],
            "conflict_type": "insufficient",
            "cheapest_test": {"action": "human review of the exact spans", "cost_tier": "human",
                              "dataset": ""},
            "expected_updates": [{"outcome": "resolved", "belief_change": "admit the supported stance"}],
            "uncertainty": round(max(0.0, 1.0 - agreement), 3),
            "authority_boundary": "human anchors any high-stakes reversal",
        }
        return inbox.file_handoff("debate_unresolved", dossier)
    except Exception:
        return ""


def debate(claim: str, positions=None, *, rounds: int = 2, parent_id=None) -> dict:
    """Run a de-identified, gated debate over one contested claim. `positions` = de-identified stances
    `[{"span": <verbatim quote>, "stance": "+"|"-"|"0"|"na", "claim_id"?, "qualifiers"?}]`.
    Returns the frozen F1.4 shape:
        {ok, resolved, verdict, agreement, rounds_used, transcript_ref, escalate}
    `agreement` is ALWAYS present; a resolved-but-low-agreement verdict is never sold as confident —
    low agreement ESCALATES (files an FC-2 handoff), it does not outvote the minority."""
    positions = _deidentify(positions)
    if len(positions) < 2:                        # nothing to debate
        return _result(resolved=True, verdict=positions[0]["stance"] if positions else "",
                       agreement=1.0)
    votes = _run_rounds(claim, positions, min(int(rounds), MAX_ROUNDS), parent_id)
    if not votes:                                 # debate could not run ($0 / no budget) — don't escalate
        return _result(resolved=False, verdict="", agreement=0.0)
    agreement, verdict = _tally(votes)
    resolved = agreement >= TAU
    escalate = not resolved
    ref = _escalate(claim, positions, agreement, parent_id) if escalate else ""
    return _result(resolved=resolved, verdict=verdict, agreement=agreement, rounds_used=len(votes),
                   transcript_ref=ref, escalate=escalate)
