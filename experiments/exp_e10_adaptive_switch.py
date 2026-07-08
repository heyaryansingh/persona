"""
E10 - Online correlated-disagreement detector / the adaptive membrane switch
(gates BUILD_PLAN 5.4). Now IMPLEMENTED (was a stub).

PRE-REGISTERED HYPOTHESIS
  The membrane's cheap online detector flips fast-path <-> strict on the correlated-
  disagreement (poisoning) signature: high volume, low independence, attacking an
  established belief -- WITHOUT firing on benign high-volume independent evidence.

METRIC (>=20 seeds, mean +/- 95% CI)
  poison_detect_rate      : fraction of seeds the poisoned claim goes strict (want ~1)
  benign_false_strict_rate: fraction of seeds a benign claim wrongly goes strict (want ~0)
  poison_retention        : fraction of seeds the established belief survives (want ~1)
  popular_committed_rate  : benign high-volume INDEPENDENT claim still commits (want ~1)

GO / NO-GO
  detect_rate high AND false_strict_rate ~0 AND retention ~1 -> ship the adaptive switch.
  Drives the REAL persona.membrane.Membrane (not a re-implementation) -> validates the
  shipped code, per CLAUDE.md test-at-the-seams.
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


_N = [0]  # each candidate = a distinct document (store dedups by doc_id)


def _cand(key, direction, group, conf=0.6):
    _N[0] += 1
    return Candidate(key, f"{key} claim", direction, group, f"{group}:d{_N[0]}", confidence=conf)


def one_seed(seed: int) -> dict:
    rng = np.random.default_rng(seed)
    s = BeliefStore()
    # an already-established TRUE belief (not anchored: tests the detector, not the store guard)
    s.add_claim(Claim("target", "established true belief", logit=3.0, tier="core"))
    m = Membrane(s)

    # correlated sustained poison against target: high volume, few groups, wrong direction
    p_vol = int(rng.integers(6, 15))
    p_groups = int(rng.integers(1, 3))               # 1-2 correlated groups
    for i in range(p_vol):
        m.submit(_cand("target", -1.0, f"troll_{i % p_groups}"))

    # benign INDEPENDENT high-volume claim: many distinct groups -> must NOT go strict
    b_vol = int(rng.integers(6, 12))
    for i in range(b_vol):
        m.submit(_cand("popular", +1.0, f"lab_{i}"))

    # small benign claim: 2 independent groups -> should just commit, never strict
    m.submit(_cand("benign", +1.0, "labA"))
    m.submit(_cand("benign", +1.0, "labB"))

    rep = m.harvest()
    strict = set(rep.strict_claims)
    out = {
        "poison_detect": 1.0 if "target" in strict else 0.0,
        "benign_false_strict": 1.0 if ("popular" in strict or "benign" in strict) else 0.0,
        "poison_retention": 1.0 if s.get_claim("target").predicted == 1 else 0.0,
        "popular_committed": 1.0 if "popular" in rep.committed else 0.0,
    }
    s.close()
    return out


def ci(x):
    x = np.array(x)
    m = x.mean()
    h = stats.t.ppf(0.975, len(x) - 1) * x.std(ddof=1) / np.sqrt(len(x)) if len(x) > 1 else 0.0
    return m, h


def run(n_seeds: int = 50) -> dict:
    rows = [one_seed(1000 + i) for i in range(n_seeds)]
    res = {}
    print(f"=== E10 adaptive switch | {n_seeds} seeds (drives the real Membrane) ===")
    for k in rows[0].keys():
        m, h = ci([r[k] for r in rows])
        res[k] = [m, h]
        print(f"  {k:<22} {m:.3f} +/- {h:.3f}")
    return res


if __name__ == "__main__":
    res = run(50)
    Path("results").mkdir(exist_ok=True)
    with open("results/e10_adaptive_switch.json", "w") as f:
        json.dump(res, f, indent=2)
    ok = (res["poison_detect"][0] >= 0.95 and res["benign_false_strict"][0] <= 0.05
          and res["poison_retention"][0] >= 0.95)
    print("\nGO" if ok else "\nNO-GO", "-> results/e10_adaptive_switch.json")
