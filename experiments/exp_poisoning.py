"""exp_poisoning (v4 P6, CI oracle) — the anchor write-policy resists correlated poisoning.

Threat: a coordinated flood of contrary claims from FEW labs (citation echo / injection) tries to
overturn a human-verified belief. Test: anchor "X reduces Y" (HUMAN_CONFIRMED), then flood 24
"X increases Y" claims from only 2 labs. Verify (1) the anchored belief is RETAINED (confidence
pinned, sign unchanged), and (2) the poison pattern is DETECTED (high volume, low independence,
contradicting an anchor). Mirrors the v3 result (anchored 100% vs naive 71% under attack).

Run: python experiments/exp_poisoning.py    (needs FalkorDB on :6379)
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from persona.memory.kg import KG                                    # noqa: E402


def main():
    kg = KG(name="kg_poison_test")
    kg.g.query("MATCH (n) DETACH DELETE n")

    # a human-verified belief: X reduces Y (anchored)
    kg.upsert_source({"slug": "trusted", "title": "RCT", "year": 2021, "affiliations": ["NIH"]})
    kg.add_claim({"claim_id": "x", "subject": "drugX", "relation": "reduces", "object": "mortality",
                  "effect_sign": "-", "confidence": 0.9, "provenance": "READ"}, "trusted")
    # find its id and anchor it
    belief = kg.beliefs(min_independent=1)[0]
    anchored_id = belief["claim_id"]
    kg.anchor(anchored_id, "HUMAN_CONFIRMED", truth=True)
    before = kg.beliefs(min_independent=1)
    before_conf = next(b["confidence"] for b in before if b["claim_id"] == anchored_id)

    # THE ATTACK: 24 contrary claims (X increases mortality) from only 2 labs
    for i in range(24):
        lab = f"echolab{i % 2}"
        kg.upsert_source({"slug": f"poison{i}", "title": "echo", "year": 2022, "affiliations": [lab]})
        kg.add_claim({"claim_id": "x", "subject": "drugX", "relation": "increases",
                      "object": "mortality", "effect_sign": "+", "confidence": 0.9,
                      "provenance": "READ"}, f"poison{i}")
    kg.link_all_contradictions()

    after = kg.beliefs(min_independent=1)
    after_anchor = next((b for b in after if b["claim_id"] == anchored_id), None)
    signals = kg.poisoning_signals(min_volume=8, max_indep_ratio=0.4)

    print("=== anchor resistance under correlated poisoning ===")
    print(f"anchored belief present after attack: {after_anchor is not None}")
    print(f"anchored confidence: {before_conf:.2f} -> {after_anchor['confidence']:.2f} "
          f"(sign {after_anchor['effect_sign']}, anchored={after_anchor['anchored']})")
    print(f"attack claim independent labs: "
          f"{next((b['independent_sources'] for b in after if b['effect_sign']=='+'), 0)} "
          f"(from 24 claims -> low independence)")
    print(f"poisoning signals detected: {len(signals)}")
    for s in signals:
        print(f"  ALERT: {s['subject']}->{s['object']} volume={s['volume']} "
              f"independent_labs={s['independent_labs']} attacking anchor")

    retained = (after_anchor is not None and after_anchor["anchored"]
                and after_anchor["effect_sign"] == "-" and after_anchor["confidence"] >= 0.9)
    detected = len(signals) >= 1
    print(f"\nVERDICT: {'PASS' if retained and detected else 'FAIL'} — "
          f"anchor {'RETAINED' if retained else 'LOST'}; poison {'DETECTED' if detected else 'MISSED'}")
    kg.g.query("MATCH (n) DETACH DELETE n")
    assert retained, "anchored belief must survive correlated poisoning"
    assert detected, "poison pattern must be detected"


if __name__ == "__main__":
    main()
