"""Async swarm orchestrator (v2, P2): bounded parallel fan-out of real Claude reads with
backpressure, a persistent daily budget, and crash-resume.

Design (from planning/TECH_RESEARCH_V2.json, orchestration domain): no heavyweight engine.
- asyncio.Semaphore(N) bounds concurrency (default 16 I/O-bound Claude calls in flight; raise
  `concurrency` up to the account's rate limit — it is NOT "hundreds" out of the box).
- AIMD backoff on 429/529 (multiplicative decay on success, additive increase on throttle).
- PERSISTENT daily USD budget (persona.budget.DailyBudget, SQLite by UTC date): spend
  accumulates across ticks/swarms/restarts and resets at UTC midnight — not a per-tick counter.
- Optional Sonnet/Opus escalation: a doc whose Haiku read is AMBIGUOUS (no claims from a
  substantive abstract, or all claims below the confidence floor) is re-read once by the reasoner.
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
from .claude_reader import EXTRACT_TOOL, _SYSTEM
from .reader import Candidate, build_candidate


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


def candidates_from_claims(doc, raw: list, canon=None) -> list[Candidate]:
    """Build membrane Candidates from raw Claude claim dicts — via the SHARED build_candidate
    (same effect-sign + canonicalization as every other extractor path)."""
    from ..ingest.independence import independence_group
    group = independence_group(doc)
    out = []
    for c in raw:
        if not isinstance(c, dict):
            continue
        try:
            conf = float(c.get("confidence", 0.6))
        except (TypeError, ValueError):
            conf = 0.6
        cand = build_candidate(c.get("subject"), c.get("object"),
                               c.get("relation", "associated_with"), group, doc.doc_id,
                               confidence=conf, canon=canon, population=c.get("population"))
        if cand is None:
            continue
        cand.meta["year"] = doc.year
        out.append(cand)
    return out


class AsyncSwarm:
    def __init__(self, membrane: Membrane, *, concurrency: int = 16, model: str | None = None,
                 budget_usd: float | None = None, max_tokens: int = 4096, extract_fn=None,
                 canonicalize: bool = True, escalate: bool = False,
                 reasoner_model: str | None = None, confidence_floor: float = 0.5):
        self.membrane = membrane
        self.store = membrane.store
        self.ledger = ReadLedger(self.store)
        if canonicalize and extract_fn is None:
            from ..canonicalize import EntityCanonicalizer
            self.canon = EntityCanonicalizer()
        else:
            self.canon = None
        self.model = model or config.MODEL_READER
        self.budget = budget_usd if budget_usd is not None else config.DAILY_BUDGET_USD
        from ..budget import DailyBudget
        self.daily = DailyBudget(self.store, self.budget)      # persistent, UTC-daily
        self.escalate = escalate
        self.reasoner_model = reasoner_model or config.MODEL_REASONER
        self.confidence_floor = confidence_floor
        self.escalations = 0
        self.max_tokens = max_tokens
        # extract_fn(doc) -> list[Candidate] (async): injectable for deterministic/offline
        # tests (the crash-resume bake-off); None -> real Claude path.
        self.extract_fn = extract_fn
        self._sem = asyncio.Semaphore(concurrency)
        self.spent = 0.0
        self.backoff = 0.0
        self.errors = 0
        self._client = None
        self._on_event = None

    def _emit(self, ev: dict) -> None:
        if self._on_event:
            try:
                self._on_event(ev)
            except Exception:
                pass

    async def _read_one(self, doc) -> tuple:
        async with self._sem:
            if self.extract_fn is not None:                # deterministic/offline path
                cands = await self.extract_fn(doc)
                self._emit({"type": "read", "doc_id": doc.doc_id, "ok": True,
                            "n_claims": len(cands), "group": doc.group})
                return (doc.doc_id, cands)
            if not self.daily.can_spend():
                return (doc.doc_id, None)                  # daily budget exhausted -> resume later
            if self.backoff:
                await asyncio.sleep(self.backoff)
            try:
                cands = await self._read_with(doc, self.model)
            except Exception:
                self.backoff = min(30.0, self.backoff + 2.0)    # throttle/error -> back off
                self.errors += 1
                self._emit({"type": "read", "doc_id": doc.doc_id, "ok": False, "group": doc.group})
                return (doc.doc_id, None)                        # not marked done -> retried next run
            self.backoff = max(0.0, self.backoff * 0.5)         # AIMD: success -> decay
            # escalate an AMBIGUOUS Haiku read to the reasoner once (T2.3)
            if self.escalate and self._ambiguous(doc, cands) and self.daily.can_spend():
                try:
                    strong = await self._read_with(doc, self.reasoner_model)
                    self.escalations += 1
                    self._emit({"type": "escalate", "doc_id": doc.doc_id, "to": self.reasoner_model,
                                "n_claims": len(strong)})
                    cands = strong or cands
                except Exception:
                    pass
            self._emit({"type": "read", "doc_id": doc.doc_id, "ok": True,
                        "n_claims": len(cands), "group": doc.group,
                        "title": (doc.title or "")[:70]})
            return (doc.doc_id, cands)

    def _ambiguous(self, doc, cands) -> bool:
        """Signal a Haiku read that warrants a stronger re-read: nothing extracted from a
        substantive abstract, or every claim below the confidence floor."""
        if len(doc.text or "") >= 200 and not cands:
            return True
        return bool(cands) and all(c.confidence < self.confidence_floor for c in cands)

    async def _read_with(self, doc, model) -> list:
        resp = await self._client.messages.create(
            model=model, max_tokens=self.max_tokens,
            system=[{"type": "text", "text": _SYSTEM, "cache_control": {"type": "ephemeral"}}],
            tools=[EXTRACT_TOOL], tool_choice={"type": "tool", "name": "record_claims"},
            messages=[{"role": "user",
                       "content": f"Title: {doc.title}\n\nText: {doc.text}\n\nExtract the claims."}])
        u = resp.usage
        cost = config.est_cost_usd(model, u.input_tokens, u.output_tokens,
                                   cache_read=getattr(u, "cache_read_input_tokens", 0) or 0,
                                   cache_write=getattr(u, "cache_creation_input_tokens", 0) or 0)
        self.spent += cost
        self.daily.add(cost)             # persistent daily accounting
        raw = []
        for b in resp.content:
            if b.type == "tool_use":
                raw = b.input.get("claims", []) or []
        return candidates_from_claims(doc, raw, self.canon)

    async def read_many(self, docs, *, on_event=None) -> dict:
        """Fan out reads over docs (skipping ledger-done); commit sequentially; mark done.
        on_event(dict) streams live swarm events (spawn/read/admit/reject/flag) for the UI."""
        self._on_event = on_event
        if self.extract_fn is None:
            from anthropic import AsyncAnthropic
            self._client = AsyncAnthropic(api_key=config.ANTHROPIC_API_KEY)
        todo = [d for d in docs if not self.ledger.is_done(d.doc_id)]
        for d in todo:
            self._emit({"type": "spawn", "doc_id": d.doc_id, "group": d.group,
                        "title": (d.title or "")[:70]})
        try:
            results = await asyncio.gather(*[self._read_one(d) for d in todo])
        finally:
            if self._client is not None:
                await self._client.close()
        read = 0
        for doc_id, cands in results:                 # sequential single-writer commit
            if cands is None:
                continue
            for c in cands:
                self.membrane.submit(c)
            read += 1
        rep = self.membrane.harvest()
        for k in rep.committed:
            self._emit({"type": "admit", "claim_key": k})
        for k in rep.held:
            self._emit({"type": "reject", "claim_key": k})
        for ev in rep.contradictions:
            self._emit({"type": "flag", "claim_key": ev.claim_key, "kind": ev.kind})
        self.ledger.mark_many([doc_id for doc_id, cands in results if cands is not None])
        return {"read": read, "committed": len(rep.committed), "held": len(rep.held),
                "contradictions": len(rep.contradictions), "strict": len(rep.strict_claims),
                "spent_usd": round(self.spent, 4), "spent_today_usd": round(self.daily.spent_today(), 4),
                "budget_remaining_usd": round(self.daily.remaining(), 4),
                "escalations": self.escalations, "errors": self.errors,
                "ledger_total": self.ledger.count(), "report": rep}
