"""First-pass REANALYSIS backends (v3 T0.4) — the step that touches real data.

The audit's finding #3: "reanalysis touches zero data" — offline returned a constant,
online only *reasoned over an accession string*. This makes it real: a gene<->disease claim
is cross-checked against Open Targets' computed target-disease association (a real number
derived from genetic/genomic evidence pipelines). A result is `is_replay=False` ONLY when a
real external computation produced the verdict; otherwise it falls back and stays honest.

We lead with Open Targets (keyless, robust, genetics-grade) rather than a live GEO
differential-expression download because DE-from-SOFT is fragile across arbitrary accessions
(probe mapping, subset labels) and would fake more than it computes. GEO stays the dataset
*scout* (real accessions); Open Targets is the first-pass *compute*.
"""
from __future__ import annotations

from typing import Optional

from .self_test import SelfTestResult, Hypothesis, HeuristicTester, ClaudeScienceTester
from ..ingest.opentargets import OpenTargetsClient

# Open Targets association-score bands (0-1). Genetic association is the highest-value signal
# (Minikel Nature 2024: genetic support ~2.6x higher clinical success).
# Validated in experiments/exp_reanalysis_bands.py on 12 textbook-true vs 12 unrelated pairs:
# overall>=0.30 sits inside a PERFECT-separation interval [0.07, 0.63] (neg max=0.061, pos
# min=0.637 -> F1=1.00); genetic>=0.10 adds the genetic-grade branch with 0 false positives
# (neg genetic max=0.055) and catches the drug-target case overall alone would miss.
_STRONG = 0.10      # genetic score at/above -> a real, non-trivial association
_ANY = 0.01         # any association at all


class OpenTargetsTester:
    """First-pass reanalysis via Open Targets. Resolves the claim's two entities to a
    target<->disease association and reads the computed score. Real external computation ->
    is_replay=False. Returns None (not a fake 'supports') when the claim isn't gene<->disease
    or the entities don't resolve, so a caller can fall back cleanly."""

    def __init__(self, client: Optional[OpenTargetsClient] = None):
        self.client = client or OpenTargetsClient()

    def run(self, hypothesis: Hypothesis, dataset) -> Optional[SelfTestResult]:
        a, b = (hypothesis.subject or "").strip(), (hypothesis.object or "").strip()
        if not a or not b:
            return None
        try:
            r = self.client.associate(a, b)
        except Exception:
            return None
        if not r.get("found"):
            return None
        score = max(r["overall"], r["genetic"])
        if r["genetic"] >= _STRONG or r["overall"] >= 0.3:
            outcome, conf = "supports", min(0.95, 0.55 + 0.45 * score)
        elif score >= _ANY:
            outcome, conf = "inconclusive", 0.45 + 0.2 * score
        else:
            # resolved to a real target/disease pair with ~no association evidence -> refutes the
            # existence of a strong link (a real negative, computed, not a replay).
            outcome, conf = "refutes", 0.55
        detail = (f"Open Targets association {r['target']}<->{r['disease']}: "
                  f"overall={r['overall']:.3f}, genetic={r['genetic']:.3f} "
                  f"({r.get('ensembl','?')} / {r.get('efo','?')}). First-pass over real "
                  f"genetic-association evidence.")
        return SelfTestResult(hypothesis=hypothesis, dataset=dataset, outcome=outcome,
                              confidence=float(conf), detail=detail, is_replay=False)


class CompositeTester:
    """Try real-data backends first (Open Targets), then reasoning (Claude), then the
    labelled heuristic replay. The first backend that yields a result wins; is_replay is
    honest per backend."""

    def __init__(self, ot: Optional[OpenTargetsTester] = None, reasoner=None):
        self.ot = ot or OpenTargetsTester()
        self.reasoner = reasoner or ClaudeScienceTester()

    def run(self, hypothesis: Hypothesis, dataset) -> SelfTestResult:
        real = self.ot.run(hypothesis, dataset)
        if real is not None:
            return real
        return self.reasoner.run(hypothesis, dataset)   # Claude if key, else heuristic replay
