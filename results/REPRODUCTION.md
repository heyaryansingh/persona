# Gate-0 Reproduction Report
*Persona Phase-0, execution step 0. Verifies the FINDINGS.md numbers reproduce before any architecture is built on them (CLAUDE.md §2/§4). Environment: Python 3.12.10, numpy 1.26.4, scipy 1.16.2, Windows.*

## Verdict: **PASS** (with one claim-refining finding — Confound A, below)

All three experiments reproduce. Means are **bit-identical** to the committed baselines; the only diffs are last-ULP floating-point noise (15th–16th significant digit) in the 95%-CI half-widths, expected across numpy/scipy versions. The headline poisoning crossover — whose numbers were **never persisted to JSON** and lived only in prose — reproduces **to the digit**.

## What was run
- `experiments/exp_memory_core.py` → `results/memory_core_results.json`
- `experiments/exp_memory_v2.py` → `results/memory_v2_results.json`
- `experiments/exp_when_protection_matters.py` → prints only (stdout captured to `results/repro_poison_crossover.log`)
- Baselines copied to `results/baseline_memory_core_results.json` / `baseline_memory_v2_results.json` for the diff.

## 1. Benign-noise story (v1 core) — reproduced
Under independent noise the naive continuous-update self **wins**, exactly as FINDINGS states (protection only adds latency; independent noise self-cancels):

| E1 low-noise | final_acc | flip_lag |
|---|---|---|
| naive_absorb | 0.960 ± .006 | 1204 |
| membrane | 0.875 ± .010 | 1263 |
| surprise_replay | 0.928 ± .008 | 902 |
| anchored_surprise | 0.909 ± .008 | 838 |

`surprise_replay`/`anchored_surprise` cut flip-latency (~902/838 vs 1263) — reproduces `[E3]`.

## 2. Independent corruption burst (v2) — reproduced
Naive recovers fine from an *independent* high-noise blip (victim-recovery 0.988 vs membrane 0.953 / anchored 0.952) — i.e. independent bursts do **not** justify protection. This is why the third experiment tests the *correlated* regime.

## 3. Headline: correlated sustained poisoning — reproduced **exactly**

| Agent | human_acc DURING | human_acc AFTER | all_poisoned AFTER | stable AFTER |
|---|---|---|---|---|
| naive | 0.762 ± .022 | 0.709 ± .045 | 0.683 ± .039 | 1.000 |
| quorum | 0.950 ± .010 | 0.811 ± .039 | 0.738 ± .032 | 0.999 |
| **human_anchored** | **1.000 ± .000** | **1.000 ± .000** | **0.880 ± .019** | 0.999 |

Matches FINDINGS.md to the digit.

**New datapoint (not in FINDINGS): milder correlated poison (strength 0.65)** → naive recovers to **0.973** human_acc AFTER (vs 0.709 at strength 0.85). → the crossover is a **strong-poison** phenomenon; it fades as poison weakens. (Confirms and quantifies "Confound C": the pro-protection result is regime-dependent — it needs *sustained, strong, correlated* attack.)

## Confound A — CONFIRMED and quantified (claim refinement)
The plan flagged that the "all_poisoned 0.880 vs 0.683" advantage is inflated because most "victims" are human-anchored. An instrumented pass (50 worlds, poison 0.85) separating human-anchored victims from ordinary poisoned beliefs:

| Agent | human-only | **NON-human victims** | all-victims (as reported) |
|---|---|---|---|
| naive | 0.709 | **0.607** | 0.683 |
| quorum | 0.811 | **0.520** | 0.738 |
| human_anchored | 1.000 | **0.520** | 0.880 |

Set sizes per world: `|human|=9, |victims|=12, |non-human victims|=3` → **human-confirmed are 75% of all "victims."**

**Reading:** on *ordinary* poisoned beliefs, `human_anchored ≡ quorum` (both 0.520) — anchoring adds **nothing** beyond the membrane there — and **naive is actually higher (0.607)** because recency-tracking recovers un-quorumable beliefs faster post-attack. The entire 0.880 "all-poisoned" advantage is the 9/12 anchored beliefs sitting at 1.000. *(n=3 non-human victims/world is small, so 0.520/0.607 are noisy; the qualitative decomposition follows directly from the set sizes and is robust.)*

**Refined architectural claim (supersedes the FINDINGS overclaim):**
- ✅ **Anchoring guarantees the human-confirmed core survives** correlated poisoning (1.000 vs naive 0.762 DURING / 0.709 AFTER). This is clean, load-bearing, and *is* the justification for making human-as-resolver central and anchoring the confirmed core.
- ❌ Anchoring does **not** broadly "rescue poisoned beliefs." The membrane (quorum) does most of the general anti-poison work (0.762→0.950 DURING), and on un-quorumable poisoned beliefs neither membrane nor anchor beats naive.
- → Report `non-human-victim` recovery separately from now on; do not cite "88% vs 68% of all poisoned" as an anchoring win.

## Threats still open (→ experiments)
- All of the above is a **boolean-channel simulation**. Promotion gate to the real regime = **E8** (real Claude extraction + a MINJA-style injection attack).
- Anchoring is never tested with a **wrong** human label → **E9** (escape hatch).
- The **adaptive switch** (fast-path ↔ strict) itself is untested; only fixed policies were run → **E10**.

## Reproduce
```
python experiments/exp_memory_core.py
python experiments/exp_memory_v2.py
python experiments/exp_when_protection_matters.py
```
Deterministic (seeds `1000+s`, `7000+s`, `13000+i`). Expect bit-identical means.
