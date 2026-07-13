"""F1.6 — surprise-ranked tension queue (core).

A new claim that OPPOSES a high-confidence belief is belief-overturning and should be investigated
sooner; a claim restating a known belief is not. Surprise maps to a lower (sooner) queue priority
without any change to the lease SQL. Pure + local — no encoder, no API/logprob call.
"""
from persona.reading.reader import contradiction_surprise, surprise_priority

BELIEFS = [{"subject": "X", "object": "Y", "effect_sign": "+", "confidence": 0.9},
           {"subject": "A", "object": "B", "effect_sign": "-", "confidence": 0.3}]


def test_opposing_claim_outranks_restatement():
    opposing = {"subject": "X", "object": "Y", "effect_sign": "-"}      # contradicts the 0.9 belief
    restate = {"subject": "X", "object": "Y", "effect_sign": "+"}       # restates it
    assert contradiction_surprise(opposing, BELIEFS) == 0.9
    assert contradiction_surprise(restate, BELIEFS) == 0.0
    assert contradiction_surprise(opposing, BELIEFS) > contradiction_surprise(restate, BELIEFS)


def test_surprise_scales_with_belief_confidence():
    # opposing a 0.9 belief is more surprising than opposing a 0.3 one
    hi = contradiction_surprise({"subject": "X", "object": "Y", "effect_sign": "-"}, BELIEFS)
    lo = contradiction_surprise({"subject": "A", "object": "B", "effect_sign": "+"}, BELIEFS)
    assert hi > lo == 0.3


def test_novel_claim_no_match_is_not_surprising():
    assert contradiction_surprise({"subject": "P", "object": "Q", "effect_sign": "+"}, BELIEFS) == 0.0


def test_more_surprise_means_sooner_priority():
    assert surprise_priority(0.9) < surprise_priority(0.0)             # sooner = lower number
    assert all(0 <= surprise_priority(s / 10) <= 6 for s in range(0, 11))   # stays in [0,6] band
    assert surprise_priority(1.0) <= surprise_priority(0.5) <= surprise_priority(0.0)
