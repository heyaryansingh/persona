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
                 poison_new_ratio: float = 0.25, poison_new_volume: int = 6,
                 escape_quorum: int = 4):
        # poison_new_* derived by sweep in experiments/exp_poison_thresholds.py: (6, 0.25) gives
        # perfect separation (attack+fabricate flag=1.00, benign_new+benign_small=0.00).
        self.store = store
        self.fast_quorum = fast_quorum
        self.strict_quorum = strict_quorum
        self.confidence_floor = confidence_floor
        self.poison_min_volume = poison_min_volume
        self.poison_indep_ratio = poison_indep_ratio
        self.poison_new_ratio = poison_new_ratio      # stricter bar for fabricating a NEW belief
        self.poison_new_volume = poison_new_volume
        self.escape_quorum = escape_quorum   # independent groups needed to CHALLENGE an anchor (E9)
        self.strict_mode: set[str] = set()      # claim_keys currently under strict policy
        self.backpressure: float = 1.0           # fan-out scale the orchestrator reads (<=1)

    # ------------------------------------------------------------- intake
    def submit(self, cand: Candidate) -> None:
        """Swarm hands a candidate to the DURABLE observation log (never writes the self).
        Persisting immediately makes the membrane crash-safe: a restart recomputes beliefs
        from accumulated evidence and loses nothing held."""
        self.store.add_observation(cand.claim_key, cand.statement, cand.direction,
                                   cand.group, cand.doc_id, cand.confidence,
                                   relation=cand.meta.get("relation", ""),
                                   population=cand.meta.get("population"),
                                   subject=cand.meta.get("subject", ""),
                                   object=cand.meta.get("object", ""))

    @staticmethod
    def _to_cands(rows) -> list:
        return [Candidate(claim_key=r["claim_key"], statement=r["statement"],
                          direction=r["direction"], group=r["grp"], doc_id=r["doc_id"],
                          confidence=r["confidence"],
                          meta={"relation": r.get("relation", ""), "population": r.get("population"),
                                "subject": r.get("subject", ""), "object": r.get("object", "")})
                for r in rows]

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
        existing = self.store.get_claim(key)
        # (a) attack on an ESTABLISHED belief: high volume, low independence, opposes the anchor
        if independence_ratio <= self.poison_indep_ratio:
            if existing is not None and existing.logit * dominant_dir < 0 and abs(existing.logit) >= 2:
                return True
        # (b) FABRICATION of a NEW belief (v3 T1.3): a coordinated push of many candidates from
        # very few groups, with no established belief yet — manufacture-by-volume. Stricter bar
        # (lower ratio, higher volume) so a single legitimate large study isn't flagged. The
        # group-based quorum already blocks the COMMIT; this adds strict-mode + a human flag.
        not_established = existing is None or abs(existing.logit) < 2
        if (not_established and len(same_dir) >= self.poison_new_volume
                and independence_ratio <= self.poison_new_ratio):
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
        """Type the contradiction from the EXTRACTED CONTEXT, not just group counts (v3 T1.3).
        BioDivergence 2026: most apparent contradictions are context-divergence — the effect is
        real but flips with population/assay. So when both sides report a population, we type by
        whether they studied the SAME population (genuine disagreement) or DIFFERENT ones (context)."""
        stmt = sup[0].statement if sup else (ref[0].statement if ref else key)
        sup_pops = {c.meta.get("population") for c in sup if c.meta.get("population")}
        ref_pops = {c.meta.get("population") for c in ref if c.meta.get("population")}
        if sup_pops and ref_pops:
            if sup_pops.isdisjoint(ref_pops):
                return ContradictionEvent(key, stmt, "context-divergence", sup_groups, ref_groups,
                    f"opposite effects in DIFFERENT populations ({sorted(sup_pops)} vs "
                    f"{sorted(ref_pops)}) — likely context, not conflict")
            return ContradictionEvent(key, stmt, "true-refutation", sup_groups, ref_groups,
                f"opposite effects in the SAME population(s) ({sorted(sup_pops & ref_pops)}) — "
                f"genuine disagreement")
        # population unknown -> fall back to the independence-count heuristic
        if sup_groups >= 2 and ref_groups >= 2:
            kind, detail = "context-divergence", "both sides independently supported (population unstated)"
        elif min(sup_groups, ref_groups) == 1 and max(sup_groups, ref_groups) >= 2:
            kind, detail = "true-refutation", "one side single-source; likely weaker"
        else:
            kind, detail = "no-evidence", "insufficient independent support either side"
        return ContradictionEvent(key, stmt, kind, sup_groups, ref_groups, detail)

    def _commit(self, key: str, sup: list[Candidate], direction: float) -> None:
        if self.store.get_claim(key) is None:
            m = sup[0].meta
            ents = [e for e in (m.get("subject"), m.get("object")) if e]
            self.store.add_claim(Claim(key, sup[0].statement, tier="core", entities=ents,
                                       direction=("up" if direction > 0 else "down"),
                                       population=m.get("population")))
        # record each supporting doc once (idempotent; a paper can't count twice)
        for c in sup:
            if not self.store.has_source(key, c.doc_id):
                self.store.add_source(key, c.doc_id, c.group)
        # belief = NET independent evidence over ALL observations (support AND refute), recomputed
        # every harvest so newly-arrived CONTRARY evidence lowers it. Idempotent / crash-safe.
        self.store.set_swarm_belief(key)
