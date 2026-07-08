"""Researcher — the top-level facade that ties the self, swarm, membrane, engine and
loops into one persistent researcher, and exposes JSON-serializable views for the API/UI.

This is the object the UI renders: a mind at work (BUILD_PLAN §6). Everything it returns
is provenance- and uncertainty-honest.
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

from . import config
from .self_state import Self
from .membrane import Membrane
from .swarm.reader import HeuristicExtractor, Extractor
from .ingest import EuropePMCAdapter
from .ingest.base import DiskCache, SourceAdapter
from .loops.inner import run_inner_loop
from .loops.outer import build_agenda, propose_interests, TasteWeights, Interest
from .loops.delegation import HandoffInbox
from .loops.artifact import mini_review, note_reversal
from .loops.self_test import (run_self_test, apply_result_with_signoff, MockDatasetScout,
                              HeuristicTester, GEODatasetScout, ClaudeScienceTester)
from .ingest.base import DiskCache as _DiskCache
from .engine import trajectory, state_of_argument, load_bearing, fragility_cascade, rank_experiments


class Researcher:
    def __init__(self, root: str | Path = "runs/researcher", *,
                 name: str = "Ada", disposition: str = "skeptical-exploratory",
                 seed_interests: Optional[list[str]] = None,
                 adapter: Optional[SourceAdapter] = None,
                 extractor: Optional[Extractor] = None,
                 weights: Optional[TasteWeights] = None,
                 fast_quorum: Optional[int] = None, confidence_floor: Optional[float] = None):
        self.me = Self(root).hydrate()
        self.name = name
        self.disposition = disposition
        self.seed_interests = seed_interests or ["neuroinflammation", "microglia", "tau"]
        self.weights = weights or TasteWeights()
        self.adapter = adapter or EuropePMCAdapter(cache=DiskCache("tests/fixtures/ingest"))
        self.extractor = extractor or HeuristicExtractor(entities=self.seed_interests)
        # disposition -> membrane strictness: a PURE skeptic demands more independent
        # convergence; a balanced/exploratory disposition commits on the normal quorum.
        d = disposition.lower()
        pure_skeptic = "skeptic" in d and "explor" not in d
        fq = fast_quorum if fast_quorum is not None else (3 if pure_skeptic else 2)
        floor = confidence_floor if confidence_floor is not None else (0.6 if pure_skeptic else 0.5)
        self.membrane = Membrane(self.me.store, fast_quorum=fq, confidence_floor=floor)
        self.inbox = HandoffInbox(self.me.store)
        self._last = None
        self._contradictions = []
        self._pending_tests = {}          # claim_key -> SelfTestResult awaiting human sign-off
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
        from .swarm.dependency_tagger import HeuristicDependencyTagger
        self.tag_dependencies(tagger=HeuristicDependencyTagger())   # deterministic, free per tick
        self.me.consolidate()
        return {"docs_read": summary.docs_read, "candidates": summary.candidates,
                "committed": summary.committed, "held": summary.held,
                "contradictions": summary.contradictions, "strict": summary.strict}

    def reflect(self) -> dict:
        """Outer loop (BUILD_PLAN 2.2/2.3): recompute agenda, act unbidden, spawn interests.
        Narrates initiative to the notebook. Returns the top agenda item."""
        agenda = build_agenda(self.me.store, self._contradictions, self._interests(), self.weights)
        top = agenda[0] if agenda else None
        if top:
            self.me.notebook(f"reflected → top of agenda: [{top.kind}] {top.target} ({top.why})")
        # self-spawn an interest where the graph is most alive (uncertain + load-bearing + moving)
        for i in propose_interests(self.me.store, top_k=1):
            if i.name.lower() not in [s.lower() for s in self.seed_interests]:
                self.seed_interests.append(i.name)
                self.me.notebook(f"spawned interest: {i.name} (weight {i.weight}) — {i.reason}")
                break
        return top.__dict__ if top else {}

    def review_queue(self, threshold: float = 0.25) -> list[dict]:
        """Decision-theoretic escalation (P7/T0.2): committed beliefs the researcher flags for
        human review because they are UNCERTAIN × HIGH-STAKES (uncertainty × load-bearing ≥
        threshold). Uses calibrate.should_escalate — a real production caller of the module."""
        from .calibrate import should_escalate, uncertainty
        lb = load_bearing(self.me.store)
        out = []
        for c in self.me.store.core_claims():
            stakes = max(0.05, lb.get(c.claim_id, 0.1))
            if should_escalate(c.calibrated_p, stakes, threshold):
                out.append({"claim_id": c.claim_id, "statement": c.statement,
                            "calibrated_p": round(c.calibrated_p, 3),
                            "uncertainty": round(uncertainty(c.calibrated_p), 3),
                            "stakes": round(stakes, 4)})
        out.sort(key=lambda d: d["uncertainty"] * d["stakes"], reverse=True)
        return out

    def tag_dependencies(self, tagger=None, max_pairs: int = 80) -> int:
        """Run the inferential-dependency tagger over committed claims -> candidate
        derives-from/presupposes edges (T0.5). This is what makes load_bearing / VoI / the idea
        graph light up. Heuristic (free, deterministic) by default in tick(); Claude in the
        autonomous cycle. Returns the number of NEW candidate edges added."""
        from .swarm.dependency_tagger import tag_dependencies as _tag
        n = _tag(self.me.store, tagger, max_pairs=max_pairs)
        if n:
            self.me.notebook(f"tagged {n} candidate inferential-dependency edge(s) "
                             f"(derives-from/presupposes — CANDIDATE, human-auditable)")
        return n

    def idea_graph(self) -> dict:
        """The idea-evolution graph: temporal network of claims (P5)."""
        from .graph import build_idea_graph
        return build_idea_graph(self.me.store)

    @property
    def index(self):
        """Lazily-built PERSISTENT vector index — the corpus accumulates across ticks/restarts
        (v3 T2.2), so retrieval improves the more Persona reads instead of re-embedding a fresh 40."""
        if getattr(self, "_index", None) is None:
            from .retrieval import PersistentIndex
            self._index = PersistentIndex(Path(self.me.root) / "index")
        return self._index

    def retrieve(self, question: str, fetch: int = 40, k: int = 10, mode: str = "hybrid") -> list:
        """Fetch fresh candidates, ADD them to the persistent index, then retrieve top-k over the
        WHOLE accumulated corpus (dense). Lets Persona read on demand and remember what it read."""
        docs = self.adapter.search(question, limit=fetch)
        added = self.index.add(docs)
        hits = self.index.search(question, k=k)
        self.me.notebook(f"retrieved {len(hits)} of {self.index.size()} indexed papers for "
                         f"\"{question[:48]}\" (+{added} new)")
        return hits

    def corroborate(self, statement: str, k: int = 8) -> dict:
        """Retrieval-based cross-check (v3 T2.2): how many INDEPENDENT groups (senior authors /
        journals) in the accumulated corpus are relevant to this claim? Surfaces independent
        corroboration the belief may not yet have counted — a real use of the index in the loop."""
        hits = self.index.search(statement, k=k)
        groups = {h.get("group") for h in hits if h.get("group")}
        return {"statement": statement[:100], "n_relevant": len(hits),
                "independent_groups": len(groups), "top": hits[:5]}

    async def aread(self, queries=None, limit: int = 12, on_event=None) -> dict:
        """Async, parallel, REAL swarm read (v2, P2): fan out Claude readers over the docs,
        streaming live swarm events. Contradictions route to the human inbox."""
        from .swarm.orchestrator import AsyncSwarm
        queries = queries or [" AND ".join(self.seed_interests[:2] + ["alzheimer"])]
        docs = []
        for q in queries:
            docs.extend(self.adapter.search(q, limit=limit))
        try:
            self.index.add(docs)            # accumulate the corpus (persistent index, T2.2)
        except Exception:
            pass                            # embedder optional — never block a read on it
        swarm = AsyncSwarm(self.membrane, concurrency=16, budget_usd=config.DAILY_BUDGET_USD)
        summary = await swarm.read_many(docs, on_event=on_event)
        rep = summary.pop("report")
        self._contradictions = rep.contradictions
        for ev in rep.contradictions:
            self.inbox.add_event(ev)
        self.me.notebook(
            f"swarm read {summary['read']} docs (real Claude) → committed {summary['committed']}, "
            f"held {summary['held']}, {summary['contradictions']} contradiction(s); "
            f"${summary['spent_usd']:.3f} spent")
        self.me.consolidate()
        return summary

    async def autonomous_cycle(self, limit: int = 8, on_event=None) -> dict:
        """One always-on tick (v2, P9): read in parallel (real Claude) → reflect + spawn an
        interest → act unbidden by self-testing a flagged contradiction (real first-pass) →
        follow curiosity by retrieving on the newest interest. Initiative, end to end."""
        summary = await self.aread(limit=limit, on_event=on_event)
        self.tag_dependencies()        # real Claude tagger if key -> the flagship graph lights up
        self.reflect()
        acted = None
        corroboration = None
        if self._contradictions:                       # act on the sharpest tension
            ev = self._contradictions[0]
            acted = self.self_test(ev.claim_key)
            # retrieval as a loop cross-checker (T2.2): independent corroboration for the claim
            corroboration = self.corroborate(ev.statement)
            self.me.notebook(f"corroboration for {ev.claim_key}: {corroboration['independent_groups']} "
                             f"independent group(s) across {corroboration['n_relevant']} indexed papers")
        # follow curiosity: retrieve on the most recent self-spawned interest (accumulates corpus)
        if self.seed_interests:
            self.retrieve(self.seed_interests[-1], fetch=20, k=5)
        return {**summary, "acted_on": (self._contradictions[0].claim_key
                                        if self._contradictions else None),
                "self_test": acted, "corroboration": corroboration}

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
        if not self.me.notebook_path.exists():
            return []
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
        """Open dossiers, ranked by escalation priority (uncertainty × stakes) so the human
        sees the highest-leverage judgment calls first (P7, decision-theoretic escalation)."""
        from .calibrate import uncertainty
        lb = load_bearing(self.me.store)
        items = []
        for d in self.inbox.open_items():
            c = self.me.store.get_claim(d.claim_key)
            p = c.calibrated_p if c else 0.5
            stakes = max(0.05, lb.get(d.claim_key, 0.1))
            items.append({**d.__dict__, "calibrated_p": round(p, 3),
                          "priority": round(uncertainty(p) * stakes, 4)})
        items.sort(key=lambda x: x["priority"], reverse=True)
        return items

    def resolve_handoff(self, claim_key: str, explanation: str, truth: int) -> dict:
        c = self.inbox.resolve(claim_key, explanation, truth)
        self.me.notebook(f"human resolved {claim_key} → anchored ({explanation[:60]})")
        return {"claim_id": c.claim_id, "provenance_state": c.provenance_state, "anchor": c.anchor}

    def self_test(self, claim_key: str) -> dict:
        ev = next((e for e in self._contradictions if e.claim_key == claim_key), None)
        if ev is None:
            return {"error": "no open contradiction for that claim"}
        from .loops.self_test import hypothesize
        from .loops.reanalysis import CompositeTester
        entities = self.me.store.entities_for(claim_key)   # recover canonical (subject, object)
        # real path: live GEO scout for a citable dataset + CompositeTester (Open Targets real
        # first-pass over genetic-association data, Claude reasoning fallback). Offline: mock+replay.
        if config.have_key() or any(entities):
            scout = GEODatasetScout(cache=_DiskCache("tests/fixtures/ingest"))
            tester = CompositeTester()
        else:
            scout, tester = MockDatasetScout(), HeuristicTester()
        hyp = hypothesize(ev, entities=entities)
        hits = scout.search(hyp)
        res = tester.run(hyp, hits[0] if hits else None)
        self._pending_tests[claim_key] = res      # hold for human sign-off (loop closes on resolve)
        self.me.notebook(f"self-test on {claim_key}: {res.outcome} "
                         f"(conf {res.confidence:.2f}, replay={res.is_replay}) — needs human sign-off")
        return {"claim_key": claim_key, "outcome": res.outcome, "confidence": res.confidence,
                "dataset": (res.dataset.__dict__ if res.dataset else None),
                "is_replay": res.is_replay, "detail": res.detail}

    def resolve_self_test(self, claim_key: str, human_ok: bool, truth: int) -> dict:
        """CLOSE the acting loop: a human signs off on a pending self-test → the result writes
        back into the belief-state (TESTED only if real compute ran, else HUMAN_CONFIRMED)."""
        res = self._pending_tests.get(claim_key)
        if res is None:
            return {"error": "no pending self-test for that claim"}
        c = apply_result_with_signoff(self.me.store, res, human_ok=human_ok, truth=truth)
        if c is None:
            self.me.notebook(f"self-test on {claim_key} declined by human")
            return {"claim_key": claim_key, "written": False}
        self._pending_tests.pop(claim_key, None)
        self.me.notebook(f"acting loop CLOSED on {claim_key}: written as {c.provenance_state} "
                         f"(anchor={c.anchor}) after human sign-off")
        return {"claim_id": c.claim_id, "written": True, "provenance_state": c.provenance_state,
                "anchor": c.anchor, "calibrated_p": round(c.calibrated_p, 3)}

    def artifacts(self) -> dict:
        ids = [c.claim_id for c in self.me.store.core_claims()]
        review = mini_review(self.me.store, ids, title=f"{self.name}: state of the field")
        errors = []
        if self.me.errors_path.exists():
            errors = [ln for ln in self.me.errors_path.read_text(encoding="utf-8").splitlines()
                      if ln.startswith("- ")]
        return {"mini_review": review, "error_log": errors}
