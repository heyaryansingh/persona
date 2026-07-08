"""
E10 - Online correlated-disagreement detector / the adaptive membrane switch (gates BUILD_PLAN 5.4)

PRE-REGISTERED (write before implementing the gated piece; CLAUDE.md section 2).
Status: STUB - not yet run.

HYPOTHESIS
  A cheap online statistic (source-correlation of disagreement + evidential-independence estimate) flips the membrane fast-path <-> strict-quorum with acceptable precision/latency, realizing E1's benefit ONLINE (E1 only tested FIXED policies).

METRIC
  Switch detection AUC + switch latency; adaptive accuracy/latency vs always-strict and always-fast baselines. >=20 seeds across benign and correlated regimes.

METHOD
  Implement the detector over the swarm's harvested candidate stream; key on source/prompt/model independence, NOT raw agent-count agreement (correlated same-base-model readers give false confidence, arXiv:2603.16244). Backpressure narrows fan-out only on independence-weighted disagreement.

GO / NO-GO BAR
  Adaptive ~= always-strict accuracy at meaningfully lower latency in benign regimes, and switches into strict before correlated poison corrupts the core. Else default to always-strict and pay the latency.

LITERATURE ANCHORS
  FINDINGS.md conclusion 1; Anthropic multi-agent write-up; arXiv:2603.16244 (more rounds add noise).

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
