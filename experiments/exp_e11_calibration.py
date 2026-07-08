"""
E11 - Calibration method selection (gates 5.3 confidence + membrane gate + escalation). IMPLEMENTED.

The tech sweep (planning §2.5) warns RLHF-tuned models are overconfident and that SAMPLING/
CONSISTENCY signals beat verbalized confidence. Test it directly on a small labeled set of
biomedical statements with KNOWN truth: compare (A) verbalized P(true) from one call vs
(B) self-consistency (fraction of K samples that answer "true"). Metric: Brier + ECE +
selective AUROC vs the truth labels.

GO: the better-calibrated signal (lower Brier/ECE) is the one Persona should use to gate the
membrane / drive escalation. Prediction from the literature: self-consistency >= verbalized.
Needs ANTHROPIC_API_KEY (~$0.05 on Haiku).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np
from persona import config

# curated labeled biomedical statements (1 = true, 0 = false)
LABELED = [
    ("APOE4 allele increases risk of Alzheimer's disease", 1),
    ("Amyloid-beta plaques are a pathological hallmark of Alzheimer's disease", 1),
    ("Microglia are the resident immune cells of the central nervous system", 1),
    ("Hyperphosphorylated tau forms neurofibrillary tangles", 1),
    ("Smoking increases the risk of lung cancer", 1),
    ("BRCA1 mutations increase breast cancer risk", 1),
    ("TNF-alpha is a pro-inflammatory cytokine", 1),
    ("NLRP3 inflammasome activation promotes neuroinflammation", 1),
    ("The MMR vaccine causes autism", 0),
    ("Aluminium cookware is the primary cause of Alzheimer's disease", 0),
    ("Antibiotics are effective at curing viral infections", 0),
    ("Amyloid-beta reduces neuroinflammation in Alzheimer's disease", 0),
    ("Homeopathy cures metastatic cancer", 0),
    ("Adult human cortical neurons regenerate freely after injury", 0),
    ("Vitamin C megadoses definitively cure the common cold", 0),
]


def verbalized_p(client, stmt):
    tool = {"name": "rate", "input_schema": {"type": "object",
            "properties": {"p_true": {"type": "number"}}, "required": ["p_true"]}}
    r = client.messages.create(model=config.MODEL_READER, max_tokens=200, tools=[tool],
                               tool_choice={"type": "tool", "name": "rate"},
                               messages=[{"role": "user", "content":
                                          f"Statement: \"{stmt}\"\nGive p_true = your probability (0-1) that this biomedical statement is TRUE."}])
    for b in r.content:
        if b.type == "tool_use":
            return float(b.input.get("p_true", 0.5))
    return 0.5


def consistency_p(client, stmt, k=5):
    tool = {"name": "answer", "input_schema": {"type": "object",
            "properties": {"is_true": {"type": "boolean"}}, "required": ["is_true"]}}
    yes = 0
    for _ in range(k):
        r = client.messages.create(model=config.MODEL_READER, max_tokens=100, temperature=1.0,
                                   tools=[tool], tool_choice={"type": "tool", "name": "answer"},
                                   messages=[{"role": "user", "content":
                                              f"Is this biomedical statement true? \"{stmt}\""}])
        for b in r.content:
            if b.type == "tool_use":
                yes += 1 if b.input.get("is_true") else 0
    return yes / k


def brier(ps, ys):
    return float(np.mean((np.array(ps) - np.array(ys)) ** 2))


def ece(ps, ys, bins=5):
    ps, ys = np.array(ps), np.array(ys)
    e, n = 0.0, len(ps)
    for b in range(bins):
        lo, hi = b / bins, (b + 1) / bins
        m = (ps >= lo) & (ps < hi if b < bins - 1 else ps <= hi)
        if m.sum():
            e += (m.sum() / n) * abs(ps[m].mean() - ys[m].mean())
    return float(e)


def main():
    if not config.have_key():
        print("SKIP E11: no ANTHROPIC_API_KEY")
        return
    client = config.anthropic_client()
    ys = [y for _, y in LABELED]
    verb = [verbalized_p(client, s) for s, _ in LABELED]
    cons = [consistency_p(client, s) for s, _ in LABELED]
    print("=== E11 calibration | 15 labeled biomedical statements (Haiku) ===")
    print(f"  {'signal':<14}{'Brier':<10}{'ECE':<10}{'acc@0.5':<10}")
    res = {}
    for name, ps in (("verbalized", verb), ("self-consistency", cons)):
        acc = np.mean([(p > 0.5) == bool(y) for p, y in zip(ps, ys)])
        res[name] = {"brier": brier(ps, ys), "ece": ece(ps, ys), "acc": float(acc)}
        print(f"  {name:<14}{res[name]['brier']:<10.3f}{res[name]['ece']:<10.3f}{acc:<10.3f}")
    best = min(res, key=lambda k: res[k]["brier"])
    import json
    Path("results").mkdir(exist_ok=True)
    json.dump(res, open("results/e11_calibration.json", "w"), indent=2)
    print(f"\nGO — use '{best}' as the confidence signal (lower Brier). "
          f"{'Confirms the literature (consistency >= verbalized).' if best == 'self-consistency' else 'Note: verbalized won here on this small set — validate on a larger labeled set before committing.'}")


if __name__ == "__main__":
    main()
