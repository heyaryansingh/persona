"""exp_reanalysis_bands — validate the Open Targets score bands used by the first-pass
reanalysis tester (persona/loops/reanalysis.py _STRONG / _ANY).

Hypothesis: Open Targets' genetic_association score separates ESTABLISHED gene-disease links
from UNRELATED gene-disease pairs; a threshold exists that classifies the two sets well.
Method: 12 textbook-true pairs vs 12 unrelated pairs (same genes/diseases, scrambled), pull
real scores, sweep a threshold on each of {overall, genetic}, report the best F1 + separation.

Not seed-based: Open Targets scores are deterministic external data, so validity comes from
labeled-pair separation (n=24), not seed variance. Reruns are byte-identical (cached).
Run: python experiments/exp_reanalysis_bands.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from persona.ingest.opentargets import OpenTargetsClient   # noqa: E402

POS = [
    ("APOE", "Alzheimer disease"), ("LDLR", "familial hypercholesterolemia"),
    ("BRCA1", "breast carcinoma"), ("CFTR", "cystic fibrosis"),
    ("HTT", "Huntington disease"), ("PCSK9", "hypercholesterolemia"),
    ("IL23R", "inflammatory bowel disease"), ("HBB", "beta thalassemia"),
    ("LRRK2", "Parkinson disease"), ("SOD1", "amyotrophic lateral sclerosis"),
    ("MYH7", "hypertrophic cardiomyopathy"), ("TNF", "rheumatoid arthritis"),
]
NEG = [
    ("CFTR", "Alzheimer disease"), ("HBB", "Parkinson disease"),
    ("BRCA1", "cystic fibrosis"), ("HTT", "rheumatoid arthritis"),
    ("SOD1", "breast carcinoma"), ("MYH7", "inflammatory bowel disease"),
    ("LDLR", "Huntington disease"), ("IL23R", "hypertrophic cardiomyopathy"),
    ("LRRK2", "beta thalassemia"), ("PCSK9", "amyotrophic lateral sclerosis"),
    ("SOD1", "cystic fibrosis"), ("MYH7", "Huntington disease"),
]


def _f1(scores_pos, scores_neg, thr):
    tp = sum(s >= thr for s in scores_pos)
    fp = sum(s >= thr for s in scores_neg)
    fn = len(scores_pos) - tp
    prec = tp / (tp + fp) if (tp + fp) else 0.0
    rec = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = 2 * prec * rec / (prec + rec) if (prec + rec) else 0.0
    return prec, rec, f1


def _sweep(pos, neg, label):
    best = (0.0, 0.0, 0.0, 0.0)
    for thr in [i / 100 for i in range(1, 100)]:
        p, r, f = _f1(pos, neg, thr)
        if f > best[3]:
            best = (thr, p, r, f)
    lo_pos, hi_neg = min(pos), max(neg)
    print(f"  [{label}] pos mean={sum(pos)/len(pos):.3f} min={lo_pos:.3f} | "
          f"neg mean={sum(neg)/len(neg):.3f} max={hi_neg:.3f}")
    print(f"  [{label}] best thr={best[0]:.2f}  precision={best[1]:.2f} recall={best[2]:.2f} "
          f"F1={best[3]:.2f}")
    return best


def main():
    c = OpenTargetsClient()
    try:
        pos = [c.associate(a, b) for a, b in POS]
        neg = [c.associate(a, b) for a, b in NEG]
    except Exception as e:
        print(f"SKIP: no network ({e})")
        return
    unresolved = [p for p in POS if not c.associate(*p)["found"]]
    if unresolved:
        print(f"note: {len(unresolved)} positive pair(s) did not resolve: {unresolved}")
    pg = [r["genetic"] for r in pos]; ng = [r["genetic"] for r in neg]
    po = [r["overall"] for r in pos]; no = [r["overall"] for r in neg]
    print(f"n_pos={len(pos)} n_neg={len(neg)}")
    print("GENETIC_ASSOCIATION datatype:")
    bg = _sweep(pg, ng, "genetic")
    print("OVERALL association score:")
    bo = _sweep(po, no, "overall")
    print()
    print(f"VERDICT: genetic F1={bg[3]:.2f}@thr={bg[0]:.2f}  vs  overall F1={bo[3]:.2f}@thr={bo[0]:.2f}")
    print("The reanalysis bands should track whichever discriminates better; current code uses "
          "genetic>=0.10 OR overall>=0.30.")


if __name__ == "__main__":
    main()
