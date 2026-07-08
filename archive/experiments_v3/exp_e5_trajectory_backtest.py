"""
E5 - Trajectory vs static collapse backtest (gates BUILD_PLAN 3.1 / argument-state screen)

PRE-REGISTERED (write before implementing the gated piece; CLAUDE.md section 2).
Status: STUB - not yet run.

HYPOTHESIS
  Trajectory features (evidence velocity/acceleration, INDEPENDENCE-drift, citation-vs-support divergence) predict eventual collapse better than a STRONG static baseline, under proper temporal splits (freeze at T, predict T+delta).

METRIC
  AUC & Brier, trajectory vs static, 95% CI over >=20 temporal-split seeds; calibration curve. Pre-registered margin: +0.05 AUC over the strong baseline.

METHOD
  Lead with independence-drift (Danchev/Rzhetsky/Evans eLife 2019: decentralized communities +45% replication). SPLIT 'collapse' into typed heads: retraction (Retraction Watch) / replication-failure (DARPA SCORE, replication markets) / abandonment (citation decay) - validate each separately. Inflation-normalize + era-control ALL citation features (disruption/CD index is a cross-time artifact, QSS 2024; pub-year base rate dominates retraction ML). Strong static baseline = Uzzi-style text model (~0.68-0.72 AUC, PNAS 2020) + Open Targets genetic prior - NEVER a citation-count straw man.

GO / NO-GO BAR
  Ship the trajectory model into argument-state ONLY if it clears +0.05 AUC over the strong baseline on temporally-split data. Else render the trajectory as DESCRIPTIVE (no collapse forecast).

LITERATURE ANCHORS
  eLife 2019 (independence); PNAS 2020/2023 (static baseline + critiques); QSS 2024 arXiv:2406.15311 (disruption artifact); DARPA SCORE (ceiling).

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
