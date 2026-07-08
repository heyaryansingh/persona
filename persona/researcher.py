"""Researcher — the top-level facade that ties the self, swarm, membrane, engine and
loops into one persistent researcher, and exposes JSON-serializable views for the API/UI.

This is the object the UI renders: a mind at work (BUILD_PLAN §6). Everything it returns
is provenance- and uncertainty-honest.
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

from .self_state import Self
from .membrane import Membrane
from .swarm.reader import HeuristicExtractor, Extractor
from .ingest import EuropePMCAdapter
from .ingest.base import DiskCache, SourceAdapter
from .loops.inner import run_inner_loop
from .loops.outer import build_agenda, propose_interests, TasteWeights, Interest
from .loops.delegation import HandoffInbox
from .loops.artifact import mini_review, note_reversal
from .loops.self_test import run_self_test, apply_result_with_signoff, MockDatasetScout, HeuristicTester
from .engine import trajectory, state_of_argument, load_bearing, fragility_cascade, rank_experiments


class Researcher:
    def __init__(self, root: str | Path = "runs/researcher", *,
                 name: str = "Ada", disposition: str = "skeptical-exploratory",
                 seed_interests: Optional[list[str]] = None,
                 adapter: Optional[SourceAdapter] = None,
                 extractor: Optional[Extractor] = None,
                 weights: Optional[TasteWeights] = None):
        self.me = Self(root).hydrate()
        self.name = name
        self.disposition = disposition
        self.seed_interests = seed_interests or ["neuroinflammation", "microglia", "tau"]
        self.weights = weights or TasteWeights()
        self.adapter = adapter or EuropePMCAdapter(cache=DiskCache("tests/fixtures/ingest"))
        self.extractor = extractor or HeuristicExtractor(entities=self.seed_interests)
        self.membrane = Membrane(self.me.store)
        self.inbox = HandoffInbox(self.me.store)
        self._last = None
        self._contradictions = []
        self._write_identity()

    def _write_identity(self):
        self.me.identity_path.write_text(
            f"# identity\n\nname: {self.name}\ndisposition: {self.disposition}\n"
            f"risk_appetite: moderate\n\n_seed interests: {', '.join(self.seed_interests)}_\n",
            encoding="utf-8")

    # ------------------------------------------------------------- act
    def tick(self, queries: Optional[list[str]] = None, limit: int = 8) -> dict:
        """One inner-loop tick + outer reflection; route contradictions to the inbox."""
        queries = queries or [" AND ".join(self.seed_interests[:2] + ["alzheimer"])]
        summary = run_inner_loop(self.me, self.adapter, self.extractor, self.membrane,
                                 queries, limit=limit)
        self._last = summary
        self._contradictions = summary.contradiction_events
        for ev in summary.contradiction_events:
            self.inbox.add_event(ev)
        self.me.consolidate()
        return {"docs_read": summary.docs_read, "candidates": summary.candidates,
                "committed": summary.committed, "held": summary.held,
                "contradictions": summary.contradictions, "strict": summary.strict}

    def close(self):
        self.me.close()

    # ------------------------------------------------------------- views (JSON)
    def dashboard(self) -> dict:
        agenda = build_agenda(self.me.store, self._contradictions,
                              self._interests(), self.weights)
        return {
            "name": self.name, "disposition": self.disposition,
            "interests": [i.__dict__ for i in self._interests()],
            "agenda": [a.__dict__ for a in agenda[:8]],
            "attention": (self._last.__dict__ if self._last else {}),
            "n_beliefs": len(self.me.store.core_claims()),
            "n_open_handoffs": len(self.inbox.open_items()),
        }

    def _interests(self) -> list[Interest]:
        seeded = [Interest(n, 1.0, "seed interest") for n in self.seed_interests]
        return seeded + propose_interests(self.me.store, top_k=3)

    def notebook(self, n: int = 40) -> list[str]:
        lines = self.me.notebook_path.read_text(encoding="utf-8").splitlines()
        return [ln for ln in lines if ln.startswith("- ")][-n:]

    def beliefs(self) -> list[dict]:
        out = []
        for c in self.me.store.core_claims():
            out.append({"claim_id": c.claim_id, "statement": c.statement,
                        "calibrated_p": round(c.calibrated_p, 3),
                        "provenance_state": c.provenance_state, "anchor": c.anchor,
                        "independent_sources": self.me.store.independent_source_count(c.claim_id)})
        return out

    def argument_state(self, claim_id: str) -> dict:
        t = trajectory(self.me.store, claim_id)
        return {"claim_id": claim_id, "velocity": round(t.velocity, 4),
                "acceleration": round(t.acceleration, 4),
                "independence_ratio": round(t.independence_ratio, 3),
                "n_updates": t.n_updates,
                "state": state_of_argument(self.me.store, claim_id),
                "forecast": "descriptive (E5 gate not passed)"}

    def dependency_graph(self) -> dict:
        lb = load_bearing(self.me.store)
        nodes = [{"claim_id": cid, "load_bearing": round(sc, 4),
                  "statement": (self.me.store.get_claim(cid).statement[:80]
                                if self.me.store.get_claim(cid) else cid)}
                 for cid, sc in lb.items()]
        edges = []
        for c in self.me.store.claims(valid_only=True):
            for e in self.me.store.edges_from(c.claim_id, "derives-from"):
                edges.append({"src": e["src"], "dst": e["dst"], "confidence": e["confidence"],
                              "candidate": True})   # INFERRED until E6 passes
        return {"nodes": nodes, "edges": edges, "note": "edges are CANDIDATE (E6 gate not passed)"}

    def experiment_queue(self, candidates) -> list[dict]:
        return rank_experiments(self.me.store, candidates, load_bearing(self.me.store))

    def handoffs(self) -> list[dict]:
        return [d.__dict__ for d in self.inbox.open_items()]

    def resolve_handoff(self, claim_key: str, explanation: str, truth: int) -> dict:
        c = self.inbox.resolve(claim_key, explanation, truth)
        self.me.notebook(f"human resolved {claim_key} → anchored ({explanation[:60]})")
        return {"claim_id": c.claim_id, "provenance_state": c.provenance_state, "anchor": c.anchor}

    def self_test(self, claim_key: str) -> dict:
        ev = next((e for e in self._contradictions if e.claim_key == claim_key), None)
        if ev is None:
            return {"error": "no open contradiction for that claim"}
        res = run_self_test(ev, MockDatasetScout(), HeuristicTester())
        self.me.notebook(f"self-test on {claim_key}: {res.outcome} "
                         f"(conf {res.confidence:.2f}, replay={res.is_replay}) — needs human sign-off")
        return {"claim_key": claim_key, "outcome": res.outcome, "confidence": res.confidence,
                "dataset": (res.dataset.__dict__ if res.dataset else None),
                "is_replay": res.is_replay, "detail": res.detail}

    def artifacts(self) -> dict:
        ids = [c.claim_id for c in self.me.store.core_claims()]
        review = mini_review(self.me.store, ids, title=f"{self.name}: state of the field")
        errors = [ln for ln in self.me.errors_path.read_text(encoding="utf-8").splitlines()
                  if ln.startswith("- ")]
        return {"mini_review": review, "error_log": errors}
