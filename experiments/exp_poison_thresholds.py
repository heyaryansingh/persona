"""exp_poison_thresholds (T1.3) — derive the new-belief-fabrication poison thresholds by sweep.

The membrane must flag two attack shapes for strict-mode + human review while leaving benign
regimes untouched:
  - ATTACK: many low-independence candidates OPPOSING an established belief.
  - FABRICATE: many low-independence candidates manufacturing a NEW belief (no established one).
And must NOT flag:
  - BENIGN-NEW: a genuine new belief with many INDEPENDENT groups.
  - BENIGN-SMALL: a modest handful of candidates.

We sweep (poison_new_volume, poison_new_ratio) over >=20 seeds/scenario and pick the point that
maximizes (attack+fabricate flag rate) - (benign flag rate).
Run: python experiments/exp_poison_thresholds.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import numpy as np                                                # noqa: E402
from persona.store import BeliefStore, Claim                      # noqa: E402
from persona.membrane import Membrane                             # noqa: E402
from persona.swarm.reader import Candidate                        # noqa: E402

SEEDS = 30


def _cand(key, group, i, direction=+1.0):
    return Candidate(key, f"{key} claim", direction, group, f"{group}:{i}", confidence=0.6)


def _scenario(kind, seed, membrane_kwargs):
    rng = np.random.default_rng(seed)
    s = BeliefStore()
    m = Membrane(s, **membrane_kwargs)
    key = "target"
    if kind == "attack":
        s.add_claim(Claim(key, "established", logit=3.0))          # established +belief
        vol = int(rng.integers(8, 16)); groups = int(rng.integers(1, 3))
        for i in range(vol):
            m.submit(_cand(key, f"g{i % groups}", i, direction=-1.0))   # opposing, few groups
    elif kind == "fabricate":
        vol = int(rng.integers(8, 18)); groups = int(rng.integers(1, 3))
        for i in range(vol):
            m.submit(_cand(key, f"g{i % groups}", i, direction=+1.0))   # new belief, few groups
    elif kind == "benign_new":
        vol = int(rng.integers(8, 18)); groups = vol                   # every candidate a new group
        for i in range(vol):
            m.submit(_cand(key, f"g{i}", i, direction=+1.0))
    elif kind == "benign_small":
        vol = int(rng.integers(2, 5)); groups = int(rng.integers(1, 3))
        for i in range(vol):
            m.submit(_cand(key, f"g{i % groups}", i, direction=+1.0))
    rep = m.harvest()
    flagged = key in rep.strict_claims
    s.close()
    return flagged


def _rate(kind, kwargs):
    return np.mean([_scenario(kind, 500 + i, kwargs) for i in range(SEEDS)])


def main():
    print(f"=== poison-threshold sweep | {SEEDS} seeds/scenario ===")
    best = None
    for vol in (6, 8, 10, 12):
        for ratio in (0.15, 0.20, 0.25, 0.30):
            kw = dict(poison_new_volume=vol, poison_new_ratio=ratio)
            atk = _rate("attack", kw); fab = _rate("fabricate", kw)
            bn = _rate("benign_new", kw); bs = _rate("benign_small", kw)
            sep = (atk + fab) / 2 - (bn + bs) / 2
            if best is None or sep > best[0]:
                best = (sep, vol, ratio, atk, fab, bn, bs)
    sep, vol, ratio, atk, fab, bn, bs = best
    print(f"best (poison_new_volume={vol}, poison_new_ratio={ratio}):")
    print(f"  attack flag={atk:.2f}  fabricate flag={fab:.2f}  "
          f"benign_new flag={bn:.2f}  benign_small flag={bs:.2f}  separation={sep:.2f}")
    # report the ADOPTED defaults too
    cur = dict(poison_new_volume=6, poison_new_ratio=0.25)
    print(f"current defaults {cur}:")
    print(f"  attack={_rate('attack', cur):.2f} fabricate={_rate('fabricate', cur):.2f} "
          f"benign_new={_rate('benign_new', cur):.2f} benign_small={_rate('benign_small', cur):.2f}")


if __name__ == "__main__":
    main()
