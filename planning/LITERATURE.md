# Current-Literature Review (last ~18 months)
*Persona Phase-0, Step 2. Source: a 6-domain adversarial read-only sweep — 6 Opus-4.8 scouts, 104 web searches, each told to hunt for work that **challenges** the plan and rate every citation's confidence. Raw structured output: `planning/literature_sweep_raw.json`. Citations marked (low) are reconstructed-from-memory / unverified — verify before the paper.*

**One-line takeaway:** the plan's *architecture* (swarm/self split, harvest-then-commit, living-docs memory, human-as-resolver) is well-supported or SOTA; the plan's *epistemics* (autonomous contradiction ignition, binary contradiction, convergence-by-agreement, per-belief calibration "for free", dependency-edge precision, trajectory-beats-static) need the corrections below.

---

## A. Persistent-agent memory & continual learning
| Work | Year | Relevance |
|---|---|---|
| Letta / MemGPT + AgentFile (`.af`) | 2023–25 | Ships the plan's living-docs bet: human-readable, agent-editable memory blocks + serialized stateful self |
| Zep / **Graphiti** (arXiv:2501.13956) | 2025 | Bi-temporal KG memory (valid-from/valid-to, invalidation edges, provenance) — SOTA substrate for belief-over-time |
| Mem0 (arXiv:2504.19413) | 2025 | Adversarial datapoint: graph memory adds only **~2 pts** on LOCOMO at ~1.5× latency |
| A-MEM (arXiv:2502.12110) | 2025 | Note-based memory w/ LLM link-generation + "memory evolution" → the consolidation mechanism |
| Sleep-time Compute (arXiv:2504.13171) | 2025 | Named analog of "consolidation on sleep" |
| MINJA (arXiv:2503.03704, med) / PoisonedRAG (USENIX Sec'25) | 2024–25 | Memory-injection >95% success / one poisoned passage — the anchoring threat is real |
| Titans (arXiv:2501.00663) | 2025 | Parametric test-time memory — the alternative to **explicitly reject** on legibility grounds |

**Verdicts:** CONFIRM living-docs (5.5) and 3-memory-types + consolidation. **UPDATE:** (1) two-tier memory — small in-context core + tool-retrieved archival, don't re-hydrate everything; (2) make the claim-graph **bi-temporal**; (3) reframe "anchoring" as **provenance/trust-tiered write-policy** + a poisoning-defense reranker, and add a **MINJA-style injection** to the E8 oracle. Benchmark the self on **LongMemEval**.

## B. Multi-agent orchestration & swarms
| Work | Year | Relevance |
|---|---|---|
| Anthropic "How we built our multi-agent research system" | 2025 | Orchestrator-worker beat single-agent Opus by **90.2%**; **~80% of variance is token usage**; ~15× cost; subagents never write |
| MAST (arXiv:2503.13657) | 2025 | 14 failure modes: ~42% spec/role ambiguity, ~21% verification gaps |
| Cognition "Don't Build Multi-Agents" | 2025 | Endorses read-only write-free single-purpose subagents as the *only* safe form |
| Tran & Kiela (arXiv:2604.02460) | 2026 | Single agent ≥ multi-agent on multi-hop under matched compute (Data-Processing-Inequality) |
| "Illusion of Multi-Agent Advantage" (arXiv:2606.13003) | 2026 | ~10× cost for negligible gain; redundancy not specialization |
| OpenAI Agents SDK / LangGraph | 2025 | Guardrails as first-class; durable checkpoint/resume |
| "More Rounds, More Noise" (arXiv:2603.16244, med) | 2026 | Correlated same-model errors → agreement is false confidence |

**Verdicts:** CONFIRM swarm/self split + harvest-then-commit + budgeted heterogeneous fan-out (best-evidenced choices in the plan). **CHALLENGE:** don't make hypothesizer/tester a debate ensemble — keep reasoning single-agent + self-consistency. **UPDATE:** backpressure keys on **independence + calibrated uncertainty**, not agent-count agreement; add production layer (checkpoint/resume, observability, guardrails, cross-checker hard gate).

## C. Structured biomedical extraction & the dependency graph (E6)
| Work | Year | Relevance |
|---|---|---|
| KARMA (NeurIPS'25) / MedKGent (~90%) / iKraph (Nat.Mach.Intell.'25) | 2025 | Support/contradict + KG extraction at PubMed scale is SOTA-competitive |
| PaperQA2 / ContraCrow (arXiv:2409.13740) | 2024 | Contradiction edge only **~70% expert-validated** |
| TheoremGraph (arXiv:2606.25363, med) | 2026 | Only large `derives-from` graph — but *formal math* (proofs cite lemmas); ships candidate edges |
| Argument-mining survey (arXiv:2506.16383) | 2025 | Inter-claim dependency beyond support/attack "**firmly open**"; presupposition = LLM failure mode |
| Fuzzy-relation IAA / causal hallucination (arXiv:2510.20345, med) | 2025 | Low inter-annotator agreement on fuzzy relations; LLMs fabricate dependency links |
| ACL-ARC / SciCite | 2018–25 | Existing schemas to anchor labels (Uses/Extends ≈ derives-from/operationalizes) |

**Verdict: CHALLENGE E6.** No dataset/method exists for the four inferential labels; expect per-edge precision **<0.7**. **Fixes (now in the E6 spec):** judge on **rank correlation** not per-edge precision; **measure inter-annotator agreement FIRST** (renegotiate labels if low); **anchor labels to existing schemas**; emit **candidate edges** into INFERRED provenance; add a **citation-graph backbone**. Expect the human-in-the-loop downgrade to be the realistic outcome.

## D. Contradiction detection & convergence
| Work | Year | Relevance |
|---|---|---|
| ContraCrow (arXiv:2409.13740) | 2024 | ~30% wild false-positive; **inter-expert agreement only 75.5%** (a hard ceiling) |
| BioDivergence (arXiv:2606.11208) | 2026 | Most apparent contradictions are **context-divergence**; LLMs separate at ~0.55 acc |
| NLI4CT / SemEval-2024 (arXiv:2404.04963) | 2024 | Biomedical NLI labels flip under paraphrase (consistency 0.73) |
| Greenberg (BMJ 2009 b2680) + Sarol/Schneider (ASIS&T'25) | 2009/25 | Apparent consensus is often **citation echo/amplification**, not independence |
| scite audit (Hypothesis 2023) | 2023 | Citation-stance labels have low real-world recall |

**Verdicts (structural reframe):** **CHALLENGE** autonomous ignition (unsafe at ~30% FP / 75% ceiling) → detection is a **surfacing** step → **human-gated** ignition. **CHALLENGE** binary contradiction → emit **typed** output (`true-refutation / context-divergence / no-evidence`). **CHALLENGE** convergence-by-agreement → define convergence as **evidential independence** + citation-echo screen + power prefilter. CONFIRM detection as a high-recall surfacing mechanism.

## E. Calibration & uncertainty
| Work | Year | Relevance |
|---|---|---|
| Semantic entropy (Farquhar et al., *Nature* 2024) | 2024 | Reference sampling-based UQ signal |
| LM-Polygraph (TACL 2025, arXiv:2406.15627) | 2025 | Toolkit to pick the estimator empirically (MSP/HUQ-MD/SAR/LexSim best for selective QA) |
| SConU (ACL'25, arXiv:2504.14154) / COIN | 2025 | Conformal selective-prediction → provable error rate |
| UQLM (TMLR 2025, arXiv:2504.19254) | 2025 | Tuned ensemble beats any single scorer |
| AbstentionBench (Meta, arXiv:2506.09038) | 2025 | Knowing-when-to-defer is **unsolved**; reasoning FT degrades it |
| Tian et al. (EMNLP'23) | 2023 | RLHF verbalized confidence is overconfident |

**Verdicts:** **UPDATE 5.3** to `[H]` — calibration needs an estimator + per-domain held-out set + drift monitoring, *not* asking the model. CONFIRM membrane gate = selective prediction, driven by **sampling/consistency signals** + **conformal thresholds**. **CHALLENGE** "escalate exactly on uncertain" → escalation is **decision-theoretic (uncertainty × stakes)**, per-domain, audited; decompose long syntheses into atomic claims.

## F. Science-of-science: trajectory (E5) & experiment-value (E7)
| Work | Year | Relevance |
|---|---|---|
| Danchev/Rzhetsky/Evans (*eLife* 2019) | 2019 | Decentralized communities **+45% replication** — validates the independence feature |
| Belikov et al. (NMI 2022) | 2022 | Predicts robust gene-interaction facts from community structure |
| Yang/Youyou/Uzzi (PNAS 2020) + critiques (2023) | 2020–23 | Static text-ML replication ~0.68–0.72 AUC — the baseline to beat, itself contested as style-learning |
| "Failing to replicate predicts citation declines" (PNAS 2023) | 2023 | Citations fall only **after** replication → citation velocity is **lagging** |
| Disruption-index bias (QSS 2024, arXiv:2406.15311) | 2024 | Temporal citation metrics confounded by inflation |
| DARPA SCORE | 2023–24 | Round 1: no team beat a constant-0.5 baseline (sobering ceiling) |
| Minikel (*Nature* 2024, s41586-024-07316-0) | 2024 | Genetic support → **2.6× clinical success** = the real E7 baseline |
| BoxingGym (ICLR'25, arXiv:2501.01540) | 2025 | LLMs are mediocre at EIG-optimal design → calibrate the VoI estimate |
| EVPI/EVSI (health econ) | 2004–15 | The rigorous seminal base for E7's VoI math |

**Verdicts:** **UPDATE E5** — "trajectory beats static" is genuinely untested (a real contribution *if earned*); lead with **independence-drift**, not citation velocity; **type "collapse"** (retraction/replication/abandonment); inflation-normalize. **CONFIRM E7** is an open gap — but **beat the genetic-evidence prior**, not raw citations, and **calibrate the VoI estimate**.

---

## Net changes forced into the plan (see PHASE0_PLAN.md §2.7)
1. **Human-gated ignition** (contradiction = surfacing → handoff). 2. **Typed contradiction** + **convergence = evidential independence**. 3. **Two-tier + bi-temporal memory**; anchoring → **write-policy** (+MINJA in E8). 4. **Single-agent reasoning**; backpressure on independence; production layer. 5. **5.3 = `[H]`**; conformal calibration; decision-theoretic escalation. 6. **E5 independence-led / typed / inflation-controlled**; **E7 vs genetic prior**. 7. **E6 = rank-correlation + IAA-first + candidate edges**.
