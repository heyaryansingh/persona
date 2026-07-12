"""RQ-E07a: evidence-retrieval team physics over real Curie packets.

This is a replay simulation, not 1,000 live LLM calls. It asks one bounded question:
for a decomposable evidence-breadth task, how do homogeneous search, dense sharing, per-agent source
partitioning, and five-agent cells trade unique grounded evidence against redundancy/coordination?
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
OUT_JSON = ROOT / "results" / "rq_e07a_swarm_physics.json"
OUT_PNG = ROOT / "results" / "rq_e07a_swarm_physics.png"
SEEDS = 30
TEAM_SIZES = (1, 3, 5, 10, 30, 100, 300, 1000)
BUDGET_PER_AGENT = 6
TOPOLOGIES = ("homogeneous", "dense_debate", "central_partition", "cells_of_five")


def norm(text: str) -> str:
    return " ".join(unicodedata.normalize("NFKC", text or "").casefold().split())


def stable_bucket(text: str, n: int) -> int:
    return int(hashlib.sha1(text.encode()).hexdigest()[:12], 16) % max(1, n)


def load_packets() -> tuple[list[dict], dict[str, list[int]]]:
    packets, topics = [], defaultdict(list)
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
            packet = {"key": f"{slug}:{claim.get('claim_id','')}", "source": slug,
                      "valid_span": bool(quote and quote in clean),
                      "weight": max(.05, float(claim.get("confidence", .6) or .6))}
            idx = len(packets)
            packets.append(packet)
            for entity in {norm(claim.get("subject", "")), norm(claim.get("object", ""))}:
                if entity:
                    topics[entity].append(idx)
    usable = {topic: ids for topic, ids in topics.items()
              if len(ids) >= 10 and sum(packets[i]["valid_span"] for i in ids) >= 5}
    return packets, usable


def weighted_sample(rng: random.Random, pool: list[int], packets: list[dict], k: int) -> list[int]:
    if not pool or k <= 0:
        return []
    # Agent-local reading is without replacement; different agents can still duplicate work.
    work = list(pool)
    out = []
    for _ in range(min(k, len(work))):
        weights = [packets[i]["weight"] for i in work]
        choice = rng.choices(range(len(work)), weights=weights, k=1)[0]
        out.append(work.pop(choice))
    return out


def select(topology: str, n: int, pool: list[int], packets: list[dict], rng: random.Random) -> tuple[list[int], int]:
    if topology == "homogeneous":
        selected = []
        for _ in range(n):
            selected += weighted_sample(rng, pool, packets, BUDGET_PER_AGENT)
        return selected, max(0, n - 1)

    if topology == "dense_debate":
        selected, shared = [], []
        copy_p = min(.92, .18 + .12 * math.log2(max(1, n)))
        for _ in range(n):
            own = weighted_sample(rng, pool, packets, BUDGET_PER_AGENT)
            prior = list(shared)
            agent_items = []
            for item in own:
                if prior and rng.random() < copy_p:
                    item = rng.choice(prior)
                agent_items.append(item)
            selected += agent_items
            shared += agent_items
        return selected, n * max(0, n - 1)

    if topology == "central_partition":
        partitions = [[] for _ in range(n)]
        for item in pool:
            partitions[stable_bucket(packets[item]["source"], n)].append(item)
        selected = []
        for part in partitions:
            selected += weighted_sample(rng, part, packets, BUDGET_PER_AGENT)
        return selected, max(0, n - 1) * 2

    cells = math.ceil(n / 5)
    partitions = [[] for _ in range(cells)]
    for item in pool:
        partitions[stable_bucket(packets[item]["source"], cells)].append(item)
    selected = []
    for agent in range(n):
        selected += weighted_sample(rng, partitions[agent // 5], packets, BUDGET_PER_AGENT)
    local_messages = sum(size * max(0, size - 1) for size in
                         [min(5, n - c * 5) for c in range(cells)])
    return selected, max(0, n - 1) * 2 + local_messages


def metrics(selected: list[int], messages: int, n: int, pool: list[int], packets: list[dict]) -> dict:
    unique = set(selected)
    valid = {i for i in unique if packets[i]["valid_span"]}
    total_valid = sum(packets[i]["valid_span"] for i in set(pool))
    planned_actions = n * BUDGET_PER_AGENT
    work_units = planned_actions + .05 * messages
    return {"validated_unique": len(valid), "coverage": len(valid) / max(1, total_valid),
            "redundancy": 1 - len(unique) / max(1, len(selected)),
            "rejection_waste": sum(not packets[i]["valid_span"] for i in selected) /
                               max(1, len(selected)),
            "coordination_messages": messages, "work_units": work_units,
            "efficiency": len(valid) / max(1, work_units), "selected": len(selected)}


def aggregate(rows: list[dict]) -> dict:
    out = {}
    for topology in TOPOLOGIES:
        out[topology] = {}
        for n in TEAM_SIZES:
            subset = [r for r in rows if r["topology"] == topology and r["n"] == n]
            vals = {}
            for key in ("validated_unique", "coverage", "redundancy", "rejection_waste",
                        "coordination_messages", "work_units", "efficiency", "effective_team_size"):
                xs = [r[key] for r in subset]
                mean = statistics.fmean(xs)
                half = 1.96 * statistics.stdev(xs) / math.sqrt(len(xs)) if len(xs) > 1 else 0
                vals[key] = {"mean": mean, "ci95_half": half}
            out[topology][str(n)] = vals
    return out


def stopping_points(summary: dict) -> dict:
    stops = {}
    for topology in TOPOLOGIES:
        stop = TEAM_SIZES[-1]
        previous = summary[topology][str(TEAM_SIZES[0])]["coverage"]["mean"]
        for n in TEAM_SIZES[1:]:
            current = summary[topology][str(n)]["coverage"]["mean"]
            if current - previous < .01:
                stop = n
                break
            previous = current
        stops[topology] = stop
    return stops


def chart(summary: dict) -> None:
    import matplotlib.pyplot as plt

    colors = {"homogeneous": "#7f8c8d", "dense_debate": "#b44d3a",
              "central_partition": "#426b9a", "cells_of_five": "#3f7e67"}
    labels = {"homogeneous": "homogeneous", "dense_debate": "dense sharing",
              "central_partition": "central source partitions", "cells_of_five": "5-agent cells"}
    fig, axes = plt.subplots(1, 3, figsize=(14, 4.2))
    for topology in TOPOLOGIES:
        x = list(TEAM_SIZES)
        for ax, metric in zip(axes, ("coverage", "redundancy", "efficiency")):
            y = [summary[topology][str(n)][metric]["mean"] for n in x]
            ax.plot(x, y, marker="o", linewidth=2, markersize=4, color=colors[topology],
                    label=labels[topology])
    titles = ("Unique grounded-evidence coverage", "Duplicate-work rate", "Grounded evidence / work unit")
    for ax, title in zip(axes, titles):
        ax.set_xscale("log")
        ax.set_xlabel("logical agents (log scale)")
        ax.set_title(title)
        ax.grid(alpha=.2)
    axes[0].set_ylabel("rate")
    axes[1].set_ylabel("rate")
    axes[2].set_ylabel("efficiency")
    axes[0].legend(fontsize=8)
    fig.suptitle("Persona RQ-E07a — decomposable evidence breadth, 30 seeded Curie replays",
                 fontweight="bold")
    fig.tight_layout()
    fig.savefig(OUT_PNG, dpi=180, bbox_inches="tight", facecolor="white")


def main() -> None:
    packets, topics = load_packets()
    topic_names = sorted(topics)
    if len(topic_names) < SEEDS:
        raise RuntimeError(f"need at least {SEEDS} usable topics, found {len(topic_names)}")
    rows = []
    for seed in range(SEEDS):
        task_topics = random.Random(seed).sample(topic_names, 3)
        topic = " | ".join(task_topics)
        pool = sorted({item for name in task_topics for item in topics[name]})
        trial_rows = []
        for n in TEAM_SIZES:
            for topology in TOPOLOGIES:
                rng = random.Random(seed * 100_000 + n * 10)
                selected, messages = select(topology, n, pool, packets, rng)
                trial_rows.append({"seed": seed, "topic": topic, "topology": topology, "n": n,
                                   **metrics(selected, messages, n, pool, packets)})
        single = next(r["validated_unique"] for r in trial_rows
                      if r["topology"] == "homogeneous" and r["n"] == 1)
        for row in trial_rows:
            row["effective_team_size"] = row["validated_unique"] / max(1, single)
        rows += trial_rows
    summary = aggregate(rows)
    result = {"experiment": "RQ-E07a swarm evidence physics", "kind": "real-data replay simulation",
              "seeds": SEEDS, "team_sizes": TEAM_SIZES, "budget_per_agent": BUDGET_PER_AGENT,
              "packets": len(packets), "usable_topics": len(topic_names), "summary": summary,
              "stopping_points_first_lt_1pct_coverage_gain": stopping_points(summary),
              "rows": rows,
              "limitations": ["Logical retrieval agents, not live language-model agents.",
                              "Grounded means exact stored span, not scientific truth.",
                              "Coordination messages and work units are normalized proxies.",
                              "Only decomposable evidence-breadth tasks are tested; sequential tasks remain RQ-E07b."]}
    OUT_JSON.write_text(json.dumps(result, indent=2), encoding="utf-8")
    chart(summary)
    print(f"packets={len(packets)} usable_topics={len(topic_names)} seeds={SEEDS}")
    print("first <1 percentage-point coverage gain:", result["stopping_points_first_lt_1pct_coverage_gain"])
    for topology in TOPOLOGIES:
        best = max(TEAM_SIZES, key=lambda n: summary[topology][str(n)]["efficiency"]["mean"])
        s30 = summary[topology]["30"]
        print(f"{topology:18} best-efficiency N={best}; N30 coverage={s30['coverage']['mean']:.3f} "
              f"redundancy={s30['redundancy']['mean']:.3f} efficiency={s30['efficiency']['mean']:.3f}")
    print(f"wrote {OUT_JSON.relative_to(ROOT)} and {OUT_PNG.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
