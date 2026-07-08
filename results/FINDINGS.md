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
