"""
E9 - Human-error escape hatch (gates the anchoring / write-policy)

PRE-REGISTERED (write before implementing the gated piece; CLAUDE.md section 2).
Status: STUB - not yet run.

HYPOTHESIS
  A bounded escape hatch (anchor resistant not immune; overwhelming INDEPENDENT contrary evidence + a re-escalation trigger can unlock a wrong anchor) recovers from a wrong human label WITHOUT reopening the poisoning vulnerability.

METRIC
  Trade curve: recovery-from-wrong-anchor vs retention-under-poison, swept over resist/threshold. >=20 seeds.

METHOD
  Extend exp_when_protection_matters: seed a fraction of human anchors as WRONG (currently all correct by construction - Confound B). Add an unlock rule gated on INDEPENDENT (not correlated) contrary evidence + re-escalation. Correlated poison alone must never unlock.

GO / NO-GO BAR
  Exists a resist/threshold setting that keeps poison-retention near the anchored baseline while making wrong-anchor recovery possible. Else anchoring is a permanent-corruption risk revocable only by a human.

LITERATURE ANCHORS
  FINDINGS.md threats ('anchor-locking assumes human labels correct'); results/REPRODUCTION.md (Confound B).

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
