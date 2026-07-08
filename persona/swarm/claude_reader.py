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
from .reader import Candidate, HeuristicExtractor, build_candidate, RELATION_SIGN

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
                                     "enum": list(RELATION_SIGN.keys())},
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
           "strongly the text asserts each claim. Use CANONICAL, SHORT entity names for "
           "subject and object — the standard gene/protein/cell/pathway/process name, and "
           "DROP modifiers (write 'microglia' not 'microglial activation'; 'neuroinflammation' "
           "not 'neuroinflammatory response'; 'tau' not 'hyperphosphorylated tau protein'; "
           "'NLRP3' not 'NLRP3 inflammasome activation') so the same relation from different "
           "papers matches and converges.")


class ClaudeExtractor:
    """Real reader. `extract(doc) -> [Candidate]`. Reuses one client across calls."""

    def __init__(self, model: Optional[str] = None, client=None, max_tokens: int = 4096,
                 canon=None):
        self.model = model or config.MODEL_READER
        self.max_tokens = max_tokens
        self._client = client
        self._canon = canon                 # optional EntityCanonicalizer (shared with the async path)
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
        from ..ingest.independence import independence_group
        group = independence_group(doc)
        out: list[Candidate] = []
        for c in raw:
            if not isinstance(c, dict):
                continue
            cand = build_candidate(c.get("subject"), c.get("object"),
                                   c.get("relation", "associated_with"), group, doc.doc_id,
                                   confidence=c.get("confidence", 0.6), canon=self._canon,
                                   population=c.get("population"))
            if cand:
                cand.meta["year"] = doc.year
                out.append(cand)
        return out
