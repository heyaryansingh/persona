"""
E15 - Contradiction trigger + typing precision (gates the self-test loop IGNITION, BUILD_PLAN 2.5)

PRE-REGISTERED (write before implementing the gated piece; CLAUDE.md section 2).
Status: STUB - not yet run.

HYPOTHESIS
  At a high-precision operating point PLUS a context-divergence filter, the flagged 'true-refutation' rate is precise enough that HUMAN-GATED ignition spends reanalysis compute well (detection is a surfacing step, not autonomous ignition).

METRIC
  Precision/FPR of true-refutation at the chosen threshold, >=20 seeds, vs ContraDetect + BioDivergence oracles. Typed output: true-refutation / context-divergence / no-evidence.

METHOD
  Emit a TYPED contradiction (not boolean). Filter context-conditioned divergence (BioDivergence: most apparent contradictions are context-divergence; LLMs separate at ~0.55 acc). Add a study-quality/power prefilter. The loop ignites only via the human handoff for high-stakes (ContraCrow: ~30% wild FP, ~75% inter-expert ceiling).

GO / NO-GO BAR
  Precision at the chosen threshold clears a pre-registered floor AND the loop is human-gated at ignition. Autonomous ignition on raw contradiction is disallowed (unsafe per the 75% ceiling).

LITERATURE ANCHORS
  PaperQA2/ContraCrow arXiv:2409.13740; BioDivergence arXiv:2606.11208; NLI4CT arXiv:2404.04963.

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
