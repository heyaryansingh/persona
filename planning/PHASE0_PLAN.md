# Persona — Phase 0: Research, Verification & Build Plan
*Living document. Produced in plan mode (read-only). Nothing below is implemented yet.*

---

## Context

**Persona** is a persistent, always-on synthetic researcher for the biomedical literature (see `Initial Planning Docs/BUILD_PLAN.md`). It keeps a durable **self** (interests, beliefs, memory, taste) and spawns an ephemeral **swarm** of bounded agents to read at scale, closing an agentic loop: flagged contradiction → falsifiable hypothesis → located public dataset → first-pass reanalysis (Claude Science) → written back into its belief-state, escalating to a human exactly when it needs wet-lab results or experimental judgment. Target: the **Claude Science hackathon with Gladstone Institutes**.

This document is the deliverable for **Phase 0**: orient, verify, and plan *like a scientist* (per `CLAUDE.md` §2) **before any module code**. It answers the six kickoff steps. Two hard constraints shaped how it was produced:

1. **Plan mode is active** — this file is the only thing I may write this session. The step-by-step artifacts (extending `results/` and a new `planning/`) and the experiment stub files are written **on approval**, as execution step 0. This file *is* the plan being shown for review.
2. **Never assume (`CLAUDE.md` §1).** Every architectural choice is tagged evidence-backed `[E]`, hypothesis `[H]`, or my-own-flag `[?]`. Unproven `[H]`/`[?]` items are the experiment backlog (Step 4).

**Method used for this plan:** read all 6 repo files in full (BUILD_PLAN, FINDINGS, 3 experiment scripts, 2 result JSONs); statically analyzed the experiments (found one real confound — Step 3); launched a **6-domain read-only current-literature sweep** as a background workflow (Step 2, integrated on completion); pulled design guidance from the `frontend-design` skill. Execution-by-running-code (reproducing the experiments) is deferred to gate-0 on approval, because plan mode forbids running non-read-only tools.

---

## Step 1 — What exists, and the evidence ledger

### 1.1 The architecture in one screen

**The one commitment everything derives from: separate the Swarm from the Self.**

- **The Self** (durable, small, singular): identity/disposition, standing interests (attention weights over belief-graph regions, each with a revisable *reason*), the belief-state (calibrated, provenance-typed claim-graph), memory (episodic/semantic/procedural), body of prior work (notebook, mini-reviews, error log), and a taste function ranking what to pursue next.
- **The Swarm** (ephemeral, vast, stateless): bounded, budgeted, disposable agents — reader, extractor, dependency-tagger, cross-checker, dataset-scout, hypothesizer, tester, reflector, orchestrator. They **read; they never write to the self**.
- **The Membrane** (anti-slop funnel): swarm output is *candidate*; nothing becomes belief without **convergence + provenance + calibration**, and for high-stakes claims, **human adjudication**. Slogan: *scale of reading, discipline of believing.*
- **Five loops**: inner (read→update, always-on), outer (reflect→reprioritize→act), initiative (act unbidden), human-delegation (assemble dossier → route → anchor answer), self-test (the centerpiece: contradiction → hypothesis → dataset → Claude Science reanalysis → write-back), artifact (living notebook + mini-reviews + error log).
- **Storage**: self as human-readable living docs (`self/*.md`, `beliefs.json`) re-hydrated each wake, backed by a claim-graph store for structured queries.

### 1.2 The intellectual engine (BUILD_PLAN Part 3) — what makes it not-a-search-tool

Six instruments that treat the literature as a *structured, moving system*:

| # | Instrument | Core idea | Hypothesis / test named in plan |
|---|---|---|---|
| 3.1 | **Argument-state dynamics** | report the *derivative* of evidence (velocity/acceleration/independence-drift), forecast collapse | H3.1 / **E5** backtest vs static |
| 3.2 | **Assumption graph** | inferential-dependency DAG (`presupposes`/`derives-from`); load-bearing score = downstream mass × inverse independent-support | H3.2 / **E6** extraction precision vs gold |
| 3.3 | **Fragility propagation** | perturb a node → recompute what downstream weakens | H3.3 expert face-validity |
| 3.4 | **Experiment-value ranking** | rank by value-of-information ÷ cost — "highest-leverage experiment this month" | H3.4 / **E7** vs expert, vs citation baseline |
| 3.5 | **Silence detector** | find *abandonment* (hot→quiet, not refuted) → hunt buried nulls | H3.5 case-control |
| 3.6 | **Cross-field translation** | same mechanism, two vocabularies that never cite each other | recovery vs embedding baseline |
| 3.7 | **Human-as-resolver** | human is the adjudication step *inside* the loop; their answer becomes a durable shared belief node | (design principle; validated indirectly by the anchoring finding) |

### 1.3 The one validated finding (FINDINGS.md) — stated precisely

Sandboxed simulation (belief-store as a noisy boolean channel; 40–50 worlds; seeded; mean ± 95% CI). The honest arc:

- **Under benign (stationary, independent) noise**, a naive continuous-update self is *as accurate or better* than any membrane/anchor machinery — protection only adds latency. Confirmed by the persisted JSONs: E1 low-noise `naive 0.960` vs `membrane 0.875`; v2 independent corruption-burst `naive victim-recovery 0.988` vs `anchored 0.952`. **This is a reversal the authors kept and diagnosed** (independent noise is self-cancelling).
- **Under correlated, sustained poisoning** (a wrong review cited 200×; a subfield-wide method error; injection-style poisoning) — the realistic open-literature threat — the result **inverts**:

| Agent | human-verified retained DURING | recovered AFTER | all-poisoned recovered AFTER |
|---|---|---|---|
| naive continuous | 0.762 | 0.709 | 0.683 |
| quorum membrane | 0.950 | 0.811 | 0.738 |
| **human-anchored** | **1.000** | **1.000** | **0.880** |

The architecture in Part 5 (adaptive membrane; anchored human-confirmed core; surprise-gated verification that can't move an anchor without sign-off) is *derived* from this. **Caveat I found (Step 3): the "all-poisoned 0.880 vs 0.683" gap is partly an artifact; the clean result is the DURING/AFTER human-belief retention.**

### 1.4 The ledger: `[E]` evidence-backed vs `[H]` unproven hypothesis

**Evidence-backed `[E]` (only these three, and all rest on the sim — not yet on real Claude extraction):**

- `[E1]` Membrane/protection earns its latency cost **only** under correlated/adversarial input; use an **adaptive** policy (fast-path benign, strict quorum on correlated disagreement). *Load-bearing numbers are un-persisted (see Step 3) → must be re-derived.*
- `[E2]` A protected human-confirmed **anchor** preserves verified beliefs under correlated poisoning (100% vs 76% during attack). *Recovery-of-all-poisoned magnitude is confounded (Step 3); refine the claim.*
- `[E3]` Surprise-prioritized verification lowers correct-flip latency (v1: `surprise_replay lag 902` vs `membrane 1263` at low noise) but must never move an anchor without human sign-off.

**Unproven `[H]`/`[?]` — the experiment backlog (Step 4 gives each a spec):**

| ID | Claim currently unproven | Where it bites | Named in plan? |
|---|---|---|---|
| E5 | trajectory features beat static scores at predicting collapse | 3.1, argument-state screen | yes |
| E6 | LLMs extract `derives-from`/`presupposes` edges at usable precision | 3.2, dependency graph — **biggest differentiator, hardest** | yes |
| E7 | VoI÷cost ranking beats citation baseline vs expert judgment | 3.4, experiment queue | yes |
| E8 `[?]` | the poisoning crossover survives **real Claude extraction** (not a boolean sim) | whole membrane/anchor justification | flagged as "next step" in FINDINGS |
| E9 `[?]` | anchoring is safe when a human label is **wrong** (escape hatch) | anchoring policy — a corruption vector | flagged in FINDINGS threats |
| E10 `[?]` | the **online correlated-disagreement detector** (the adaptive *switch*) actually fires correctly | 5.4 adaptive membrane | no — the switch itself is untested |
| E11 `[?]` | some current calibration method yields confidence good enough to **gate** and to trigger escalation | 5.3, membrane, 3.7 | no |
| E12 `[?]` | bounded many-agent fan-out beats one strong agent at extraction accuracy per token | 5.1/5.2, the swarm premise | no |
| E13 | interests/taste are **functional** (weights measurably change what's read/concluded) | 1.4/1.5 — anti-"anthropomorphic theater" | yes (E4, not run) |
| E14 `[?]` | independent-source **convergence** is estimable in real corpora (citation coupling, shared data confound it) | 1.3 membrane convergence gate | no |
| E15 `[?]` | contradiction detection is precise enough to be an autonomous **loop trigger** (false-positive rate) | 2.5 self-test loop | no |
| H3.3 | fragility cascades are face-valid to experts | 3.3 | yes (qualitative) |
| H3.5 | abandonment signatures enrich for discoverable nulls | 3.5 | yes |
| H3.6 | cross-field translation beats an embedding-similarity baseline | 3.6 | yes |

The `[?]` items are ones I added that the plan does **not** currently gate — the highest-value additions to the research program. **Literature-adjusted (Step 2):** the sweep confirms `5.3` (calibrated per-belief probability) is `[H]` not `[E]`; reframes anchoring as a provenance-typed **write-policy** (add a MINJA injection attack to the oracle); downgrades E6's realistic expectation (per-edge precision <0.7 → judge on rank-correlation); and elevates the **human-gated contradiction trigger (E15)** and **convergence = evidential independence (E14)** from optional to load-bearing. See §2.7.

---

## Step 2 — Current literature (last ~18 months)

*Source: a 6-domain adversarial read-only sweep (6 Opus-4.8 scouts, 104 web searches). Each was told to hunt for work that **challenges** the plan and to rate every citation's confidence. Verdicts below are per BUILD_PLAN section; citations are the scouts' (a few marked low-confidence / unverified — flagged inline; verify before the paper).*

### 2.1 Persistent-agent memory & continual learning
- **CONFIRM — living-docs self (5.5).** This is current SOTA, not naive: **Letta/MemGPT** ships human-readable, agent-editable "memory blocks" + the AgentFile (`.af`) serialization of a whole stateful self. Consider building the self *on* Letta rather than reinventing serialization.
- **UPDATE — don't re-hydrate everything each wake (5.5).** SOTA is a **two-tier** split: a small always-in-context core (identity/agenda) + a large tool-retrieved archival store. Re-hydrating a growing `beliefs.json`+`notebook.md` will blow context. → build the self two-tier.
- **UPDATE — make the claim-graph bi-temporal (5.5).** **Zep/Graphiti** (arXiv:2501.13956) gives facts `valid-from/valid-to` + invalidation edges + per-fact provenance — purpose-built for "belief that changed over time," which is Persona's core. Caveat (**Mem0**, arXiv:2504.19413): graph memory adds only ~2 pts on LOCOMO at ~1.5× latency, concentrated in temporal/multi-hop — justify the graph by the *temporal* workload, not blanket accuracy.
- **UPDATE — reframe "anchoring" (5.4).** The threat is real and current: **MINJA** (query-only memory injection, >95% success) and **PoisonedRAG** (USENIX Sec 2025, one poisoned passage). But "anchoring" is home-grown; the field frames it as **provenance/trust-tiered writes + a write-policy** (READ/INFERRED cannot silently overwrite HUMAN_CONFIRMED/TESTED) + a poisoning-defense reranker — and reports *no single defense is robust*. → keep the mechanism, rename/reframe it, and **add a MINJA-style injection attack to the E8 oracle** alongside correlated noise.
- **CONFIRM** three memory types + "consolidation on sleep" (named lineage: Generative Agents reflection 2023 → **Sleep-time Compute** arXiv:2504.13171 → **A-MEM** memory-evolution). Borrow A-MEM link-generation; make consolidation novelty-gated (incremental), not a full re-scan.
- **Reject parametric memory (Titans, arXiv:2501.00663) explicitly** — powerful but not legible/auditable; legibility is the product thesis, so state the rejection reason in §5. **Benchmark the self on LongMemEval** (knowledge-update + abstention subsets) for reviewer-facing numbers.

### 2.2 Multi-agent orchestration & swarms
- **CONFIRM — swarm/self split + harvest-then-commit (5.1) are the two best-evidenced choices in the whole plan.** Anthropic's own orchestrator-worker read system beat single-agent Opus-4 by **90.2%** *because* research is breadth-first and exceeds one context window; the loudest skeptic (Cognition) explicitly endorses **read-only, write-free single-purpose subagents** as the one safe multi-agent form. Persona sits in the zone both camps bless.
- **CONFIRM — budgeted heterogeneous fan-out (5.2).** Anthropic ships Opus-lead + Sonnet-workers and reports **token usage explains ~80% of performance variance** (multi-agent ≈ **15× chat tokens**). → gate wide fan-out on task value (only a flagged, high-precision contradiction justifies 15×).
- **CHALLENGE — do NOT fan the hypothesizer/tester into a debate/ensemble (5.2).** Under *matched compute*, a single strong agent matches or beats multi-agent on multi-hop reasoning (Tran & Kiela 2026, arXiv:2604.02460 — grounded in the Data-Processing Inequality: every handoff can only lose information), and multi-agent debate ≈ self-consistency at best. → **hypothesizer+tester = one strong agent with self-consistency + an explicit verification pass**, not an ensemble. Fan-out stays in read/extract/dataset-scout only.
- **UPDATE — redesign backpressure (5.2).** "Narrow under correlated disagreement" is dangerous: readers sharing one base model have **correlated errors**, so their *agreement* is false confidence and more rounds add noise (arXiv:2603.16244). → key backpressure on **calibrated uncertainty + source/evidential independence + model/prompt diversity**, not agent-count agreement. (Dovetails with the anchoring/poisoning machinery.)
- **UPDATE — add the production layer every always-on system now treats as mandatory** and which 5.1/5.2 omit: durable **checkpoint/resume** (LangGraph-style), swarm decision-trace **observability**, retry-and-adapt on tool failure, boundary **guardrails** (OpenAI Agents SDK), and the **cross-checker as a hard fail-loud gate** (MAST, arXiv:2503.13657: ~42% of MAS failures are spec/role ambiguity, ~21% verification gaps). Optionally replace the *static* budget with adaptive VoI-gated allocation (AgentTTS, arXiv:2508.00890 — *medium confidence*).

### 2.3 Structured biomedical extraction & the dependency graph (the E6 risk)
- **CONFIRM — the support/contradict extraction layer is SOTA-competitive** (KARMA NeurIPS'25; MedKGent ~90% acc; iKraph Nat. Mach. Intell. 2025; PaperQA2). Risk is concentrated *entirely* in the E6 inferential-dependency layer, not here.
- **CHALLENGE — E6's per-edge precision premise (3.2).** No biomedical (or scientific-prose) dataset/method exists for `presupposes/derives-from/generalizes/operationalizes` — genuinely unbuilt (the differentiator, but also untested). Ceilings are unforgiving: well-defined biomedical RE tops ~0.88–0.9 **precision at only ~0.6 recall**; PaperQA2's *easier* contradiction edge is only ~70% expert-validated; the argument-mining survey (arXiv:2506.16383) calls inter-claim dependency beyond support/attack "**firmly open**" and names **presupposition as an LLM failure mode**. The only large `derives-from` graph (TheoremGraph, arXiv:2606.25363) works only in *formal math* where proofs cite lemmas. **Expect per-edge precision meaningfully below 0.7.**
- **UPDATE — the fixes make E6 survivable (and are now baked into the E6 spec):** (1) change the acceptance metric from per-edge precision to **rank correlation** of load-bearing claims vs expert-nominated foundational claims — a noisy edge set can still rank; (2) **build a small dev set and report inter-annotator agreement FIRST** — if experts don't agree on `derives-from` vs `generalizes` (fuzzy-relation IAA is documented low, arXiv:2510.20345), the target is ill-posed and must be renegotiated before spending model budget; (3) **anchor the four labels to existing schemas** (`derives-from/operationalizes` ≈ citation-intent Uses/Extends — ACL-ARC/SciCite; `presupposes` ≈ concept-prerequisite extraction) rather than inventing blind; (4) emit **candidate edges w/ calibrated confidence** (TheoremGraph pattern) into `INFERRED` provenance, never as fact; (5) add a **citation-graph backbone** so the ranking survives even if LLM edge precision is poor. LLMs also commit "causal hallucination" (spurious dependency links) — the exact failure mode most damaging here.

### 2.4 Contradiction detection & convergence (a structural reframe)
- **CHALLENGE — contradiction is not a safe autonomous trigger (2.5).** Best deployed system (ContraCrow/PaperQA2): only **~70% of flagged contradictions are expert-validated** (~30% wild false-positive), and **inter-expert agreement is only 75.5%** — ground truth itself caps near 75%. Autonomously spending reanalysis compute on a 1-in-3-wrong signal is exactly the CLAUDE.md §1 trap.
- **CHALLENGE — contradiction is not binary (1.3).** Most apparent biomedical contradictions are **context-conditioned divergence** (cohort/dose/assay/subtype), both claims locally valid; LLMs separate true-refutation from divergence at only **~0.55 acc** (BioDivergence, arXiv:2606.11208). NLI labels also flip under paraphrase (NLI4CT consistency 0.73). → the membrane must emit a **typed** object: `true-refutation / context-divergence / no-evidence`, not a boolean.
- **CHALLENGE — convergence ≠ agreement count (1.3).** Apparent independent agreement is routinely **manufactured by citation echo/amplification** (Greenberg, BMJ 2009; Sarol/Schneider 2025). → redefine convergence as **evidential independence** (distinct cohorts/datasets/methods) + a citation-echo screen; no off-the-shelf tool conditions on statistical power, so add a **study-quality/power prefilter** upstream.
- **CONFIRM — detection as a high-recall *surfacing* mechanism is good and improving** (ContraCrow 88% precision / 0.842 AUC on curated benchmark). The correction is architectural, not abandonment: **detection → typed → context-divergence filter → high-precision operating point → human handoff**, and **human-as-resolver becomes non-optional at ignition.** Reuse ContraDetect + BioDivergence as test oracles with ≥20-seed CIs.

### 2.5 Calibration & uncertainty (5.3 is a hypothesis, not `[E]`)
- **UPDATE — "every belief carries a calibrated probability" (5.3) is achievable but not free, and not by asking the model.** RLHF models are systematically overconfident (ECE ~0.2–0.4; verbalized confidence clusters at 80–100% even when wrong). Calibration is **domain-shift-dependent** (clinical calibration varies by specialty, EACL 2026). → mark 5.3 `[H]`; it requires a chosen estimator + per-domain held-out calibration set + drift monitoring.
- **CONFIRM — calibration as a membrane gate (1.3) = selective prediction**, but drive it from **sampling/consistency signals** — semantic entropy (Farquhar et al., *Nature* 2024) or cheap proxies (SAR / lexical-similarity / SE-probes; pick via **LM-Polygraph**, TACL 2025) — and set the cutoff via **conformal/selective prediction** (SConU ACL'25, COIN) for a *provable* error rate. A tuned ensemble beats any single scorer (UQLM, TMLR 2025).
- **CHALLENGE — "escalate exactly on the uncertain calls" (3.7) overstates capability.** Abstention is empirically **unsolved** (AbstentionBench, Meta 2025) and reasoning fine-tuning *degrades* it; deeper reasoning → *more* overconfident. → escalation must be **decision-theoretic (uncertainty × stakes)**, per-domain, audited — never verbalized confidence. Decompose long syntheses into **atomic claims** for per-claim UQ (matches the per-belief model).

### 2.6 Science-of-science: trajectory (E5) & experiment-value (E7)
- **UPDATE — E5 "trajectory beats static" is genuinely untested (3.1)** → a real contribution *if* earned in Persona's own ≥20-seed head-to-head, not asserted. The **independence** component is strongly confirmed in Persona's exact domain (Danchev/Rzhetsky/Evans, *eLife* 2019: decentralized communities **+45% replication**; Belikov et al., NMI 2022). The **citation-velocity** component is contradicted as a *leading* indicator (PNAS 2023: citations fall only *after* a failed replication). → **lead E5 with independence-drift; treat citation velocity as secondary and inflation-normalized.**
- **CHALLENGE — "collapse" is not one label (3.1).** Retraction (misconduct-dominated, ~87% predictable from bibliometrics), replication-failure (statistical, and the text-ML baseline is contested as *style*-learning — PNAS 2023 critiques), and abandonment (decay) are different phenomena → **typed heads / stratified reporting**, validated against Retraction Watch / DARPA SCORE / citation-decay separately.
- **CHALLENGE — raw temporal citation features are confounded** by citation inflation (the disruption/CD index is dismantled cross-time, QSS 2024) and publication-year base rate dominates retraction ML → **inflation-normalize + era-control** or E5 reproduces the artifact (the CLAUDE.md §1 "flattering-but-wrong" trap). Sobering ceiling: DARPA SCORE Round 1 — *no team beat a constant-0.5 baseline*.
- **CONFIRM — E7 (VoI÷cost ranking) is an open gap** (defensible "first" claim). Pieces exist (health-econ EVPI/EVSI is the rigorous seminal base — cite it; BED-LLM computes LLM EIG; AI co-scientist Elo-ranked and beat experts on 11 goals) but no one has shown "VoI÷cost beats baseline, judged by experts" at biomedical literature scale. **UPDATE the baseline**: beat the **Open Targets genetic-evidence prior** (Minikel, *Nature* 2024, **2.6× clinical success**), not raw citations (a straw man). The VoI estimate itself is noisy (BoxingGym ICLR'25: LLMs mediocre at EIG-optimal design) → **calibrate the VoI estimate** before trusting the ranking.

### 2.7 Net changes the literature forces (propagated below)
1. **Ignition is human-gated, not autonomous.** The self-test loop still *closes* (money-shot intact), but contradiction detection is a high-precision **surfacing** step → context-divergence filter → **human handoff**, and the human sign-off is what lets a conclusion anchor. (Steps 4/6.) The autonomy lives in reading, dossier-assembly, and *first-pass* reanalysis — not in believing.
2. **Membrane emits a typed contradiction** (`true-refutation / context-divergence / no-evidence`) and defines **convergence as evidential independence** + citation-echo screen + power prefilter — not agreement count. (Steps 4/5.)
3. **Memory goes two-tier + bi-temporal**; "anchoring" → provenance-typed **write-policy**; E8 oracle gains a **MINJA-style injection** attack. (Steps 1/4/6.)
4. **Reasoning stays single-agent** (self-consistency + verification); fan-out confined to read/extract/scout; **backpressure keys on independence, not disagreement**; add checkpoint/observability/guardrails. (Step 6.)
5. **5.3 is `[H]`**: calibration via semantic-entropy/consistency + **conformal thresholds** (E11 sharpened); escalation is decision-theoretic. (Steps 1/4/5.)
6. **E5 leads with independence**, types "collapse", inflation-controls; **E7 beats the genetic-evidence prior**, not citations, and calibrates its own VoI. (Step 4.)
7. **E6 acceptance = rank correlation + IAA-first + label-anchoring + candidate-edges + citation backbone.** Expect the human-in-the-loop downgrade path to be the realistic outcome. (Steps 4/5.)

---

## Step 3 — Verifying the existing experiments

### 3.1 Static analysis (done now, read-only) — findings

**Reproduction setup**
- All three scripts seed deterministically (`exp_when_protection_matters` uses n=50 worlds, seeds `13000+i`), so re-runs should match to the digit.
- **The headline pro-anchoring numbers (100%/76% etc.) come only from `exp_when_protection_matters.py`, which prints and persists no JSON.** The two saved JSONs (`memory_core_results.json`, `memory_v2_results.json`) cover only the *benign-noise* v1/v2 story. → **Reproducing the third script is the load-bearing verification.**
- `exp_memory_core.py` and `exp_memory_v2.py` write to `results/…json` (relative). With no `results/` dir they will crash at the write. Execution step 0 must create `results/` first.

**Confound A — the "all-poisoned recovery" advantage is inflated (real finding).**
In `exp_when_protection_matters.py`: `poison_frac=0.2, K=60` → **12 victims**; `human_confirm_frac=0.15` → **9 human-confirmed, drawn from the 12 victims**. So **~75% of "poisoned" beliefs are human-anchored** and trivially protected (start at ±6 logit, `resist=0.05`). The reported `all-poisoned recovered 0.880 vs 0.683` is therefore dominated by the locked subset, not by better handling of ordinary poisoned beliefs. **The clean, non-circular results are the human-verified retention DURING (1.000 vs 0.762) and AFTER (1.000 vs 0.709).** Also note **quorum alone already reaches 0.950 DURING** — most anti-poison protection comes from the *membrane*; anchoring adds guaranteed protection for the human-confirmed subset specifically. → **Refine the plan's claim** from "anchoring is decisive" to "the membrane does most of the work; anchoring guarantees the human-confirmed core." (Report the non-human-victim recovery separately in the rebuild.)

**Confound B — anchoring is never tested when the human is wrong.** By construction all human-confirmed beliefs are seeded *correct*. Anchoring a *wrong* human label = permanent, self-inflicted corruption with no path back. FINDINGS flags this ("add a human-error escape hatch"). → experiment **E9**.

**Confound C — the pro-protection result lives only in the correlated-sustained regime.** v2's corruption burst is *independent* high-noise and naive recovers fine (it's a blip). The entire architectural case rests on "the real threat is correlated, not independent." That premise is asserted, plausibly, but is itself an empirical claim about the literature → validate via Step 2 and the real-corpus replay **E8**.

**Confound D — boolean-channel abstraction.** Real extraction error is *structured* and content-correlated, not a symmetric bit-flip. FINDINGS flags this. → **E8** replays the crossover with real Claude extraction on a seeded poisoned corpus; it is the promotion gate from "sim result" to "architecture we ship."

**Minor:** `RNG_MASTER` in `exp_memory_core.py` is defined but unused; v1 membrane destructively "consumed" evidence (fixed non-destructively in v2). Neither affects conclusions.

### 3.2 Verification-as-gate-0 (first execution action, on approval)
Create `results/`; run all three scripts; diff the two JSONs byte-for-value against the committed ones; capture `exp_when_protection_matters.py` stdout into `results/poison_crossover.json` (add a persist block); write `results/REPRODUCTION.md` recording PASS/FAIL + the Confound-A re-analysis (report non-human-victim recovery separately). **Go/no-go:** the DURING/AFTER human-retention crossover reproduces within CI. If it does not reproduce, that is itself the finding and the membrane design is reopened.

---

## Step 4 — The experiment program (specs + stubs to create)

Each spec: **hypothesis → metric → method → seeds/CI → go/no-go bar → which build step it gates → effort.** Stubs are created under `experiments/` on approval (one file each), pre-registered before the gated piece is built. Not all run now; they are **sequenced against the build** (Step 6). Every result lands in `results/FINDINGS.md` (extended) with the reversal written down if the evidence contradicts the assumption.

**Priority tier 1 — gate a load-bearing, expensive-to-reverse piece:**

- **E8 — real-Claude poisoning replay** *(gates the whole membrane/anchor build).* H: the DURING-attack retention crossover (anchored ≫ naive) persists when the noisy boolean channel is replaced by real Claude claim-extraction over a seeded corpus salted with correlated poison (a fabricated review repeated across many "papers"). Metric: human-verified-belief retention during/after, anchored vs naive vs quorum. Method: 30–50 seeded corpora; real extractor agent; same anchor policy. Bar: anchored retention ≥ quorum ≥ naive with non-overlapping CIs, same ordering as sim. Effort: M. Stub `experiments/exp_e8_real_claude_poisoning.py`.
- **E6 — dependency-edge extraction precision** *(gates 3.2 dependency graph — the biggest differentiator).* **Lit-update (§2.3): primary acceptance metric is RANK correlation, not per-edge precision** — expect per-edge precision <0.7 (no dataset exists; biomedical RE tops 0.88–0.9 P at ~0.6 R; presupposition is a named LLM failure mode). **Run the discriminating pre-check FIRST:** build a 50–150 claim-pair dev set and report **inter-annotator agreement** (Krippendorff α) on the four labels; if IAA is low the target is ill-posed → renegotiate labels *before* spending model budget. Anchor the labels to existing schemas (`derives-from/operationalizes` ≈ ACL-ARC/SciCite Uses/Extends; `presupposes` ≈ concept-prerequisite). H: computed load-bearing rank correlates (Spearman ≥ 0.5) with an expert "what's foundational" ranking; emit **candidate edges with calibrated confidence** into `INFERRED` provenance (never fact) + a **citation-graph backbone** so the ranking survives poor edge precision. Bar: if rank-correlation < 0.5 or IAA too low → **downgrade 3.2 to human-in-the-loop assisted** (the expected, honestly-labelled outcome) in the UI. Effort: L (annotation is the cost). Stub `experiments/exp_e6_dependency_extraction.py`.
- **E11 — calibration method selection** *(gates the confidence field + membrane gate + escalation trigger).* H: a **sampling/consistency** signal (semantic entropy / SAR / SE-probe — **not** verbalized confidence, which RLHF makes overconfident) gives per-claim confidence with low ECE + good risk-coverage, good enough to (a) gate the membrane and (b) drive escalation. **Lit-update (§2.5):** use **LM-Polygraph** to pick the estimator empirically; set the gate/escalation cutoff via **conformal selective-prediction** (SConU/COIN) for a *provable* error rate; make escalation **decision-theoretic (uncertainty × stakes)**; decompose long syntheses into atomic claims. Method: on a labelled biomedical claim set, compare estimators' ECE + risk-coverage; validate on biomedical QA (calibration is specialty-dependent). Bar: pick the best; if none clears, escalation reverts to a conservative rule and we say so. Effort: M. Stub `experiments/exp_e11_calibration.py`.

**Priority tier 2 — engine instruments (each has a clean go/no-go):**

- **E5 — trajectory vs static collapse backtest** *(gates 3.1 / argument-state).* H: trajectory features (evidence velocity/acceleration, independence-ratio drift, citation-vs-support divergence) predict eventual collapse (retraction / failed replication / trial-stoppage) better than any static score (citation count, static support ratio), under *proper temporal splits* (freeze at T, predict T+Δ). Metric: AUC trajectory vs AUC static, pre-registered margin (propose **+0.05 AUC**). Data: Open Targets trial-stoppage / genetics + ClinicalTrials.gov terminations. **Lit-update (§2.6):** lead with the *independence-drift* feature (validated +45% replication, eLife 2019), not citation-velocity (a *lagging* signal — PNAS 2023); split *collapse* into typed heads (retraction / replication-failure / abandonment), validated against Retraction Watch / DARPA SCORE / citation-decay separately; inflation-normalize + era-control all citation features (the disruption-index artifact); use a *strong* static baseline (Uzzi-text + Open Targets genetic prior), never a straw man. Bar: ship the trajectory model only if it clears the margin over the strong baseline. Effort: M–L. Stub `experiments/exp_e5_trajectory_backtest.py`.
- **E7 — experiment-value ranking vs expert** *(gates 3.4 / experiment queue).* H: VoI÷cost ranking correlates with blinded-expert "worth doing" ranking better than a citation-count baseline. Metric: Spearman(ours, expert) vs Spearman(baseline, expert). **Lit-update (§2.6):** the baseline is the **Open Targets genetic-evidence prior** (Minikel *Nature* 2024, 2.6× clinical success), *not* raw citations (an unconvincing straw man); borrow health-econ **EVPI/EVSI** framing + BED-LLM EIG, and **calibrate the VoI estimate itself** (BoxingGym: LLMs are mediocre at EIG-optimal design). Bar: ours ≥ genetic-prior baseline by pre-registered margin on a curated candidate set. Effort: M (needs expert labels; for the hackathon, use 1–2 domain reviewers or a curated proxy and label the limitation). Stub `experiments/exp_e7_experiment_value.py`.

**Priority tier 3 — safety/validity of choices the plan glosses:**

- **E9 — human-error escape hatch** *(gates anchoring policy).* H: a bounded escape hatch (anchor is resistant, not immune; overwhelming *independent* contrary evidence + a re-escalation trigger can unlock) recovers from a wrong human anchor without reopening the poisoning vulnerability. Metric: recovery-from-wrong-anchor vs retention-under-poison trade curve. Bar: exists a resist/threshold setting that keeps poison-retention high while making wrong-anchor recovery possible. Effort: S (extends the sim). Stub `experiments/exp_e9_human_error_hatch.py`.
- **E10 — online correlated-disagreement detector** *(gates the adaptive membrane switch).* H: a cheap online statistic (source-correlation of disagreement) flips the membrane from fast-path to strict quorum with acceptable precision/latency, so the adaptive policy actually realizes E1's benefit online (E1 tested *fixed* policies, not the switch). Metric: detection AUC + switch latency vs an always-strict baseline's cost. Bar: adaptive ≈ always-strict accuracy at lower latency in benign regimes. Effort: S–M. Stub `experiments/exp_e10_adaptive_switch.py`.
- **E12 — swarm vs single strong agent** *(gates the fan-out investment).* H: bounded fan-out of readers/cross-checkers beats one strong agent on extraction accuracy per token (convergence catches errors a single pass misses). Metric: accuracy vs token cost frontier. Bar: fan-out dominates on the frontier at the demo's scale; if not, shrink the swarm and say so. Effort: M. Stub `experiments/exp_e12_swarm_vs_single.py`.
- **E13 — interests/taste are functional** *(gates the "self" being real, not theater).* H: changing interest weights / the surprise term measurably changes which papers get read and which beliefs update, vs a no-taste control. Metric: divergence in read-set and belief-trajectory across dispositions. Bar: non-trivial, reproducible behavioral divergence. Effort: S–M. Stub `experiments/exp_e13_taste_functional.py`.
- **E14 — evidential-independence estimation** *(gates the convergence gate; elevated to tier-1 by §2.4).* H: despite citation coupling + shared-data confounds, we can estimate whether sources are *evidentially* independent (distinct cohorts/datasets/methods) well enough that a citation-echo screen (Greenberg/Sarol paradigm) blocks amplified single-source claims from passing convergence. Bar: echo-screen precision high enough that "convergence" stops counting propagation as independence. Effort: M. Stub `experiments/exp_e14_independence.py`.
- **E15 — contradiction trigger + typing precision** *(gates the self-test loop ignition; elevated to tier-1 by §2.4).* H: at a high-precision operating point plus a BioDivergence-style context-divergence filter, the flagged `true-refutation` rate is precise enough (report precision/FPR at threshold, ≥20 seeds, vs ContraDetect + BioDivergence oracles) that **human-gated** ignition spends reanalysis compute well. Bar: precision at the chosen threshold clears a pre-registered floor; the loop ignites only via the human handoff for high-stakes. Effort: M. Stub `experiments/exp_e15_contradiction_trigger.py`.

---

## Step 5 — Design concepts (the 7 screens + swarm view)

> Concepts only, per kickoff. Interactive visual mockups via Claude Design (mcp `plan` visual-plan / Artifact) are produced on approval — plan mode blocks publishing them now.

### 5.1 Visual direction (consistent with BUILD_PLAN §6 + `frontend-design`)
A scientist's **bound lab journal crossed with a live systems console** — *not a BI dashboard*. Calm, editorial, high-legibility. Committing to the §6 spec with distinctive (non-"AI-slop") type:
- **Type**: a characterful **monospace** for the researcher's *voice* (notebook, provenance, raw claims) — e.g. IBM Plex Mono / Departure Mono; a **serif** for synthesized reviews and prose state-of-the-argument — e.g. Newsreader / Source Serif; a quiet grotesque only for UI chrome. Deliberately avoid Inter/Roboto/Space Grotesk.
- **Palette**: warm paper / near-black ink base, restrained. **Exactly two accents**, load-bearing not decorative: one for **live activity** (an agent returning, a belief updating) and one for **needs-human** (escalation). Provenance state is encoded by texture/weight, never by a third loud color.
- **Honest-uncertainty encoding**: confidence shown as an explicit interval/bar (from the conformal gate, §2.5); `provenance_state` (READ / INFERRED / HUMAN_CONFIRMED / TESTED) always visible as a glyph or border weight. **An INFERRED belief must never render with the visual authority of a HUMAN_CONFIRMED / TESTED one.** Contradictions render as a **typed** badge (`true-refutation` / `context-divergence` / `no-evidence`, §2.4), never a bare "conflict"; dependency edges render as *candidate* (dashed) until confirmed (§2.3).
- **Motion**: only on real state change (belief flip, agent return, contradiction fires, membrane admit/reject). One orchestrated reveal per event; no ambient animation.

### 5.2 The screens — each answers one real researcher question

| Screen (§6) | Question it answers | Concept |
|---|---|---|
| **Dashboard** (6.1) | "What is this mind, and what is it on right now?" | The Self at a glance: name+disposition; interests as live weighted chips; active programs w/ one-line status; an attention meter; a recent-moves ticker. |
| **Living Notebook** (6.2) | "What is it actually thinking?" | Append-only timestamped stream in the researcher's monospace voice: `noticed → suspected → spawned N → found (3 support/1 contra) → updated X → flagged`. Each line links to evidence + touched belief nodes. The demo's beating heart. |
| **Argument-State** (6.3) | "Where is this question *heading*?" | Per target: trajectory chart (support velocity/acceleration, independence ratio, citation-vs-support divergence), an inflection marker, and a prose state-of-the-argument the researcher rewrites. **Gated by E5** — if E5 fails, ship the chart without the collapse forecast and label it descriptive. |
| **Dependency Graph** (6.4) | "What is this field actually standing on?" | Interactive DAG; nodes sized by downstream dependency mass, colored by independent support; click → fragility preview. **Gated by E6** — if precision < bar, render as human-in-the-loop assisted (suggested edges the user confirms), not automated truth. |
| **Experiment Queue** (6.5) | "What is the single highest-leverage experiment?" | Ranked VoI÷cost list; each row: question resolved, downstream literature de-risked, whether public data exists (one-click → Tester), cost tier. **Gated by E7.** The screen that makes a PI say "I want this." |
| **Human Handoff inbox** (6.6) | "What needs *my* judgment?" | Each item a pre-assembled dossier: the contradiction, evidence both sides, candidate explanations, the exact question. The answer **anchors** a belief and is attributed forever. Frames human as resolver. |
| **Artifacts shelf** (6.7) | "What is its body of work / can I trust it?" | Auto-written mini-reviews (serif, cited, explicit "unresolved dissents"); side-project threads; the **error log** ("times I was wrong") as first-class credibility signal. |
| **Swarm view** (6.8) | "How does scale-of-reading meet discipline-of-believing?" | Live: agents spawn → read → return candidates → the **membrane** admits/rejects into the self. Shows the architecture without a slide. |

**Demo camera path (§6.9):** Dashboard (meet it) → Notebook (watch it think) → self-test loop closing on Argument-State/Experiment screens (watch it *act*) → Handoff inbox (division of labor) → Artifacts. Money-shot: the loop closing on one real contradiction.

### 5.3 Stack (justified, not defaulted — ponytail-lazy where it holds)
- **Backend**: Python (given) — FastAPI serving JSON + **SSE** for the live notebook/swarm stream. The self is already living-docs (`self/*.md`, `beliefs.json`), so much of the UI renders files directly; no heavy state layer needed. **Ingestion is live-early behind a source-agnostic adapter interface** (Europe PMC / Open Targets / ClinicalTrials first; web/dataset/repo adapters next), with an aggressive cache as the resilience backstop.
- **Graph store**: start **SQLite + networkx** (BUILD_PLAN 10.0 suggests this or DuckDB) — a quick test decides only if it doesn't scale to the demo subfield. `[?]` cheap to reverse; no experiment needed unless it stalls.
- **Frontend**: **Vite + React + Motion** for the orchestrated state-change moments; **Cytoscape.js** for the dependency DAG (interactivity the notebook/queue need); lightweight SVG/visx for trajectory charts. Rejected: Streamlit (generic aesthetic fails "not a dashboard"); a pure server-rendered stack (the DAG + live swarm interactivity fight it). This is the minimum weight that delivers the interactive money-shot.

---

## Step 6 — Revised, dependency-ordered build sequence

Improves on BUILD_PLAN §9.6/10.3 by (a) inserting **gate-0 reproduction first**, (b) gating each engine screen on its pre-registered experiment, and (c) inserting the `[?]` experiments the original plan omitted (E8 before the membrane ships; E10 for the adaptive switch; E11 before calibration gates anything). Every step stays demoable (§9.6 invariant). **Scope: full implementation** (spine + Tier-2 + stretch) per the locked decision; **data is live-early** (Step 1 wires real clients behind a source-agnostic adapter + cache). Stretch instruments and the second researcher are steps 8–9.

| Step | Build | Gated by (run first) | Acceptance criteria |
|---|---|---|---|
| **0** | Repro: create `results/`, run 3 experiments, persist crossover, write `REPRODUCTION.md` + Confound-A re-analysis | — | Crossover reproduces within CI; else membrane design reopened |
| **1** | Belief-store schema (5.3) + living-doc self (**two-tier**: small in-context core + retrieved archival, §2.1) + **bi-temporal** claim-graph + `hydrate()`; wire live Europe PMC / Open Targets / ClinicalTrials behind a **source-agnostic adapter + cache**; seed a checkable program (Alzheimer's neuroinflammation) | — | Self can be killed and re-hydrated with **no belief loss**; only the core tier loads into context; a live query returns normalized evidence |
| **2** | Reader+extractor swarm (read-only, harvest-then-commit); **adaptive membrane** emitting *typed* contradictions + **evidential-independence** convergence; production layer (checkpoint/resume, decision-trace observability, cross-checker hard gate, §2.2); notebook v1 | **E8** (real-Claude + MINJA crossover), **E10** (switch), **E12** (fan-out worth it), **E14** (independence) | Membrane tests reproduce the poisoning crossover (reuse `exp_when_protection_matters` as oracle, per 10.1); backpressure keys on independence not agreement; notebook streams real moves |
| **3** | Trajectory engine (3.1, **independence-drift-led** + inflation-normalized, §2.6) + dashboard + argument-state screen | **E5** (vs strong static baseline) | First real trajectory renders; collapse-forecast shown **only if E5 clears the margin over the strong baseline**, else labeled descriptive |
| **4** | Hypothesizer + dataset-scout (**single strong agent + self-consistency**, not an ensemble — §2.2) + **one Claude Science self-test**; **human-gated ignition** (§2.7) | **E15** (trigger + typing precision) | One *human-confirmed* contradiction → hypothesis → located dataset → first-pass reanalysis → write-back that anchors **on sign-off**, end-to-end (pre-run + honest live attempt per §9.7) |
| **5** | Human-handoff inbox + **anchoring** (provenance-typed write-policy, §2.1); dependency graph (3.2) as *candidate* edges | **E9** (escape hatch), **E11** (conformal calibration → escalation), **E6** (rank-correlation + IAA) | One dossier → answered → **anchored** belief; DAG automated **iff** E6 clears the rank-correlation bar, else human-in-the-loop (expected) |
| **6** | Experiment-value queue (3.4); auto mini-review; self-spawned second interest | **E7**, **E13** (taste functional) | Queue ranks better than citation baseline; a self-spawned interest is visible and *changed behavior* (E13) |
| **7** | Always-on autonomous run (overnight + continuous) to fill the notebook | — | Notebook shows hours of autonomous moves; re-run after steps 8–9 to capture the richer behavior |
| **8** | Stretch engine: **silence/abandonment detector** (3.5) + **cross-field mechanism translation** (3.6) + **fragility propagation** (3.3) | **H3.5** (abandonment enriches nulls), **H3.6** (beats embedding baseline), **H3.3** (cascades face-valid) — each pre-registered | Each instrument ships only if its test clears; silence detector surfaces ≥1 real buried null; cross-field surfaces ≥1 checkable synonymous-mechanism win |
| **9** | **Second researcher** with different taste that cites/challenges the first (7.1); polish money-shot; record fallback | — | Two personas visibly disagree on ≥1 belief; disagreement logged as signal; a human can arbitrate; fallback recording exists (§9.7) |

**Standing rule (BUILD_PLAN 10.4):** before any unproven sub-choice inside a step, write its sandboxed test under `experiments/` first, run ≥20 seeds, report mean ± 95% CI, and cite it in a code comment. Reversals get written down.

---

## Decisions (locked with the user)
- **Identity over domain.** Persona is *its own persistent persona*, not a domain tool: given seed interests it diverges autonomously — always-on, reading at scale, self-directed curiosity across **any source it wants** (papers, datasets, websites, code repos, arbitrary media), continuously updating its self/beliefs and doing real scientific questioning. It pulls in a human whenever it needs one to **run/test** something, **resolve** an adjudication, **explore** a lead further, **break a bottleneck**, or **enable/connect** something — a broadened human-interface trigger set (extends §2.4/§3.7). For the demo it still **seeds one sanity-checkable program (Alzheimer's neuroinflammation)** for ground-truth *and* shows a genuinely self-spawned interest — the seed is a starting point, not the identity.
  - **Honesty guard (from §2.2):** "hundreds of agents, always-on" = the **reading/extraction/scout swarm** (the breadth-first niche the evidence blesses), under adaptive budgeted fan-out; **reasoning and believing stay centralized** in the single self (Data-Processing-Inequality result). Always-on requires the production layer (checkpoint/resume, decision-trace observability) added in §2.2.
  - **Source-agnostic ingestion:** build reader/scout agents against a **source-agnostic adapter interface** (biomedical APIs are the first adapters; web/dataset/repo adapters follow) so curiosity isn't fenced to one corpus.
- **Ambition: full implementation.** Target the *whole* vision — spine (§4.1) + Tier-2 "feels alive" (§4.2) + Stretch (§4.3: silence detector 3.5, cross-field translation 3.6, fragility propagation 3.3, a second researcher 7.1). Step 6 is re-scoped to the full arc, preserving the demoable-at-every-checkpoint invariant.
- **UI stack:** Vite + React + Motion + Cytoscape (§5.3).
- **Data posture: live-early.** Wire live Europe PMC / Open Targets / ClinicalTrials (+ source-agnostic scouts) from the start, with an aggressive **cache layer as a resilience backstop** and a pre-run Claude Science result for the money-shot (§9.7). Accept the live-rate-limit risk for a system that visibly reacts to real, new literature.

## Threats to validity carried forward
- Every `[E]` rests on a boolean-channel sim; **E8 is the promotion gate** to real extraction. Until E8, the membrane/anchor design is "well-motivated," not "validated on the real regime."
- E6 is the highest-risk instrument; the plan already has a documented downgrade path (automated → human-assisted). Treat that as the expected outcome until proven otherwise.
- Expert-label experiments (E6/E7) are labor-bound; for the hackathon they use a curated proxy / 1–2 reviewers, and that limitation is stated in the artifact.
