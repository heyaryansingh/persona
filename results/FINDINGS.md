# Experimental Findings — Self / Memory Architecture
*(sandboxed simulations; seeded; 40–50 worlds each; means ± 95% CI)*
*Original findings preserved verbatim below; Phase-0 additions (reproduction + refinements) appended after the rule.*

## What we tested and why
The single hardest technical question in an always-on synthetic researcher is:
**how does a persistent "self" learn continuously from a firehose of literature
without (a) forgetting hard-won stable beliefs or (b) being corrupted by bad input?**
We cannot fine-tune a frontier model in-sandbox, so we tested the *architectural
policies* we actually control — the write-membrane and the identity-anchoring
policy over an external belief-store (the same knobs Letta / Mem0 / SuRe expose,
so results transfer to the real build).

## The key finding (and an honest reversal)
**v1/v2 under benign (stationary, independent) noise:** naive continuous update was
*as good or better* than membrane/anchor machinery — the protection added latency
without accuracy. **We did not hide this.** We diagnosed it: independent random noise
is self-cancelling, so protection buys nothing.

**The regime that matters — correlated, sustained poisoning** (a wrong review cited
200×, a systematic subfield-wide methodological error, injection-style poisoning):
this is the realistic threat for an agent reading the open literature, and here the
result inverts decisively:

| Agent | Human-verified beliefs retained DURING attack | Recovered AFTER | All poisoned recovered AFTER |
|---|---|---|---|
| naive continuous update | 0.762 ± .022 | 0.709 ± .045 | 0.683 ± .039 |
| quorum (convergence+provenance membrane) | 0.950 ± .010 | 0.811 ± .039 | 0.738 ± .032 |
| **human-anchored (protected core)** | **1.000 ± .000** | **1.000 ± .000** | **0.880 ± .019** |

Stable (unattacked) beliefs stay ~1.00 for all agents — anchoring costs nothing there.

## Architectural conclusions (now evidence-based, not asserted)
1. **The membrane is only worth its latency cost under correlated/adversarial input.**
   → Build it, but make it *adaptive*: cheap fast-path in benign regimes, strict
     quorum when correlated-source disagreement is detected. (Don't pay for it always.)
2. **A protected, human-confirmed core is essential and cheap.** Human-adjudicated
   beliefs (Part 3.7) must be *anchored* — resistant (not immune) to swarm overwrite.
   This is both the identity-protection mechanism AND the anti-slop mechanism, and it
   validates making the human-as-resolver loop central rather than optional.
3. **Surprise-prioritized verification** helped flip-latency in early tests but
   trades off calibration; keep it, but gate it so it can never move an anchored core
   belief without human sign-off (prevents surprise-seeking from becoming a corruption
   vector). This is a concrete, tested safety boundary.

## What this earns for the paper
A clean, reproducible result: *identity-anchoring in external-memory agents is
unnecessary under benign noise but decisive under correlated poisoning* — with a
quantified crossover. That is a publishable, non-obvious contribution about how to
build persistent LLM agents that read adversarial corpora.

## Threats to validity (stated honestly)
- Simulation abstracts the LLM as a noisy boolean channel; real extraction error is
  structured. Next step (real build): replay this with actual Claude extraction on a
  seeded poisoned corpus and confirm the crossover persists.
- Boolean propositions ≠ graded scientific claims; extend to continuous effect sizes.
- Anchor-locking assumes human labels are correct; add a human-error escape hatch.

---

# Phase-0 additions (2026-07-08)

## Reproduction (gate-0) — PASS
Re-ran all three experiments (Python 3.12.10 / numpy 1.26.4 / scipy 1.16.2). Means are **bit-identical** to the committed baselines; the only diffs are last-ULP floating-point noise in the CI half-widths. **The headline crossover — whose numbers were never persisted to JSON, only prose — reproduces to the digit.** Full report: [`results/REPRODUCTION.md`](REPRODUCTION.md).

New datapoint: at **milder** correlated poison (strength 0.65 vs 0.85), naive recovers to **0.973** (vs 0.709) — the crossover is a **strong-poison** phenomenon, quantifying the regime-dependence.

## Refinement — Confound A (the "all-poisoned 0.880 vs 0.683" claim is an artifact)
Instrumented pass (50 worlds, poison 0.85) separating human-anchored victims from ordinary poisoned beliefs:

| Agent | human-only | **NON-human victims** | all-victims (as reported) |
|---|---|---|---|
| naive | 0.709 | **0.607** | 0.683 |
| quorum | 0.811 | **0.520** | 0.738 |
| human_anchored | 1.000 | **0.520** | 0.880 |

Set sizes: `|human|=9, |victims|=12` → **human-confirmed are 75% of "victims."** On *ordinary* poisoned beliefs, `human_anchored ≡ quorum` (0.520) — anchoring adds nothing there — and **naive is actually higher (0.607)**. The 0.880 advantage is entirely the anchored subset sitting at 1.000.

**Refined claim (supersedes the original overclaim):**
- ✅ Anchoring **guarantees the human-confirmed core survives** (1.000 vs 0.762 DURING). This is the real, clean justification for human-as-resolver + anchoring.
- ❌ Anchoring does **not** broadly rescue poisoned beliefs; the membrane does the general work, and even it doesn't beat naive on un-quorumable victims. Report `non-human-victim` recovery separately; stop citing "88% vs 68% of all poisoned" as an anchoring win.

## Literature-driven refinements (see `planning/LITERATURE.md`)
- The correlated-poison threat model is **confirmed real and current** (MINJA >95% memory-injection; PoisonedRAG one passage). → E8 adds a MINJA-style injection to the oracle.
- "Anchoring" is home-grown terminology; the field frames it as **provenance/trust-tiered write-policy** + poisoning-defense reranker, and reports *no single defense is robust* — so anchoring is necessary but not sufficient.
- All of the above is still a **boolean-channel sim**. The promotion gate to "architecture we ship" is **E8** (real Claude extraction). Until E8, treat the crossover as well-motivated, not validated on the real regime.

## New validated gates (build phase; drive the real shipped code)
All 50 seeds, mean ± 95% CI. Each experiment drives the actual `persona.membrane.Membrane`
/ `persona.loops.outer` — validating shipped code, not a re-implementation.

| Gate | Result | Meaning |
|---|---|---|
| **E10** adaptive switch (`exp_e10_adaptive_switch.py`) | detect 1.000, false-strict 0.000, retention 1.000 | the membrane flips to strict on correlated poison, never on benign independent volume |
| **E14** independence convergence (`exp_e14_independence.py`) | independent-commit 1.000, echo-commit 0.000 (naive-count would admit echo 1.000) | counting *independent groups*, not agreement, blocks manufactured consensus |
| **E13** taste functional (`exp_e13_taste_functional.py`) | top-1 change 0.800, top-3 Jaccard 0.466, control identical 1.000 | disposition measurably changes the agenda — taste is not theater |
| **E9** escape hatch (`exp_e9_human_error_hatch.py`) | wrong-anchor re-escalate 1.000, poison re-escalate 0.000, retention 1.000 | independent evidence recovers a *wrong* human anchor (Confound B) without reopening poisoning |

**Still pending (need real data / annotations / an API key):** E5 (trajectory backtest),
E6 (dependency extraction precision), E7 (VoI vs expert), E8 (real-Claude poisoning replay),
E11 (calibration estimator), E12 (swarm vs single), E15 (contradiction-trigger precision).
Pre-registered as stubs under `experiments/`.

## v2 build gates (real LLM + scale)
| Gate | Result |
|---|---|
| P1 real extraction | Claude Haiku extracts **7 real structured claims** from a real abstract (~$0.004); night-and-day vs v1 keyword fragments |
| **P2 crash-resume bake-off** | resume **byte-identical 1.000**, no-double-commit 1.000, **15.7× parallel speedup**, 0 new deps → asyncio swarm wins; **LangGraph unnecessary** (bake-off settled) |
| P4 retrieval | hybrid (RRF) **MRR 0.947 / recall@1 0.909** > lexical (0.936/0.886) & dense (0.919/0.864), 44 live abstracts |
| P7 calibration | split-conformal coverage ≥0.9; decision-theoretic escalation |
| **Scale convergence** | 40 live papers → **"neuroinflammation causes neurodegeneration" with 7 independent sources** (p=0.99) + 3 more converged beliefs, $0.144 |

Architectural change validated in v2: a swarm belief is now a **deterministic function of its
accumulated independent evidence** (not an incremental step) over a **durable observation
log** — making the membrane crash-safe and re-reads idempotent, and making the anchor guard
**absolute by construction**. This supersedes (and strengthens) the boolean-sim crossover.

---

## v3 T0.4 — first-pass reanalysis over REAL data (Open Targets), and its bands

The acting loop's "reanalysis" no longer reasons over an accession *string*; it cross-checks a
gene↔disease claim against Open Targets' **computed** target–disease association (genetic +
literature + pathway evidence). `is_replay=False` only when a real external computation returned
a number.

**Band validation** (`experiments/exp_reanalysis_bands.py`, 12 textbook-true vs 12 unrelated
gene–disease pairs; Open Targets scores are deterministic external data, so n=24 labeled-pair
separation, not seeds):

| signal | pos mean | pos min | neg mean | neg max | best thr | precision | recall | F1 |
|---|---|---|---|---|---|---|---|---|
| genetic_association | 0.831 | 0.000 | 0.005 | 0.055 | 0.06 | 1.00 | 0.92 | 0.96 |
| overall association | 0.771 | 0.637 | 0.027 | 0.061 | 0.07 | 1.00 | 1.00 | 1.00 |

**Read:** the `overall` score is a *near-perfect* discriminator here — every true pair scores
≥0.637, every unrelated pair ≤0.061, so any threshold in **[0.07, 0.63]** is error-free on this
set. The production band `overall≥0.30` sits mid-interval with margin on both sides. The
`genetic≥0.10` branch (genetic evidence = higher clinical-success prior, Minikel 2024) adds zero
false positives (neg genetic max 0.055) and recovers the one drug-target case (TNF↔RA, genetic=0
but overall=0.637) that a genetic-only rule would miss. Both bands are therefore evidence-backed,
and the OR of them is justified. Honest caveat: Open Targets' fuzzy entity search can resolve a
non-gene phrase to *some* target, but such spurious matches fall in the inconclusive/refute band
(low score), so they don't manufacture a fake "supports".

---

## v3 T0.5 — the inferential-dependency graph exists (E6, honestly gated)

Audit #5: extraction emitted no `derives-from`/`presupposes` edges, so `load_bearing`
returned `{}` on real data and VoI was 0 for everything — the flagship graph (BUILD_PLAN 3.2)
was never built. It is now: a dependency-tagger pass proposes CANDIDATE edges between
co-mentioning committed claims (heuristic offline; Claude reasoner with a key).

**E6** (`experiments/exp_e6_dependency.py`, gold DAG of 12 biomedical claims → 20 co-mention
pairs, 11 gold edges):

| tagger | pairs | acc | Cohen κ | edge precision | edge recall | load_bearing Spearman |
|---|---|---|---|---|---|---|
| heuristic (offline) | 20 | 0.45 | 0.03 | 0.50 | 0.36 | **0.38** |
| claude (reasoner)   | 20 | 0.45 | 0.06 | 0.50 | 0.18 | **0.50** |

**Read (honest):** per-edge direction agreement is weak (κ≈0) — neither tagger reliably
gets individual edge *direction* right, and the Claude tagger is conservative (low recall,
which on real data is the safer failure). BUT the metric that actually feeds VoI —
`load_bearing`, PageRank over the (noisy) edges — shows a **moderate positive** rank
correlation with the gold foundational ordering (Spearman 0.38–0.50). So the graph is a
legitimate hypothesis-*ranker*, not ground truth.

**Verdict:** E6 is NOT passed for autonomy. Edges stay `CANDIDATE`/`INFERRED` and the
dependency + idea-graph views keep their "E6 gate not passed" labels; these edges rank where
a human should *look*, they don't assert dependency as fact. This is the predicted
human-in-the-loop downgrade, now quantified rather than assumed.

---

## v3 T1.1 — evidential independence: senior-author, not journal (E14 made real)

Audit #4: convergence counted distinct JOURNALS. `exp_e14_independence.py` already proved the
membrane gate counts distinct *groups* (not raw agreement) on synthetic labels; the open
question was whether the group KEY is right. `exp_e14_independence_real.py` answers it on 180
real Europe PMC papers (3 Alzheimer's queries):

- **Under-count:** 27 journals each host ≥2 independent labs. Worst: *Alzheimer's & Dementia*
  collapses **9 distinct labs into a single "independent source"** — journal-grouping erases
  most real independence in a popular venue.
- **Over-count (echo):** 7 labs publish across ≥2 journals. Worst: one senior author spans 2
  journals → journal-grouping credits that single lab with 2 "independent" votes.

Journal is therefore wrong in **both** directions. Independence is now keyed on the **senior
(last) author** (`persona/ingest/independence.py`, `independence_group()`), the cheapest
high-signal lab proxy — cross-batch stable and deterministic. It splits co-journal labs and
merges a lab's cross-journal echo. Last-name collisions between real labs *under*-count (the
safe, harder-to-converge direction for an anti-slop membrane). Author-set-overlap and
citation-graph screens remain a future refinement; senior-author is the load-bearing fix.
