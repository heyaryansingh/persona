"""
E11 - Calibration method selection (gates BUILD_PLAN 5.3 confidence + 1.3 membrane gate + 3.7 escalation)

PRE-REGISTERED (write before implementing the gated piece; CLAUDE.md section 2).
Status: STUB - not yet run.

HYPOTHESIS
  A SAMPLING/CONSISTENCY signal (semantic entropy / SAR / SE-probe) - NOT verbalized confidence - gives per-claim confidence with low ECE + good risk-coverage, good enough to (a) gate the membrane and (b) drive decision-theoretic escalation.

METRIC
  ECE + risk-coverage (selective-prediction) AUROC per estimator; conformal admit/escalation error rate. Validate on biomedical QA (calibration is specialty-dependent).

METHOD
  Use LM-Polygraph (TACL 2025) to pick the estimator empirically on our task. Set gate/escalation cutoffs via CONFORMAL selective-prediction (SConU/COIN) for a provable error rate. Escalation is decision-theoretic: threshold on uncertainty x stakes. Decompose long syntheses into atomic claims. Do NOT use raw RLHF verbalized confidence (overconfident, ECE 0.2-0.4).

GO / NO-GO BAR
  Pick the best estimator; if none clears the ECE/risk-coverage bar on biomedical QA, escalation reverts to a conservative always-escalate-high-stakes rule and we say so. Mark 5.3 [E] only after this clears.

LITERATURE ANCHORS
  Farquhar Nature 2024 (semantic entropy); LM-Polygraph TACL 2025 arXiv:2406.15627; SConU ACL 2025 arXiv:2504.14154; AbstentionBench arXiv:2506.09038; Tian EMNLP 2023.

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
