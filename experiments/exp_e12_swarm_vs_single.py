"""
E12 - Swarm vs single strong agent (gates the fan-out investment, BUILD_PLAN 5.1/5.2)

PRE-REGISTERED (write before implementing the gated piece; CLAUDE.md section 2).
Status: STUB - not yet run.

HYPOTHESIS
  Bounded fan-out of readers/cross-checkers beats one strong agent on extraction accuracy PER TOKEN at the demo scale (convergence catches errors a single pass misses) - for READING/EXTRACTION only, not reasoning.

METRIC
  Accuracy vs token-cost frontier; is fan-out Pareto-dominant at demo scale?

METHOD
  Compare N-reader swarm + membrane convergence vs one strong agent at matched total tokens on an extraction gold set. Keep reasoning/synthesis single-agent (Data-Processing-Inequality; Tran&Kiela 2026). Tests ONLY the blessed niche (breadth-first reading).

GO / NO-GO BAR
  Fan-out dominates the accuracy/token frontier at demo scale -> invest in the swarm. Else shrink the swarm and route reading through fewer/stronger agents; say so.

LITERATURE ANCHORS
  Anthropic multi-agent write-up (~80% variance is tokens; 15x cost); Tran&Kiela arXiv:2604.02460; Cognition 'Don't build multi-agents'.

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
