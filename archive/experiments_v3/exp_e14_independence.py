"""
E14 - Evidential-independence convergence gate (gates BUILD_PLAN 1.3). Now IMPLEMENTED.

PRE-REGISTERED HYPOTHESIS
  Defining convergence as EVIDENTIAL INDEPENDENCE (distinct source groups) lets the
  membrane commit genuinely independent corroboration while REJECTING citation echo
  (one source amplified N times) -- which a raw agreement-count gate would wrongly admit.

METRIC (>=20 seeds, mean +/- 95% CI)
  independent_commit_rate : claims with K distinct groups get committed (want ~1)
  echo_commit_rate        : claims with N repeats from ONE group get committed (want ~0)
  naive_count_echo_admits : a raw agreement-count gate (>=quorum agreeing candidates,
                            ignoring group) admits echo (want ~1, i.e. the failure we avoid)

GO / NO-GO
  independent_commit_rate high AND echo_commit_rate ~0 -> the independence gate works;
  the gap vs naive_count shows why counting agreement (not independence) is unsafe
  (Greenberg BMJ 2009: apparent consensus is often amplification). See planning/LITERATURE.md §D.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import json
import numpy as np
from scipy import stats

from persona.store import BeliefStore
from persona.membrane import Membrane
from persona.swarm.reader import Candidate


def _cand(key, group, i):
    return Candidate(key, f"{key} claim", +1.0, group, f"{group}:{i}", confidence=0.6)


def one_seed(seed: int) -> dict:
    rng = np.random.default_rng(seed)
    s = BeliefStore()
    m = Membrane(s, fast_quorum=3)     # need 3 independent groups

    # genuinely independent: >=3 distinct groups
    n_indep = int(rng.integers(3, 7))
    for i in range(n_indep):
        m.submit(_cand("independent", f"lab_{i}", i))

    # echo: one source amplified many times (raw count high, independence 1)
    n_echo = int(rng.integers(4, 10))
    for i in range(n_echo):
        m.submit(_cand("echo", "single_source", i))

    rep = m.harvest()
    committed = set(rep.committed)

    # naive agreement-count baseline (the WRONG gate we avoid): would echo pass a
    # count>=quorum test? yes if n_echo>=3, regardless of independence.
    naive_admits_echo = 1.0 if n_echo >= 3 else 0.0

    out = {
        "independent_commit_rate": 1.0 if "independent" in committed else 0.0,
        "echo_commit_rate": 1.0 if "echo" in committed else 0.0,
        "naive_count_echo_admits": naive_admits_echo,
    }
    s.close()
    return out


def ci(x):
    x = np.array(x)
    m = x.mean()
    h = stats.t.ppf(0.975, len(x) - 1) * x.std(ddof=1) / np.sqrt(len(x)) if len(x) > 1 else 0.0
    return m, h


def run(n_seeds: int = 50) -> dict:
    rows = [one_seed(2000 + i) for i in range(n_seeds)]
    res = {}
    print(f"=== E14 evidential-independence gate | {n_seeds} seeds (real Membrane) ===")
    for k in rows[0].keys():
        m, h = ci([r[k] for r in rows])
        res[k] = [m, h]
        print(f"  {k:<26} {m:.3f} +/- {h:.3f}")
    return res


if __name__ == "__main__":
    res = run(50)
    Path("results").mkdir(exist_ok=True)
    with open("results/e14_independence.json", "w") as f:
        json.dump(res, f, indent=2)
    ok = res["independent_commit_rate"][0] >= 0.95 and res["echo_commit_rate"][0] <= 0.05
    print("\nGO" if ok else "\nNO-GO",
          "(independence gate rejects echo that a raw-count gate would admit)")
