"""exp_e6_dependency (E6) — does the inferential-dependency tagger recover real structure?

The flagship graph (BUILD_PLAN 3.2) is only worth building if its CANDIDATE edges track the
true dependency structure well enough to be a useful hypothesis-ranker. We test on a gold dev
set of biomedical claims with an expert-labelled dependency DAG:

  1. edge classification: tagger vs gold on every co-mentioning pair (3-way: A->B / B->A / none),
     reported as accuracy + Cohen's kappa (chance-corrected).
  2. load-bearing ranking: Spearman(load_bearing(store), gold foundational rank) — the metric that
     actually matters, since VoI multiplies by load_bearing.

Honest expectation (planning: E6 may downgrade to human-in-the-loop): the offline heuristic uses
provenance+replication+generality as a proxy for foundational-ness, so it will MISS dependencies
between equally-established claims. We measure how much. If a key is present we also run the real
Claude tagger. Deterministic (no seeds): the dev set + heuristic are fixed; validity is the n=labeled
agreement, not seed variance.
Run: python experiments/exp_e6_dependency.py
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from persona.store import BeliefStore, Claim                              # noqa: E402
from persona.engine.dependency import load_bearing                        # noqa: E402
from persona.swarm.dependency_tagger import (candidate_pairs,             # noqa: E402
    HeuristicDependencyTagger, ClaudeDependencyTagger)
from persona import config                                                # noqa: E402

# (claim_id, statement, [entities], provenance, anchor, n_independent_sources, gold_foundational_rank)
# lower rank = more foundational. Realistic: foundational claims tend to be better replicated,
# but NOT perfectly — B7 is well-replicated yet derived (the trap that exposes the heuristic).
CLAIMS = [
    ("c1", "amyloid-beta accumulates in alzheimer",   ["amyloid", "alzheimer"],       "HUMAN_CONFIRMED", True, 5, 1),
    ("c2", "microglia respond to amyloid-beta",        ["microglia", "amyloid"],       "READ", False, 4, 2),
    ("c3", "microglia drive neuroinflammation",        ["microglia", "neuroinflammation"], "READ", False, 3, 3),
    ("c4", "neuroinflammation accelerates tau",        ["neuroinflammation", "tau"],   "READ", False, 2, 4),
    ("c5", "nlrp3 activates in microglia",             ["nlrp3", "microglia"],         "READ", False, 2, 3),
    ("c6", "il-1 released downstream of nlrp3",         ["il-1", "nlrp3"],              "READ", False, 1, 4),
    ("c7", "trem2 modulates microglia",                ["trem2", "microglia"],         "READ", False, 4, 3),
    ("c8", "tau spreads trans-synaptically",           ["tau", "synapse"],             "READ", False, 2, 4),
    ("c9", "synapse loss correlates with cognition",   ["synapse", "cognition"],       "HUMAN_CONFIRMED", True, 4, 2),
    ("c10", "apoe4 increases amyloid deposition",       ["apoe", "amyloid"],            "READ", False, 3, 2),
    ("c11", "complement tags synapses for pruning",     ["complement", "synapse"],      "READ", False, 2, 3),
    ("c12", "microglia prune synapses via complement",  ["microglia", "complement"],    "READ", False, 2, 4),
]
# gold dependency edges: (src derives-from dst)  == src depends on the more-foundational dst
GOLD_EDGES = {("c2", "c1"), ("c3", "c2"), ("c4", "c3"), ("c5", "c2"), ("c6", "c5"), ("c7", "c2"),
              ("c8", "c4"), ("c4", "c9"), ("c10", "c1"), ("c12", "c11"), ("c12", "c3"), ("c11", "c9")}


def _build_store():
    s = BeliefStore()
    for cid, stmt, ents, prov, anchor, nsrc, _ in CLAIMS:
        s.add_claim(Claim(cid, stmt, logit=(6.0 if anchor else 1.0),
                          provenance_state=prov, anchor=anchor, entities=ents))
        for k in range(nsrc):
            s.add_source(cid, f"{cid}_src{k}", f"grp_{cid}_{k}")
    return s


def _gold_label(a_id, b_id):
    if (a_id, b_id) in GOLD_EDGES:
        return "a->b"
    if (b_id, a_id) in GOLD_EDGES:
        return "b->a"
    return "none"


def _pred_label(res, a_id, b_id):
    if not res:
        return "none"
    if res["src"] == a_id and res["dst"] == b_id:
        return "a->b"
    if res["src"] == b_id and res["dst"] == a_id:
        return "b->a"
    return "none"


def _cohen_kappa(gold, pred):
    labels = ["a->b", "b->a", "none"]
    n = len(gold)
    po = sum(g == p for g, p in zip(gold, pred)) / n
    pe = sum((gold.count(l) / n) * (pred.count(l) / n) for l in labels)
    return (po - pe) / (1 - pe) if (1 - pe) else 0.0, po


def _spearman(xs, ys):
    def rank(v):
        order = sorted(range(len(v)), key=lambda i: v[i])
        r = [0] * len(v)
        for pos, i in enumerate(order):
            r[i] = pos
        return r
    rx, ry = rank(xs), rank(ys)
    n = len(xs)
    d2 = sum((a - b) ** 2 for a, b in zip(rx, ry))
    return 1 - 6 * d2 / (n * (n * n - 1)) if n > 1 else 0.0


def _eval(tagger, name):
    s = _build_store()
    pairs = candidate_pairs(s, max_pairs=99)
    gold, pred = [], []
    for a, b in pairs:
        gold.append(_gold_label(a.claim_id, b.claim_id))
        pred.append(_pred_label(tagger.tag(s, a, b), a.claim_id, b.claim_id))
    kappa, acc = _cohen_kappa(gold, pred)
    # directed-edge precision/recall (ignoring 'none' correct-rejections)
    tp = sum(g == p and g != "none" for g, p in zip(gold, pred))
    pred_pos = sum(p != "none" for p in pred)
    gold_pos = sum(g != "none" for g in gold)
    prec = tp / pred_pos if pred_pos else 0.0
    rec = tp / gold_pos if gold_pos else 0.0

    # load-bearing ranking vs gold foundational rank (only for claims the tagger connected)
    for a, b in pairs:
        r = tagger.tag(s, a, b)
        if r:
            try:
                s.add_edge(r["src"], r["dst"], r["relation"], r["confidence"])
            except Exception:
                pass
    lb = load_bearing(s)
    gold_rank = {cid: rk for cid, *_ , rk in [(c[0], c[-1]) for c in CLAIMS]}
    connected = [cid for cid in gold_rank if cid in lb]
    if len(connected) >= 3:
        # higher load_bearing should mean more foundational => lower gold rank number
        spear = _spearman([lb[c] for c in connected], [-gold_rank[c] for c in connected])
    else:
        spear = float("nan")
    print(f"\n[{name}]  pairs={len(pairs)}  accuracy={acc:.2f}  kappa={kappa:.2f}")
    print(f"  directed edges: precision={prec:.2f} recall={rec:.2f} (tp={tp}/pred={pred_pos}/gold={gold_pos})")
    print(f"  load_bearing vs gold-foundational Spearman={spear:.2f} (n_connected={len(connected)})")
    return {"tagger": name, "accuracy": round(acc, 3), "kappa": round(kappa, 3),
            "precision": round(prec, 3), "recall": round(rec, 3),
            "spearman_loadbearing": round(spear, 3) if spear == spear else None,
            "n_pairs": len(pairs)}


def main():
    out = [_eval(HeuristicDependencyTagger(), "heuristic (offline)")]
    if config.have_key():
        out.append(_eval(ClaudeDependencyTagger(), "claude (reasoner)"))
    else:
        print("\n(no ANTHROPIC_API_KEY — skipped the Claude tagger; heuristic is the offline floor)")
    verdict = ("edges are a useful CANDIDATE ranker" if out[-1]["kappa"] >= 0.4
               else "edges are WEAK -> keep human-in-the-loop (E6 not passed for autonomy)")
    print(f"\nVERDICT: {verdict}")
    res = {"results": out, "verdict": verdict}
    (Path(__file__).resolve().parent.parent / "results" / "e6_dependency.json").write_text(
        json.dumps(res, indent=2), encoding="utf-8")
    print("saved -> results/e6_dependency.json")


if __name__ == "__main__":
    main()
