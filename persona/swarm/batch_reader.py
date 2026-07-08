"""Batch-API reader (v3 T2.1) — the real cost lever for background bulk reading.

The Anthropic Message Batches API runs asynchronously at ~50% of standard price. It is the
honest economics win for "read thousands/day": the interactive AsyncSwarm is for live/urgent
reads; BatchReader is for the always-on background sweep where a few-minutes-to-24h turnaround
is fine. Same Extractor semantics (EXTRACT_TOOL + _SYSTEM + the shared candidates_from_claims),
so everything downstream is unchanged.

(Prompt caching, the other T2.1 item, is a NO-OP for single-abstract extraction: the stable
prefix here is system+tools ~300 tokens, below Haiku's 2048-token cache minimum, so nothing
caches. Verified — see results/FINDINGS.md T2.1. Caching would only pay off with a large stable
few-shot prefix; Batch is the lever that actually applies.)
"""
from __future__ import annotations

import time
from typing import Optional

from .. import config
from .claude_reader import EXTRACT_TOOL, _SYSTEM
from .orchestrator import candidates_from_claims


class BatchReader:
    def __init__(self, model: Optional[str] = None, max_tokens: int = 4096, canon=None):
        self.model = model or config.MODEL_READER
        self.max_tokens = max_tokens
        self.canon = canon

    def build_requests(self, docs) -> tuple:
        """Build (requests, id_map). custom_id is index-based (safe, <=64 chars); id_map maps
        it back to the Document. Pure — unit-testable without network."""
        requests, id_map = [], {}
        for i, doc in enumerate(docs):
            cid = f"d{i}"
            id_map[cid] = doc
            requests.append({
                "custom_id": cid,
                "params": {
                    "model": self.model,
                    "max_tokens": self.max_tokens,
                    "system": [{"type": "text", "text": _SYSTEM,
                                "cache_control": {"type": "ephemeral"}}],
                    "tools": [EXTRACT_TOOL],
                    "tool_choice": {"type": "tool", "name": "record_claims"},
                    "messages": [{"role": "user",
                                  "content": f"Title: {doc.title}\n\nText: {doc.text}\n\n"
                                             f"Extract the claims."}],
                },
            })
        return requests, id_map

    def submit(self, docs, client=None) -> tuple:
        client = client or config.anthropic_client()
        requests, id_map = self.build_requests(docs)
        batch = client.messages.batches.create(requests=requests)
        return batch.id, id_map

    def poll(self, batch_id: str, client=None) -> str:
        client = client or config.anthropic_client()
        return client.messages.batches.retrieve(batch_id).processing_status

    def collect(self, batch_id: str, id_map: dict, client=None) -> dict:
        """Gather results into {doc_id: [Candidate]} once the batch has ended."""
        client = client or config.anthropic_client()
        out = {}
        for res in client.messages.batches.results(batch_id):
            doc = id_map.get(res.custom_id)
            if doc is None or res.result.type != "succeeded":
                continue
            raw = []
            for b in res.result.message.content:
                if b.type == "tool_use":
                    raw = b.input.get("claims", []) or []
            out[doc.doc_id] = candidates_from_claims(doc, raw, self.canon)
        return out

    def read_and_wait(self, docs, membrane, *, poll_s: float = 10.0, timeout_s: float = 3600.0,
                      client=None) -> dict:
        """Convenience: submit a batch, wait for it, submit candidates to the membrane, harvest.
        For scripts/background jobs — NOT the live request path."""
        client = client or config.anthropic_client()
        batch_id, id_map = self.submit(docs, client=client)
        waited = 0.0
        while self.poll(batch_id, client=client) != "ended":
            if waited >= timeout_s:
                return {"batch_id": batch_id, "status": "timeout", "read": 0}
            time.sleep(poll_s)
            waited += poll_s
        results = self.collect(batch_id, id_map, client=client)
        read = 0
        for cands in results.values():
            for c in cands:
                membrane.submit(c)
            read += 1
        rep = membrane.harvest()
        return {"batch_id": batch_id, "status": "ended", "read": read,
                "committed": len(rep.committed), "held": len(rep.held),
                "contradictions": len(rep.contradictions), "report": rep}
