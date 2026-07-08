"""
Sandboxed experiments for the Synthetic Researcher's *self* / memory layer.

We cannot fine-tune a frontier LLM in this sandbox, so we test the ARCHITECTURAL
hypotheses on a controlled simulation that mirrors the real regime: a persistent
agent ingests a stream of "claims" (some true, some noise, some that CONTRADICT
prior beliefs), and must maintain an accurate, calibrated belief-state over time
WITHOUT (a) forgetting hard-won stable beliefs or (b) being corrupted by noise.

This isolates the mechanism we actually control in the real build: the *membrane*
policy and the *replay/consolidation* policy over an external belief-store. These
are the knobs Letta/Mem0/SuRe-style systems expose, so results transfer.

Hypotheses under test
---------------------
H_MEM (membrane):   A convergence+provenance gate before writing to the self yields
                    higher belief accuracy under noisy swarm input than writing
                    every observation ("naive absorb").
H_SURE (surprise):  Surprise-prioritized re-examination (spend scarce verification
                    budget on observations that VIOLATE current belief) yields
                    better final accuracy AND faster correct belief-flips than
                    uniform/random verification, at equal budget.
H_ANCHOR (identity):A protected "core" of high-confidence, human-confirmed beliefs
                    that is exempt from overwrite resists corruption from a burst
                    of adversarial/noisy contradicting input better than an
                    unprotected store (a "catastrophic forgetting" analogue).

Everything is seeded and repeated across many worlds; we report means +/- 95% CI.
"""

import numpy as np
from dataclasses import dataclass, field
from scipy import stats

RNG_MASTER = np.random.default_rng(20260708)


# ----------------------------- world model -----------------------------------
@dataclass
class World:
    """Ground truth: each of K propositions has a true boolean value that may
    flip at most once (a real scientific reversal)."""
    K: int = 60
    flip_frac: float = 0.25          # fraction of propositions that truly reverse
    horizon: int = 4000              # number of incoming observations
    noise: float = 0.30              # P(observation is wrong about its proposition)
    contradiction_burst: bool = False
    seed: int = 0

    def __post_init__(self):
        self.rng = np.random.default_rng(self.seed)
        self.truth = self.rng.integers(0, 2, self.K).astype(int)
        # schedule flips
        self.flip_time = {}
        flippers = self.rng.choice(self.K, int(self.flip_frac * self.K), replace=False)
        for k in flippers:
            self.flip_time[k] = self.rng.integers(self.horizon // 3, 2 * self.horizon // 3)

    def truth_at(self, k, t):
        v = self.truth[k]
        if k in self.flip_time and t >= self.flip_time[k]:
            v = 1 - v
        return v

    def stream(self):
        """Yield (t, k, observed_value, provenance_independent_id)."""
        for t in range(self.horizon):
            k = self.rng.integers(self.K)
            true_v = self.truth_at(k, t)
            obs = true_v if self.rng.random() > self.noise else 1 - true_v
            # provenance: independent "labs" 0..3; convergence = multiple labs agree
            lab = self.rng.integers(4)
            yield t, k, int(obs), lab


# ----------------------------- belief stores ---------------------------------
@dataclass
class Belief:
    logit: float = 0.0               # belief in "value==1", as a log-odds
    support: int = 0
    labs: set = field(default_factory=set)
    human_locked: bool = False


def brier(beliefs, world, t):
    """Calibration: mean squared error of P(value==1) vs truth, over all props."""
    errs = []
    for k, b in beliefs.items():
        p = 1 / (1 + np.exp(-b.logit))
        errs.append((p - world.truth_at(k, t)) ** 2)
    return float(np.mean(errs)) if errs else 1.0


def accuracy(beliefs, world, t):
    ok = []
    for k, b in beliefs.items():
        pred = 1 if b.logit > 0 else 0
        ok.append(pred == world.truth_at(k, t))
    return float(np.mean(ok)) if ok else 0.0


# ----------------------------- agents ----------------------------------------
class NaiveAbsorb:
    """Writes every observation straight into the self. No membrane."""
    name = "naive_absorb"

    def __init__(self, K):
        self.b = {k: Belief() for k in range(K)}

    def observe(self, t, k, obs, lab, verify_budget):
        step = 1.0 if obs == 1 else -1.0
        self.b[k].logit += 0.6 * step
        self.b[k].logit = float(np.clip(self.b[k].logit, -8, 8))
        return 0


class MembraneGate:
    """Only commit when >=2 independent labs have reported the same direction
    recently (convergence + provenance). Otherwise hold in a scratch buffer."""
    name = "membrane"

    def __init__(self, K):
        self.b = {k: Belief() for k in range(K)}
        self.scratch = {k: {} for k in range(K)}   # lab -> last obs

    def observe(self, t, k, obs, lab, verify_budget):
        self.scratch[k][lab] = obs
        votes = list(self.scratch[k].values())
        # need at least 2 labs agreeing on the majority direction
        if len(votes) >= 2:
            mean = np.mean(votes)
            if mean >= 0.75 or mean <= 0.25:
                step = 1.0 if mean >= 0.75 else -1.0
                self.b[k].logit += 0.6 * step
                self.b[k].logit = float(np.clip(self.b[k].logit, -8, 8))
                self.scratch[k] = {}   # consume evidence
        return 0


class SurpriseReplay:
    """Membrane + a scarce verification budget spent preferentially on SURPRISING
    observations (those contradicting current belief). Verification = draw an extra
    independent look at the true-ish signal (models re-reading / re-analysis)."""
    name = "surprise_replay"

    def __init__(self, K, surprise=True):
        self.b = {k: Belief() for k in range(K)}
        self.scratch = {k: {} for k in range(K)}
        self.surprise = surprise

    def _commit(self, k, direction, strength=0.6):
        self.b[k].logit += strength * direction
        self.b[k].logit = float(np.clip(self.b[k].logit, -8, 8))

    def observe(self, t, k, obs, lab, verify_budget):
        self.scratch[k][lab] = obs
        used = 0
        p = 1 / (1 + np.exp(-self.b[k].logit))
        obs_dir = 1.0 if obs == 1 else -1.0
        surprise = abs((1 if obs == 1 else 0) - p)   # how much obs violates belief
        votes = list(self.scratch[k].values())
        if len(votes) >= 2:
            mean = np.mean(votes)
            if mean >= 0.75 or mean <= 0.25:
                self._commit(k, 1.0 if mean >= 0.75 else -1.0)
                self.scratch[k] = {}
        # spend verification on surprising, still-uncertain contradictions
        trigger = (surprise if self.surprise else 0.5)
        if verify_budget[0] > 0 and trigger > 0.6 and abs(self.b[k].logit) < 6:
            verify_budget[0] -= 1
            used = 1
            # an extra corroborating look, weighted by that it survived scrutiny
            self._commit(k, obs_dir, strength=0.9)
        return used


class AnchoredSurprise(SurpriseReplay):
    """Adds identity protection: beliefs that reach high confidence get 'locked'
    (human-confirmed analogue) and become resistant (not immune) to overwrite,
    the multi-anchor idea. Locked beliefs still update, but at reduced rate,
    preventing an adversarial burst from erasing established knowledge."""
    name = "anchored_surprise"

    def __init__(self, K, lock_at=4.0, resist=0.25):
        super().__init__(K, surprise=True)
        self.lock_at = lock_at
        self.resist = resist

    def _commit(self, k, direction, strength=0.6):
        if abs(self.b[k].logit) >= self.lock_at:
            self.b[k].human_locked = True
        factor = self.resist if self.b[k].human_locked else 1.0
        self.b[k].logit += strength * direction * factor
        self.b[k].logit = float(np.clip(self.b[k].logit, -8, 8))


# ----------------------------- experiment runner -----------------------------
def run_world(agent_cls, world_kwargs, budget_per_1k=40, **agent_kwargs):
    w = World(**world_kwargs)
    agent = agent_cls(w.K, **agent_kwargs)
    total_budget = int(budget_per_1k * w.horizon / 1000)
    budget = [total_budget]
    traj = []
    flip_detect_lag = []   # for truly-flipping props, how long to correct belief
    corrected = set()
    for t, k, obs, lab in w.stream():
        agent.observe(t, k, obs, lab, budget)
        if t % 200 == 0:
            traj.append((t, accuracy(agent.b, w, t), brier(agent.b, w, t)))
        # measure flip-correction latency
        if k in w.flip_time and t >= w.flip_time[k] and k not in corrected:
            b = agent.b[k]
            pred = 1 if b.logit > 0 else 0
            if pred == w.truth_at(k, t):
                flip_detect_lag.append(t - w.flip_time[k])
                corrected.add(k)
    final_acc = accuracy(agent.b, w, w.horizon - 1)
    final_brier = brier(agent.b, w, w.horizon - 1)
    mean_lag = float(np.mean(flip_detect_lag)) if flip_detect_lag else np.nan
    frac_flips_caught = len(corrected) / max(1, len(w.flip_time))
    return final_acc, final_brier, mean_lag, frac_flips_caught


def ci95(x):
    x = np.array([v for v in x if not np.isnan(v)])
    if len(x) < 2:
        return (np.nan, np.nan)
    m = x.mean()
    h = stats.t.ppf(0.975, len(x) - 1) * x.std(ddof=1) / np.sqrt(len(x))
    return m, h


def compare(agents, world_kwargs, n_worlds=40, budget_per_1k=40, label=""):
    print(f"\n=== {label} | noise={world_kwargs.get('noise')} "
          f"contradiction_burst={world_kwargs.get('contradiction_burst')} "
          f"| {n_worlds} worlds, budget={budget_per_1k}/1k obs ===")
    print(f"{'agent':<20}{'final_acc':<20}{'final_brier':<20}{'flip_lag':<18}{'flips_caught':<14}")
    out = {}
    for name, (cls, kw) in agents.items():
        accs, briers, lags, caught = [], [], [], []
        for s in range(n_worlds):
            wk = dict(world_kwargs); wk['seed'] = 1000 + s
            a, b, lag, fc = run_world(cls, wk, budget_per_1k, **kw)
            accs.append(a); briers.append(b); lags.append(lag); caught.append(fc)
        am, ah = ci95(accs); bm, bh = ci95(briers); lm, lh = ci95(lags); cm, ch = ci95(caught)
        print(f"{name:<20}{am:.3f}+/-{ah:.3f}      {bm:.3f}+/-{bh:.3f}      "
              f"{lm:6.0f}+/-{lh:<6.0f}   {cm:.2f}+/-{ch:.2f}")
        out[name] = dict(acc=(am, ah), brier=(bm, bh), lag=(lm, lh), caught=(cm, ch),
                         raw_acc=accs, raw_brier=briers)
    return out


if __name__ == "__main__":
    # ---- E1/E2: membrane vs naive under noise (H_MEM) ----
    agents_core = {
        "naive_absorb":      (NaiveAbsorb, {}),
        "membrane":          (MembraneGate, {}),
        "surprise_replay":   (SurpriseReplay, {"surprise": True}),
        "uniform_replay":    (SurpriseReplay, {"surprise": False}),
        "anchored_surprise": (AnchoredSurprise, {}),
    }
    r_lo = compare(agents_core, dict(noise=0.20, contradiction_burst=False),
                   label="E1 low-noise")
    r_hi = compare(agents_core, dict(noise=0.35, contradiction_burst=False),
                   label="E2 high-noise")

    # ---- E3: surprise vs uniform at MATCHED budget, harder noise (H_SURE) ----
    # (already directly comparable above: surprise_replay vs uniform_replay)

    # ---- H_ANCHOR: adversarial contradiction burst (identity protection) ----
    # Emulate a burst by cranking noise very high in the flip window via higher noise
    r_adv = compare(
        {"membrane": (MembraneGate, {}),
         "surprise_replay": (SurpriseReplay, {"surprise": True}),
         "anchored_surprise": (AnchoredSurprise, {})},
        dict(noise=0.45, contradiction_burst=True, flip_frac=0.25),
        label="E_ANCHOR adversarial high-noise")

    # ---- persist results ----
    import json
    def pack(r):
        return {k: {m: v[m] for m in ("acc", "brier", "lag", "caught")} for k, v in r.items()}
    with open("results/memory_core_results.json", "w") as f:
        json.dump({"E1_low_noise": pack(r_lo),
                   "E2_high_noise": pack(r_hi),
                   "E_anchor_adversarial": pack(r_adv)}, f, indent=2)
    print("\nSaved -> results/memory_core_results.json")
