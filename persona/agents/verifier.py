"""Tool-grounded Verifier agent (Lane 1 · F1.2) — an INDEPENDENT agent that re-runs the actual check
on contested/high-stakes claims. Its first move is an APPLICABILITY GATE that emits an explicit
`not_applicable` verdict (distinct from a pass), so an out-of-domain claim is never falsely "verified"
— the out-of-domain false positive is the correctness boundary the epistemic charter names.

This fill ships the gate (the correctness boundary — deterministic, $0, tested). The independent
re-check itself is a thin ROUTER over existing PAID execution — computational claims →
`analyst.investigate` (verification-framed, pinning the claim), math claims → `reason.prove` — and the
strict supported/refuted verdict-from-session mapping + TESTED-provisional recording. That routing is
budget-gated (it spends), so it runs only with a key/budget; at $0 it degrades to `inconclusive`
without spending. See PRD-01 F1.2 + FC-1.
"""
from __future__ import annotations

VERDICTS = ("supported", "refuted", "inconclusive", "not_applicable")
_MODEL_SYSTEMS_MATH = "na"


def _result(claim_id: str, verdict: str, *, check_kind=None, ran_code: bool = False,
            artifact_ids=None, span: str = "", note: str = "") -> dict:
    return {"ok": True, "claim_id": str(claim_id), "verdict": verdict, "check_kind": check_kind,
            "ran_code": ran_code, "artifact_ids": list(artifact_ids or []), "span": span, "note": note}


def _claim_quote(claim: dict) -> str:
    """The exact source span for the claim, if any (top-level quote or the first source's quote)."""
    q = (claim.get("quote") or "").strip()
    if q:
        return q
    for s in (claim.get("sources") or []):
        if isinstance(s, dict) and (s.get("quote") or "").strip():
            return s["quote"].strip()
    return ""


def is_verifiable(claim: dict) -> tuple[bool, str]:
    """Applicability gate — CAN this agent independently re-check the claim? Only if it has an exact
    source span AND is either a directional empirical claim (reproducible by computation) or a
    math/theoretical statement (provable). Everything else → not verifiable-by-this-agent, an explicit
    SKIP distinct from a pass. Deterministic, $0. This is what prevents the out-of-domain false positive."""
    if not isinstance(claim, dict):
        return False, "no claim"
    if not _claim_quote(claim):
        return False, "no exact-span quote to verify against"
    sign = claim.get("effect_sign")
    if sign == _MODEL_SYSTEMS_MATH:
        return True, "math"                     # theoretical/mathematical → reason.prove
    if sign in ("+", "-"):
        return True, "computational"            # directional empirical → analyst reproduction
    return False, "null/non-directional claim — nothing to reproduce"


def _lookup_claim(claim_id: str) -> dict | None:
    """Resolve a claim_id → claim dict via the belief graph (Lane 2 / FC-3), read-only + import-guarded
    so this lane never hard-blocks on the membrane's availability."""
    try:
        from ..context import get_persona
        kg = get_persona().kg
        claim = kg.provenance(claim_id)
        return claim if isinstance(claim, dict) and claim else None
    except Exception:
        return None


def _statement(claim: dict) -> str:
    return f"{claim.get('subject','')} {claim.get('relation','')} {claim.get('object','')}".strip()


def verify(claim_id: str, *, parent_id=None, evidence_claim_ids=None) -> dict:
    """Independently re-check a single claim. Returns the frozen F1.2 shape:
        {ok, claim_id, verdict∈VERDICTS, check_kind, ran_code, artifact_ids, span, note}

    APPLICABILITY GATE FIRST (the tested $0 correctness boundary): a claim with no exact-span quote, or
    a null/non-directional claim, returns `not_applicable` and makes NO model/sandbox call. Only a
    verifiable claim is routed to the paid independent re-check (self-gating on budget)."""
    claim = _lookup_claim(claim_id)
    if claim is None:
        return _result(claim_id, "not_applicable", note="claim not found in the belief graph")
    ok, reason = is_verifiable(claim)
    if not ok:
        # neutral control — an explicit skip, NOT a failure, and NO paid call.
        return _result(claim_id, "not_applicable", note=reason, span=_claim_quote(claim))

    # verifiable → route to the existing paid execution. Both callees gate themselves on key/budget,
    # so at $0 they return not-ok and we honestly report `inconclusive` (couldn't run the check).
    span = _claim_quote(claim)
    statement = _statement(claim)
    try:
        if reason == "math":
            from . import reason as reason_agent
            res = reason_agent.prove(f"Prove or disprove: {statement}", parent_id=parent_id)
            verdict = "supported" if res.get("ok") and res.get("proved") else "inconclusive"
            return _result(claim_id, verdict, check_kind="math", ran_code=False,
                           span=span, note=res.get("reason", ""))
        # computational: independent reproduction, pinning the claim + any supplied evidence.
        from . import analyst
        pinned = [claim_id] + list(evidence_claim_ids or [])
        res = analyst.investigate(
            f"Independently REPRODUCE or REFUTE this claim with real data/computation: {statement}",
            parent_id=parent_id, evidence_claim_ids=pinned)
        if not res.get("ok"):
            return _result(claim_id, "inconclusive", check_kind="computational",
                           note=f"re-check did not run: {res.get('reason','')}")
        verdict, artifacts = _verdict_from_session(res.get("session_id", ""))
        if verdict == "supported":               # a reproduced computational result is TESTED-provisional
            _record_tested(statement, artifacts)
        return _result(claim_id, verdict, check_kind="computational",
                       ran_code=bool(res.get("ran_code")), artifact_ids=artifacts, span=span,
                       note=f"session {res.get('session_id','')}")
    except Exception as exc:                      # never let the verifier crash its caller
        return _result(claim_id, "inconclusive", check_kind=reason, note=f"verify error: {str(exc)[:120]}")


def _verdict_from_session(session_id: str) -> tuple[str, list]:
    """Map the analyst run's recorded conclusions to a verdict. A SUPPORTED conclusion = the claim
    reproduced (`supported`); otherwise the reproduction was inconclusive. Analyst's schema does not
    emit an explicit refutation, so `refuted` is reserved for a future contradiction signal."""
    try:
        from ..context import get_persona
        from ..sessions import read_session
        loaded = read_session(get_persona().paths.runs_dir, session_id)
        if not loaded:
            return "inconclusive", []
        concl = loaded["session"].get("conclusions") or []
        artifacts = [e for c in concl for e in (c.get("evidence_ids") or [])
                     if str(e).startswith("artifact:")][:3]
        if any(c.get("status") == "SUPPORTED" for c in concl):
            return "supported", artifacts
        return "inconclusive", artifacts
    except Exception:
        return "inconclusive", []


def _record_tested(statement: str, artifacts: list) -> None:
    """A supported computational verification is a TESTED-provisional result — same gate as the analyst,
    no new authority, tagged source='verify'. Import-guarded (verified ledger is Lane 2's)."""
    try:
        from ..memory import verified as vled
        vled.record(statement, "analyst", "verified", evidence=",".join(artifacts[:3]), source="verify")
    except Exception:
        pass
