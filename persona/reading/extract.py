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
    "description": "Record the specific, checkable claims this text asserts or reports — empirical "
                   "findings AND mathematical/theoretical statements (theorems, bounds, definitions, "
                   "results, conjectures).",
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
                        "qualifiers": {"type": "object", "description": "OPTIONAL context that scopes "
                            "the claim. Include a field ONLY if the text states it; omit otherwise. "
                            "qual_source MUST be a sentence copied verbatim from the text — the span "
                            "the qualifiers are read from — or the whole qualifier block is dropped.",
                            "properties": {
                                "population": {"type": "string", "description": "who/what the finding is about, e.g. 'aged female mice', 'type-2 diabetics'"},
                                "model_system": {"type": "string", "enum": ["in_vivo", "in_vitro", "post_mortem", "cohort"]},
                                "direction": {"type": "string", "enum": ["+", "-", "na"], "description": "effect direction within this qualified context"},
                                "magnitude": {"type": "string", "description": "effect size as stated, e.g. '2.1-fold', 'HR 1.4'"},
                                "timepoint": {"type": "string", "description": "when measured, e.g. 'at 6 months', 'day 14'"},
                                "n": {"type": "integer", "description": "sample size if stated"},
                                "qual_source": {"type": "string", "description": "verbatim sentence the qualifiers are drawn from (exact span)"},
                            }},
                    },
                    "required": ["subject", "relation", "object", "effect_sign", "quote"],
                },
            }
        },
        "required": ["claims"],
    },
}

_SYSTEM = ("You extract specific, checkable claims from research text, in ANY field (biology, physics, "
           "economics, mathematics, computer science...). Return the 3-10 most important claims as "
           "(subject, relation, object) tuples with an effect sign and a quote copied EXACTLY from the "
           "text. For a CAUSAL/EMPIRICAL finding use effect_sign '+' (raises/enables) or '-' "
           "(lowers/prevents). For a MATHEMATICAL or THEORETICAL statement — a theorem, bound, "
           "definition, identity, result, or conjecture — use effect_sign 'na', with subject = the "
           "object/concept, relation = the verb (is/satisfies/implies/bounds/equals/holds_for), object "
           "= the property or result. Do not force theorems into causal tuples. Use canonical, short "
           "names so the same claim from different papers matches. Copy the quote EXACTLY as a full "
           "sentence that appears verbatim in the text — never paraphrase, never invent a claim. "
           "When the text scopes a finding (population, in_vivo/in_vitro/post_mortem/cohort model, "
           "sample size, timepoint, effect magnitude/direction), add a `qualifiers` object AND set "
           "`qual_source` to the verbatim sentence you read them from — a qualifier with no exact "
           "source span is dropped. Omit qualifiers you cannot ground in the text; never guess them.")


# §B FROZEN qualifier contract (S4 extracts → S5 stores; changes only via requests/…--to--S0).
# Six fields + qual_source. Every qualifier MUST cite an exact source span (RQ-E01a discipline) or
# the whole qualifier block is dropped — additive: a bad qualifier never kills an otherwise-valid claim.
_MODEL_SYSTEMS = frozenset({"in_vivo", "in_vitro", "post_mortem", "cohort"})
_DIRECTIONS = frozenset({"+", "-", "na"})


def _clean_qualifiers(q: object, haystack: str) -> dict | None:
    """Return a validated qualifiers dict, or None to drop the block. Exact-span gate first: no
    verbatim qual_source in the source text → the block is not grounded → dropped. Then keep only
    schema-valid, in-vocabulary fields. Unknown/malformed fields are silently ignored, never stored."""
    if not isinstance(q, dict):
        return None
    src = q.get("qual_source")
    if not isinstance(src, str) or not src.strip() or _norm(src) not in haystack:
        return None                                    # ungrounded qualifier — reject per RQ-E01a
    out: dict = {"qual_source": src}
    for field in ("population", "magnitude", "timepoint"):   # free-text, must be non-empty strings
        v = q.get(field)
        if isinstance(v, str) and v.strip():
            out[field] = v.strip()
    ms = q.get("model_system")
    if isinstance(ms, str) and ms in _MODEL_SYSTEMS:
        out["model_system"] = ms
    d = q.get("direction")
    if isinstance(d, str) and d in _DIRECTIONS:
        out["direction"] = d
    n = q.get("n")
    if isinstance(n, bool):                             # bool is an int subclass — never a sample size
        pass
    elif isinstance(n, int):
        out["n"] = n
    elif isinstance(n, float) and n.is_integer():
        out["n"] = int(n)
    return out if len(out) > 1 else None                # qual_source alone carries no information


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
            # Qualifiers are ADDITIVE: validate exact-span + schema, strip if ungrounded, but never
            # let a bad qualifier reject a claim that passed the core gate (identity = subject|object|sign).
            if "qualifiers" in claim:
                cleaned = _clean_qualifiers(claim.get("qualifiers"), haystack)
                if cleaned:
                    claim["qualifiers"] = cleaned
                else:
                    claim.pop("qualifiers", None)
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


def _identity(claim: dict) -> str:
    """The frozen claim identity used to match two independent extractions (same key the KG merges on:
    subject|relation|object|effect_sign, normalized)."""
    return "|".join(_norm(str(claim.get(k, ""))) for k in ("subject", "relation", "object", "effect_sign"))


def cross_check_claims(text: str, title: str = "", *, model_a: str = None, model_b: str = None,
                       client=None) -> tuple[list[dict], list[dict], dict]:
    """F1.3 — TWO independent extractions must AGREE before a claim from a high-value paper is trusted.

    Runs `extract_claims` twice (two models, or the same reader model at different draws), validates
    EACH pass through the exact-span gate (`validate_claims`), then matches on the frozen claim
    identity. Returns `(agreed, disagreements, usage)`: a claim present-and-valid in BOTH passes is
    `agreed` (what the membrane may harvest); a claim in exactly ONE pass is a `disagreement` — kept and
    flagged (auditable), NEVER silently admitted. Agreement is a count of independent reads, never a
    model self-report. This is a STRICTER membrane, not a looser one. The two reads are paid; the
    matching is deterministic and $0."""
    raw_a, ua = extract_claims(text, title, model=model_a or config.MODEL_READER, client=client)
    raw_b, ub = extract_claims(text, title, model=model_b or config.MODEL_READER, client=client)
    a, _ = validate_claims(raw_a, text)
    b, _ = validate_claims(raw_b, text)
    a_by = {_identity(c): c for c in a}
    b_by = {_identity(c): c for c in b}
    agreed = [a_by[k] for k in a_by if k in b_by]
    disagreements = ([a_by[k] for k in a_by if k not in b_by]
                     + [b_by[k] for k in b_by if k not in a_by])
    usage = {"in": ua.get("in", 0) + ub.get("in", 0), "out": ua.get("out", 0) + ub.get("out", 0),
             "cost": round(ua.get("cost", 0.0) + ub.get("cost", 0.0), 5)}
    return agreed, disagreements, usage
