"""Citation checker (v5 P6) — the eval-in-the-loop gate for defensibility.

Verifies that a synthesis's sentences are actually supported by the source quotes it was built
from (in-the-wild citation hallucination is 11-57%; we generate FROM quotes to avoid it, and this
CHECKS it). A cheap Haiku pass returns the unsupported sentences; the caller records the support
rate on the note and can revise. Deliverable-quality guard (also gates reviews/papers).
"""
from __future__ import annotations

from .. import config
from ..budget import budget

_TOOL = {"name": "report_support", "description": "Report which synthesis sentences are NOT "
         "supported by the provided source quotes.",
         "input_schema": {"type": "object", "properties": {
             "total_sentences": {"type": "integer"},
             "unsupported": {"type": "array", "items": {"type": "string"},
                             "description": "verbatim sentences that go beyond the quotes"}},
             "required": ["total_sentences", "unsupported"]}}

_SYSTEM = ("You are a strict fact-checker. Given SOURCE QUOTES and a SYNTHESIS, identify sentences "
           "in the synthesis that are NOT supported by the quotes (claims that go beyond the "
           "evidence). Ignore headers, the citation markers [n], and the sources list. Be precise.")


def check(body: str, quotes: list[str]) -> dict:
    """Return {support_rate, total, unsupported}. support_rate None if unavailable."""
    if not config.have_key() or not budget().can_spend() or not quotes:
        return {"support_rate": None, "total": 0, "unsupported": []}
    from ..providers import anthropic_client
    client = anthropic_client()
    qs = "\n".join(f"- {q}" for q in quotes if q)[:6000]
    resp = client.messages.create(
        model=config.MODEL_READER, max_tokens=1024, system=_SYSTEM, tools=[_TOOL],
        tool_choice={"type": "tool", "name": "report_support"},
        messages=[{"role": "user", "content": f"SOURCE QUOTES:\n{qs}\n\nSYNTHESIS:\n{body[:6000]}"}])
    u = resp.usage
    budget().add((u.input_tokens * 1.0 + u.output_tokens * 5.0) / 1_000_000)
    out = {}
    for b in resp.content:
        if b.type == "tool_use":
            out = b.input
    total = max(1, int(out.get("total_sentences", 1)))
    unsup = out.get("unsupported", []) or []
    return {"support_rate": round(max(0.0, 1 - len(unsup) / total), 3), "total": total,
            "unsupported": unsup[:8]}
