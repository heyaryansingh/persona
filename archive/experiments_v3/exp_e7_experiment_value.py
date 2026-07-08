"""
E7 - Experiment-value (VoI/cost) ranking vs expert (gates BUILD_PLAN 3.4 / experiment queue)

PRE-REGISTERED (write before implementing the gated piece; CLAUDE.md section 2).
Status: STUB - not yet run.

HYPOTHESIS
  A VoI/cost ranking of candidate experiments correlates with blinded-expert 'worth doing' ranking better than the Open Targets genetic-evidence prior baseline.

METRIC
  Spearman(ours, expert) vs Spearman(baseline, expert); top-k precision. >=20 seeds where stochastic.

METHOD
  Baseline = Open Targets genetic-evidence prior (Minikel Nature 2024: genetic support -> 2.6x clinical success) - NOT raw citations. Borrow health-econ EVPI/EVSI + BED-LLM EIG. CALIBRATE the VoI estimate itself (BoxingGym ICLR 2025: LLMs mediocre at EIG-optimal design) before trusting the ranking. Hackathon expert labels = 1-2 domain reviewers or a curated proxy; state the limitation.

GO / NO-GO BAR
  Ship the queue ranking only if ours >= genetic-prior baseline by the pre-registered margin; else rank by the genetic prior and label the VoI score experimental.

LITERATURE ANCHORS
  Minikel Nature 2024 (s41586-024-07316-0); EVPI/EVSI (Claxton/Sculpher); BoxingGym arXiv:2501.01540; BED-LLM arXiv:2508.21184; AI co-scientist arXiv:2502.18864.

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
