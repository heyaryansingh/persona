"""The membrane: the anti-slop funnel between swarm and self (BUILD_PLAN 1.3 / 5.4).

Nothing becomes belief without **convergence + provenance + calibration**. Corrections
from the literature sweep (planning/LITERATURE.md §B/§D) are baked in:

- Convergence = EVIDENTIAL INDEPENDENCE (distinct source groups), NOT raw agreement count
  (citation echo manufactures fake consensus — Greenberg BMJ 2009).
- ADAPTIVE (E10): cheap fast-path quorum in benign regimes; switch to strict quorum +
  backpressure when a correlated-disagreement (poisoning) signature is detected — many
  candidates, few independent groups, attacking an established belief.
- Backpressure keys on independence, not agent-count agreement (same-base-model readers
  have correlated errors -> agreement is false confidence).
- Contradictions are emitted TYPED {true-refutation, context-divergence, no-evidence}
  (BioDivergence 2026: most apparent contradictions are context-divergence), NOT committed
  autonomously — they route to the human handoff (ignition is human-gated).
- Commits go through the store, whose anchor write-policy is the last-line guard.
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field

from .store import BeliefStore, Claim
from .swarm.reader import Candidate


@dataclass
class ContradictionEvent:
    claim_key: str
    statement: str
    kind: str                       # true-refutation | context-divergence | no-evidence
    support_groups: int
    refute_groups: int
    detail: str = ""


@dataclass
class HarvestReport:
    committed: list[str] = field(default_factory=list)
    held: list[str] = field(default_factory=list)
    contradictions: list[ContradictionEvent] = field(default_factory=list)
    strict_claims: list[str] = field(default_factory=list)


class Membrane:
    def __init__(self, store: BeliefStore, *, fast_quorum: int = 2, strict_quorum: int = 3,
                 confidence_floor: float = 0.5, window: int = 40,
                 poison_min_volume: int = 6, poison_indep_ratio: float = 0.4,
                 escape_quorum: int = 4):
        self.store = store
        self.fast_quorum = fast_quorum
        self.strict_quorum = strict_quorum
        self.confidence_floor = confidence_floor
        self.poison_min_volume = poison_min_volume
        self.poison_indep_ratio = poison_indep_ratio
        self.escape_quorum = escape_quorum   # independent groups needed to CHALLENGE an anchor (E9)
        self.strict_mode: set[str] = set()      # claim_keys currently under strict policy
        self.backpressure: float = 1.0           # fan-out scale the orchestrator reads (<=1)

    # ------------------------------------------------------------- intake
    def submit(self, cand: Candidate) -> None:
        """Swarm hands a candidate to the DURABLE observation log (never writes the self).
        Persisting immediately makes the membrane crash-safe: a restart recomputes beliefs
        from accumulated evidence and loses nothing held."""
        self.store.add_observation(cand.claim_key, cand.statement, cand.direction,
                                   cand.group, cand.doc_id, cand.confidence)

    @staticmethod
    def _to_cands(rows) -> list:
        return [Candidate(claim_key=r["claim_key"], statement=r["statement"],
                          direction=r["direction"], group=r["grp"], doc_id=r["doc_id"],
                          confidence=r["confidence"]) for r in rows]

    # ------------------------------------------------- E10: poisoning detector
    def _detect_poisoning(self, key: str, cands: list, dominant_dir: float) -> bool:
        """Correlated-disagreement signature: high volume, low independence, attacking an
        established belief. Returns True -> switch this claim to strict + apply backpressure.
        """
        same_dir = [c for c in cands if c.direction == dominant_dir]
        if len(same_dir) < self.poison_min_volume:
            return False
        groups = {c.group for c in same_dir}
        independence_ratio = len(groups) / len(same_dir)
        if independence_ratio > self.poison_indep_ratio:
            return False                          # genuinely many independent sources
        existing = self.store.get_claim(key)
        # only a *signature* if it opposes an already-established belief
        if existing is not None and existing.logit * dominant_dir < 0 and abs(existing.logit) >= 2:
            return True
        return False

    def _quorum_for(self, key: str) -> int:
        return self.strict_quorum if key in self.strict_mode else self.fast_quorum

    # ------------------------------------------------------------- harvest
    def harvest(self) -> HarvestReport:
        """Decide what crosses. Convergence by independent groups; typed contradictions
        routed out (not auto-committed)."""
        report = HarvestReport()
        for key in self.store.observation_keys():
            cands = self._to_cands(self.store.observations_for(key))
            if not cands:
                continue
            by_dir: dict[float, list[Candidate]] = defaultdict(list)
            for c in cands:
                by_dir[c.direction].append(c)
            # dominant direction = most independent groups
            def indep(cands):
                return len({c.group for c in cands})
            dominant_dir = max(by_dir, key=lambda d: indep(by_dir[d]))
            other_dir = -dominant_dir
            sup = by_dir.get(dominant_dir, [])
            ref = by_dir.get(other_dir, [])
            sup_groups, ref_groups = indep(sup), indep(ref)

            # adaptive switch (E10)
            if self._detect_poisoning(key, cands, dominant_dir):
                self.strict_mode.add(key)
                self.backpressure = 0.3
                report.strict_claims.append(key)

            # typed contradiction (routed to human, not auto-committed)
            if ref_groups >= 1 and sup_groups >= 1:
                report.contradictions.append(self._type_contradiction(
                    key, sup, ref, sup_groups, ref_groups))

            # escape hatch (E9): independent, sustained contrary evidence against a HUMAN
            # anchor RE-ESCALATES to a human — it never silently overwrites (the store guard
            # still holds), and correlated poison (few groups) can't reach escape_quorum.
            existing = self.store.get_claim(key)
            if existing is not None and existing.anchor:
                contrary_groups = len({c.group for c in cands if c.direction * existing.logit < 0})
                if contrary_groups >= self.escape_quorum:
                    report.contradictions.append(ContradictionEvent(
                        key, existing.statement, "anchor-challenge",
                        support_groups=sup_groups, refute_groups=contrary_groups,
                        detail="independent evidence challenges a human-anchored belief — re-escalate"))
                    if key not in self.strict_mode:
                        self.strict_mode.add(key)
                        report.strict_claims.append(key)

            quorum = self._quorum_for(key)
            mean_conf = (sum(c.confidence for c in sup) / len(sup)) if sup else 0.0
            if sup_groups >= quorum and mean_conf >= self.confidence_floor:
                self._commit(key, sup, dominant_dir)
                report.committed.append(key)
            else:
                report.held.append(key)
        return report

    def _type_contradiction(self, key, sup, ref, sup_groups, ref_groups) -> ContradictionEvent:
        stmt = sup[0].statement if sup else (ref[0].statement if ref else key)
        if sup_groups >= 2 and ref_groups >= 2:
            kind, detail = "context-divergence", "both sides independently supported"
        elif min(sup_groups, ref_groups) == 1 and max(sup_groups, ref_groups) >= 2:
            kind, detail = "true-refutation", "one side single-source; likely weaker"
        else:
            kind, detail = "no-evidence", "insufficient independent support either side"
        return ContradictionEvent(key, stmt, kind, sup_groups, ref_groups, detail)

    def _commit(self, key: str, sup: list[Candidate], direction: float) -> None:
        # idempotency: drop candidates whose document already contributed to this claim,
        # so re-reading a paper (e.g. after a crash-resume) can't count it twice.
        fresh = [c for c in sup if not (self.store.get_claim(key) is not None
                                        and self.store.has_source(key, c.doc_id))]
        if self.store.get_claim(key) is None:
            self.store.add_claim(Claim(key, sup[0].statement, tier="core"))
            fresh = sup
        if not fresh:
            return                      # every supporting doc already counted -> no-op
        for c in fresh:
            self.store.add_source(key, c.doc_id, c.group)
        # belief = deterministic function of accumulated independent evidence (idempotent to
        # re-reads / crash-resume); the store leaves anchored beliefs untouched.
        self.store.set_swarm_belief(key, direction)
