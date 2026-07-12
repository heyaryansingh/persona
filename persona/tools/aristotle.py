"""Aristotle (Harmonic) — formally-verified Lean 4 proofs (v8, optional).

When a Harmonic Aristotle API key is present (env PERSONA_ARISTOTLE_KEY; sign up at
aristotle.harmonic.fun) and `aristotlelib` is installed, Persona can attempt a FORMAL Lean 4 proof of
a mathematical statement — checked by the Lean kernel, the strongest possible TESTED tier (Aristotle
delivered formally-verified solutions to 5/6 IMO-2025 problems). Without a key/lib it is a safe no-op
and the mind falls back to the sympy verify-refine loop. Any failure returns verified=False so the
`prove` step never breaks.
"""
from __future__ import annotations

import os


def available() -> bool:
    """True only if a key is set AND the client lib imports — otherwise `prove` uses sympy."""
    if not os.environ.get("PERSONA_ARISTOTLE_KEY"):
        return False
    try:
        import aristotlelib  # noqa: F401
        return True
    except Exception:
        return False


def prove_formal(statement: str, *, timeout: int = 300) -> dict:
    """Attempt a formal Lean 4 proof of `statement`. Returns {available, verified, proof, error}.

    The exact aristotlelib surface is confirmed against the installed version at call time; on ANY
    mismatch or error this returns verified=False and the caller degrades to sympy (fail-safe).
    """
    if not available():
        return {"available": False, "verified": False}
    key = os.environ["PERSONA_ARISTOTLE_KEY"]
    try:
        import aristotlelib
        # try the documented client patterns; whichever the installed lib exposes
        client = None
        for ctor in ("Client", "Aristotle", "AristotleClient"):
            if hasattr(aristotlelib, ctor):
                client = getattr(aristotlelib, ctor)(api_key=key)
                break
        if client is None:
            return {"available": True, "verified": False, "error": "aristotlelib client not found"}
        fn = next((getattr(client, m) for m in ("prove", "prove_statement", "verify", "submit")
                   if hasattr(client, m)), None)
        if fn is None:
            return {"available": True, "verified": False, "error": "no prove method on client"}
        res = fn(statement, timeout=timeout) if "timeout" in fn.__code__.co_varnames else fn(statement)
        d = res if isinstance(res, dict) else getattr(res, "__dict__", {}) or {}
        verified = bool(d.get("verified") or getattr(res, "verified", False)
                        or d.get("status") == "verified")
        proof = (d.get("proof") or d.get("lean_code") or d.get("lean")
                 or getattr(res, "proof", None))
        return {"available": True, "verified": verified, "proof": proof}
    except Exception as e:
        return {"available": True, "verified": False, "error": str(e)[:200]}
