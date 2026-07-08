"""Real LLM reader (v2, P1): Claude Haiku extracts STRUCTURED claims from a document and
maps them to membrane Candidates. Plugs into the existing `Extractor` Protocol so the
whole v1 pipeline (membrane, loops, engine, UI) works unchanged — just with real claims
instead of keyword fragments.

Validated in experiments/exp_p1_claude_extraction.py (7 real claims from a real abstract,
~$0.004/abstract raw). Constrained via forced tool-use (portable + auditable). Falls back
to the HeuristicExtractor when no API key is present, so the demo still runs offline.
"""
from __future__ import annotations

from typing import Optional

from .. import config
from ..ingest.base import Document
from .reader import Candidate, claim_key, HeuristicExtractor

# relation -> belief direction (+1 asserts the claim, -1 refutes/negates it)
_RELN_DIR = {
    "increases": +1.0, "causes": +1.0, "associated_with": +1.0, "requires": +1.0,
    "inhibits": +1.0,   # "X inhibits Y" asserts a real (negative) mechanism -> the claim holds
    "decreases": +1.0,  # asserts a real effect direction; membrane tracks the relation's existence
    "no_effect": -1.0,  # a null result -> refutes the association
}

EXTRACT_TOOL = {
    "name": "record_claims",
    "description": "Record the falsifiable scientific claims asserted or tested in this text.",
    "input_schema": {
        "type": "object",
        "properties": {
            "claims": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "subject": {"type": "string"},
                        "relation": {"type": "string",
                                     "enum": list(_RELN_DIR.keys())},
                        "object": {"type": "string"},
                        "population": {"type": "string"},
                        "confidence": {"type": "number"},
                    },
                    "required": ["subject", "relation", "object"],
                },
            }
        },
        "required": ["claims"],
    },
}

_SYSTEM = ("You extract falsifiable biomedical claims as structured tuples. Be precise, "
           "prefer the 3-8 most important claims, never pad, and set confidence to how "
           "strongly the text asserts each claim.")


class ClaudeExtractor:
    """Real reader. `extract(doc) -> [Candidate]`. Reuses one client across calls."""

    def __init__(self, model: Optional[str] = None, client=None, max_tokens: int = 4096):
        self.model = model or config.MODEL_READER
        self.max_tokens = max_tokens
        self._client = client
        self._fallback = HeuristicExtractor()
        self.last_usage = {"in": 0, "out": 0, "cost": 0.0}

    def _client_or_none(self):
        if self._client is None and config.have_key():
            self._client = config.anthropic_client()
        return self._client

    def extract(self, doc: Document) -> list[Candidate]:
        client = self._client_or_none()
        if client is None:                       # no key -> honest offline fallback
            return self._fallback.extract(doc)
        text = f"Title: {doc.title}\n\nText: {doc.text}".strip()
        if not text:
            return []
        resp = client.messages.create(
            model=self.model, max_tokens=self.max_tokens, system=_SYSTEM,
            tools=[EXTRACT_TOOL], tool_choice={"type": "tool", "name": "record_claims"},
            messages=[{"role": "user", "content": text + "\n\nExtract the claims."}],
        )
        u = resp.usage
        self.last_usage = {"in": u.input_tokens, "out": u.output_tokens,
                           "cost": config.est_cost_usd(self.model, u.input_tokens, u.output_tokens)}
        raw = []
        for block in resp.content:
            if block.type == "tool_use":
                raw = block.input.get("claims", []) or []
        group = doc.group or doc.source
        out: list[Candidate] = []
        for c in raw:
            subj, obj = c.get("subject", "").strip(), c.get("object", "").strip()
            reln = c.get("relation", "associated_with")
            if not subj or not obj:
                continue
            out.append(Candidate(
                claim_key=claim_key(subj, obj),
                statement=f"{subj} {reln.replace('_', ' ')} {obj}",
                direction=_RELN_DIR.get(reln, +1.0),
                group=group, doc_id=doc.doc_id, provenance="READ",
                confidence=float(c.get("confidence", 0.6)),
                meta={"subject": subj, "object": obj, "relation": reln,
                      "population": c.get("population"), "year": doc.year},
            ))
        return out
