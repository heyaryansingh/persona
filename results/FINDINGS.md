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

---

## v3 T1.2 — canonicalization: deterministic + symbol-safe

v2 clustered entities by MiniLM similarity: order-dependent (broke crash-resume determinism)
and false-merged distinct symbols (IL-6/IL-1 embed near-identically → fake convergence). v3
makes canon() a PURE rule-based function (modifier-stripping + plural/hyphen normalization +
curated synonym map); embeddings are demoted to a guarded opt-in (digit-symbol signature blocks
il6/il1 merges; deterministic shortest-alphabetical representative).

`experiments/exp_canonicalization.py` (gold grouping of 40 entity strings):
- order-independent over **25 shuffles**: True
- distinct-symbol false merges: **0** (IL-6/IL-1, NLRP3/NLRP1, APOE4/APOE2 stay separate)
- pairwise **precision 1.00, recall 0.89, F1 0.94**

The tradeoff is deliberate and correct-first: perfect precision (never fabricate convergence),
0.89 recall (rules miss a few rare variants — the safe direction). This supersedes the v2
threshold=0.72 (unvalidated) with threshold=0.80 gating the *optional* embedding path only.

---

## v3 T1.3 — contradiction typing from context; poison detection for NEW beliefs

Typing no longer uses group counts alone. Now that observations persist `population`,
`_type_contradiction` types by the extracted context (BioDivergence 2026: most apparent
contradictions are context, not conflict): opposite effects in DIFFERENT populations →
`context-divergence`; in the SAME population → `true-refutation`. Group counts remain the
fallback when population is unstated.

Poison detection extended beyond attacks on established beliefs to catch **fabrication of a
NEW belief** — a coordinated push of many candidates from very few independent groups. Thresholds
derived by sweep (`experiments/exp_poison_thresholds.py`, 30 seeds/scenario): **poison_new_volume=6,
poison_new_ratio=0.25** gives perfect separation — attack + fabricate flag rate 1.00, benign-new +
benign-small 0.00. (The commit gate already blocks such low-independence claims; this adds
strict-mode backpressure + a human flag, i.e. observability of the attack pattern.)

---

## v3 T2.1 — economics: Batch API is the lever; prompt caching is a no-op for abstracts

Two cost levers were proposed. Measured honestly:
- **Prompt caching:** NO-OP for single-abstract extraction. The stable prefix (system + tools)
  is ~300 tokens; a full read totals ~1000 input tokens — below Haiku's 2048-token cache
  minimum. A real read confirmed `cache_read=0, cache_write=0`. The reader is now caching-READY
  (`cache_control` on the system block, cache-token accounting) so a future large few-shot prefix
  would benefit, but for short abstracts it changes nothing. (Don't assume a technique helps —
  measure it. CLAUDE.md §1.)
- **Batch API:** the real ~2x lever. `persona/swarm/batch_reader.py` (BatchReader) runs the same
  extractor semantics through the Message Batches API at ~0.5x price for the always-on background
  sweep (interactive AsyncSwarm stays for live reads). `est_cost_usd(..., batch=True)` prices it.

Net: the earlier "~2x cheaper via caching+batch" claim resolves to "~2x cheaper via Batch";
caching is inapplicable at this prompt size and is not counted.

---

## v3 T2.3 — persistent daily budget + model escalation + honest concurrency

- **Daily budget** (`persona/budget.py`): was an in-memory `AsyncSwarm.spent` counter that reset
  every tick and forgot spend on restart (could blow far past the cap over a day). Now a SQLite
  ledger keyed by UTC date — spend accumulates across ticks/swarms/restarts and resets at UTC
  midnight. Soft cap (concurrent reads near the ceiling can overshoot by ~concurrency; documented).
- **Escalation:** an AMBIGUOUS Haiku read (no claims from a substantive abstract, or all claims
  below the confidence floor) is re-read once by the reasoner (Sonnet). Off by default; tracked
  via `escalations` in the swarm summary.
- **Concurrency honesty:** the docstring claimed "hundreds of parallel readers"; the real default
  is a Semaphore of 16, raisable up to the account rate limit. Docstring corrected rather than
  overclaimed. Crash-resume invariant preserved (byte-identical, no double-commit).

---

## v3 T4 (a) — cross-field alignment: embeddings bridge vocabulary, Jaccard can't

`engine/cross_field.similarity` was lexical Jaccard, which scores same-mechanism / different-
vocabulary pairs ~0 (its one job — bridging subfields — it couldn't do). Now embedding cosine
(MiniLM) by default, Jaccard fallback. `experiments/exp_cross_field.py` (5 synonymous disjoint-
vocab pairs vs 5 unrelated): embedding synonymous mean **0.509** vs unrelated **0.016**
(separation +0.493, separates 10/10 at thr 0.20); Jaccard scores every synonymous pair **0.000**.
The vocabulary-bridging claim (BUILD_PLAN 3.6) is now real and validated.

---

## v3 T4 (b) — E5 & E7: descriptive engine stays descriptive (honest gates, on real data)

**E7 (VoI vs Open Targets genetic prior)** — `experiments/exp_e7_voi.py`, 12 gene-disease claims,
all resolving to real OT genetic scores. Finding: the comparison is **ill-posed**. VoI = load_bearing
× uncertainty operates on the INFERENTIAL-dependency hierarchy of mechanistic claims; a flat set of
gene-disease *associations* are siblings with no hierarchy, so `load_bearing` is empty and VoI is 0
for all — there is no meaningful correlation to report (reporting one would be an artifact). VoI is
validated STRUCTURALLY by E6 (load_bearing Spearman 0.38–0.50 vs gold foundational rank), not by the
genetic prior, and cannot be promoted to "predicts experimental payoff" without experimental-outcome
data. Honest reversal: E7 as originally framed is not a valid test.

**E5 (trajectory vs strong static baseline)** — `experiments/exp_e5_trajectory.py`, 397 real dated
Europe PMC papers replayed in year order (heuristic reader), cutoff 2022. Finding: **INCONCLUSIVE →
stays DESCRIPTIVE**. Only 1 of 32 committed beliefs had converged *by the cutoff* with a defined
trajectory (the corpus is back-loaded to 2023–24), far below the ≥8 needed for a stable estimate.
The trajectory forecast therefore stays honestly labelled "descriptive (E5 gate not passed)" on the
argument screen. Passing E5 needs a richer real-Claude corpus spanning more years; not gold-plated.

Net: both engine "predictive" claims remain **descriptive with evidence attached** — exactly the
plan's allowed outcome, and consistent with what the UI already tells the user.

---

# Persona v4 findings

## P6 — anchor write-policy resists correlated poisoning (CI oracle)

`experiments/exp_poisoning.py` (FalkorDB): a human-verified belief "drugX reduces mortality"
(anchored HUMAN_CONFIRMED) is attacked by 24 contrary "increases" claims from only 2 labs.
Result: the anchored belief is **RETAINED** (confidence 0.99 → 0.99, sign unchanged, still
anchored) because the anchor write-policy pins verified knowledge against cheap READ evidence;
and the poison pattern is **DETECTED** (volume 24, independent_labs 2, contradicting an anchor).
Mirrors the v3 corruption-resistance result. The human-escalation inbox (/api/inbox) surfaces
contradictions; a human resolve anchors the chosen side, which is then protected henceforth.
