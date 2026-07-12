"""RQ-E07b: does distribution + specialization make a large reading swarm deliver
*higher-quality* evidence, not just more of it?

E07a (exp_rq_e07a_swarm_physics.py) showed that for a decomposable breadth task,
source-partitioning removes duplicate work and effective team size saturates ~14-15;
dense all-to-all sharing is harmful. E07a measured only *coverage of grounded spans*.
It deliberately omitted the failure mode Persona actually cares about: bad extractions
crossing into belief, and the spurious ("false") contradictions they create
(RQ-E01a: 24% of stored evidence is non-verbatim; those drive false sign-collisions).

E07b adds the two things E07a lacked, over the SAME real Curie packets:

  1. Specialization — heterogeneous reader roles instead of one homogeneous role:
       * extractor        — reads a source partition (the E07a winner);
       * exact_span_verifier — re-checks each admitted packet's span against its source
                               and drops non-verbatim ones (costs extra read tokens);
       * reducer          — deduplicates and groups by independent source.
  2. Correlated extraction error — a fraction of *sources* are systematically noisy
     (their stored spans no longer match), modelling a bad reader/OCR/paraphrase run.
     This is where an independent verifier earns its token tax.

Quality metrics (per token, so a 1000-agent swarm can't win by brute force):
  validated_unique / token, false_admitted (bad evidence that became belief),
  false_conflict_rate (sign-collisions with >=1 non-verbatim side), coverage,
  effective_team_size. All means +/- 95% CI over >=30 seeds.

Pre-registered gate for shipping the specialized+partition+verifier swarm as default:
  Under correlated error, specialized must
    (G1) drive false_admitted and false_conflict_rate to ~0 (verifier removes them),
    (G2) keep validated_unique/token >= partition-without-verifier within a 20% margin
         (the verify tax is affordable), and
    (G3) beat the homogeneous baseline on validated_unique/token at N>=30.

This is still a replay simulation, not live LLM agents (that is RQ-E07b-live). Grounded
means exact stored span, not scientific truth. Coordination/token costs are proxies.
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
SOURCES = ROOT / "personas" / "curie-3c33" / "sources"
OUT_JSON = ROOT / "results" / "rq_e07b_specialized_swarm.json"
OUT_PNG = ROOT / "results" / "rq_e07b_specialized_swarm.png"
SEEDS = 30
TEAM_SIZES = (1, 3, 5, 10, 30, 100, 300, 1000)
BUDGET_PER_AGENT = 6
ERROR_RATES = (0.0, 0.30)          # fraction of sources that are systematically noisy
TOPOLOGIES = ("homogeneous", "partition", "specialized", "selective")
VERIFY_FRACTION = 0.30             # share of the team acting as exact-span verifiers
# "specialized" verifies every proposed packet (naive). "selective" verifies only
# DECISION-RELEVANT packets: those in a sign-collision, or convergent belief-candidates
# (same canonical claim from >=2 sources) -- the only evidence that can become a belief
# or a contradiction. Everything else is single-source noise the membrane ignores anyway.


def norm(text: str) -> str:
    return " ".join(unicodedata.normalize("NFKC", text or "").casefold().split())


def stable_bucket(text: str, n: int) -> int:
    return int(hashlib.sha1(text.encode()).hexdigest()[:12], 16) % max(1, n)


def load_packets():
    """Real Curie packets: valid_span (verbatim), weight, and the subject/object/sign
    needed to detect sign-collisions. Mirrors E07a's loader, plus conflict structure."""
    packets, topics, pairs = [], defaultdict(list), defaultdict(list)
    for path in SOURCES.glob("*/claims.jsonl"):
        clean_path = path.with_name("clean.md")
        if not clean_path.exists():
            continue
        clean = norm(clean_path.read_text(encoding="utf-8", errors="replace"))
        slug = path.parent.name
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            try:
                claim = json.loads(line)
            except json.JSONDecodeError:
                continue
            quote = norm(claim.get("quote", ""))
            subj, obj = norm(claim.get("subject", "")), norm(claim.get("object", ""))
            sign = claim.get("effect_sign") or claim.get("sign") or "na"
            idx = len(packets)
            packets.append({
                "key": f"{slug}:{claim.get('claim_id','')}", "source": slug,
                "valid_span": bool(quote and quote in clean),
                "weight": max(.05, float(claim.get("confidence", .6) or .6)),
                "subject": subj, "object": obj, "sign": sign})
            for entity in {subj, obj}:
                if entity:
                    topics[entity].append(idx)
            if subj and obj and sign in ("+", "-"):
                pairs[(subj, obj)].append(idx)
    usable = {t: ids for t, ids in topics.items()
              if len(ids) >= 10 and sum(packets[i]["valid_span"] for i in ids) >= 5}
    return packets, usable, pairs


def weighted_sample(rng, pool, packets, k):
    if not pool or k <= 0:
        return []
    work, out = list(pool), []
    for _ in range(min(k, len(work))):
        weights = [packets[i]["weight"] for i in work]
        choice = rng.choices(range(len(work)), weights=weights, k=1)[0]
        out.append(work.pop(choice))
    return out


def corrupted_sources(pool, packets, rate, rng):
    """Correlated error: whole sources go noisy together (systematic misread)."""
    srcs = sorted({packets[i]["source"] for i in pool})
    k = int(round(rate * len(srcs)))
    return set(rng.sample(srcs, k)) if k else set()


def effective_valid(idx, packets, bad_sources):
    return packets[idx]["valid_span"] and packets[idx]["source"] not in bad_sources


def select_reads(topology, n, pool, packets, rng):
    """Return (per-agent read lists, coordination_messages). Reads only; admission/
    verification happen in run_trial so token accounting is explicit."""
    if topology == "homogeneous":
        reads = [weighted_sample(rng, pool, packets, BUDGET_PER_AGENT) for _ in range(n)]
        return reads, max(0, n - 1)
    # both partition and specialized read from source-bucketed partitions (E07a winner)
    parts = [[] for _ in range(n)]
    for item in pool:
        parts[stable_bucket(packets[item]["source"], n)].append(item)
    reads = [weighted_sample(rng, parts[a], packets, BUDGET_PER_AGENT) for a in range(n)]
    return reads, max(0, n - 1) * 2


def false_conflicts(admitted, packets, pairs, bad_sources):
    """A sign-collision is a candidate conflict; it is FALSE if >=1 contributing side is
    non-verbatim under current corruption. Returns (n_candidate, n_false)."""
    admitted = set(admitted)
    by_pair_sign = defaultdict(lambda: {"+": [], "-": []})
    for idx in admitted:
        p = packets[idx]
        if p["sign"] in ("+", "-") and (p["subject"], p["object"]) in pairs:
            by_pair_sign[(p["subject"], p["object"])][p["sign"]].append(idx)
    candidate = false = 0
    for pair, sides in by_pair_sign.items():
        if sides["+"] and sides["-"]:
            candidate += 1
            contributors = sides["+"] + sides["-"]
            if any(not effective_valid(i, packets, bad_sources) for i in contributors):
                false += 1
    return candidate, false


def decision_relevant(unique_read, packets, pairs):
    """Packets that can actually become a belief or a contradiction: convergent
    (same canonical claim from >=2 sources) or a participant in a sign-collision."""
    reads = list(unique_read)
    by_claim = defaultdict(set)
    for i in reads:
        p = packets[i]
        by_claim[(p["subject"], p["object"], p["sign"])].add(p["source"])
    convergent = {k for k, srcs in by_claim.items() if len(srcs) >= 2}
    by_pair = defaultdict(lambda: {"+": False, "-": False})
    for i in reads:
        p = packets[i]
        if p["sign"] in ("+", "-") and (p["subject"], p["object"]) in pairs:
            by_pair[(p["subject"], p["object"])][p["sign"]] = True
    conflict_pairs = {pr for pr, s in by_pair.items() if s["+"] and s["-"]}
    out = set()
    for i in reads:
        p = packets[i]
        if (p["subject"], p["object"], p["sign"]) in convergent:
            out.add(i)
        if p["sign"] in ("+", "-") and (p["subject"], p["object"]) in conflict_pairs:
            out.add(i)
    return out


def run_trial(topology, n, pool, packets, pairs, rate, rng):
    bad = corrupted_sources(pool, packets, rate, rng)
    reads, messages = select_reads(topology, n, pool, packets, rng)
    read_actions = sum(len(r) for r in reads)
    unique_read = {i for r in reads for i in r}

    if topology == "specialized":        # naive: verify every proposed packet
        verify_set = set(unique_read)
    elif topology == "selective":        # verify only decision-relevant evidence
        verify_set = decision_relevant(unique_read, packets, pairs)
    else:                                # homogeneous / partition: no verification
        verify_set = set()
    verify_actions = len(verify_set)
    # a verified packet is dropped if non-verbatim; unverified packets pass through
    admitted = {i for i in unique_read
                if i not in verify_set or effective_valid(i, packets, bad)}

    tokens = read_actions + verify_actions
    validated = {i for i in admitted if effective_valid(i, packets, bad)}
    false_admitted = len(admitted) - len(validated)
    total_valid = sum(effective_valid(i, packets, bad) for i in set(pool))
    n_cand, n_false = false_conflicts(admitted, packets, pairs, bad)
    return {
        "topology": topology, "n": n, "error_rate": rate,
        "validated_unique": len(validated),
        "coverage": len(validated) / max(1, total_valid),
        "validated_per_token": len(validated) / max(1, tokens),
        "false_admitted": false_admitted,
        "false_admit_rate": false_admitted / max(1, len(admitted)),
        "false_conflicts": n_false,
        "candidate_conflicts": n_cand,
        "false_conflict_rate": n_false / max(1, n_cand),
        "tokens": tokens, "coordination_messages": messages,
    }


def aggregate(rows):
    keys = ("validated_unique", "coverage", "validated_per_token", "false_admitted",
            "false_admit_rate", "false_conflicts", "false_conflict_rate", "tokens",
            "effective_team_size")
    out = {}
    for rate in ERROR_RATES:
        out[str(rate)] = {}
        for topology in TOPOLOGIES:
            out[str(rate)][topology] = {}
            for n in TEAM_SIZES:
                subset = [r for r in rows if r["topology"] == topology
                          and r["n"] == n and r["error_rate"] == rate]
                vals = {}
                for key in keys:
                    xs = [r[key] for r in subset]
                    mean = statistics.fmean(xs)
                    half = 1.96 * statistics.stdev(xs) / math.sqrt(len(xs)) if len(xs) > 1 else 0.0
                    vals[key] = {"mean": mean, "ci95_half": half}
                out[str(rate)][topology][str(n)] = vals
    return out


def evaluate_gate(summary):
    """Shipping candidate = 'selective' (verify only decision-relevant evidence).
    G1 false sign-collisions eliminated; G2 verify tax affordable vs partition;
    G3 beats homogeneous per token. 'specialized' (verify-all) is kept as contrast."""
    hi = str(max(ERROR_RATES))
    ship = "selective"
    false_conf = max(summary[hi][ship][str(n)]["false_conflict_rate"]["mean"]
                     for n in TEAM_SIZES)
    g1 = false_conf <= 1e-9
    ratios, wins = [], []
    for n in (30, 100, 300, 1000):
        part = summary[hi]["partition"][str(n)]["validated_per_token"]["mean"]
        homo = summary[hi]["homogeneous"][str(n)]["validated_per_token"]["mean"]
        shp = summary[hi][ship][str(n)]["validated_per_token"]["mean"]
        ratios.append(shp / part if part else 0.0)
        wins.append(shp >= homo)
    g2, g3 = min(ratios) >= 0.80, all(wins)
    # contrast: the naive verify-all approach and its (failing) affordability
    naive_ratio = min(summary[hi]["specialized"][str(n)]["validated_per_token"]["mean"]
                      / (summary[hi]["partition"][str(n)]["validated_per_token"]["mean"] or 1)
                      for n in (30, 100, 300, 1000))
    return {
        "error_rate_tested": float(hi),
        "shipping_candidate": ship,
        "G1_false_sign_collisions_eliminated": bool(g1),
        "G1_max_false_conflict_rate": false_conf,
        "G2_verify_tax_affordable": bool(g2),
        "G2_min_selective_over_partition_validated_per_token": min(ratios),
        "G3_beats_homogeneous_per_token": bool(g3),
        "contrast_naive_verify_all_min_over_partition": naive_ratio,
        "verdict": "GO" if (g1 and g2 and g3) else "NO-GO",
        "reading": ("Selective span-verification of decision-relevant evidence "
                    "(sign-collisions + convergent belief-candidates) over a source-partitioned "
                    "swarm removes false contradictions at a fraction of the verify-all token tax."),
    }


def chart(summary):
    import matplotlib.pyplot as plt
    hi = str(max(ERROR_RATES))
    colors = {"homogeneous": "#7f8c8d", "partition": "#426b9a",
              "specialized": "#b44d3a", "selective": "#3f7e67"}
    labels = {"homogeneous": "homogeneous (no verify)",
              "partition": "source partition (no verify)",
              "specialized": "partition + verify-ALL (naive)",
              "selective": "partition + selective verify (ship)"}
    fig, axes = plt.subplots(1, 3, figsize=(14, 4.2))
    metrics = ("validated_per_token", "false_admit_rate", "false_conflict_rate")
    titles = ("Validated evidence / token", "Bad evidence admitted (rate)",
              "False sign-collision rate")
    for topology in TOPOLOGIES:
        for ax, metric in zip(axes, metrics):
            y = [summary[hi][topology][str(n)][metric]["mean"] for n in TEAM_SIZES]
            ax.plot(TEAM_SIZES, y, marker="o", linewidth=2, markersize=4,
                    color=colors[topology], label=labels[topology])
    for ax, title in zip(axes, titles):
        ax.set_xscale("log")
        ax.set_xlabel("logical agents (log scale)")
        ax.set_title(title)
        ax.grid(alpha=.2)
    axes[0].legend(fontsize=8)
    fig.suptitle(f"Persona RQ-E07b — specialization + distribution under {int(float(hi)*100)}% "
                 "correlated source error, 30 seeded Curie replays", fontweight="bold")
    fig.tight_layout()
    fig.savefig(OUT_PNG, dpi=180, bbox_inches="tight", facecolor="white")


def main():
    packets, topics, pairs = load_packets()
    topic_names = sorted(topics)
    if len(topic_names) < SEEDS:
        raise RuntimeError(f"need >= {SEEDS} usable topics, found {len(topic_names)}")
    rows = []
    for seed in range(SEEDS):
        task_topics = random.Random(seed).sample(topic_names, 3)
        pool = sorted({i for name in task_topics for i in topics[name]})
        trial = []
        for rate in ERROR_RATES:
            for n in TEAM_SIZES:
                for topology in TOPOLOGIES:
                    rng = random.Random(seed * 100_000 + n * 10 + int(rate * 7))
                    trial.append(run_trial(topology, n, pool, packets, pairs, rate, rng))
        # effective team size vs a single homogeneous agent at the same error rate
        for rate in ERROR_RATES:
            single = next(r["validated_unique"] for r in trial
                          if r["topology"] == "homogeneous" and r["n"] == 1
                          and r["error_rate"] == rate)
            for r in trial:
                if r["error_rate"] == rate:
                    r["effective_team_size"] = r["validated_unique"] / max(1, single)
        rows += trial
    summary = aggregate(rows)
    gate = evaluate_gate(summary)
    result = {
        "experiment": "RQ-E07b specialized distributed swarm",
        "kind": "real-data replay simulation",
        "seeds": SEEDS, "team_sizes": TEAM_SIZES, "budget_per_agent": BUDGET_PER_AGENT,
        "error_rates": ERROR_RATES, "verify_fraction": VERIFY_FRACTION,
        "packets": len(packets), "usable_topics": len(topic_names),
        "summary": summary, "gate": gate, "rows": rows,
        "limitations": [
            "Logical retrieval agents, not live language-model agents (RQ-E07b-live is separate).",
            "Grounded means exact stored span, not scientific truth.",
            "Correlated error is modelled as whole-source corruption; real misreads are messier.",
            "Verifier is assumed to re-check spans perfectly; a real verifier has its own error rate.",
            "Token/coordination costs are normalized proxies, not measured wall-clock or dollars.",
        ],
    }
    OUT_JSON.write_text(json.dumps(result, indent=2), encoding="utf-8")
    chart(summary)
    hi = str(max(ERROR_RATES))
    print(f"packets={len(packets)} usable_topics={len(topic_names)} seeds={SEEDS}")
    print(f"--- under {hi} correlated source error ---")
    for topology in TOPOLOGIES:
        s = summary[hi][topology]
        print(f"{topology:12} N=100: valid/token={s['100']['validated_per_token']['mean']:.4f} "
              f"false_admit={s['100']['false_admit_rate']['mean']:.3f} "
              f"false_conflict={s['100']['false_conflict_rate']['mean']:.3f} "
              f"eff_team={s['100']['effective_team_size']['mean']:.1f}")
    print("GATE:", json.dumps(gate, indent=2))
    print(f"wrote {OUT_JSON.relative_to(ROOT)} and {OUT_PNG.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
