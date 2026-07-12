"""RQ-E10: an honest learning loop — optimize a POLICY against a FROZEN, held-out evaluator with
keep/revert. NOT weight training (hosted Claude weights are not customer-trainable; see
docs/CONTINUATION_HANDOFF.md:183). This is the prompt/tool/memory-optimization pattern made concrete.

Mutable surface: the numeric weights of an ESCALATION policy that decides which candidate sign-
collisions to route to a human reviewer. Frozen evaluator: held-out real Curie sign-collisions,
labelled by exact-span eligibility — BOTH sides must be verbatim before a candidate can proceed to
human review. This is not a label for a true scientific contradiction; RQ-E02 still needs human
gold. If either side is non-verbatim it is an extraction error the pipeline should auto-fix, not
escalate. The optimizer sees only TRAIN features/labels; the held-out split is never read during search.

Contract (the whole point of RQ-E10):
  - Mutable = policy weights only. Evaluator, label rule, and held-out split are immutable.
  - Optimizer never evaluates on held-out during search; keep/revert is logged.
  - Ship the evolved policy only if held-out F1 gain over the baseline hand-rule is > 0.
Arms: baseline hand-rule · random search · greedy-keep-best · diverse-archive.
>= 20 seeded train/held-out splits; mean +/- 95% CI.

Honest scope: this optimizes a policy over real data with a frozen evaluator — reproducible and
free (no model calls). Swapping the objective for a live-model research-quality score (citation-F1 x
execution-pass x replay-clean per $) is the same machinery with a paid evaluator; that live variant
is the budgeted extension, not run here.
"""
from __future__ import annotations

import hashlib
import json
import math
import random
import statistics
import unicodedata
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PERSONAS = ROOT / "personas"       # pool sign-collisions across every mind's real corpus
OUT_JSON = ROOT / "results" / "rq_e10_policy_optimizer.json"
OUT_PNG = ROOT / "results" / "rq_e10_policy_optimizer.png"
SEEDS = 30
MUTATIONS = 40                     # policy evaluations per optimizer arm per seed (fixed budget)
FEATURES = ("min_indep", "conf_gap", "min_conf", "lexsim", "bias")
ARM_SEED_OFFSET = {"random": 101, "greedy": 211, "archive": 307}


def norm(t: str) -> str:
    return " ".join(unicodedata.normalize("NFKC", t or "").casefold().split())


def load_pairs():
    """Candidate sign-collisions with proxy features and an exact-span eligibility label."""
    by_pair = defaultdict(lambda: {"+": [], "-": []})
    for path in PERSONAS.glob("*/sources/*/claims.jsonl"):
        clean_p = path.with_name("clean.md")
        if not clean_p.exists():
            continue
        clean = norm(clean_p.read_text(encoding="utf-8", errors="replace"))
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            try:
                c = json.loads(line)
            except json.JSONDecodeError:
                continue
            sign = c.get("effect_sign")
            if sign not in ("+", "-"):
                continue
            subj, obj = norm(c.get("subject", "")), norm(c.get("object", ""))
            if not subj or not obj:
                continue
            quote = norm(c.get("quote", ""))
            by_pair[(subj, obj)][sign].append({
                "conf": float(c.get("confidence", 0.6) or 0.6),
                "verbatim": bool(quote and quote in clean),
                "src": path.parent.name})
    pairs = []
    for (subj, obj), sides in by_pair.items():
        if not (sides["+"] and sides["-"]):
            continue
        pos, neg = sides["+"], sides["-"]
        pos_indep = len({x["src"] for x in pos}); neg_indep = len({x["src"] for x in neg})
        pos_conf = statistics.fmean(x["conf"] for x in pos)
        neg_conf = statistics.fmean(x["conf"] for x in neg)
        both_verbatim = any(x["verbatim"] for x in pos) and any(x["verbatim"] for x in neg)
        toks_s, toks_o = set(subj.split()), set(obj.split())
        lexsim = len(toks_s & toks_o) / max(1, len(toks_s | toks_o))
        feats = {
            "min_indep": min(pos_indep, neg_indep) / 5.0,
            "conf_gap": abs(pos_conf - neg_conf),
            "min_conf": min(pos_conf, neg_conf),
            "lexsim": lexsim,
            "bias": 1.0,
        }
        pairs.append({"feats": feats, "label": 1 if both_verbatim else 0})
    return pairs


def score(theta, feats):
    z = sum(theta[k] * feats[k] for k in FEATURES)
    return 1.0 / (1.0 + math.exp(-z))


def f1(theta, pairs):
    tp = fp = fn = 0
    for p in pairs:
        pred = 1 if score(theta, p["feats"]) >= 0.5 else 0
        if pred and p["label"]:
            tp += 1
        elif pred and not p["label"]:
            fp += 1
        elif not pred and p["label"]:
            fn += 1
    prec = tp / (tp + fp) if (tp + fp) else 0.0
    rec = tp / (tp + fn) if (tp + fn) else 0.0
    return 2 * prec * rec / (prec + rec) if (prec + rec) else 0.0


BASELINE = {"min_indep": 4.0, "conf_gap": 0.0, "min_conf": 0.0, "lexsim": 0.0, "bias": -1.5}
# a plausible hand rule: escalate when both sides have some independence (min_indep term dominates)


def mutate(theta, rng, scale):
    return {k: theta[k] + rng.gauss(0, scale) for k in FEATURES}


def optimize(train, rng, arm):
    """Search policy weights on TRAIN ONLY (held-out never touched). Returns the chosen theta."""
    best = dict(BASELINE); best_f = f1(best, train)
    archive = [(best_f, best)]
    for _ in range(MUTATIONS):
        if arm == "random":
            cand = {k: rng.uniform(-4, 4) for k in FEATURES}
        elif arm == "greedy":
            cand = mutate(best, rng, 0.6)
        else:  # diverse-archive: mutate a random archived elite
            parent = rng.choice(archive)[1]
            cand = mutate(parent, rng, 0.8)
        cf = f1(cand, train)
        archive.append((cf, cand))
        if len(archive) > 24:
            archive.sort(key=lambda x: x[0], reverse=True)
            archive[:] = archive[:24]
        if cf > best_f:            # keep/revert: only adopt a strict improvement on TRAIN
            best_f, best = cf, cand
    return best


def main():
    pairs = load_pairs()
    if len(pairs) < 20:
        raise RuntimeError(f"need >= 20 sign-collisions, found {len(pairs)}")
    arms = ("random", "greedy", "archive")
    rows = {a: [] for a in arms}
    base_rows = []
    for seed in range(SEEDS):
        rng = random.Random(seed)
        idx = list(range(len(pairs)))
        rng.shuffle(idx)
        cut = len(idx) // 2
        train = [pairs[i] for i in idx[:cut]]
        held = [pairs[i] for i in idx[cut:]]       # NEVER passed to optimize()
        base_rows.append(f1(BASELINE, held))
        for arm in arms:
            theta = optimize(train, random.Random(seed * 991 + ARM_SEED_OFFSET[arm]), arm)
            rows[arm].append(f1(theta, held))       # held-out score only after search
    def stat(xs):
        m = statistics.fmean(xs)
        h = 1.96 * statistics.stdev(xs) / math.sqrt(len(xs)) if len(xs) > 1 else 0.0
        return {"mean": m, "ci95_half": h}
    base = stat(base_rows)
    summary = {a: stat(rows[a]) for a in arms}
    best_arm = max(arms, key=lambda a: summary[a]["mean"])
    gain = summary[best_arm]["mean"] - base["mean"]
    # paired: does the best arm beat baseline on the SAME held-out splits, on average?
    paired_gain = statistics.fmean(rows[best_arm][i] - base_rows[i] for i in range(SEEDS))
    ship = gain > 0 and paired_gain > 0
    result = {
        "experiment": "RQ-E10 policy optimizer (escalation policy vs frozen held-out evaluator)",
        "kind": "offline reproducible optimization over real Curie sign-collisions",
        "seeds": SEEDS, "mutations_per_arm": MUTATIONS, "n_pairs": len(pairs),
        "arm_seed_offsets": ARM_SEED_OFFSET,
        "evaluator_label": "both sides pass exact-span eligibility; not human contradiction gold",
        "positive_rate": round(statistics.fmean(p["label"] for p in pairs), 3),
        "baseline_hand_rule_heldout_f1": base,
        "arms_heldout_f1": summary, "best_arm": best_arm,
        "heldout_gain_over_baseline": gain, "paired_mean_gain": paired_gain,
        "gate": {
            "optimizer_reads_heldout": False,
            "ship_only_if_heldout_gain_positive": True,
            "heldout_gain_positive": bool(gain > 0 and paired_gain > 0),
            "verdict": ("HARNESS-GO; RUNTIME-POLICY-NOT-INTEGRATED" if ship
                        else "KEEP-BASELINE (revert)"),
        },
        "honesty": ("Optimizes policy weights (not model weights) against an immutable held-out "
                    "objective the optimizer never reads. Reproducible and free. The live-model "
                    "research-quality evaluator is the same machinery with a paid scorer — not run here."),
        "limitations": [
            "Objective label = both-sides exact-span eligibility, not a true contradiction or human gold (RQ-E02).",
            "Policy features are proxies (independence, confidence gap, lexical similarity).",
            "No model calls: this validates the optimizer + held-out gate, not live research quality.",
        ],
    }
    OUT_JSON.write_text(json.dumps(result, indent=2), encoding="utf-8")
    try:
        _chart(base, summary, arms)
    except Exception as e:
        result["chart_error"] = str(e)[:120]
    print(f"pairs={len(pairs)} positive_rate={result['positive_rate']} seeds={SEEDS}")
    print(f"baseline held-out F1 = {base['mean']:.3f} +/- {base['ci95_half']:.3f}")
    for a in arms:
        print(f"  {a:8} held-out F1 = {summary[a]['mean']:.3f} +/- {summary[a]['ci95_half']:.3f}")
    print(f"best arm = {best_arm}; paired mean gain = {paired_gain:+.3f}; verdict = {result['gate']['verdict']}")
    print(f"wrote {OUT_JSON.relative_to(ROOT)}")


def _chart(base, summary, arms):
    import matplotlib.pyplot as plt
    labels = ["baseline\n(hand rule)"] + [a for a in arms]
    means = [base["mean"]] + [summary[a]["mean"] for a in arms]
    errs = [base["ci95_half"]] + [summary[a]["ci95_half"] for a in arms]
    colors = ["#7f8c8d", "#b44d3a", "#426b9a", "#3f7e67"]
    fig, ax = plt.subplots(figsize=(7, 4.2))
    ax.bar(labels, means, yerr=errs, capsize=4, color=colors)
    ax.set_ylabel("held-out F1 (exact-span-eligible candidates)")
    ax.set_title("RQ-E10 — policy optimized vs frozen held-out evaluator (30 seeds)", fontweight="bold")
    ax.grid(axis="y", alpha=.2)
    fig.tight_layout()
    fig.savefig(OUT_PNG, dpi=180, bbox_inches="tight", facecolor="white")


if __name__ == "__main__":
    main()
