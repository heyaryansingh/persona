"""
E9 - Human-error escape hatch (gates the anchoring / write-policy). Now IMPLEMENTED.

Addresses Confound B (results/REPRODUCTION.md): anchoring was never tested when the human
label is WRONG. The escape hatch: independent, sustained contrary evidence RE-ESCALATES a
human anchor to a human (never silently overwrites — the store guard still holds), while
correlated poison cannot reach the independence threshold.

PRE-REGISTERED HYPOTHESIS
  There is an escape_quorum (independent groups) that RE-ESCALATES a wrong anchor when
  genuinely independent contrary evidence mounts, WITHOUT re-escalating (or overwriting)
  under correlated poison.

METRIC (>=20 seeds, mean +/- 95% CI)
  wrong_anchor_reescalate_rate : independent contrary evidence re-escalates a wrong anchor (want ~1)
  poison_reescalate_rate       : correlated poison re-escalates a correct anchor (want ~0)
  poison_retention             : correct anchor still survives poison (want ~1)

GO / NO-GO
  wrong_anchor_reescalate high AND poison_reescalate ~0 AND retention ~1 -> the hatch
  recovers from human error without reopening the poisoning vulnerability. Drives the real Membrane.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import json
import numpy as np
from scipy import stats

from persona.store import BeliefStore, Claim
from persona.membrane import Membrane
from persona.swarm.reader import Candidate


def _cand(key, direction, group):
    return Candidate(key, f"{key} claim", direction, group, f"{group}:d", confidence=0.6)


def one_seed(seed: int) -> dict:
    rng = np.random.default_rng(seed)
    s = BeliefStore()
    m = Membrane(s, escape_quorum=4)

    # a CORRECT human anchor, then correlated poison against it (few groups, high volume)
    s.add_claim(Claim("correct", "correct anchored belief", tier="core"))
    s.human_confirm("correct", truth=1)
    p_groups = int(rng.integers(1, 3))
    for i in range(int(rng.integers(6, 15))):
        m.submit(_cand("correct", -1.0, f"troll_{i % p_groups}"))

    # a WRONG human anchor (human said TRUE, reality is FALSE), then INDEPENDENT correct
    # contrary evidence mounts from many distinct groups
    s.add_claim(Claim("wrong", "wrongly anchored belief", tier="core"))
    s.human_confirm("wrong", truth=1)
    k = int(rng.integers(4, 9))
    for i in range(k):
        m.submit(_cand("wrong", -1.0, f"lab_{i}"))

    rep = m.harvest()
    challenged = {e.claim_key for e in rep.contradictions if e.kind == "anchor-challenge"}
    out = {
        "wrong_anchor_reescalate_rate": 1.0 if "wrong" in challenged else 0.0,
        "poison_reescalate_rate": 1.0 if "correct" in challenged else 0.0,
        "poison_retention": 1.0 if s.get_claim("correct").predicted == 1 else 0.0,
    }
    s.close()
    return out


def ci(x):
    x = np.array(x)
    m = x.mean()
    h = stats.t.ppf(0.975, len(x) - 1) * x.std(ddof=1) / np.sqrt(len(x)) if len(x) > 1 else 0.0
    return m, h


def run(n_seeds: int = 50) -> dict:
    rows = [one_seed(4000 + i) for i in range(n_seeds)]
    res = {}
    print(f"=== E9 human-error escape hatch | {n_seeds} seeds (real Membrane) ===")
    for k in rows[0].keys():
        m, h = ci([r[k] for r in rows])
        res[k] = [m, h]
        print(f"  {k:<30} {m:.3f} +/- {h:.3f}")
    return res


if __name__ == "__main__":
    res = run(50)
    Path("results").mkdir(exist_ok=True)
    with open("results/e9_human_error_hatch.json", "w") as f:
        json.dump(res, f, indent=2)
    ok = (res["wrong_anchor_reescalate_rate"][0] >= 0.95
          and res["poison_reescalate_rate"][0] <= 0.05
          and res["poison_retention"][0] >= 0.95)
    print("\nGO" if ok else "\nNO-GO", "-> recovers from human error without reopening poisoning")
