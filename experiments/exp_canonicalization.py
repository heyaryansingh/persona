"""exp_canonicalization (T1.2) — is entity canonicalization reproducible AND symbol-safe?

Three claims the v3 canonicalizer must satisfy (the v2 defects the audit flagged):
  1. ORDER-INDEPENDENT: same entities in any read order -> identical canonical assignment
     (>=20 shuffles; v2's greedy first-seen-wins failed this and broke crash-resume determinism).
  2. NO FALSE MERGE of distinct symbols: IL-6 vs IL-1, NLRP3 vs NLRP1, APOE4 vs APOE2 must NOT
     collapse (v2 + generic embeddings did — fake convergence, the worst bug here).
  3. HIGH MERGE RECALL of true variants: microglia/microglial activation/activated microglia
     -> one canonical.
Reported as pairwise clustering precision/recall/F1 vs a gold grouping, plus the two hard checks.
Run: python experiments/exp_canonicalization.py
"""
import json
import random
import sys
from itertools import combinations
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from persona.canonicalize import EntityCanonicalizer, normalize_entity   # noqa: E402

# gold clusters: each inner list is variants of ONE entity
GOLD = [
    ["microglia", "microglial activation", "activated microglia", "microglial cells", "reactive microglia"],
    ["tau", "tau protein", "hyperphosphorylated tau", "p-tau", "phosphorylated tau"],
    ["amyloid-beta", "abeta", "amyloid beta", "amyloid", "amyloid deposition"],
    ["neuroinflammation", "neuroinflammatory response", "neuro-inflammation"],
    ["astrocyte", "astrocytes", "astrocytic", "reactive astrocytes"],
    ["alzheimer", "alzheimer's disease", "alzheimers", "AD"],
    ["nlrp3", "nlrp3 inflammasome", "NLRP3 activation"],
    ["il-6", "il6", "IL-6 levels"],
    ["il-1", "il1", "IL-1 expression"],
    ["apoe4", "APOE4"],
    ["apoe2"],
    ["nlrp1"],
]
DISTINCT_PAIRS = [("il-6", "il-1"), ("nlrp3", "nlrp1"), ("apoe4", "apoe2"),
                  ("il6", "il1"), ("tau", "amyloid")]


def _assign(entities):
    c = EntityCanonicalizer()          # pure rule-based (default)
    return {e: c.canon(e) for e in entities}


def _pairwise_prf(items, canon_of, gold_of):
    tp = fp = fn = 0
    for a, b in combinations(items, 2):
        same_pred = canon_of[a] == canon_of[b]
        same_gold = gold_of[a] == gold_of[b]
        tp += same_pred and same_gold
        fp += same_pred and not same_gold
        fn += (not same_pred) and same_gold
    prec = tp / (tp + fp) if (tp + fp) else 1.0
    rec = tp / (tp + fn) if (tp + fn) else 1.0
    f1 = 2 * prec * rec / (prec + rec) if (prec + rec) else 0.0
    return prec, rec, f1, fp


def main():
    items = [e for cl in GOLD for e in cl]
    gold_of = {e: i for i, cl in enumerate(GOLD) for e in cl}

    # (1) order-independence over >=20 shuffles
    base = _assign(items)
    stable = True
    for seed in range(25):
        shuf = items[:]
        random.Random(seed).shuffle(shuf)
        if _assign(shuf) != base:
            stable = False
            break
    print(f"order-independent over 25 shuffles: {stable}")

    # (2) no false merge of distinct symbols
    false_merges = [(a, b) for a, b in DISTINCT_PAIRS
                    if normalize_entity(a) == normalize_entity(b)]
    print(f"distinct-symbol false merges: {len(false_merges)}  {false_merges if false_merges else ''}")

    # (3) pairwise clustering quality vs gold
    prec, rec, f1, fp = _pairwise_prf(items, base, gold_of)
    print(f"pairwise precision={prec:.2f} recall={rec:.2f} F1={f1:.2f} (false-pair-merges={fp})")

    ok = stable and not false_merges and prec >= 0.99
    print(f"\nVERDICT: {'PASS' if ok else 'CHECK'} — "
          f"{'reproducible, symbol-safe, high-precision' if ok else 'see failures above'}")
    res = {"order_independent": stable, "false_merges": false_merges,
           "precision": round(prec, 3), "recall": round(rec, 3), "f1": round(f1, 3)}
    (Path(__file__).resolve().parent.parent / "results" / "canonicalization.json").write_text(
        json.dumps(res, indent=2), encoding="utf-8")
    print("saved -> results/canonicalization.json")


if __name__ == "__main__":
    main()
