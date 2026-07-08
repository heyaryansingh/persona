"""exp_e7_voi (E7) — is the engine's importance ranking grounded in / complementary to a real
external prior (Open Targets genetic evidence)?

VoI = load_bearing x uncertainty (experiment_value.py). The plan's E7 asks whether that ranking
is predictive rather than merely descriptive, with the Open Targets GENETIC-ASSOCIATION score as
the strong real-world prior for "which target matters".

Honest scope: we do NOT have experimental-OUTCOME data (which tested experiments actually paid
off), so E7 cannot promote VoI to "predicts payoff". What it CAN establish on real data is
whether the engine's internal signals (load_bearing, calibrated_p, VoI) are REDUNDANT with the
genetic prior or COMPLEMENTARY to it — i.e. whether the dependency graph adds information beyond
genetics. Method: 12 gene-disease claims with real OT genetic scores, a dependency graph over
them, then Spearman of each internal signal vs the OT prior.
Run: python experiments/exp_e7_voi.py
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from persona.store import BeliefStore, Claim                              # noqa: E402
from persona.engine.dependency import load_bearing                        # noqa: E402
from persona.engine.experiment_value import value_of_information          # noqa: E402
from persona.swarm.dependency_tagger import tag_dependencies, HeuristicDependencyTagger  # noqa: E402
from persona.ingest.opentargets import OpenTargetsClient                  # noqa: E402

PAIRS = [
    ("APOE", "Alzheimer disease"), ("LDLR", "familial hypercholesterolemia"),
    ("BRCA1", "breast carcinoma"), ("CFTR", "cystic fibrosis"),
    ("HTT", "Huntington disease"), ("PCSK9", "hypercholesterolemia"),
    ("IL23R", "inflammatory bowel disease"), ("HBB", "beta thalassemia"),
    ("LRRK2", "Parkinson disease"), ("SOD1", "amyotrophic lateral sclerosis"),
    ("TREM2", "Alzheimer disease"), ("SNCA", "Parkinson disease"),
]


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


def main():
    ot = OpenTargetsClient()
    try:
        genetic = {p: ot.associate(*p)["genetic"] for p in PAIRS}
    except Exception as e:
        print(f"SKIP: no network ({e})")
        return

    s = BeliefStore()
    ids = []
    for i, (g, d) in enumerate(PAIRS):
        cid = f"c{i}"
        ids.append(cid)
        # neutral, decoupled-from-OT belief so any correlation is STRUCTURAL, not planted:
        # uniform evidence -> calibrated_p driven by graph position, not by the genetic score.
        s.add_claim(Claim(cid, f"{g} associated with {d}", logit=0.8, entities=[g.lower(), d.lower()]))
        s.add_source(cid, f"{cid}_a", f"lab_{i}")
        s.add_source(cid, f"{cid}_b", f"lab_{i}_2")
    tag_dependencies(s, HeuristicDependencyTagger())    # dependency edges over shared diseases
    lb = load_bearing(s)

    rows = []
    for i, p in enumerate(PAIRS):
        cid = ids[i]
        rows.append({"pair": p, "genetic": genetic[p], "load_bearing": lb.get(cid, 0.0),
                     "calibrated_p": s.get_claim(cid).calibrated_p,
                     "voi": value_of_information(s, cid, lb)})
    print(f"n={len(rows)}  OT genetic scores resolved: {sum(g > 0 for g in genetic.values())}/{len(PAIRS)}")
    print(f"dependency edges among these claims: {sum(len(s.edges_from(cid)) for cid in ids)}  "
          f"(load_bearing non-empty: {bool(lb)})")

    # E7 is ILL-POSED with a flat set of gene-disease associations: they are siblings, not a
    # derives-from hierarchy, so the dependency graph has no structure -> load_bearing is empty and
    # VoI is 0 for all. VoI operates on the INFERENTIAL-dependency graph of MECHANISTIC claims that
    # build on each other; the OT genetic score ranks FLAT gene-disease associations. Different
    # objects -> the correlation would be an artifact, so we DON'T report one.
    if not lb:
        verdict = ("ILL-POSED / DESCRIPTIVE: a flat set of gene-disease associations has no "
                   "inferential hierarchy, so load_bearing is empty and VoI is 0 — the VoI-vs-"
                   "genetic-prior comparison conflates two different objects (structural centrality "
                   "vs evidence strength). VoI is validated STRUCTURALLY by E6 (load_bearing "
                   "Spearman 0.38-0.50 vs gold foundational rank), not by the OT prior, and cannot "
                   "be promoted to 'predicts experimental payoff' without outcome data. Honest "
                   "reversal: E7 as originally framed is not a valid test.")
    else:
        gen = [r["genetic"] for r in rows]
        rho = _spearman([r["load_bearing"] for r in rows], gen)
        verdict = f"load_bearing vs OT genetic Spearman={rho:+.2f} (see rows)."
    print(f"\nVERDICT: {verdict}")
    (Path(__file__).resolve().parent.parent / "results" / "e7_voi.json").write_text(
        json.dumps({"rows": [{**r, "pair": list(r["pair"])} for r in rows], "verdict": verdict},
                   indent=2), encoding="utf-8")
    print("saved -> results/e7_voi.json")


if __name__ == "__main__":
    main()
