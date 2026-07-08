"""Async swarm orchestrator (v2, P2): bounded parallel fan-out of real Claude reads with
backpressure, a hard budget cap, and crash-resume — the "hundreds of parallel readers".

Design (from planning/TECH_RESEARCH_V2.json, orchestration domain): no heavyweight engine.
- asyncio.Semaphore(N) bounds concurrency (I/O-bound Claude calls).
- AIMD backoff on 429/529 (multiplicative decay on success, additive increase on throttle).
- Hard USD budget cap (config.DAILY_BUDGET_USD): stop issuing calls past it.
- Crash-resume: a SQLite read-ledger (doc_id -> done) skips already-read docs on restart;
  combined with the membrane's per-doc idempotent commit, re-runs never double-count.

Reads fan out in parallel; the single COMMIT step is sequential (one writer) — "scale in
the swarm, single commit point" (Persona's self/swarm split).
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone

from .. import config
from ..membrane import Membrane
from .claude_reader import EXTRACT_TOOL, _SYSTEM, _RELN_DIR
from .reader import Candidate, claim_key


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class ReadLedger:
    def __init__(self, store):
        self.store = store
        store._db.execute(
            "CREATE TABLE IF NOT EXISTS read_ledger (doc_id TEXT PRIMARY KEY, done_at TEXT)")
        store._db.commit()

    def is_done(self, doc_id: str) -> bool:
        return self.store._db.execute(
            "SELECT 1 FROM read_ledger WHERE doc_id=?", (doc_id,)).fetchone() is not None

    def mark(self, doc_id: str) -> None:
        self.store._db.execute(
            "INSERT OR IGNORE INTO read_ledger (doc_id, done_at) VALUES (?,?)", (doc_id, _now()))
        self.store._db.commit()

    def mark_many(self, doc_ids) -> None:
        now = _now()
        self.store._db.executemany(
            "INSERT OR IGNORE INTO read_ledger (doc_id, done_at) VALUES (?,?)",
            [(d, now) for d in doc_ids])
        self.store._db.commit()          # one commit for the whole batch

    def count(self) -> int:
        return self.store._db.execute("SELECT COUNT(*) AS n FROM read_ledger").fetchone()["n"]


def candidates_from_claims(doc, raw: list) -> list[Candidate]:
    group = doc.group or doc.source
    out = []
    for c in raw:
        subj, obj = (c.get("subject") or "").strip(), (c.get("object") or "").strip()
        reln = c.get("relation", "associated_with")
        if not subj or not obj:
            continue
        out.append(Candidate(
            claim_key=claim_key(subj, obj),
            statement=f"{subj} {reln.replace('_', ' ')} {obj}",
            direction=_RELN_DIR.get(reln, +1.0), group=group, doc_id=doc.doc_id,
            provenance="READ", confidence=float(c.get("confidence", 0.6)),
            meta={"subject": subj, "object": obj, "relation": reln, "year": doc.year},
        ))
    return out


class AsyncSwarm:
    def __init__(self, membrane: Membrane, *, concurrency: int = 16, model: str | None = None,
                 budget_usd: float | None = None, max_tokens: int = 4096, extract_fn=None):
        self.membrane = membrane
        self.store = membrane.store
        self.ledger = ReadLedger(self.store)
        self.model = model or config.MODEL_READER
        self.budget = budget_usd if budget_usd is not None else config.DAILY_BUDGET_USD
        self.max_tokens = max_tokens
        # extract_fn(doc) -> list[Candidate] (async): injectable for deterministic/offline
        # tests (the crash-resume bake-off); None -> real Claude path.
        self.extract_fn = extract_fn
        self._sem = asyncio.Semaphore(concurrency)
        self.spent = 0.0
        self.backoff = 0.0
        self.errors = 0
        self._client = None

    async def _read_one(self, doc) -> tuple:
        async with self._sem:
            if self.extract_fn is not None:                # deterministic/offline path
                return (doc.doc_id, await self.extract_fn(doc))
            if self.spent >= self.budget:
                return (doc.doc_id, None)                  # budget exhausted -> resume later
            if self.backoff:
                await asyncio.sleep(self.backoff)
            try:
                resp = await self._client.messages.create(
                    model=self.model, max_tokens=self.max_tokens, system=_SYSTEM,
                    tools=[EXTRACT_TOOL], tool_choice={"type": "tool", "name": "record_claims"},
                    messages=[{"role": "user",
                               "content": f"Title: {doc.title}\n\nText: {doc.text}\n\nExtract the claims."}])
                self.backoff = max(0.0, self.backoff * 0.5)     # AIMD: success -> decay
            except Exception:
                self.backoff = min(30.0, self.backoff + 2.0)    # throttle/error -> back off
                self.errors += 1
                return (doc.doc_id, None)                        # not marked done -> retried next run
            u = resp.usage
            self.spent += config.est_cost_usd(self.model, u.input_tokens, u.output_tokens)
            raw = []
            for b in resp.content:
                if b.type == "tool_use":
                    raw = b.input.get("claims", []) or []
            return (doc.doc_id, candidates_from_claims(doc, raw))

    async def read_many(self, docs, *, on_progress=None) -> dict:
        """Fan out reads over docs (skipping ledger-done); commit sequentially; mark done."""
        if self.extract_fn is None:
            from anthropic import AsyncAnthropic
            self._client = AsyncAnthropic(api_key=config.ANTHROPIC_API_KEY)
        todo = [d for d in docs if not self.ledger.is_done(d.doc_id)]
        try:
            results = await asyncio.gather(*[self._read_one(d) for d in todo])
        finally:
            if self._client is not None:
                await self._client.close()
        read = 0
        docmap = {d.doc_id: d for d in todo}
        for doc_id, cands in results:                 # sequential single-writer commit
            if cands is None:
                continue
            for c in cands:
                self.membrane.submit(c)
            read += 1
            if on_progress:
                on_progress(doc_id, docmap.get(doc_id), cands)
        rep = self.membrane.harvest()
        self.ledger.mark_many([doc_id for doc_id, cands in results if cands is not None])
        return {"read": read, "committed": len(rep.committed), "held": len(rep.held),
                "contradictions": len(rep.contradictions), "strict": len(rep.strict_claims),
                "spent_usd": round(self.spent, 4), "errors": self.errors,
                "ledger_total": self.ledger.count(), "report": rep}
