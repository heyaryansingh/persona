"""
E13 (plan's E4) - Interests/taste are FUNCTIONAL, not theater (BUILD_PLAN 1.4/1.5). IMPLEMENTED.

PRE-REGISTERED HYPOTHESIS
  Changing the taste weights / disposition measurably changes the agenda (what the
  researcher would read/deepen next), vs a fixed no-taste control which does not.

METRIC (>=20 seeds, mean +/- 95% CI)
  top1_change_rate : fraction of seeds where the #1 agenda item differs between a
                     value-driven and a surprise-driven disposition (want >> 0)
  top3_jaccard     : overlap of the top-3 agendas across dispositions (want < 1)
  control_top1_same: a disposition vs ITSELF always agrees (sanity; want == 1)

GO / NO-GO
  top1_change_rate high AND control identical -> taste is behaviorally load-bearing
  (not anthropomorphic theater, BUILD_PLAN 0.3). Drives the real outer-loop build_agenda.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import json
import numpy as np
from scipy import stats

from persona.store import BeliefStore, Claim
from persona.loops.outer import build_agenda, TasteWeights


def random_state(rng) -> BeliefStore:
    s = BeliefStore()
    n = int(rng.integers(6, 11))
    ids = [f"c{i}" for i in range(n)]
    for cid in ids:
        s.add_claim(Claim(cid, f"{cid} claim about a topic", logit=float(rng.uniform(-3, 3)), tier="core"))
        for _ in range(int(rng.integers(0, 3))):
            s.add_source(cid, f"ref{rng.integers(999)}", f"grp{rng.integers(5)}")
    # a few derives-from edges -> load-bearing structure
    for _ in range(int(rng.integers(2, 5))):
        a, b = rng.choice(ids, 2, replace=False)
        try:
            s.add_edge(str(a), str(b), "derives-from", confidence=float(rng.uniform(0.4, 0.95)))
        except Exception:
            pass
    # a few reversals -> surprise
    for cid in rng.choice(ids, int(rng.integers(1, 3)), replace=False):
        for _ in range(4):
            s.update_belief(str(cid), +1.0)
        for _ in range(6):
            s.update_belief(str(cid), -1.0)
    return s


def one_seed(seed: int) -> dict:
    rng = np.random.default_rng(seed)
    s = random_state(rng)
    value_driven = TasteWeights(value=4.0, surprise=0.2)
    surprise_driven = TasteWeights(value=0.2, surprise=4.0)

    a_val = [i.target for i in build_agenda(s, weights=value_driven)]
    a_sur = [i.target for i in build_agenda(s, weights=surprise_driven)]
    a_val2 = [i.target for i in build_agenda(s, weights=value_driven)]   # control: same disposition
    s.close()

    top3 = lambda x: set(x[:3])
    jac = len(top3(a_val) & top3(a_sur)) / max(1, len(top3(a_val) | top3(a_sur)))
    return {
        "top1_change_rate": 1.0 if (a_val and a_sur and a_val[0] != a_sur[0]) else 0.0,
        "top3_jaccard": jac,
        "control_top1_same": 1.0 if (a_val and a_val[0] == a_val2[0]) else 0.0,
    }


def ci(x):
    x = np.array(x)
    m = x.mean()
    h = stats.t.ppf(0.975, len(x) - 1) * x.std(ddof=1) / np.sqrt(len(x)) if len(x) > 1 else 0.0
    return m, h


def run(n_seeds: int = 50) -> dict:
    rows = [one_seed(3000 + i) for i in range(n_seeds)]
    res = {}
    print(f"=== E13 taste is functional | {n_seeds} seeds (real outer-loop build_agenda) ===")
    for k in rows[0].keys():
        m, h = ci([r[k] for r in rows])
        res[k] = [m, h]
        print(f"  {k:<20} {m:.3f} +/- {h:.3f}")
    return res


if __name__ == "__main__":
    res = run(50)
    Path("results").mkdir(exist_ok=True)
    with open("results/e13_taste_functional.json", "w") as f:
        json.dump(res, f, indent=2)
    ok = res["top1_change_rate"][0] >= 0.5 and res["control_top1_same"][0] >= 0.99
    print("\nGO" if ok else "\nNO-GO", "-> taste measurably changes behavior")
