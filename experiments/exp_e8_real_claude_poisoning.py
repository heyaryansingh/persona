"""
E8 - Real-Claude poisoning replay (PROMOTION GATE for the whole membrane/anchor build)

PRE-REGISTERED (write before implementing the gated piece; CLAUDE.md section 2).
Status: STUB - not yet run.

HYPOTHESIS
  The DURING-attack retention crossover (anchored >= quorum >= naive) survives replacing the boolean-channel sim with REAL Claude claim-extraction over a seeded corpus salted with (a) correlated poison AND (b) a MINJA-style query-only injection attack.

METRIC
  Human-verified-belief retention DURING/AFTER, anchored vs naive vs quorum; report NON-human-victim recovery SEPARATELY (per Confound A). >=30 seeded corpora, 95% CI.

METHOD
  Build a seeded corpus with a fabricated review repeated across many 'papers' (correlated poison) + a MINJA-style injection. Run real reader/extractor agents through the actual membrane + write-policy. Same anchor policy as the sim.

GO / NO-GO BAR
  Anchored retention >= quorum >= naive with non-overlapping CIs, same ordering as the sim. If the crossover does NOT survive real structured extraction error, the membrane/anchor design is REOPENED (all [E] tags currently rest on a boolean sim).

LITERATURE ANCHORS
  MINJA arXiv:2503.03704; PoisonedRAG USENIX Sec 2025; FINDINGS.md threats; results/REPRODUCTION.md (Confound A/D).

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
