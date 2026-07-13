# PRD-01 — Heterogeneous agent teams

> Owner: implementer lane 1 · Status: DRAFT-for-implementation · Autonomy: Balanced · Depends on: FC-2 (`inbox.file_handoff`), FC-5 (`calibrate.admit_decision`) · Provides: FC-1

---

## 0. Summary and how this lane advances the vision (5-8 sentences)

Today the swarm is homogeneous: every investigation runs the same deliberately-linear eight-step chain (`research/investigation.py:36-45`), workers are anonymous slots that read a `task.type` off the queue (`daemon/worker.py:22-28`), and each paper is read exactly once with no second opinion (`reading/reader.py:130`). That is "scale of reading" without the matching "discipline of believing" the product thesis promises — there is no inter-agent critique, no independent verifier, no cross-check on the papers that actually feed a contradiction, and no way to spend more scrutiny on the claims that deserve it. This lane makes the team **heterogeneous and value-aware**: a dedicated tool-grounded Verifier that re-runs the actual check on contested claims, a two-reader cross-check on the highest-value papers, a gated debate step that fires *only* when the membrane says convergence is low, span-weighted consensus that protects a lone grounded dissenter instead of outvoting it, and a surprise-ranked tension queue so the swarm investigates the claims most likely to overturn a belief first. Crucially, every added agent is **selective** — the recent literature (VerifiAgent, conditional MAD, "When Does Verification Pay Off") is unanimous that unconditional multi-agent machinery is expensive noise, so each new agent declares an *applicability gate* and emits an explicit "skipped / not-applicable" state distinct from "passed". The lane also closes two loops the map flagged open: a weakened/refuted ledger entry re-enqueues a *fresh* investigation with the new contradicting evidence attached, and Lane 2/Lane 3 conflict verdicts open investigations through one narrow seam (`investigation.open_from_conflict`, FC-1) without touching queue internals. Nothing here auto-anchors a belief or writes to the self; the swarm still only READS, humans still anchor every high-stakes claim, and every new record is provenance-typed and exact-span grounded. The result reads as a *lab of specialists* over the shoulder — a reader, a verifier, a critic, a debate panel, an orchestrator — each move legible in the notebook stream.

---

## 1. File ownership (this lane's DISJOINT set)

**New files (this lane creates):**
- `persona/agents/verifier.py` — the tool-grounded Verifier agent (F1.2).
- `persona/agents/debate.py` — the gated debate step (F1.4).

**Edited files (this lane owns the edits):**
- `persona/agents/analyst.py` — accept branch/sub-hypothesis params for DAG fan-out (F1.1); already exposes `investigate(question, *, evidence_claim_ids=…)`.
- `persona/agents/critic.py` — add a `critique_gather()` intermediate-evidence check (F1.8).
- `persona/agents/revisit.py` — re-investigation trigger on weakened/refuted (F1.9).
- `persona/agents/director.py` — value-aware assignment weighting (F1.7).
- `persona/agents/discover.py` — expose idea value for queue priority (F1.7).
- `persona/agents/deliberate.py` — no functional change expected; **read-only reference** for interest weights (F1.7). *If no edit is needed, drop it from the touched set at implementation time (ponytail: don't touch a file you don't change).*
- `persona/research/investigation.py` — branching/DAG plan + `open_from_conflict` (F1.1, F1.10, FC-1).
- `persona/daemon/supervisor.py` — schedule the new task types (`verify`, `debate`) and the re-investigation trigger (F1.2, F1.4, F1.9).
- `persona/daemon/queue.py` — surprise/value-weighted lease ordering + `verify`/`debate` enqueue paths (F1.6, F1.7).
- `persona/reading/extract.py` — two-reader cross-check helper `cross_check_claims()` (F1.3).
- `persona/reading/reader.py` — invoke cross-check on high-value papers; emit disagreement event (F1.3).

**Boundary files another lane also touches — decoupled by an FC:**
- `persona/daemon/worker.py` — the handler registry. This lane registers `@handler("verify")` and `@handler("debate")`. Other lanes register their own handlers in the same file. **Decoupling:** the `@handler(name)` decorator (`worker.py:15`) means each handler is an independent additive registration; two lanes appending disjoint `@handler` blocks do not collide on logic, only on file text. **Merge protocol:** append handlers at the end of the file, never re-order the registry; if a genuine conflict arises it is a text merge, not a contract change. Flagged here so the master can serialize the final worker.py merge.
- The consensus record `{claim, admit_votes, weighted_support, dissent:[…]}` (F1.5) is **produced by this lane** and **consumed by Lane 2's membrane** — this is FC-1, so the shape is frozen below and neither side redefines it.
- `investigation.open_from_conflict(conflict_id, evidence_claim_ids=None)` (F1.10) is **provided by this lane** (FC-1) and **called by Lane 2** (conflict-review verdicts) and **Lane 3** (fieldmap contradictions). Frozen signature below.

---

## 2. Frozen contracts (verbatim)

**FC-1 — this lane PROVIDES:**
- Queue task types `"verify"`, `"debate"`.
- `investigation.open_from_conflict(conflict_id, evidence_claim_ids=None) -> Investigation`.
- Consensus record shape: `{claim, admit_votes:int, weighted_support:float, dissent:[{claim_id, span, weight}]}`.

**FC-2 — this lane CONSUMES (Lane 2 provides, `persona/inbox.py`):**
- `inbox.file_handoff(kind:str, dossier:dict) -> handoff_id:str`.
- Dossier schema = `{decision_requested, why_unresolvable, disagreeing:[{claim_id,span,qualifiers}], conflict_type:'temporal'|'semantic'|'misinformation'|'insufficient', cheapest_test:{action,cost_tier,dataset}, expected_updates:[{outcome,belief_change}], uncertainty, authority_boundary}`.

**FC-5 — this lane CONSUMES (Lane 2 provides, `persona/memory/calibrate.py`):**
- `calibrate.admit_decision(candidate:dict) -> {admit:bool, calibrated_p:float, route:'commit'|'human'|'reject', reason:str, bound:float}`.

**Milestone-0 obligation for this lane:** land `persona/agents/verifier.py` and `persona/agents/debate.py` with the exact public signatures below returning typed empty/fixture results, register `@handler("verify")`/`@handler("debate")` no-op stubs in `worker.py`, and land `Investigation.open_from_conflict` returning a real (empty-plan) Investigation, so Lanes 2/3 can wire against them from hour 1. Consume FC-2/FC-5 behind a **narrow import-guarded shim** (try/except ImportError → typed default) until Lane 2 lands them, so this lane never hard-blocks on Lane 2's stub timing.

---

## 3. Features

### F1.1 — Branching / DAG investigations

- **Problem & evidence.** `DEFAULT_PLAN` is a hardcoded linear chain (`research/investigation.py:36-45`) and `launch()` wires each step to depend on exactly the previous one (`investigation.py:130-146`, `depends_on=[prev_id]`). A real investigation with two independent sub-hypotheses must run them serially even though the queue's dependency engine already supports arbitrary DAG joins (`queue.py:111-129`, `lease()` waits on *all* of `depends_on`). The map itself says "DAG is gold-plating until needed" — so this ships the fan-out **only** where a question decomposes, keeping the linear default. Research backing: least-to-most / plan-decompose prompting (Zhou et al., arXiv:2205.10625) — decomposing into independently-verifiable sub-problems raises solve rate on compositional tasks; the point is *legible decomposition*, not depth.
- **Design.** In `investigation.py`:
  - Add a decomposition helper (pure, no model): `def _branch_plan(sub_hypotheses: list[str]) -> list[dict]` that, given ≥2 sub-hypotheses, emits parallel `analyze` (`investigate`) steps — one per sub-hypothesis — that all depend on the shared `harvest` step, then a single `synthesize` step that depends on *all* the parallel analyze steps (the DAG join). Falls back to `DEFAULT_PLAN` when `len(sub_hypotheses) < 2`.
  - Extend `Investigation.create(question, *, specialization="", plan=None, sub_hypotheses: list[str] | None = None)` — when `sub_hypotheses` is given, `plan = _branch_plan(sub_hypotheses)`. Signature stays backward-compatible (new kw-only arg, default None).
  - Extend `launch()` to honor a per-step `depends_on: list[int]` (indices into the step list) instead of the implicit "previous only": each step dict gains an optional `"deps": [idx,…]`; `launch()` maps step-indices → task-ids and passes the full list to `queue.enqueue(..., depends_on=[…])`. When `"deps"` is absent it falls back to the current previous-step behavior, so `DEFAULT_PLAN` is unchanged.
  - Legibility: `plan.md` already lists steps (`investigation.py:84-86`); extend it to render the DAG as an indented tree (parallel steps under their shared parent) so the folder-per-investigation stays the readable artifact. One folder, one `plan.md`, branches visible.
  - `analyst.investigate` already takes the sub-question as `question` and `evidence_claim_ids` — the fan-out threads each sub-hypothesis as its own `question` (edit `launch()`'s param-threading at `investigation.py:131-138`).
- **Epistemic guardrails.** No new belief type. Each parallel analyze step is a normal `investigate` run that must still ground conclusions in exact claim IDs (`analyst._finish_error`, `analyst.py:118-151`) and only records a SUPPORTED computational conclusion to the TESTED-provisional ledger (`analyst.py:444-462`). The join step (`synthesize`/`consolidate`) does not invent — it cites the sub-reports. Human-anchor gate unchanged.
- **Required experiment.** **RQ-HT01 — does branching find the answer with fewer paid steps than the linear chain on decomposable questions?** Hypothesis: on a fixed set of ≥20 seeded decomposable questions (two independent sub-claims each), the branch plan reaches a SUPPORTED-or-refuted verdict on the parent in ≤ the linear chain's paid-model-call count, with no drop in grounding rate (fraction of conclusions with a valid claim ID). Metric: paid-model-calls-to-verdict (mean ± 95% CI, 20 seeds) and grounding-rate. Go/no-go gate: branch ≤ linear on calls AND grounding-rate not worse by >2pp; else ship linear-only and log the reversal. `experiments/exp_ht01_branch_vs_linear.py`, results to `/results`.
- **Acceptance criteria.** (1) `Investigation.create(q, sub_hypotheses=["a","b"])` produces a plan whose two `investigate` steps share the harvest dep and both feed one synthesize step; `DEFAULT_PLAN` path byte-identical to today. (2) Runnable check: `pytest tests/test_investigation_branch.py::test_branch_dag_join` asserts the synthesize step's `deps` contains both analyze indices and that `launch()` enqueues them with the right `depends_on` task-ids.
- **Effort** M · **Dependencies** none (uses existing queue DAG engine).

---

### F1.2 — Dedicated tool-grounded Verifier agent

- **Problem & evidence.** Verification today is entangled with authorship: the analyst writes *and* self-grades (`analyst.py:433-462`), and `critic.py` reviews prose but runs no code. There is no independent agent that re-executes the actual statistical/data check. Map gap: "workers generic (no roles visible to queue)". Research: **VerifiAgent** (arXiv:2504.00406) — a unified verifier combining meta-verification + tool-based checking beats self-verification and cuts cost; **CRITIC** (Gou et al., arXiv:2305.11738) — LLMs correct themselves reliably *only* when grounded in external tool feedback, not introspection; **"When Does Verification Pay Off?"** (arXiv:2512.02304) — verification is net-positive **selectively**, on contested/high-stakes items, and net-negative if applied to everything.
- **Design.** New `persona/agents/verifier.py`:
  - `def verify(claim_id: str, *, parent_id=None, evidence_claim_ids: list[str] | None = None) -> dict` — returns `{ok, claim_id, verdict:'supported'|'refuted'|'inconclusive'|'not_applicable', check_kind, ran_code:bool, artifact_ids:[str], span:str, note}`.
  - **Applicability gate first (correctness boundary).** `_is_verifiable(claim) -> (bool, reason)`: a claim is verifiable-by-this-agent only if it has an exact-span quote AND is either (a) a computational/statistical claim reproducible from public data, or (b) a math/theoretical claim (`effect_sign == "na"`) routable to `reason.prove`. Anything else returns `verdict="not_applicable"` with the reason — **an explicit skipped state distinct from a pass** (honors the applicability-gate discipline). This prevents the out-of-domain false-positive that the epistemic charter names as the correctness boundary.
  - Reuse, don't rebuild (ponytail): the Verifier is a **thin router over existing execution**, not a new sandbox loop. Computational claims → `analyst.investigate(statement, evidence_claim_ids=[claim_id, …])` with a verification-framed question ("Reproduce or refute: <claim>"); math claims → `reason.prove(statement)`. The Verifier's own contribution is the *independence* (fresh context, no access to the original author's reasoning), the applicability gate, and a strict verdict mapping from the run result. `# ponytail: router over analyst/reason, not a second sandbox — a bespoke verifier loop is the thing we delete.`
  - Registration: `@handler("verify")` in `worker.py` (append). Params: `{claim_id, evidence_claim_ids}`.
  - **Selective routing (the whole point).** Verification runs ONLY on contested/high-stakes claims. Two triggers, both in `supervisor.py`: (1) a claim that is one side of a live contradiction (`kg.contradictions()`, `kg.py:217`); (2) a candidate the membrane routes to `human` or flags high-stakes via FC-5 (`calibrate.admit_decision(...).route == 'human'`). Never enqueue `verify` for an uncontested, low-stakes READ claim. Cap: at most one `verify` per contradiction per scheduler tick (reuse the `_announced` de-dup pattern from `membrane.py:34-46`).
- **Epistemic guardrails.** The Verifier writes **nothing** to the self and never anchors. A `supported` verdict on a computational claim records a TESTED-provisional entry via the existing `verified.record(..., method="analyst", source="verify")` path (`verified.py:49`) — same gate as the analyst, no new authority. A `refuted` verdict does NOT delete the belief; it emits a `belief_update` event and (F1.9) can trigger re-investigation, but the human still anchors any high-stakes reversal. `not_applicable` is logged as a neutral control event (like the membrane's held-back-claims event, `reader.py:169`), never as a failure.
- **Required experiment.** **RQ-HT02 — does selective verification improve net decision quality vs no-verify and vs verify-everything?** Hypothesis: routing `verify` to contested/high-stakes claims raises the fraction of correct admit/reject decisions on a labeled set of ≥20 seeded (contested-true, contested-false) claim pairs, at lower total cost than verify-everything. Metric: decision-accuracy and cost-per-correct-decision (mean ± 95% CI). Go/no-go: selective ≥ verify-everything on accuracy AND strictly cheaper; selective > no-verify on accuracy. Else: keep no-verify and log why. `experiments/exp_ht02_selective_verify.py`.
- **Acceptance criteria.** (1) `verify(claim_id)` on a non-computational, non-math claim returns `verdict="not_applicable"` and does NOT call the sandbox or the model. (2) On a computational claim it produces a verdict and, if supported+computational, one TESTED-provisional ledger entry with `source="verify"`. (3) Runnable check: `pytest tests/test_verifier.py::test_applicability_gate_skips_non_verifiable` asserts `not_applicable` + zero model/sandbox calls (mock the sandbox, assert not called).
- **Effort** M · **Dependencies** FC-5 (routing trigger; shimmed until Lane 2 lands it), existing `analyst`/`reason`.

---

### F1.3 — Two-reader cross-check on high-value papers

- **Problem & evidence.** Every paper is read exactly once (`reader.read_work`, `reader.py:130`) and its claims pass one verbatim-span gate (`extract.validate_claims`, `extract.py:115`). A single extraction on a paper that *feeds a contradiction or evidence packet* is a single point of failure — an extraction slip on a load-bearing paper silently biases the whole tension. Map gap: "extraction single-shot per paper". Research: self-consistency / sample-and-agree (Wang et al., arXiv:2203.11171) — agreement across independent samples is a strong reliability signal; applied here as **two independent extractions must agree** before a claim from a high-value paper is trusted.
- **Design.** In `extract.py`, new pure helper:
  - `def cross_check_claims(text: str, title: str = "", *, model_a=None, model_b=None, client=None) -> tuple[list[dict], list[dict], dict]` → `(agreed_claims, disagreements, usage)`. Runs `extract_claims` twice — either same model / different temperature or two models (`model_a=config.MODEL_READER`, `model_b` defaulting to the same) — validates each pass with the existing `validate_claims` (so every claim is still exact-span grounded), then **matches on the frozen claim identity** `subject|relation|object|effect_sign` (the same key `reader._claim_id` computes, `reader.py:27-29`). A claim in the intersection is `agreed`; a claim in exactly one pass is a `disagreement` (kept, but flagged, never silently admitted).
  - In `reader.read_work` (`reader.py:161-181`): gate the second read on **value**, not on every paper (cost discipline). A paper is high-value if it will feed a contradiction/evidence packet — detect via `interest`/params carrying a `cross_check=True` flag set by the caller (the `gather` handler for investigation evidence, `worker.py:99-120`, and any read spawned from a contradiction). Default path = single read, unchanged. When `cross_check`, call `cross_check_claims`, write `agreed` to `claims.jsonl` (the trusted set), write `disagreements` to a new `claims_disputed.jsonl`, and emit a **legible disagreement event**: `log().emit("control", f"two readers disagreed on {n} claim(s) in <title>", actor="membrane", …)` (mirrors the held-back event at `reader.py:169`). Disagreement is its own event, not a hidden drop.
- **Epistemic guardrails.** Both passes go through `validate_claims` — no cross-checked claim escapes the verbatim-span gate. Only **agreeing** claims land in `claims.jsonl` (what the membrane harvests, `membrane.py:89`), so the belief graph only ingests claims two independent reads confirm from a high-value paper — a stricter membrane, not a looser one. Disagreements are preserved (auditable) and surfaced, honoring "show the funnel". No confidence is fabricated: agreement is a count, not a model self-report.
- **Required experiment.** **RQ-HT03 — does two-reader agreement raise extraction precision on load-bearing papers enough to justify the second read?** Hypothesis: on ≥20 seeded papers with human-checked gold claims, the two-reader-agree set has higher precision than single-read at acceptable recall loss. Metric: precision/recall of admitted claims (mean ± 95% CI, 20 seeds/papers). Go/no-go: precision up ≥5pp with recall loss ≤10pp; else restrict cross-check to contradiction-feeding papers only (narrower) or drop and log. `experiments/exp_ht03_two_reader.py`.
- **Acceptance criteria.** (1) `cross_check_claims` returns only claims present-and-valid in both passes as `agreed`; a claim in one pass appears in `disagreements`. (2) A single-read paper (no `cross_check` flag) is byte-identical to today. (3) Runnable check: `pytest tests/test_cross_check.py::test_only_agreeing_claims_admitted` with two stubbed extraction outputs (one shared claim, one divergent) asserts the shared claim in `agreed`, the divergent in `disagreements`.
- **Effort** M · **Dependencies** none (pure extend of extract/reader).

---

### F1.4 — Gated debate step

- **Problem & evidence.** No inter-agent debate exists; disagreements are resolved by counting or by the analyst's own judgment. But unconditional debate is a known trap. Map gap: "no inter-agent critique/debate". Research: **conditional multi-agent debate** (arXiv:2505.22960) — debate helps *only* on hard/ambiguous items and hurts on easy ones, so it must be *triggered*, not default; the **"deliberative illusion"** (arXiv:2606.03032) — multi-agent deliberation can manufacture false confidence, so the raw agreement number must be logged, not just the verdict; **anonymization in debate** (arXiv:2510.07517) — de-identifying which agent said what reduces sycophancy/anchoring. All three say: gate it, cap it, measure it, anonymize it.
- **Design.** New `persona/agents/debate.py`:
  - `def debate(claim: str, positions: list[dict], *, rounds: int = 2, parent_id=None) -> dict` → `{ok, resolved:bool, verdict:str, agreement:float, rounds_used:int, transcript_ref:str, escalate:bool}`. `positions` = de-identified reader/analyst outputs: `[{"span": <verbatim quote>, "stance": "+"|"-"|"0"|"na"}]` — **no author identity** passed to the model (honors arXiv:2510.07517). Cap `rounds` (default 2, hard max 3).
  - `agreement` = the self-consistency-equivalent number: fraction of the panel converging on the majority verdict at the final round. **Always logged beside the verdict** (honors the deliberative-illusion finding) — a high verdict with low `agreement` is surfaced as unresolved, not sold as confident.
  - **Gate (the whole point).** Debate is enqueued ONLY when the membrane reports **low convergence** or **high stakes**. Consume FC-5: after `calibrate.admit_decision(candidate)`, if `route == 'human'` OR `bound` is wide (calibrated_p far from 0/1 within `bound`), the supervisor may enqueue `debate`. Never debate a cleanly-admitted or cleanly-rejected candidate. Registration: `@handler("debate")` in `worker.py`.
  - Resolution: if `resolved and agreement >= τ` → emit the verdict as a normal candidate back through the membrane (Lane 2 decides admit). If `not resolved` (low agreement) → **escalate, don't outvote**: file a handoff via FC-2 `inbox.file_handoff("debate_unresolved", dossier)` where the dossier's `disagreeing` carries each position's `{claim_id, span, qualifiers}` and `conflict_type` is set from the debate. This is the human-anchor path.
- **Epistemic guardrails.** Debate never writes a belief directly — its output is a *candidate* re-entering the membrane, or a *handoff* to a human. No fabricated confidence: `agreement` is a measured convergence fraction, surfaced verbatim; the deliberative-illusion guard means a confident-sounding but low-agreement verdict routes to human. De-identification prevents sycophancy. Rounds capped so it can't spin. High-stakes reversal stays human-anchored.
- **Required experiment.** **RQ-HT04 — does gated debate resolve genuinely-ambiguous tensions without corrupting easy ones?** Hypothesis: firing debate only on low-convergence/high-stakes candidates improves resolution accuracy on a labeled set of ≥20 ambiguous tensions while never being invoked on (and thus never harming) the unambiguous ones. Metric: resolution-accuracy on ambiguous set + invocation-count on easy set (must be ~0), mean ± 95% CI. Go/no-go: accuracy on ambiguous up vs no-debate AND easy-set invocations = 0; else tighten the gate or drop. `experiments/exp_ht04_gated_debate.py`.
- **Acceptance criteria.** (1) `debate` receives positions with no author identity (assert the prompt contains no actor names). (2) `agreement` is always present in the return and in the logged event. (3) Low-agreement → `escalate=True` and a handoff is filed, not a belief written. (4) Runnable check: `pytest tests/test_debate.py::test_low_agreement_escalates` asserts `escalate=True` and that `inbox.file_handoff` was called (mock).
- **Effort** L · **Dependencies** FC-2 (handoff), FC-5 (gate) — both shimmed until Lane 2 lands them.

---

### F1.5 — Span-weighted consensus with protected dissent

- **Problem & evidence.** Convergence today is a **count** of independent labs (`kg.beliefs(min_independent=…)`, `kg.py:204-215`; `membrane.py:118`). A count lets a swarm of weakly-grounded agreers bury a single strongly-grounded dissenter — exactly the failure the epistemic charter warns about. Map: consensus is vote-based, no dissent protection. Research: **"Voting or Consensus?"** (arXiv:2502.19130) — consensus protocols that weight by evidence quality beat majority voting on multi-agent factuality, and preserving minority-but-grounded positions avoids majority collapse.
- **Design.** New pure function, in `investigation.py` (it is investigation-scoped aggregation, keeping FC-1's producer local) — or a small `persona/agents/consensus.py` if the master prefers a dedicated module; **default: put it in `verifier.py` alongside the verdict logic to avoid a one-function file (ponytail).**
  - `def span_weighted_consensus(reader_outputs: list[dict]) -> dict` → the **FC-1 consensus record** `{claim, admit_votes:int, weighted_support:float, dissent:[{claim_id, span, weight}]}`. Each `reader_output` = `{claim_id, subject, relation, object, effect_sign, span, confidence, independent_lab:bool}`.
  - Weight = a function of **exact-span quality**, not vote count: a claim with a verbatim, specific span (has qualifiers / magnitude / n) weighs more than a bare assertion. `weighted_support` = sum of pro-stance weights / total weight. `admit_votes` = raw count (kept for legibility/comparison).
  - **Protected dissent (the rule).** A dissenter with a high-quality span above a floor `w_min` is NOT outvoted: it always appears in `dissent[]`, and if its weight exceeds the protection threshold the record sets a flag that Lane 2's membrane reads to route to human rather than admit-by-majority. A lone grounded dissenter → escalation, never silent loss.
  - Emit the record for Lane 2 to consume at the harvest/membrane seam (Lane 2 owns the admit decision; this lane only *produces* the record).
- **Epistemic guardrails.** This IS an epistemic guardrail. Weighting by span quality operationalizes exact-span grounding at the aggregation layer; protected dissent operationalizes "abstain/escalate rather than fabricate consensus". No confidence is invented — `weighted_support` is a deterministic function of stored span features. The record never itself anchors; it hands the decision to the calibrated membrane (FC-5) and, on protected dissent, to a human (FC-2).
- **Required experiment.** **RQ-HT05 — does span-weighted consensus with protected dissent beat majority voting on adversarial agreement?** Hypothesis: on ≥20 seeded tensions where the *majority* is wrong but weakly grounded and the *minority* is right and strongly grounded, span-weighted+protected-dissent recovers the correct verdict (or escalates) more often than majority voting. Metric: correct-or-escalated rate (mean ± 95% CI). Go/no-go: strictly beats majority voting on the adversarial set with no worse than −2pp on the easy (aligned) set. **Reuse `experiments/exp_when_protection_matters.py` as the oracle** — it already encodes the correlated-poisoning / weak-majority regime (anchoring retained 100% vs 71% naive, per `/results/FINDINGS.md`); extend it with the consensus function rather than writing a fresh harness. `experiments/exp_ht05_span_consensus.py` (thin wrapper reusing that oracle).
- **Acceptance criteria.** (1) `span_weighted_consensus` returns the exact FC-1 shape (keys `claim, admit_votes, weighted_support, dissent` with dissent items `{claim_id, span, weight}`). (2) A single high-span dissenter against many low-span agreers appears in `dissent` with weight > threshold. (3) Runnable check: `pytest tests/test_consensus.py::test_grounded_minority_protected` asserts the grounded dissenter is in `dissent` and the protection flag is set.
- **Effort** M · **Dependencies** FC-1 (this lane defines the shape), consumed by Lane 2.

---

### F1.6 — Surprise-ranked tension queue

- **Problem & evidence.** The queue leases strictly by `(priority, created_at)` (`queue.py:125`), FIFO within a priority. So the swarm investigates contradictions in arrival order, not in order of how *surprising* (belief-overturning) they are. Map gap: no value-based worker rebalancing; discover.py ranks ideas but the queue ignores it. Research: **SuRe / surprise as a prioritization signal** (arXiv:2511.22367) — surprise (high model NLL / low predictability) is a cheap, effective ranking signal for *what to attend to*, used at inference not training. RQ posed in the brief: does surprise-ranking find validated tensions faster than FIFO?
- **Design.**
  - **Honesty check first (never assume the library).** The Anthropic Messages API does **not** expose per-token logprobs, so a literal "perplexity/NLL of the claim under the reader model" is **not computable from the reader's own API calls**. This is a load-bearing uncertainty — do not design around a capability that isn't there. Two grounded alternatives to test in RQ-HT06: (a) **embedding-novelty surprise** — cosine distance of a new claim's span embedding from the persona's existing belief set, using the free local `bge-small` encoder already in the codebase (`memory/embed.encode`, used at `reader.py:70-73`); a claim far from everything known is "surprising". (b) **contradiction-magnitude surprise** — a new claim that *opposes a high-confidence anchored belief* is maximally surprising (cheap, uses `kg` sign + confidence already stored). Prefer (a)+(b) combined; only reach for a small **local** LM for true NLL if the experiment shows embedding-novelty is insufficient. `# ponytail: no API logprobs — use the local encoder we already load, not a new model dependency.`
  - Compute a `surprise` score at claim-extraction time (`reader.read_work`, after validation `reader.py:163`) and store it on the claim record in `claims.jsonl` (additive field, harvest ignores unknown fields). Pure, local, free.
  - When a contradiction/tension spawns an investigation, map its surprise → queue `priority` (lower number = leased sooner, per `queue.py:125`): `priority = clamp(base − round(surprise * k))`. This reuses the *existing* priority mechanism — **no schema change to the lease query**, just a smarter priority at enqueue. The lease ordering `ORDER BY t.priority, t.created_at` already does the rest.
- **Epistemic guardrails.** Surprise is a **prioritization** signal only — it changes *order*, never *belief*. A surprising claim gets looked at sooner; it still passes the full membrane + grounding gates before anything is believed. No confidence is derived from surprise. The score is a deterministic local computation, logged so the ordering is auditable ("investigating the most surprising tension first").
- **Required experiment.** **RQ-HT06 — does surprise-ranking surface validated tensions faster than FIFO, and which surprise signal?** Hypothesis: ordering the tension queue by embedding-novelty(+contradiction-magnitude) surprise reaches the first *validated* (verifier-supported or human-confirmed) tension in fewer investigations than FIFO. Metric: investigations-to-first-validated-tension (mean ± 95% CI, ≥20 seeded streams of mixed trivial/surprising claims); secondary: compare signal (a) vs (b) vs combined. Go/no-go: combined surprise strictly beats FIFO; pick the cheaper signal if two tie. Else keep FIFO and log the reversal. `experiments/exp_ht06_surprise_rank.py`. **This is load-bearing and the signal is genuinely uncertain — full loop required.**
- **Acceptance criteria.** (1) A claim opposing a high-confidence anchored belief scores higher surprise than a claim restating a known belief. (2) Surprise maps to a lower (sooner) queue priority without altering the lease SQL. (3) Runnable check: `pytest tests/test_surprise.py::test_novel_claim_outranks_known` asserts ordering and that no logprob/API call is made (pure local).
- **Effort** M · **Dependencies** none (local encoder already present); interacts with F1.7 priority.

---

### F1.7 — Director-aware worker prioritization

- **Problem & evidence.** `director.assign_question` (`director.py:43`) picks a *non-overlapping* question but assigns no *value* — every investigation's steps enqueue at a flat `priority=2` (`investigation.py:140`). Meanwhile `discover.py` already elicits a per-idea `value` and `novelty` from the model (`discover.py:33`, tool schema) but that value is written to `ideas.md`/`ideas.jsonl` and then dropped — the queue never sees it. Map gap: no value-based worker rebalancing. (No specific external paper needed — this is wiring an existing signal into an existing knob; the mechanism is priority-scheduling, well-established.)
- **Design.**
  - In `discover.py`: when routing a computable idea to an `investigate` task (`discover.py:104-108`), pass its `value` through. Add `value` to the enqueue params and let it set priority: `priority = clamp(4 − round(value_norm * 3), 0, 6)` (higher value → lower number → leased sooner). `value` is already elicited (`discover.py:33`); just stop discarding it.
  - In `director.assign_question(open_questions, specialization="", *, value_hint: float | None = None)` — accept an optional value and log it; when the supervisor opens an investigation from a high-value question, thread that into `Investigation.launch`'s per-step priority (currently hardcoded `priority=2` at `investigation.py:140`) → `priority=step_priority` where `step_priority` derives from the investigation's value. Keep default = 2 so unvalued investigations are unchanged.
  - This composes with F1.6: surprise (per-claim, reactive) and director-value (per-investigation, deliberate) both feed the *same* priority integer; combine as `priority = clamp(base − round(w1*surprise + w2*value))`. One knob, two inputs, existing lease logic.
- **Epistemic guardrails.** Value/priority affects *scheduling only* — which investigation a worker picks up first — never what is believed or anchored. `value` is a model-elicited *estimate* used for ordering, explicitly not a confidence and never written to a belief. Legible: log "prioritizing the higher-value investigation" so the ordering is auditable.
- **Required experiment.** trivial — no experiment. This is threading an already-elicited scalar into an existing priority field; the priority mechanism is proven (queue lease already orders by it). *Guard:* if combining surprise+value weights turns out to starve low-value work, that's a tuning knob (F1.6's experiment already measures ordering); no separate load-bearing decision here. `# ponytail: reuse the priority int, don't build a scheduler.`
- **Acceptance criteria.** (1) A high-`value` discover idea enqueues an `investigate` task with a lower (sooner) priority than a low-value idea. (2) `assign_question` default behavior (no `value_hint`) is unchanged. (3) Runnable check: `pytest tests/test_director_value.py::test_high_value_gets_sooner_priority`.
- **Effort** S · **Dependencies** composes with F1.6.

---

### F1.8 — Critique of intermediate steps

- **Problem & evidence.** `critic.critique` runs on the *final compiled report* (`critic.py:56`, globs `paper-*/*/paper.md`) — a thin-evidence investigation isn't caught until after the expensive write/compile steps. Map gap: critique only at the end. Research: process-supervision / step-level critique (Lightman et al., "Let's Verify Step by Step", arXiv:2305.20050) — checking *intermediate* reasoning steps catches errors far more cheaply and reliably than outcome-only checking. Here: check evidence *sufficiency after gather*, before paying for analyze/prove/write.
- **Design.** In `critic.py`, new function:
  - `def critique_gather(question: str, *, investigation_id: str = "", parent_id=None) -> dict` → `{ok, sufficient:bool, verdict:'proceed'|'gather_more'|'abandon', gaps:[str], note}`. Runs after the `harvest` step (so evidence is in the KG). It reads the evidence packet for the question (reuse `analyst._evidence_packet`, `analyst.py:88` — already pure, no model) and asks a cheap model call (Haiku, `MODEL_READER`, not the Sonnet worker) one question: *is there enough independently-grounded evidence to investigate this, or is it too thin?* Writes `gather_review.md` into the investigation folder (mirrors `critique.md`, `critic.py:76`).
  - Wire it as a step between `harvest` and `analyze` in `DEFAULT_PLAN` (`investigation.py:36-45`): new step `("check_evidence", "critique_gather", "check evidence sufficiency before spending on analysis")`. Register `@handler("critique_gather")` in `worker.py`.
  - **Early-exit that saves money:** if `verdict == "gather_more"`, enqueue one more `gather` (bounded, once — reuse a counter in investigation meta to prevent loops) instead of proceeding; if `abandon`, mark the investigation `insufficient` and file a low-priority note (not a human handoff — abandonment for thin evidence is routine, not a decision requiring judgment). `# ponytail: one re-gather max, then proceed or abandon — no unbounded gather loop.`
- **Epistemic guardrails.** This is a *sufficiency* check, not a truth check — it never admits or rejects a belief, it decides whether to keep spending. It reads only exact-span-grounded packets (via `_evidence_packet`). Honest: an abandoned investigation is logged as "not enough grounded evidence yet", the correct scientific posture (abstain), not a failure. Cheap model on purpose — no need for the expensive worker to judge sufficiency.
- **Required experiment.** **RQ-HT07 — does post-gather critique cut wasted spend on thin investigations without killing good ones?** Hypothesis: gating analyze/write on a post-gather sufficiency check reduces total model spend on a mixed set of ≥20 seeded questions (some with rich evidence, some with almost none) while not abandoning any question that the full pipeline would have answered SUPPORTED. Metric: spend-saved and false-abandon-rate (mean ± 95% CI). Go/no-go: net spend down AND false-abandon-rate = 0 on the good subset; else loosen the abandon threshold. `experiments/exp_ht07_gather_critique.py`. *(Load-bearing: it can kill work, so the false-abandon gate matters.)*
- **Acceptance criteria.** (1) `critique_gather` on a question with zero grounded evidence returns `verdict != "proceed"`. (2) The step sits between harvest and analyze in the default plan; `abandon` stops downstream steps (their `depends_on` sees a terminal state — reuse the graceful-degradation join, `queue.py:111-115`). (3) Runnable check: `pytest tests/test_gather_critique.py::test_thin_evidence_not_proceed`.
- **Effort** M · **Dependencies** none.

---

### F1.9 — Revisit → re-investigation

- **Problem & evidence.** `revisit.revisit` re-tests a past result and calls `vled.update_status(key, new, note)` (`revisit.py:45`) — it flips the ledger *label* (verified→weakened/refuted) but that's the end of the line. A refuted result just sits there labeled; nothing re-opens the question with the new contradicting evidence. Map: revisit only updates a status label. The analyst already accepts `evidence_claim_ids` (`analyst.investigate`, `analyst.py:178`; worker `_investigate` threads it, `worker.py:305-316`) — the plumbing to attach new evidence exists and is unused by revisit.
- **Design.** In `revisit.py`, after `update_status` (`revisit.py:45`):
  - When `new in ("weakened", "refuted")` AND the drop crossed a threshold (e.g. verified→refuted, or a re-review flipping solid→revise with material issues), **re-enqueue a fresh investigation** carrying the new contradicting evidence. Use FC-1: `investigation.open_from_conflict(conflict_id=<synthetic id for this ledger key>, evidence_claim_ids=<the claim IDs that now contradict it>)` — routing through the single seam (F1.10) rather than poking the queue directly.
  - Source the contradicting evidence: the re-review/re-prove already knows *why* it weakened (`note`, and for analyst-method the critic's issues). Map the ledger statement back to its KG claim(s) and collect the opposing-sign claim IDs from `kg.contradictions()` (`kg.py:217`). If no concrete contradicting claim IDs can be located, pass `evidence_claim_ids=None` (the fresh investigation re-gathers) — never fabricate a claim ID.
  - Idempotency: don't re-open if an active investigation already covers that statement — `director._taken()` (`director.py:21`) already dedups by normalized statement; reuse it.
- **Epistemic guardrails.** Re-investigation is the self-correcting loop working — a refuted belief triggers *fresh grounded work*, not a silent overwrite. The old ledger entry keeps its provenance/history (append-only); the new investigation produces its own TESTED-provisional result subject to the same gates. A high-stakes reversal still routes to a human anchor (the new investigation can end in a handoff). Never fabricate the contradicting evidence — abstain to a re-gather if the exact claim IDs aren't locatable.
- **Required experiment.** trivial — no experiment. This is wiring an existing status-flip to an existing investigation-open seam with the existing `evidence_claim_ids` plumbing; no uncertain modeling choice. The *behavior* is covered by F1.10's seam test + an integration test that a refuted entry produces a new investigation. `# ponytail: connect two existing wires, don't invent a re-investigation engine.`
- **Acceptance criteria.** (1) A revisit that flips verified→refuted enqueues exactly one new investigation via `open_from_conflict`, deduped against active ones. (2) A revisit that holds (verified→verified) enqueues nothing. (3) Runnable check: `pytest tests/test_revisit_reinvestigate.py::test_refutation_opens_investigation` (mock `open_from_conflict`, assert called once on refute, zero on hold).
- **Effort** S · **Dependencies** FC-1 (F1.10 seam).

---

### F1.10 — Route true_refutation → new investigation (`open_from_conflict`)

- **Problem & evidence.** Lane 2's conflict-review verdicts and Lane 3's fieldmap contradictions need to *open work* when a conflict is judged a true refutation — but they must not reach into `queue.py`/`investigation.py` internals (that couples three lanes to the queue schema). There is no seam today: `Investigation.create` + `launch` is the only path and it takes a raw question, not a conflict. This is the FC-1 obligation that unblocks Lanes 2 and 3.
- **Design.** In `research/investigation.py`, new classmethod-level function (FC-1 verbatim signature):
  - `def open_from_conflict(conflict_id: str, evidence_claim_ids: list[str] | None = None) -> Investigation`. Module-level function (matches FC-1's `investigation.open_from_conflict(...)` call form).
  - Body: resolve `conflict_id` → a research question. A conflict is a subject→object tension; build the question string from the KG (`kg.contradictions()` / `kg.provenance(claim_id)`, `kg.py:217,234`) — e.g. *"Does <subject> raise or lower <object>? (<+n> labs vs <−m> labs disagree)"*. Dedup via `director._taken()` — if an active investigation already covers it, return that one (idempotent) rather than opening a duplicate. Otherwise `Investigation.create(question, sub_hypotheses=<the two opposing stances>)` (F1.1 branch plan: one analyze branch per stance), then `.launch(get_persona().queue())`, threading `evidence_claim_ids` into the analyze step params (the analyst consumes them, `analyst.py:178`).
  - Milestone-0 stub: return `Investigation.create(f"conflict:{conflict_id}", plan=DEFAULT_PLAN)` without launching, so Lanes 2/3 have a real object to call from hour 1; fill the KG-resolution + branch + launch afterward.
- **Epistemic guardrails.** The seam opens *work*, not belief — it never anchors or writes a conclusion. `evidence_claim_ids` are passed through to ground the investigation in exact claims; if None, the investigation re-gathers (never fabricates evidence). Every opened investigation is a legible folder as usual. A conflict is only "true refutation" once a human/verifier says so upstream — `open_from_conflict` doesn't itself decide truth, it acts on a decision made elsewhere (candidate_conflict ≠ verified contradiction is respected: the *caller* is responsible for that judgment; this function just opens the follow-up).
- **Required experiment.** trivial — no experiment. It's a routing/plumbing seam; correctness is structural, covered by the seam test below. The uncertain part (branch plan) is F1.1's experiment.
- **Acceptance criteria.** (1) `open_from_conflict("c123", ["clm_a","clm_b"])` returns an `Investigation` whose folder exists and whose analyze step params carry the evidence claim IDs. (2) Calling it twice for the same conflict returns the same (deduped) investigation, not two. (3) Runnable check: `pytest tests/test_open_from_conflict.py::test_seam_returns_investigation_and_dedups`.
- **Effort** S (Milestone-0 stub) → M (full) · **Dependencies** FC-1 (provides), consumed by Lane 2 & Lane 3; uses F1.1 branch plan.

---

## 4. Sequencing within the lane

**Milestone 0 (hour 1, unblocks everyone) — land FC-1 stubs:**
1. `verifier.py::verify(...)` returning `{ok:True, verdict:"not_applicable", …}`; `debate.py::debate(...)` returning `{ok:True, resolved:False, agreement:0.0, escalate:False}`; register `@handler("verify")`/`@handler("debate")` no-op stubs in `worker.py`.
2. `investigation.open_from_conflict(conflict_id, evidence_claim_ids=None)` returning a real empty-plan Investigation (stub body).
3. `span_weighted_consensus(...)` returning the FC-1 record shape from a trivial fixture.
4. Import-guarded shims for FC-2 (`inbox.file_handoff`) and FC-5 (`calibrate.admit_decision`) so this lane compiles before Lane 2.

**Then, in dependency order:**
- **F1.1 (branch plan)** first — F1.10's full body and F1.4's escalation both want the DAG/branch primitive. Ship + RQ-HT01.
- **F1.10 (open_from_conflict full)** next — unblocks Lane 2/3's real use; needs F1.1.
- **F1.5 (span consensus)** — the membrane's admit input; reuses the protection oracle; Lane 2 waits on this shape.
- **F1.3 (two-reader)** and **F1.6 (surprise)** — both touch the reading path; do together to avoid double-editing `reader.py`. RQ-HT03, RQ-HT06.
- **F1.2 (verifier full)** + **F1.9 (re-investigation)** — verifier's refute feeds re-investigation; do adjacent. RQ-HT02.
- **F1.8 (gather critique)** — inserts a plan step; do after F1.1 settles the plan format. RQ-HT07.
- **F1.4 (debate full)** — most machinery, gated last; needs FC-2/FC-5 real. RQ-HT04.
- **F1.7 (director value)** — trivial wiring; slot in whenever F1.6's priority combine lands (shares the knob).

**Rationale:** the plan primitive (F1.1) and the seam (F1.10) are load-bearing for the most other features and other lanes, so they go first; the two reading-path features are batched to touch `reader.py` once; debate is last because it has the most dependencies and the strictest gate.

---

## 5. Test & verification plan

**Unit (pytest, no framework beyond it — ponytail):**
- `test_investigation_branch.py` — branch DAG join wiring (F1.1).
- `test_verifier.py` — applicability gate skips non-verifiable + zero model/sandbox calls (F1.2); mock sandbox.
- `test_cross_check.py` — only agreeing claims admitted, disagreements preserved (F1.3).
- `test_debate.py` — de-identification, agreement always present, low-agreement escalates (F1.4); mock `inbox.file_handoff`.
- `test_consensus.py` — FC-1 record shape + grounded-minority protected (F1.5).
- `test_surprise.py` — novel claim outranks known, pure/local, no API call (F1.6).
- `test_director_value.py` — high value → sooner priority (F1.7).
- `test_gather_critique.py` — thin evidence → not proceed (F1.8).
- `test_revisit_reinvestigate.py` — refute opens one investigation, hold opens none (F1.9).
- `test_open_from_conflict.py` — seam returns Investigation + dedups (F1.10).

**Integration:**
- End-to-end investigation with `sub_hypotheses` runs the branch plan through the real `TaskQueue` (in-memory SQLite) and asserts the join step leases only after both branches reach terminal (exercises `queue.lease()`'s DAG join, `queue.py:111-129`) — no mocks on the queue.
- Refutation loop: seed a verified ledger entry + an opposing KG claim, run `revisit`, assert a new investigation folder appears and carries the opposing claim ID (F1.9 × F1.10).

**Reused oracles:**
- **`experiments/exp_when_protection_matters.py`** is the F1.5 oracle (per build plan §10.1): the span-weighted consensus function is dropped into its correlated-poisoning regime and must retain the protected-dissent property (≥ the anchoring baseline's retention). This is real-behavior verification, not a mocked assertion — the whole point of that experiment.

**Browser smoke:** none in this lane (no new UI surface — the notebook stream renders the new events via existing `log().emit` types). If the master wants the debate transcript / verifier verdict surfaced in the UI, that's a legibility-layer (Lane 5?) concern; this lane only emits the events.

---

## 6. Open questions for the master/user

- **Surprise signal (F1.6) — genuine uncertainty, blocks nobody but affects the RQ.** Anthropic's Messages API exposes **no per-token logprobs**, so literal "NLL/perplexity under the reader model" is not computable from the reader's own calls. Proposed: embedding-novelty (local `bge-small`, already loaded) + contradiction-magnitude, and only add a small *local* LM for true NLL if RQ-HT06 shows those insufficient. **Confirm** we don't want a new local-model dependency for surprise.
- **F1.5 module placement.** Put `span_weighted_consensus` in `verifier.py` (avoid a one-function file) vs a dedicated `persona/agents/consensus.py`. Defaulting to `verifier.py`; flag if the master wants it standalone for Lane 2's import clarity.
- **`worker.py` merge (boundary file).** Multiple lanes append `@handler` registrations. Confirm the master will serialize the final `worker.py` merge, or that we should land handler registrations in a lane-local module the master imports. Does **not** block Milestone 0 (additive appends).
- **FC-2 dossier `conflict_type` from debate (F1.4).** When debate escalates, which `conflict_type` value ('temporal'|'semantic'|'misinformation'|'insufficient') does an unresolved debate map to? Default 'insufficient' (couldn't resolve); confirm Lane 2's inbox expects that for the debate-unresolved kind.
- **Re-investigation threshold (F1.9).** Which ledger transitions trigger re-investigation — refuted always, weakened only if it crossed from verified? Proposed: verified→refuted always; verified→weakened only if a concrete opposing claim ID exists (else just relabel). Confirm the autonomy posture is comfortable auto-opening on refute (it's narrow work, human still anchors any reversal).
