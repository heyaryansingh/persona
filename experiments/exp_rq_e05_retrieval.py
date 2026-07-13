"""RQ-E05: real-retrieval evaluation harness — SCAFFOLD (dry-run, $0 by default).

WHAT THIS IS. The end-to-end shape of the RQ-E05 answer-level retrieval benchmark:
iterative retrieval -> reranking -> answer+citation -> exact-span verification, scored on
correctness, citation precision/recall, abstention, primariness, cost, and latency. The full
benchmark evaluates a real system against a HUMAN-LABELED question set (LitQA2 / ScholarQA /
AstaBench + Persona questions). This file wires that harness and proves it runs end to end.

WHAT THIS IS NOT (yet). It makes NO deployment claim and produces NO scientific verdict. The
reranker, the answer+citation model, the exact-span verifier, and the correctness grader are all
PAID model stages — every one is GATED behind an explicit human budget authorization + a live
model probe (`PERSONA_E05_LIVE=1` and a real API key). With the gate closed (the default) the
harness runs its deterministic, $0 stages only: it exercises retrieval, citation, abstention,
primariness, and latency over a small hand-authored WIRING FIXTURE, marks correctness as `gated`,
and records `paid_calls: 0`, `cost_usd: 0.0`.

The bundled fixture is test scaffolding (labeled non-scientific), not an evaluation gold set — it
exists only to drive the pipeline. Real gold is loaded via `--questions <path>` and must be human
authored; per the frozen contract, labels are NEVER synthesized.

Experiment-first (AGENTS.md §2): stochastic aggregates report mean ± 95% CI over >=20 bootstrap
seeds. Run:  python experiments/exp_rq_e05_retrieval.py            # dry-run, $0
             python experiments/exp_rq_e05_retrieval.py --self-check
Live (gated, spends money — requires S0 budget greenlight):
             PERSONA_E05_LIVE=1 python experiments/exp_rq_e05_retrieval.py --live
"""
from __future__ import annotations

import argparse
import json
import math
import os
import random
import re
import time
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
OUT_JSON = ROOT / "results" / "rq_e05_retrieval.json"
OUT_PNG = ROOT / "results" / "rq_e05_retrieval.png"

DEFAULT_SEEDS = 200          # bootstrap resamples (>=20 required); pure-numpy, instant, $0
MIN_SEEDS = 20
TOP_K = 5
ABSTAIN_SCORE = 0.15         # dry-run proxy: abstain when best retrieval score is below this


# --------------------------------------------------------------------------------------------------
# data model
# --------------------------------------------------------------------------------------------------
@dataclass
class Passage:
    doc_id: str
    text: str
    primary: bool            # primary literature (True) vs review/secondary/blog (False)


@dataclass
class QAItem:
    qid: str
    question: str
    gold_answer: str
    gold_doc_ids: list[str]          # citation gold (empty when should_abstain)
    should_abstain: bool             # gold: is this UNANSWERABLE from the pool?
    pool: list[Passage]              # candidate passages (gold + distractors), the retrieval corpus


# --------------------------------------------------------------------------------------------------
# retrieval — deterministic, offline, $0 (BM25-lite over each item's candidate pool)
# --------------------------------------------------------------------------------------------------
_WORD = re.compile(r"[a-z0-9]+")
# Drop function words so shared stopwords ("the", "of", "is") can't fake retrieval confidence and
# defeat the abstention decision (a real unanswerable query must score ~0, not ~1 on "the").
_STOP = frozenset("a an the of to in on at for and or is are was were be been being this that these "
                  "those it its as by with from into out up down over under does do did there their "
                  "what which who whom how when where why between within about than then so".split())


def tokenize(text: str) -> list[str]:
    return [w for w in _WORD.findall((text or "").lower()) if w not in _STOP]


def bm25_scores(query: str, pool: list[Passage], k1: float = 1.5, b: float = 0.75) -> dict[str, float]:
    """Classic BM25 over the pool. Deterministic; no model, no network."""
    docs = {p.doc_id: tokenize(p.text) for p in pool}
    n = len(docs) or 1
    avgdl = (sum(len(t) for t in docs.values()) / n) or 1.0
    df: dict[str, int] = {}
    for toks in docs.values():
        for term in set(toks):
            df[term] = df.get(term, 0) + 1
    q_terms = set(tokenize(query))
    scores: dict[str, float] = {}
    for doc_id, toks in docs.items():
        dl = len(toks) or 1
        tf: dict[str, int] = {}
        for term in toks:
            tf[term] = tf.get(term, 0) + 1
        score = 0.0
        for term in q_terms:
            if term not in tf:
                continue
            idf = math.log(1 + (n - df[term] + 0.5) / (df[term] + 0.5))
            score += idf * (tf[term] * (k1 + 1)) / (tf[term] + k1 * (1 - b + b * dl / avgdl))
        scores[doc_id] = score
    return scores


def retrieve(query: str, pool: list[Passage], k: int = TOP_K) -> list[tuple[str, float]]:
    """Return the top-k (doc_id, RAW BM25 score) sorted desc. Raw (not normalized) so the abstention
    decision can threshold on absolute match strength — a query with no real overlap scores ~0."""
    scores = bm25_scores(query, pool)
    ranked = sorted(scores.items(), key=lambda kv: (-kv[1], kv[0]))          # tie-break by doc_id
    return [(doc_id, score) for doc_id, score in ranked[:k]]


# --------------------------------------------------------------------------------------------------
# PAID stages — GATED. Every one raises unless an explicit budget greenlight + live probe is set.
# --------------------------------------------------------------------------------------------------
class PaidStageGated(RuntimeError):
    pass


def require_live(stage: str) -> None:
    """Refuse to spend without an explicit human budget authorization AND a live model probe.
    (ORCHESTRATION: paid model calls require human budget authorization + a live model probe.)"""
    if os.environ.get("PERSONA_E05_LIVE") != "1":
        raise PaidStageGated(
            f"{stage}: PAID model stage is GATED. Set PERSONA_E05_LIVE=1 only after S0 posts a "
            f"budget greenlight, then pass a live model-name/cost probe. Refusing to spend.")
    try:
        from persona import config
    except Exception as exc:                                                  # pragma: no cover
        raise PaidStageGated(f"{stage}: cannot import config for model probe: {exc}")
    if not config.have_key():
        raise PaidStageGated(f"{stage}: no ANTHROPIC_API_KEY — live model probe failed. Refusing to spend.")
    # NOTE: even with a key, callers must FIRST probe that config.MODEL_WORKER exists and price it.
    # That probe (and the actual model calls) are intentionally not implemented in the scaffold.
    raise NotImplementedError(
        f"{stage}: live path not implemented in the scaffold — wire the real model call here behind "
        f"a priced, human-authorized budget once S0 greenlights RQ-E05 execution.")


def rerank(query: str, ranked: list[tuple[str, float]], pool: list[Passage], *, live: bool):
    if live:
        require_live("rerank")                     # paid cross-encoder / LLM reranker
    return ranked                                  # dry-run: identity passthrough (no reorder)


def answer_and_cite(item: QAItem, ranked: list[tuple[str, float]], *, live: bool) -> dict:
    """Return {answer, cited_doc_ids, abstained}. Dry-run cannot produce a real answer, so it
    exercises only the *decision wiring*: abstain on low retrieval confidence; otherwise 'cite'
    the top-k retrieved docs. Answer text + correctness are gated to the live grader."""
    if live:
        require_live("answer_and_cite")            # paid answer synthesis with citations
    best = ranked[0][1] if ranked else 0.0         # RAW top BM25 score = match strength
    abstained = best < ABSTAIN_SCORE
    # cite only docs that actually matched a query term (raw score > 0), not every top-k distractor.
    cited = [] if abstained else [doc_id for doc_id, score in ranked if score > 0.0]
    return {"answer": None, "cited_doc_ids": cited, "abstained": abstained}


def verify_spans(item: QAItem, result: dict, *, live: bool) -> dict:
    """Exact-span verification: every citation must be a verbatim span in its source. Dry-run
    checks only that cited doc_ids resolve to real passages in the pool (structural precondition
    for the real verbatim check)."""
    if live:
        require_live("verify_spans")               # paid exact-span verifier
    pool_ids = {p.doc_id for p in item.pool}
    resolvable = [d for d in result["cited_doc_ids"] if d in pool_ids]
    return {"citations_resolvable": len(resolvable) == len(result["cited_doc_ids"]),
            "resolved": len(resolvable)}


def grade_correctness(item: QAItem, result: dict, *, live: bool):
    if live:
        require_live("grade_correctness")          # paid LLM-as-judge / exact-match grader
    return None                                    # dry-run: correctness is GATED, reported as None


# --------------------------------------------------------------------------------------------------
# metrics
# --------------------------------------------------------------------------------------------------
def _prf(pred: set, gold: set) -> tuple[float, float, float]:
    if not pred and not gold:
        return 1.0, 1.0, 1.0
    tp = len(pred & gold)
    precision = tp / len(pred) if pred else 0.0
    recall = tp / len(gold) if gold else (1.0 if not pred else 0.0)
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) else 0.0
    return precision, recall, f1


def eval_item(item: QAItem, *, live: bool) -> dict:
    t0 = time.perf_counter()
    ranked = retrieve(item.question, item.pool, TOP_K)
    ranked = rerank(item.question, ranked, item.pool, live=live)
    result = answer_and_cite(item, ranked, live=live)
    verified = verify_spans(item, result, live=live)
    correct = grade_correctness(item, result, live=live)
    latency_ms = (time.perf_counter() - t0) * 1000.0

    topk_ids = {doc_id for doc_id, _ in ranked}
    gold_ids = set(item.gold_doc_ids)
    retr_recall = (len(topk_ids & gold_ids) / len(gold_ids)) if gold_ids else None
    cite_p, cite_r, cite_f1 = _prf(set(result["cited_doc_ids"]), gold_ids)
    prim = ([p.primary for p in item.pool if p.doc_id in set(result["cited_doc_ids"])])
    primariness = (sum(prim) / len(prim)) if prim else None
    abstain_correct = (result["abstained"] == item.should_abstain)
    return {
        "qid": item.qid,
        "retrieval_recall_at_k": retr_recall,
        "citation_precision": cite_p, "citation_recall": cite_r, "citation_f1": cite_f1,
        "abstained": result["abstained"], "abstain_correct": abstain_correct,
        "primariness": primariness,
        "citations_resolvable": verified["citations_resolvable"],
        "correctness": correct,                       # None => gated (dry-run)
        "latency_ms": latency_ms, "cost_usd": 0.0,
    }


def _mean_ci(values: list[float], seeds: int, base_seed: int) -> dict | None:
    """Bootstrap mean and 95% CI over `seeds` resamples of the per-item values."""
    vals = [v for v in values if v is not None]
    if not vals:
        return None
    arr = np.asarray(vals, dtype=float)
    means = np.empty(seeds)
    for s in range(seeds):
        rng = np.random.default_rng(base_seed + s)
        means[s] = arr[rng.integers(0, len(arr), len(arr))].mean()
    return {"mean": float(arr.mean()), "ci95_lo": float(np.percentile(means, 2.5)),
            "ci95_hi": float(np.percentile(means, 97.5)), "n": len(arr)}


def aggregate(per_item: list[dict], seeds: int, base_seed: int) -> dict:
    numeric = ["retrieval_recall_at_k", "citation_precision", "citation_recall", "citation_f1",
               "primariness", "latency_ms"]
    agg = {m: _mean_ci([r[m] for r in per_item], seeds, base_seed) for m in numeric}
    agg["abstention_accuracy"] = _mean_ci([1.0 if r["abstain_correct"] else 0.0 for r in per_item],
                                          seeds, base_seed)
    agg["citations_resolvable_rate"] = _mean_ci(
        [1.0 if r["citations_resolvable"] else 0.0 for r in per_item], seeds, base_seed)
    graded = [r["correctness"] for r in per_item if r["correctness"] is not None]
    agg["correctness"] = _mean_ci(graded, seeds, base_seed) if graded else "gated"
    return agg


# --------------------------------------------------------------------------------------------------
# wiring fixture — hand-authored, NON-SCIENTIFIC scaffolding (drives the pipeline only)
# --------------------------------------------------------------------------------------------------
def fixture_items() -> list[QAItem]:
    return [
        QAItem(
            qid="fx1",
            question="Does APOE4 increase Alzheimer's disease risk?",
            gold_answer="APOE4 is associated with increased Alzheimer's disease risk.",
            gold_doc_ids=["apoe_primary"],
            should_abstain=False,
            pool=[
                Passage("apoe_primary", "In a cohort study the APOE4 allele was associated with a "
                        "markedly increased risk of late-onset Alzheimer disease.", True),
                Passage("apoe_review", "Reviews summarise that APOE genotype influences Alzheimer risk.", False),
                Passage("distractor_bp", "Sodium intake was associated with higher blood pressure.", True),
            ],
        ),
        QAItem(
            qid="fx2",
            question="Is metformin associated with reduced cancer incidence?",
            gold_answer="Metformin use is associated with reduced cancer incidence in diabetics.",
            gold_doc_ids=["metformin_primary"],
            should_abstain=False,
            pool=[
                Passage("metformin_primary", "Among diabetic patients, metformin use was associated "
                        "with a reduced incidence of several cancers.", True),
                Passage("distractor_stat", "Statin therapy lowered LDL cholesterol in the trial.", True),
                Passage("distractor_diet", "A Mediterranean diet improved cardiovascular outcomes.", True),
            ],
        ),
        QAItem(
            qid="fx3",
            question="What is the capital of the fictional country of Zubrowka?",
            gold_answer="",                       # UNANSWERABLE from the pool -> should abstain
            gold_doc_ids=[],
            should_abstain=True,
            pool=[
                Passage("distractor_a", "The mitochondrion is the powerhouse of the cell.", True),
                Passage("distractor_b", "Photosynthesis converts light energy into chemical energy.", True),
            ],
        ),
        QAItem(
            qid="fx4",
            question="Does vitamin D supplementation reduce respiratory infections?",
            gold_answer="Vitamin D supplementation modestly reduced acute respiratory infections.",
            gold_doc_ids=["vitd_primary"],
            should_abstain=False,
            pool=[
                Passage("vitd_primary", "A randomized trial found vitamin D supplementation reduced "
                        "the rate of acute respiratory tract infections.", True),
                Passage("vitd_blog", "A wellness blog claims vitamin D cures every infection.", False),
                Passage("distractor_sleep", "Sleep deprivation impaired working memory in students.", True),
            ],
        ),
        QAItem(
            qid="fx5",
            question="Is there a causal link between smoking and lung cancer?",
            gold_answer="Smoking causally increases lung cancer risk.",
            gold_doc_ids=["smoke_primary", "smoke_cohort"],
            should_abstain=False,
            pool=[
                Passage("smoke_primary", "Case-control studies established that cigarette smoking is a "
                        "primary cause of lung cancer.", True),
                Passage("smoke_cohort", "A large cohort confirmed a strong dose-response between "
                        "smoking and lung cancer incidence.", True),
                Passage("distractor_uv", "UV exposure is a risk factor for melanoma.", True),
            ],
        ),
    ]


def load_items(questions_path: str | None) -> tuple[list[QAItem], str]:
    if questions_path:
        raw = json.loads(Path(questions_path).read_text(encoding="utf-8"))
        items = [QAItem(qid=d["qid"], question=d["question"], gold_answer=d.get("gold_answer", ""),
                        gold_doc_ids=list(d.get("gold_doc_ids", [])),
                        should_abstain=bool(d.get("should_abstain", False)),
                        pool=[Passage(**p) for p in d["pool"]]) for d in raw]
        return items, f"human-labeled:{Path(questions_path).name}"
    return fixture_items(), "wiring-fixture (NON-SCIENTIFIC scaffold)"


# --------------------------------------------------------------------------------------------------
# run
# --------------------------------------------------------------------------------------------------
def run(*, questions_path: str | None, seeds: int, base_seed: int, live: bool) -> dict:
    seeds = max(int(seeds), MIN_SEEDS)
    random.seed(base_seed)
    np.random.seed(base_seed)
    items, source = load_items(questions_path)
    per_item = [eval_item(it, live=live) for it in items]
    agg = aggregate(per_item, seeds, base_seed)
    return {
        "experiment": "RQ-E05 real-retrieval evaluation",
        "status": "SCAFFOLD — dry-run, no deployment claim, no scientific verdict",
        "mode": "live" if live else "dry-run",
        "gate": "paid stages require PERSONA_E05_LIVE=1 + human budget greenlight + live model probe",
        "paid_calls": 0, "cost_usd": 0.0,
        "question_source": source, "n_items": len(items),
        "seeds": seeds, "base_seed": base_seed, "top_k": TOP_K,
        "metrics": agg, "per_item": per_item,
        "caveats": [
            "Correctness, reranking, exact-span verify, and answer synthesis are GATED paid stages "
            "(not executed in dry-run).",
            "The bundled fixture is test scaffolding, not an evaluation gold set; real runs load a "
            "human-labeled question set via --questions.",
            "No hybrid/dense/deployment claim is made; this file only proves the harness runs.",
        ],
    }


def write_outputs(result: dict) -> None:
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(result, indent=2), encoding="utf-8")
    try:                                            # PNG is best-effort; JSON is the immutable record
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        metrics = result["metrics"]
        bars = [(k, v["mean"], v["mean"] - v["ci95_lo"], v["ci95_hi"] - v["mean"])
                for k, v in metrics.items()
                if isinstance(v, dict) and k != "latency_ms" and v is not None]
        if bars:
            names = [b[0] for b in bars]
            means = [b[1] for b in bars]
            lo = [b[2] for b in bars]
            hi = [b[3] for b in bars]
            fig, ax = plt.subplots(figsize=(10, 4.5))
            ax.bar(range(len(names)), means, yerr=[lo, hi], capsize=4, color="#4a6fa5")
            ax.set_xticks(range(len(names)))
            ax.set_xticklabels(names, rotation=30, ha="right", fontsize=8)
            ax.set_ylim(0, 1.05)
            ax.set_title(f"RQ-E05 SCAFFOLD (dry-run, $0) — {result['question_source']} · "
                         f"{result['seeds']} seeds", fontsize=10)
            fig.tight_layout()
            fig.savefig(OUT_PNG, dpi=110)
            plt.close(fig)
    except Exception as exc:                        # pragma: no cover
        print(f"[warn] PNG skipped: {exc}")


def self_check() -> None:
    """Assert-based self-check — fails loudly if the harness wiring breaks. $0, no model calls."""
    r = run(questions_path=None, seeds=MIN_SEEDS, base_seed=0, live=False)
    assert r["paid_calls"] == 0 and r["cost_usd"] == 0.0, "dry-run must not spend"
    assert r["seeds"] >= MIN_SEEDS, "must run >=20 bootstrap seeds"
    assert r["metrics"]["correctness"] == "gated", "correctness must be gated in dry-run"
    # abstention wiring: fx3 is unanswerable and must abstain; the answerable items must not.
    by_id = {r_["qid"]: r_ for r_ in r["per_item"]}
    assert by_id["fx3"]["abstained"] is True, "unanswerable item must abstain"
    assert all(by_id[q]["abstained"] is False for q in ("fx1", "fx2", "fx4", "fx5")), \
        "answerable items must not abstain"
    assert all(r_["abstain_correct"] for r_ in r["per_item"]), "abstention gold must match"
    # retrieval must surface the gold citation for a clearly-answerable item.
    assert by_id["fx1"]["retrieval_recall_at_k"] == 1.0, "gold doc must be retrieved for fx1"
    # every CI is well-formed: lo <= mean <= hi.
    for k, v in r["metrics"].items():
        if isinstance(v, dict):
            assert v["ci95_lo"] <= v["mean"] <= v["ci95_hi"] + 1e-9, f"bad CI for {k}"
    # the gate genuinely refuses to spend without the env greenlight.
    os.environ.pop("PERSONA_E05_LIVE", None)
    try:
        require_live("test"); raised = False
    except PaidStageGated:
        raised = True
    assert raised, "paid stage must be gated when PERSONA_E05_LIVE is unset"
    print("SELF-CHECK OK — harness runs $0, >=20 seeds, correctness gated, abstention wired, gate holds.")


def main() -> None:
    ap = argparse.ArgumentParser(description="RQ-E05 real-retrieval evaluation harness (scaffold).")
    ap.add_argument("--questions", default=None, help="path to a human-labeled question set (JSON)")
    ap.add_argument("--seeds", type=int, default=DEFAULT_SEEDS, help=f"bootstrap seeds (>= {MIN_SEEDS})")
    ap.add_argument("--seed", type=int, default=0, help="base seed")
    ap.add_argument("--live", action="store_true",
                    help="attempt the GATED paid stages (refuses unless PERSONA_E05_LIVE=1 + key)")
    ap.add_argument("--self-check", action="store_true", help="run the assert-based self-check and exit")
    args = ap.parse_args()
    if args.self_check:
        self_check()
        return
    result = run(questions_path=args.questions, seeds=args.seeds, base_seed=args.seed, live=args.live)
    write_outputs(result)
    m = result["metrics"]
    print(f"RQ-E05 SCAFFOLD [{result['mode']}] · {result['question_source']} · "
          f"{result['n_items']} items · {result['seeds']} seeds · ${result['cost_usd']}")
    for key in ("retrieval_recall_at_k", "citation_f1", "abstention_accuracy", "primariness"):
        v = m.get(key)
        if isinstance(v, dict):
            print(f"  {key:24s} {v['mean']:.3f}  [{v['ci95_lo']:.3f}, {v['ci95_hi']:.3f}]  (n={v['n']})")
    print(f"  correctness              {m['correctness']}")
    print(f"wrote {OUT_JSON.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
