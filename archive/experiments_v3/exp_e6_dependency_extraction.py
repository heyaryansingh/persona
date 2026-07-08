"""
E6 - Inferential-dependency extraction (gates BUILD_PLAN 3.2 / dependency graph - biggest differentiator, highest risk)

PRE-REGISTERED (write before implementing the gated piece; CLAUDE.md section 2).
Status: STUB - not yet run.

HYPOTHESIS
  A load-bearing RANKING of claims (dependency in-degree / PageRank over extracted edges) correlates with expert-nominated foundational claims (Spearman >= 0.5). Primary metric is RANK correlation, NOT per-edge precision (expect per-edge precision < 0.7 - no dataset exists; biomedical RE tops 0.88-0.9 P at ~0.6 R; presupposition is a documented LLM failure mode).

METRIC
  (1) FIRST: inter-annotator agreement (Krippendorff alpha) on the four labels over a 50-150 claim-pair dev set. (2) Then Spearman/Kendall of load-bearing rank vs expert ranking.

METHOD
  RUN THE IAA PRE-CHECK FIRST - if humans disagree on derives-from vs generalizes, the target is ill-posed and the label set must be renegotiated before spending model budget. Anchor labels to existing schemas (derives-from/operationalizes ~ ACL-ARC/SciCite Uses/Extends; presupposes ~ concept-prerequisite). Emit CANDIDATE edges with calibrated confidence into INFERRED provenance (never fact). Add a citation-graph backbone so the ranking survives poor edge precision.

GO / NO-GO BAR
  If IAA too low OR rank-correlation < 0.5 -> DOWNGRADE 3.2 to 'human-in-the-loop assisted' (suggested edges the user confirms) and say so in the UI. This is the EXPECTED, honestly-labelled outcome.

LITERATURE ANCHORS
  arXiv:2606.25363 (TheoremGraph); arXiv:2506.16383 (argument-mining survey: inter-claim dependency 'firmly open'); arXiv:2510.20345 (fuzzy-relation IAA); ACL-ARC/SciCite.

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
