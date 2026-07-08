"""
E13 (plan's E4) - Interests/taste are functional, not theater (gates the 'self' being real, BUILD_PLAN 1.4/1.5)

PRE-REGISTERED (write before implementing the gated piece; CLAUDE.md section 2).
Status: STUB - not yet run.

HYPOTHESIS
  Changing interest weights / the surprise term measurably changes WHICH papers get read and WHICH beliefs update, vs a no-taste control - taste is behaviorally load-bearing, not a personality prompt.

METRIC
  Divergence in read-set (Jaccard/rank) and belief-trajectory across dispositions; effect size vs a no-taste control. >=20 seeds.

METHOD
  Run the same seeded corpus under >=2 dispositions (skeptical vs exploratory; different interest weights, different w_surprise) and a no-taste control. Measure whether read-set and belief updates diverge reproducibly.

GO / NO-GO BAR
  Non-trivial, reproducible behavioral divergence across dispositions. If taste doesn't change behavior it's theater (BUILD_PLAN 0.3) and must be redesigned or dropped from the claims.

LITERATURE ANCHORS
  BUILD_PLAN 1.4/1.5/0.3; SuRe/Evo-memory surprise-driven replay (2025).

Protocol: seed everything; >=20 seeds where stochastic; report mean +/- 95% CI;
save results to results/; if the evidence contradicts the hypothesis, WRITE DOWN
the reversal in results/FINDINGS.md and follow the evidence.
"""


def run():
    raise NotImplementedError(
        "Pre-registered stub. Implement per the docstring, then remove this guard."
    )


if __name__ == "__main__":
    run()
