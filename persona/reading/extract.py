"""Claim extraction (v4) — text -> structured, auditable candidate claims via Claude (forced
tool-use). DOMAIN-GENERAL: no field-specific vocabulary or examples, so it works for any science
the agent is seeded into. Each claim carries a verbatim `quote` span (auditable, not a summary),
an effect sign (so opposing findings later contradict, not merge), and a confidence.

No key -> returns [] (the reader still fetches + stores the text; extraction resumes when a key
is present). The Batch-API bulk path + structure-aware chunking is P3; this is the online reader.
"""
from __future__ import annotations

import math
import unicodedata

from .. import config

EXTRACT_TOOL = {
    "name": "record_claims",
    "description": "Record the specific, falsifiable factual claims this text asserts or reports.",
    "input_schema": {
        "type": "object",
        "properties": {
            "claims": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "subject": {"type": "string", "description": "the entity/factor, canonical short name"},
                        "relation": {"type": "string", "description": "the relationship verb, e.g. increases/inhibits/causes/correlates_with/enables"},
                        "object": {"type": "string", "description": "the affected entity/outcome, canonical short name"},
                        "effect_sign": {"type": "string", "enum": ["+", "-", "0", "na"],
                                        "description": "+ if subject raises/enables object, - if lowers/prevents, 0 if null/no-effect, na if not directional"},
                        "quote": {"type": "string", "description": "verbatim sentence from the text supporting this claim"},
                        "confidence": {"type": "number", "description": "0-1, how strongly the text asserts it"},
                    },
                    "required": ["subject", "relation", "object", "effect_sign", "quote"],
                },
            }
        },
        "required": ["claims"],
    },
}

_SYSTEM = ("You extract specific, falsifiable factual claims from research text, in ANY field. "
           "Return the 3-10 most important claims as (subject, relation, object) tuples with an "
           "effect sign and a VERBATIM quote from the text. Use canonical, short entity names and "
           "drop modifiers so the same claim from different papers matches. Never invent claims not "
           "supported by a quote. Prefer mechanistic/causal claims over background.")


def _norm(text: str) -> str:
    return " ".join(unicodedata.normalize("NFKC", text or "").casefold().split())


def validate_claims(claims: object, source_text: str) -> tuple[list[dict], list[dict]]:
    """Return exact-span, schema-valid claims and a preserved rejection audit."""
    if not isinstance(claims, list):
        return [], [{"reason": "claims-not-a-list", "claim": claims}]
    haystack = _norm(source_text)
    accepted, rejected = [], []
    for claim in claims:
        reason = None
        if not isinstance(claim, dict):
            reason = "claim-not-an-object"
        elif any(not isinstance(claim.get(k), str) or not claim[k].strip()
                 for k in ("subject", "relation", "object", "quote")):
            reason = "missing-text-field"
        elif claim.get("effect_sign") not in {"+", "-", "0", "na"}:
            reason = "invalid-effect-sign"
        elif "confidence" in claim and (not isinstance(claim["confidence"], (int, float)) or
                                         not math.isfinite(float(claim["confidence"])) or
                                         not 0 <= float(claim["confidence"]) <= 1):
            reason = "invalid-confidence"
        elif _norm(claim["quote"]) not in haystack:
            reason = "quote-not-verbatim"
        if reason:
            rejected.append({"reason": reason, "claim": claim})
        else:
            accepted.append(claim)
    return accepted, rejected


def extract_claims(text: str, title: str = "", *, model: str = None, client=None) -> tuple[list[dict], dict]:
    """Return (claims, usage). Empty list if no API key."""
    if not config.have_key() and client is None:
        return [], {"cost": 0.0, "note": "no api key"}
    from anthropic import Anthropic
    client = client or Anthropic(api_key=config.ANTHROPIC_API_KEY)
    model = model or config.MODEL_READER
    body = (f"Title: {title}\n\nText:\n{text[:40000]}\n\nExtract the claims.").strip()
    resp = client.messages.create(
        model=model, max_tokens=2048, system=_SYSTEM, tools=[EXTRACT_TOOL],
        tool_choice={"type": "tool", "name": "record_claims"},
        messages=[{"role": "user", "content": body}])
    claims = []
    for b in resp.content:
        if b.type == "tool_use":
            claims = b.input.get("claims", []) or []
    u = resp.usage
    cost = (u.input_tokens * 1.0 + u.output_tokens * 5.0) / 1_000_000   # Haiku approx $/Mtok
    return claims, {"in": u.input_tokens, "out": u.output_tokens, "cost": round(cost, 5)}
