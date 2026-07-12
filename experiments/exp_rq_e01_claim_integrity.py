"""RQ-E01a: bootstrap audit of the current Curie claim store (no model calls).

Compares today's accept-all path with two deterministic trust-boundary gates:
1. exact: valid schema + verbatim evidence span in the stored source text;
2. strict: exact + no unambiguous polarity mismatch between quote and stored sign.

The polarity lexicon is a diagnostic proxy, not biomedical ground truth. It can identify obvious
failures such as "exacerbate" stored as negative; it cannot validate nuanced scientific claims.
"""
from __future__ import annotations

import json
import math
import random
import re
import statistics
import unicodedata
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOURCES = ROOT / "personas" / "curie-3c33" / "sources"
OUT_JSON = ROOT / "results" / "rq_e01_claim_integrity.json"
OUT_PNG = ROOT / "results" / "rq_e01_claim_integrity.png"
SEEDS = 30
SAMPLE_CLAIMS = 500

POS = re.compile(r"\b(increas(?:e|es|ed|ing)|higher|raise[sd]?|promot(?:e|es|ed|ing)|"
                 r"exacerbat(?:e|es|ed|ing)|enhanc(?:e|es|ed|ing)|caus(?:e|es|ed|ing)|"
                 r"induc(?:e|es|ed|ing)|accelerat(?:e|es|ed|ing)|worsen(?:s|ed|ing)?)\b", re.I)
NEG = re.compile(r"\b(decreas(?:e|es|ed|ing)|lower|reduce[sd]?|reduction|inhibit(?:s|ed|ing)?|"
                 r"suppress(?:es|ed|ing)?|prevent(?:s|ed|ing)?|protect(?:s|ed|ing|ive)?|"
                 r"ameliorat(?:e|es|ed|ing)|attenuat(?:e|es|ed|ing)|impair(?:s|ed|ing)?)\b", re.I)
ZERO = re.compile(r"\b(no (?:effect|association|difference)|unchanged|not associated|did not change)\b", re.I)


def norm(text: str) -> str:
    return " ".join(unicodedata.normalize("NFKC", text or "").casefold().split())


def direction(text: str) -> str | None:
    if ZERO.search(text or ""):
        return "0"
    pos, neg = bool(POS.search(text or "")), bool(NEG.search(text or ""))
    if pos == neg:
        return None
    return "+" if pos else "-"


def load_claims() -> list[dict]:
    claims = []
    for path in SOURCES.glob("*/claims.jsonl"):
        clean_path = path.with_name("clean.md")
        if not clean_path.exists():
            continue
        clean = norm(clean_path.read_text(encoding="utf-8", errors="replace"))
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            try:
                claim = json.loads(line)
            except json.JSONDecodeError:
                claim = {"_parse_error": True}
            required = ("claim_id", "subject", "relation", "object", "effect_sign", "quote")
            schema = (not claim.get("_parse_error") and
                      all(isinstance(claim.get(k), str) and claim[k].strip() for k in required) and
                      claim.get("effect_sign") in {"+", "-", "0", "na"} and
                      isinstance(claim.get("confidence", 0.6), (int, float)) and
                      math.isfinite(float(claim.get("confidence", 0.6))) and
                      0 <= float(claim.get("confidence", 0.6)) <= 1)
            quote = norm(claim.get("quote", ""))
            quote_exact = bool(quote and quote in clean)
            qdir = direction(claim.get("quote", ""))
            mismatch = qdir is not None and claim.get("effect_sign") in {"+", "-", "0"} \
                and qdir != claim.get("effect_sign")
            claims.append({**claim, "source_path": str(path.parent.relative_to(ROOT)),
                           "schema_valid": schema, "quote_exact": quote_exact,
                           "quote_direction_proxy": qdir, "direction_mismatch_proxy": mismatch})
    return claims


def arm_metrics(sample: list[dict], arm: str) -> dict:
    if arm == "baseline":
        accepted = sample
    elif arm == "exact":
        accepted = [c for c in sample if c["schema_valid"] and c["quote_exact"]]
    else:
        accepted = [c for c in sample if c["schema_valid"] and c["quote_exact"]
                    and not c["direction_mismatch_proxy"]]
    checkable = [c for c in accepted if c["quote_direction_proxy"] is not None and
                 c.get("effect_sign") in {"+", "-", "0"}]
    return {
        "retention_rate": len(accepted) / max(1, len(sample)),
        "invalid_schema_admitted_rate": sum(not c["schema_valid"] for c in accepted) /
                                        max(1, len(accepted)),
        "nonverbatim_admitted_rate": sum(not c["quote_exact"] for c in accepted) /
                                     max(1, len(accepted)),
        "direction_mismatch_admitted_rate": sum(c["direction_mismatch_proxy"] for c in checkable) /
                                            max(1, len(checkable)),
        "accepted": len(accepted),
        "direction_checkable": len(checkable),
    }


def false_conflict_proxy(claims: list[dict]) -> tuple[int, int, list[dict]]:
    pairs = defaultdict(lambda: {"+": [], "-": []})
    for c in claims:
        sign = c.get("effect_sign")
        if sign in {"+", "-"}:
            key = (norm(c.get("subject", "")), norm(c.get("object", "")))
            pairs[key][sign].append(c)
    candidates, false_proxy, examples = 0, 0, []
    for (subject, obj), sides in pairs.items():
        if not sides["+"] or not sides["-"]:
            continue
        candidates += 1
        pos_dirs = {c["quote_direction_proxy"] for c in sides["+"] if c["quote_direction_proxy"]}
        neg_dirs = {c["quote_direction_proxy"] for c in sides["-"] if c["quote_direction_proxy"]}
        if pos_dirs & neg_dirs:
            false_proxy += 1
            if len(examples) < 20:
                examples.append({"subject": subject, "object": obj,
                                 "same_quote_direction": sorted(pos_dirs & neg_dirs),
                                 "positive": [{"claim_id": c.get("claim_id"), "quote": c.get("quote"),
                                               "proxy": c["quote_direction_proxy"]} for c in sides["+"][:2]],
                                 "negative": [{"claim_id": c.get("claim_id"), "quote": c.get("quote"),
                                               "proxy": c["quote_direction_proxy"]} for c in sides["-"][:2]]})
    return candidates, false_proxy, examples


def ci(rows: list[dict], arm: str, metric: str) -> dict:
    values = [r[arm][metric] for r in rows]
    mean = statistics.fmean(values)
    half = 1.96 * statistics.stdev(values) / math.sqrt(len(values)) if len(values) > 1 else 0
    return {"mean": mean, "ci95_half": half}


def chart(summary: dict) -> None:
    import matplotlib.pyplot as plt

    arms = ["baseline", "exact", "strict"]
    labels = ["current\naccept-all", "exact span", "exact +\ndirection check"]
    colors = ["#b24c3d", "#b58a3a", "#477a68"]
    fig, axes = plt.subplots(1, 2, figsize=(10, 4.2))
    for ax, metric, title in ((axes[0], "nonverbatim_admitted_rate", "Non-verbatim evidence admitted"),
                              (axes[1], "direction_mismatch_admitted_rate", "Obvious direction mismatches admitted")):
        means = [summary[a][metric]["mean"] for a in arms]
        errs = [summary[a][metric]["ci95_half"] for a in arms]
        ax.bar(labels, means, yerr=errs, color=colors, capsize=4)
        ax.set_ylim(0, max(0.05, max(means) * 1.2))
        ax.set_ylabel("rate")
        ax.set_title(title)
        ax.grid(axis="y", alpha=.18)
        for i, v in enumerate(means):
            ax.text(i, v + max(means + [0.01]) * .035, f"{v:.1%}", ha="center", fontsize=9)
    fig.suptitle("Persona RQ-E01a — 30 seeded Curie resamples (proxy audit)", fontweight="bold")
    fig.tight_layout()
    fig.savefig(OUT_PNG, dpi=180, bbox_inches="tight")


def main() -> None:
    claims = load_claims()
    if len(claims) < SAMPLE_CLAIMS:
        raise RuntimeError(f"need {SAMPLE_CLAIMS} claims, found {len(claims)}")
    rows = []
    for seed in range(SEEDS):
        rng = random.Random(seed)
        sample = rng.choices(claims, k=SAMPLE_CLAIMS)
        rows.append({"seed": seed, **{arm: arm_metrics(sample, arm)
                                      for arm in ("baseline", "exact", "strict")}})
    summary = {arm: {metric: ci(rows, arm, metric) for metric in (
        "retention_rate", "invalid_schema_admitted_rate", "nonverbatim_admitted_rate",
        "direction_mismatch_admitted_rate")} for arm in ("baseline", "exact", "strict")}
    candidates, false_proxy, examples = false_conflict_proxy(claims)
    mismatches = [{k: c.get(k) for k in ("claim_id", "source_path", "subject", "relation", "object",
                                          "effect_sign", "quote", "quote_direction_proxy")}
                  for c in claims if c["direction_mismatch_proxy"]][:40]
    result = {
        "experiment": "RQ-E01a claim integrity audit", "seeds": SEEDS,
        "sample_claims_per_seed": SAMPLE_CLAIMS, "total_claims": len(claims),
        "summary": summary, "seed_rows": rows,
        "candidate_conflicts": candidates, "false_conflict_proxy_count": false_proxy,
        "false_conflict_proxy_rate": false_proxy / max(1, candidates),
        "false_conflict_proxy_examples": examples, "direction_mismatch_examples": mismatches,
        "limitations": ["Polarity lexicon is a diagnostic proxy, not expert ground truth.",
                        "Bootstrap resamples stored claims; it does not test a new LLM extractor.",
                        "Normalized exact-span matching tolerates whitespace and Unicode normalization."],
        "verdict": "GO exact-span admission gate; keep enriched extraction and contradiction typing gated."
    }
    OUT_JSON.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    chart(summary)
    print(f"claims={len(claims)} candidate_conflicts={candidates}")
    print(f"false-conflict proxy={false_proxy}/{candidates} ({result['false_conflict_proxy_rate']:.1%})")
    for arm in ("baseline", "exact", "strict"):
        s = summary[arm]
        print(f"{arm:8} retain={s['retention_rate']['mean']:.3f} "
              f"nonverbatim={s['nonverbatim_admitted_rate']['mean']:.3f} "
              f"direction_mismatch={s['direction_mismatch_admitted_rate']['mean']:.3f}")
    print(f"wrote {OUT_JSON.relative_to(ROOT)} and {OUT_PNG.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
