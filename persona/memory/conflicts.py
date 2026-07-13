"""Conflict typing (Lane 1 · F2.5 — RQ-E02 substrate).

Classify a sign-collision between two same-identity claims (same subject→object, opposite effect sign)
into WHY they disagree, so escalation is precise: a measurement taken at a different timepoint, or in a
different study context, is NOT a refutation. Deterministic + $0 — it reads the §B qualifiers already
attached at extraction; no model call.

The FC-2 enum {temporal, semantic, misinformation, insufficient} is frozen. This types a CANDIDATE only
— `candidate_conflict ≠ verified contradiction` until RQ-E02 clears its precision gate; nothing here
anchors a belief. (owner: imp2 via the Lane-2 redistribution — conflict-typing.)
"""
from __future__ import annotations

CONFLICT_TYPES = ("temporal", "semantic", "misinformation", "insufficient")


def _qual(claim, field: str):
    q = (claim or {}).get("qualifiers") or {}
    v = q.get(field)
    return str(v).strip().lower() if isinstance(v, str) and v.strip() else None


def _retracted(claim) -> bool:
    return bool((claim or {}).get("retracted"))


def type_conflict(claim_a: dict, claim_b: dict) -> str:
    """Why do two opposite-sign claims on the same subject→object disagree? Precedence:
      1. a retraction on either side          → 'misinformation' (a withdrawn result isn't evidence)
      2. a DIFFERENT measurement timepoint     → 'temporal' (the effect changed over time)
      3. a DIFFERENT study context (population / model system) → 'semantic' (context divergence)
      4. nothing distinguishes them            → 'insufficient' (honest default — needs more evidence)
    Returns a value in CONFLICT_TYPES. Never fabricates a stronger type than the qualifiers support."""
    if _retracted(claim_a) or _retracted(claim_b):
        return "misinformation"
    ta, tb = _qual(claim_a, "timepoint"), _qual(claim_b, "timepoint")
    if ta and tb and ta != tb:
        return "temporal"
    for field in ("population", "model_system"):
        va, vb = _qual(claim_a, field), _qual(claim_b, field)
        if va and vb and va != vb:
            return "semantic"
    return "insufficient"


def _oracle(is_retracted):
    """The retraction lookup: a caller-injected one (tests / a cheaper source), else FC-6
    `ingest.retraction.is_retracted` (imp4's, import-guarded so this never hard-blocks), else a safe
    default that flags nothing (absence of evidence is never treated as a retraction)."""
    if callable(is_retracted):
        return is_retracted
    try:
        from ..ingest import retraction
        return retraction.is_retracted
    except Exception:
        return lambda doi=None, pmid=None: {"retracted": False}


def retraction_scan(claims, *, is_retracted=None) -> list[dict]:
    """F2.13: flag every claim resting on a RETRACTED source — contamination a robustness audit must
    surface (a belief built on withdrawn evidence must not be trusted; ties to type_conflict's
    'misinformation'). Checks each claim's sources' doi/pmid against the FC-6 retraction oracle.
    Returns [{claim_id, subject, object, retraction, source}] for the contaminated claims — read-only,
    never mutates a belief."""
    oracle = _oracle(is_retracted)
    flagged = []
    for c in (claims or []):
        for s in (c.get("sources") or []):
            if not isinstance(s, dict):
                continue
            doi, pmid = s.get("doi"), s.get("pmid")
            if not doi and not pmid:
                continue
            try:
                r = oracle(doi=doi, pmid=pmid) or {}
            except Exception:
                continue
            if r.get("retracted"):
                flagged.append({"claim_id": c.get("claim_id"), "subject": c.get("subject"),
                                "object": c.get("object"), "retraction": r,
                                "source": doi or pmid or s.get("slug")})
                break                        # one retracted source is enough to flag the claim
    return flagged
