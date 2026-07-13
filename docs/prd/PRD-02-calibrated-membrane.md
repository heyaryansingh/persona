# PRD-02 — Dual-signal calibrated membrane & belief core

> Owner: implementer lane 2 · Status: DRAFT-for-implementation · Autonomy: Balanced · Depends on: FC-1 (`investigation.open_from_conflict`, Lane 1), FC-6 (`retraction.is_retracted` / `retraction.contamination`, Lane 3)

## 0. Summary and how this lane advances the vision (5-8 sentences)

Today the membrane admits a belief by counting sign-collisions and independent labs (`membrane._harvest` → `kg.beliefs(min_independent)`), and the confidence it prints is a plain average of per-source extractor confidences (`kg.add_claim`, kg.py:125-131) — a model self-report, exactly the fabricated confidence the epistemic contract forbids. This lane replaces that with a **dual-signal atomic membrane**: a candidate is admitted only when a textual entailment check over an exact source span AND the structured KG cross-check (`kg.crosscheck`) agree, and the confidence it carries is **calibrated on Persona's own adjudicated beliefs** with a statistical error bound, not asserted. Claims that cannot locate an entailing span cannot be typed READ/TESTED and hard-abstain or route to a human. We add the missing epistemic plumbing the rest of the system consumes: a single `provenance_breakdown()` query (FC-3, Lane 4's dashboard), typed dependency edges between claims (FC-3, Lane 3's dependency graph), a knowledge-conflict taxonomy (`conflicts.py`) that is the RQ-E02 substrate, and a general handoff inbox (`inbox.py`, FC-2) that finally closes the human-as-resolver loop. Two currently-dead signals get wired to real actions: `kg.poisoning_signals` (defined, zero consumers) becomes a scheduled staleness/anchor-attack revisit trigger, and belief-level retraction contamination (via FC-6) flags any belief whose evidence descends from retracted work. Everything preserves the frozen separation — the swarm still only READS, only the membrane commits, and nothing auto-anchors a high-stakes belief. The result is the discipline half of "scale of reading, discipline of believing": a belief store that knows *why* it believes each thing, *how sure* it is calibrated to be, and *when* that belief has gone stale, been attacked, or been contaminated.

## 1. File ownership (this lane's DISJOINT set)

**Edit (owned by this lane):**
- `persona/memory/membrane.py` — dual-signal admission, calibrated confidence, feasibility gate (F2.1, F2.2, F2.4, F2.6)
- `persona/memory/kg.py` — provenance_breakdown, dependency edges, citation_support_ratio, span offsets, temporal validity window, claim-vector upsert hook (F2.3-support, F2.7, F2.10, F2.11)
- `persona/memory/coherence.py` — belief-drift event + review flag (F2.8)
- `persona/memory/history.py` — staleness/age query used by the revisit trigger (F2.9)
- `persona/memory/vectors.py` — no signature change; claim-granularity upsert wired from membrane (F2.10)
- `persona/conflict_reviews.py` — `true_refutation` verdict fires FC-1 + files via inbox (F2.12)

**New (owned by this lane):**
- `persona/memory/calibrate.py` — FC-5 `admit_decision` (F2.3)
- `persona/memory/conflicts.py` — knowledge-conflict taxonomy typing (F2.5, F2.13)
- `persona/inbox.py` — FC-2 `file_handoff` (F2.12, plus consumed by F2.3/F2.8/F2.9/F2.13)

**Boundary files another lane also touches (decoupled by an FC):**
- `persona/api/app.py` — the inbox endpoints (app.py:598-722) currently read `conflict_reviews`/`kg` directly. Lane 4 owns UI/API surface. **We do not edit app.py.** We expose `inbox.file_handoff` / `inbox.open_handoffs` (FC-2) and `kg.provenance_breakdown` (FC-3) as the seam; Lane 4 calls them. Any new endpoint is Lane 4's.
- `persona/agents/deliberate.py` — already consumes `coherence.drift` (deliberate.py:146). We change only `coherence.py`'s function bodies/additions, not deliberate.py's call. If F2.8 needs a new coherence symbol, it is additive (new function), so deliberate.py is untouched.
- `persona/analysis/calibration.py` — **name collision, different thing.** That file is the replication-likelihood prior (a deterministic curve). FC-5 `calibrate.py` lives in `persona/memory/` and is a different concern (admitted-set error bound). No shared code; documented here to prevent confusion.

## 2. Frozen contracts (restate verbatim — PROVIDES + CONSUMES)

**PROVIDES:**

- **FC-2** (new `persona/inbox.py`): `inbox.file_handoff(kind:str, dossier:dict) -> handoff_id:str`. Dossier schema = `{decision_requested, why_unresolvable, disagreeing:[{claim_id,span,qualifiers}], conflict_type:'temporal'|'semantic'|'misinformation'|'insufficient', cheapest_test:{action,cost_tier,dataset}, expected_updates:[{outcome,belief_change}], uncertainty, authority_boundary}`.
- **FC-3** (`persona/memory/kg.py`): `kg.provenance_breakdown() -> {READ:int,INFERRED:int,HUMAN_CONFIRMED:int,TESTED:int, never_confirmed:[claim_id], stale:[{claim_id,age_days}]}`; `kg.add_dependency_edge(src_claim_id, dst_claim_id, rel_type:'supports'|'contradicts'|'presupposes'|'derives_from'|'generalizes'|'operationalizes'|'qualifies'|'extends', confidence:float, span:str) -> None`; `kg.dependency_edges(topic=None) -> [{src,dst,rel_type,confidence,span}]`; `kg.citation_support_ratio(claim_id) -> {support:int,contrast:int,mention:int,ratio:float}`.
- **FC-5** (new `persona/memory/calibrate.py`): `calibrate.admit_decision(candidate:dict) -> {admit:bool, calibrated_p:float, route:'commit'|'human'|'reject', reason:str, bound:float}`.

**CONSUMES:**

- **FC-1** (Lane 1): `investigation.open_from_conflict(conflict_id, evidence_claim_ids=None) -> Investigation`; consensus record shape `{claim, admit_votes:int, weighted_support:float, dissent:[{claim_id, span, weight}]}`.
- **FC-6** (Lane 3, new `persona/ingest/retraction.py`): `retraction.is_retracted(doi=None, pmid=None) -> {retracted:bool, date, reason, source}`; `retraction.contamination(claim_id) -> {contaminated:bool, path:[claim_id]}`.

---

## 3. Features

### F2.1 — Dual-signal atomic membrane

- **Problem & evidence.** Admission today is pure structural counting: `_harvest` links contradictions on `pair_key` (membrane.py:105-116) and `kg.beliefs(min_independent=2, min_conf=0.5)` (kg.py:204-215) surfaces a belief, where `min_conf` is the **average extractor self-reported confidence** (kg.py:130). `kg.crosscheck` exists (kg.py:308-327) but is consumed only by audit/mywork/app read paths — never by the admission decision. So a belief can be admitted on textual convergence alone with a fabricated confidence number. Research: MedRAGChecker (arXiv:2601.06519) — separate retrieval-faithfulness from factual-correctness signals; EMULATE (arXiv:2505.16576) — multi-agent alignment of textual evidence with structured verification before acceptance.
- **Design.** New function in `membrane.py`:
  - `def admit_candidate(kg, claim_rec: dict, source_slug: str, entail: dict) -> dict` returning `{admit, route, calibrated_p, textual_ok, structural_ok, reason, bound}`. Data flow inside `_harvest` (membrane.py:89-98): for each parsed `rec`, before `kg.add_claim`, compute two signals — (a) **textual**: `entail = _entailment(rec)` from F2.2 (an entailing span was located, offsets present); (b) **structural**: `cc = kg.crosscheck(rec["subject"], rec["object"], rec["effect_sign"])` → `structural_ok = len(cc["support"]) >= 1 and not _dominant_contradiction(cc)`. Only when `textual_ok and structural_ok` do we call `calibrate.admit_decision({...})` (F2.3) and honor its `route`. On `route == "commit"` → `kg.add_claim`; on `"human"` → `inbox.file_handoff("membrane_below_threshold", dossier)`; on `"reject"` → drop (logged, not stored as a belief).
  - Confidence written to the KG comes from `admit_decision.calibrated_p`, NOT the extractor average. Add optional param to `kg.add_claim` (kg.py:89): `calibrated_p: float | None = None`; when provided, set `c.confidence = calibrated_p` and set `c.raw_extractor_conf = mconf` for audit (do not overwrite the anchor-pinned branch, kg.py:130).
- **Epistemic guardrails.** No belief is admitted on one signal; the printed confidence is the calibrated bound (F2.3), never the model number (raw kept separately for audit). Sign-collision counting is *demoted* to a candidate signal, not an admission verdict — `candidate_conflicts` (kg.py:229) semantics unchanged (still `candidate_conflict / unverified` until RQ-E02).
- **Required experiment.** RQ-M01. **Hypothesis:** dual-signal admission (textual∧structural) reduces admitted-set error vs the current single-signal counter at equal or lower abstention, on the frozen Curie candidate set. **Metric:** admitted-set precision (agreement with existing human/verbatim gold) and abstention rate; **gate:** precision improves ≥ +0.05 absolute at abstention ≤ +0.10 over the current membrane. **Seeds:** ≥20 resample splits (reuse the RQ-E01a resampling harness style). Save to `experiments/exp_dual_signal_membrane.py` / `results/`.
- **Acceptance criteria.** A candidate with a verbatim entailing span but zero structural support is NOT admitted; one with both is admitted with `calibrated_p` == `admit_decision.calibrated_p`. Runnable check: `test_membrane_dual_signal.py::test_structural_only_not_admitted` and `::test_confidence_is_calibrated_not_extractor_avg`.
- **Effort** L · **Dependencies** F2.2 (entailment), F2.3 (calibrate), FC-5.

### F2.2 — Exact-span evidence escalation + hard abstention

- **Problem & evidence.** `validate_claims` (extract.py:115-134) already rejects a claim whose `quote` is not verbatim in the source (`_norm(claim["quote"]) not in haystack` → `"quote-not-verbatim"`, extract.py:134) — good foundation. But (a) it stores no character **offsets** (the SUPPORTED_BY edge keeps only `quote`, kg.py:120), so a span cannot be re-located or audited to a position; and (b) verbatim *presence* ≠ *entailment*: a sentence can appear in the source yet not entail the `(subject, sign, object)` directional claim. There is no escalation loop and no hard-abstain path tied to span location. Research: CiteCheck (arXiv:2605.27700) — verify each atomic claim against a located citing span; DeepSciVerify (arXiv:2605.27710) — escalate retrieval until an entailing span is found, else abstain.
- **Design.**
  - `membrane.py`: `def _entailment(kg, rec: dict, source_text: str | None) -> dict` → `{entails: bool, span: str, char_start: int, char_end: int, method: 'verbatim+nli'|'verbatim-only'|'none'}`. Step 1 locate: reuse the verbatim check to get `char_start = haystack.find(_norm(quote))`, `char_end = start + len(quote)`. Step 2 entailment: a small NLI/entailment judge over `(span, claim-as-hypothesis)`; **judge choice is the load-bearing uncertainty — see RQ-M02.** If no entailing span located after escalation → `{entails: False, method: 'none'}`.
  - `kg.add_claim` (kg.py:89-121): extend the SUPPORTED_BY `ON CREATE SET` (kg.py:120) with `r.char_start=$cs, r.char_end=$ce, r.entail_method=$em`. Persist offsets so `provenance` (kg.py:234) and dossiers can render/re-locate the exact span.
  - Hard-abstention: in `admit_candidate` (F2.1), `entails == False` ⇒ the claim **cannot** be typed READ/TESTED. Route: `inbox.file_handoff("no_entailing_span", dossier)` when it collides with an existing belief; otherwise drop with an `abstained` event. It is never stored as a READ belief.
- **Epistemic guardrails.** This IS the exact-span-grounding rule: no READ/TESTED belief without stored offsets to an entailing span; abstain rather than fabricate. Offsets make the grounding auditable, not just asserted.
- **Required experiment.** RQ-M02. **Hypothesis:** an entailment judge over the located span rejects non-entailing-but-verbatim claims that the current verbatim-only check admits, without dropping true claims. **Metric:** on a hand-labeled set of (verbatim-present, entails?) pairs drawn from the frozen Curie set, entailment-gate precision/recall vs verbatim-only; **gate:** ≥0.90 precision on "entails" with recall ≥ current verbatim-only recall − 0.05. **Seeds:** deterministic split, ≥20 bootstraps for CI. If no judge clears the gate, ship `method='verbatim-only'` and record the reversal. Save `experiments/exp_span_entailment.py`.
- **Acceptance criteria.** A stored belief has non-null `char_start/char_end` on ≥1 SUPPORTED_BY edge; a verbatim-present-but-non-entailing candidate is abstained. Check: `test_span_grounding.py::test_offsets_persisted` and `::test_nonentailing_verbatim_abstains`.
- **Effort** M · **Dependencies** none (feeds F2.1).

### F2.3 — Conformal / selective-prediction gate → human handoff (FC-5)

- **Problem & evidence.** There is no calibrated threshold anywhere on the belief path; `kg.beliefs` uses a fixed `min_conf=0.5` (kg.py:204) on an uncalibrated average. The admitted set therefore carries no statistical error guarantee. Research: ICLR 2025 QA-Calibration (group-wise/monotonic calibration for QA confidence); conformal abstention / selective prediction (distribution-free error bound at a chosen abstention rate). **DO NOT import paper constants** — fit on our own data.
- **Design.** New `persona/memory/calibrate.py`:
  - `def admit_decision(candidate: dict) -> dict` (FC-5, verbatim signature) → `{admit, calibrated_p, route, reason, bound}`. `candidate` carries the dual signals from F2.1 (`textual_ok`, `structural_ok`, `raw_conf`, `independent_labs`, `support_ratio`, `crosscheck_counts`).
  - `def fit(labeled_beliefs: list[dict], target_error: float, out_path) -> dict` — fit a calibrator (isotonic or Platt, chosen by RQ-M03) that maps candidate features → `calibrated_p`, then pick the conformal threshold `τ` such that the admitted set (calibrated_p ≥ τ) has empirical error ≤ `target_error` on held-out; persist `{tau, target_error, abstention_rate, calibrator}` to `ops_dir/calibrator.json`.
  - `def load(ops_dir) -> Calibrator`. Routing: `calibrated_p ≥ τ` → `commit`; `low_band ≤ calibrated_p < τ` → `human` (files a handoff); `< low_band` → `reject`. `bound` = the held-out error bound the calibrator certifies at `τ`.
  - Ships a **cold-start** stub before `fit` has run: `route='human'` for everything above a floor, `reason='calibrator-unfit'`, `bound=None` — so the system is safe (routes to human) rather than confidently wrong on day 1.
- **Epistemic guardrails.** Calibration is on Persona's OWN adjudicated/held-out beliefs (verbatim-gold + human labels), never a model self-report; the surfaced number carries a certified error bound. Below threshold auto-routes to `inbox.file_handoff` — human-gated by construction. Never auto-anchors.
- **Required experiment.** RQ-M03 (**load-bearing, the core of this feature**). **Hypothesis:** a calibrator fit on held-out adjudicated beliefs yields an admitted set whose empirical error ≤ target at a stated abstention rate, beating the fixed-0.5 cutoff. **Metric:** admitted-set error at fixed abstention, Brier, reliability (ECE); **gate:** admitted-set error ≤ target (e.g. 0.10) at abstention ≤ 0.30, and ECE < 0.05, on held-out over ≥20 splits (mean ± 95% CI). No paper constants. Save `experiments/exp_admission_calibration.py`, results to `results/FINDINGS.md#RQ-M03`.
- **Acceptance criteria.** `admit_decision` on a high-signal candidate returns `route='commit'` with `bound ≤ target_error`; a borderline candidate returns `route='human'`. Check: `test_calibrate.py::test_bound_holds_on_holdout` (asserts empirical admitted error ≤ persisted bound on a fixture split) and `::test_coldstart_routes_human`.
- **Effort** L · **Dependencies** F2.1 signals; provides FC-5.

### F2.4 — Recomposition / feasibility gate

- **Problem & evidence.** Atoms are admitted independently; nothing checks whether a *set* of individually-supported atoms is jointly feasible (e.g. a claim that a factor both up- and down-regulates the same target under the same qualifiers, or an entity asserted with mutually exclusive properties). Research: Matter-of-Fact (arXiv:2506.04410) — feasibility constraints over composed claims; Compositionally Infeasible Claims (arXiv:2604.10990) — reject conjunctions that no world satisfies.
- **Design.** `membrane.py`: `def _feasibility_flags(kg, admitted_this_pass: list[dict]) -> list[dict]` run after per-atom admission in `_harvest`, before `project_beliefs` (membrane.py:129). Cheap structural rules only (no model): (a) same `pair_key` admitted with both `+` and `-` from overlapping labs → mutual-exclusion flag; (b) a claim whose `presupposes`/`derives_from` dependency parent (F2.7 edges) is retired/abstained → dangling-support flag. Flagged sets are NOT auto-rejected — they file `inbox.file_handoff("infeasible_conjunction", dossier)` and are marked `fragile=true` on the claim so FC-4's dependency graph shows them. **Applicability gate:** the check runs only when ≥2 atoms share a `pair_key` or a dependency edge; otherwise it emits `skipped: single-atom` — an explicit not-applicable state distinct from "passed".
- **Epistemic guardrails.** Applicability gate is explicit (skipped ≠ passed) — the correctness boundary. Infeasibility routes to human, never silently drops a supported atom.
- **Required experiment.** RQ-M04 (light). **Hypothesis:** the feasibility rules flag known-infeasible seeded conjunctions with zero false flags on a single-atom control set. **Metric:** flag recall on seeded infeasible sets, false-flag rate on feasible controls; **gate:** recall ≥ 0.9, false-flag = 0 on the control. Seeds: deterministic fixture (rule-based, so a small fixed set + ≥20 randomized orderings suffices).
- **Acceptance criteria.** Two overlapping-lab opposite-sign atoms in one pass produce a handoff + `fragile=true`; a single-atom pass emits `skipped`. Check: `test_feasibility.py::test_mutual_exclusion_flags` and `::test_single_atom_skipped`.
- **Effort** M · **Dependencies** F2.7 (dependency edges) for rule (b); FC-2.

### F2.5 — Knowledge-conflict taxonomy typing (NEW conflicts.py)

- **Problem & evidence.** Every tension is currently one flat label: `candidate_conflicts` stamps `conflict_type: "unverified"` on all sign collisions (kg.py:229-232). To pick a resolution rule you must first know *why* two claims disagree. This is the RQ-E02 substrate. Research: Knowledge Conflicts survey (arXiv:2403.08319) — taxonomy of context-memory / inter-context conflict types.
- **Design.** New `persona/memory/conflicts.py`:
  - `def type_conflict(kg, pos_claim_id: str, neg_claim_id: str, retraction=None) -> dict` → `{conflict_type: 'temporal'|'semantic'|'misinformation'|'insufficient', signals: {...}, confidence: float}`. Deterministic, code-only signals: **temporal** — the two claims' source `year`/`valid_from` differ beyond a window and the newer supersedes (F2.7 validity window); **misinformation** — one side's sources include a retracted work (`retraction.is_retracted` per source DOI/PMID, FC-6); **semantic** — differing qualifiers/populations on the SUPPORTED_BY spans (qualifier fields); **insufficient** — too few independent labs on either side to adjudicate. Each signal declares an **applicability gate**: e.g. temporal typing emits `skipped: no-dated-sources` when years are missing, distinct from asserting "not temporal".
  - This does NOT change user-facing labeling: `candidate_conflict / unverified` stays until RQ-E02's ≥0.85-precision gate passes. `type_conflict` output is stored on the conflict dossier and used to choose the FC-1 route / handoff `conflict_type`, but is presented as a *hypothesized* type, not a verdict.
- **Epistemic guardrails.** Code-only signals (no model); each carries an applicability gate emitting explicit skipped/not-applicable. Typing is advisory until RQ-E02 precision gate; the frozen `candidate_conflict` labeling is preserved.
- **Required experiment.** RQ-E02 (existing, THIS is its substrate — see RESEARCH_QUALITY_PROGRAM.md:149-155). **Gate:** ≥0.85 precision on blinded human gold before typing may drive autonomous escalation. This lane delivers the typed-signal generator + the dossier plumbing; the gold-labeling run and precision measurement are the RQ-E02 experiment. Until it passes, typing is display-only advisory.
- **Acceptance criteria.** A conflict where one source is retracted types `misinformation`; a conflict with no dated sources emits temporal `skipped`. Check: `test_conflicts.py::test_retraction_types_misinformation` and `::test_undated_temporal_skipped`.
- **Effort** M · **Dependencies** FC-6 (retraction), F2.7 (validity window); substrate for RQ-E02.

### F2.6 — Block confidence-inflation-from-reasoning

- **Problem & evidence.** `kg.add_claim` recomputes `c.confidence` on every write from source stats (kg.py:125-131); a synthesis/reasoning step that re-asserts a claim without *new independent evidence* would still touch the write path. The anchor branch is protected, but a non-anchored belief's confidence can move on re-assertion alone. Research: ECon (arXiv:2410.04068) — reasoning steps must not manufacture confidence absent new evidence.
- **Design.** Enforce an **evidence-monotonic** invariant in the KG update path. In `kg.add_claim` (kg.py:125-131), the confidence recompute already derives from SUPPORTED_BY sources — the rule is: confidence may only *increase* when a **new distinct lab** (new `independent_source_count`) is added. Add: if `labs_after == labs_before` (no new independent lab), then `c.confidence = min(c.confidence, prior_confidence)` — a re-assertion from an already-counted lab or a synthesis pass can never raise it. Reasoning/synthesis writes (provenance `INFERRED`) are further barred from raising confidence at all: gate on `prov == 'INFERRED'` ⇒ confidence is read-only. Add a `raise_reason` audit field when confidence does increase, recording the new lab id.
- **Epistemic guardrails.** Directly encodes "no-fabricated-confidence": a belief's confidence provably tracks new independent evidence, not re-statement. INFERRED can never inflate READ/TESTED.
- **Required experiment.** trivial — no experiment. This is an invariant, not an uncertain modeling choice; it is verified by an assertion test, not a study.
- **Acceptance criteria.** Re-adding a claim from an already-counted lab leaves confidence unchanged; an INFERRED write never raises it. Check: `test_no_inflation.py::test_reassert_same_lab_no_increase` and `::test_inferred_cannot_raise`.
- **Effort** S · **Dependencies** none.

### F2.7 — MedKGent-style temporal confidence + validity window

- **Problem & evidence.** Provenance already carries per-source `year` and `slug`/`lab` (kg.py Source node), and `valid_from/valid_to` exist on claims (kg.py:113), but nothing (a) requires PMID+timestamp per source for temporal ordering, (b) makes corroboration monotonic over time, or (c) demotes a superseded claim via a validity window. `history.series` (history.py:54) records confidence-over-time but nothing acts on age. Research: MedKGent (arXiv:2508.12393) — timestamped, monotonic-under-corroboration KG confidence; Citation-Grounding temporality (arXiv:2606.00898) — validity windows for superseded claims.
- **Design.**
  - `kg.py`: `def set_validity_window(self, claim_id: str, valid_to: str, superseded_by: str | None = None) -> None` — sets `c.valid_to` (demotes from `beliefs()` which filters `valid_to IS NULL`, kg.py:208) and records `c.superseded_by`. Store `s.pmid` on Source upsert (extend `upsert_source`, kg.py:78-87) so ordering is by (year, pmid-date). `add_dependency_edge` (FC-3) with `rel_type='extends'|'generalizes'` links successor→predecessor.
  - Monotonicity is inherited from F2.6 (confidence only rises with new independent labs). Temporal demotion: `dependency_edges` marking a claim superseded, plus a `valid_to`, removes it from the live belief set without deleting it (append-only history preserved).
- **Epistemic guardrails.** Bi-temporal, append-only: superseded claims are demoted (valid_to set), never erased — audit trail intact. Corroboration monotonicity reuses F2.6's invariant.
- **Required experiment.** trivial — no experiment. Validity-window mechanics are deterministic bookkeeping; the *policy* of when to supersede is human/FC-1-gated, not an autonomous confidence move.
- **Acceptance criteria.** Setting a validity window removes a claim from `beliefs()` but keeps it in `provenance()`/history. Check: `test_validity_window.py::test_superseded_leaves_belief_set_kept_in_history`.
- **Effort** M · **Dependencies** FC-3 (dependency edges).

### F2.8 — Wire coherence.drift() into a legible event + review flag

- **Problem & evidence.** **Correction to the brief:** `coherence.drift()` (coherence.py:58-65) is NOT computed-and-discarded — it is consumed at `deliberate.py:146` to throttle wholesale interest-set replacement and it already emits a `coherence` event (deliberate.py:153). The genuine gap is narrower: that throttle is (a) about *interest* drift only, not *belief* drift, and (b) it logs but never files a human-review flag, so a sustained/repeated spiral leaves no durable, actionable record. Do not re-implement what exists.
- **Design.** Additive only (deliberate.py untouched):
  - `coherence.py`: `def belief_drift(prev_beliefs: list, cur_beliefs: list) -> float` — fraction of high-confidence beliefs whose sign/confidence changed beyond a band between two harvests (distinct from interest drift). Called from `membrane.project_beliefs` boundary or the revisit pass (F2.9).
  - `def flag_drift(kind: str, value: float, threshold: float, context: dict) -> str | None` — when `value > threshold`, emit the existing legible event AND `inbox.file_handoff("coherence_drift", dossier)` returning the handoff id; below threshold return None. The interest-drift throttle in deliberate.py can optionally call this (a one-line additive call) so a *repeated* throttle escalates to review — but that edit is Lane-owned deliberate.py; propose via HANDOFF if desired, else keep it in the F2.9 revisit pass which this lane owns.
- **Epistemic guardrails.** Motion-only-for-real-state-change: a drift flag fires only on a measured threshold breach, and it routes to human review rather than silently self-correcting.
- **Required experiment.** trivial — no experiment. Threshold `θ` is a tunable knob (like the existing `THETA=0.7`, deliberate.py:142); default reuses that value and is user-adjustable. `# ponytail: reuse deliberate's THETA=0.7; expose as config if a second call site needs a different band.`
- **Acceptance criteria.** `belief_drift` above threshold files exactly one handoff and emits one coherence event; below threshold files none. Check: `test_drift.py::test_drift_over_threshold_files_handoff`.
- **Effort** S · **Dependencies** FC-2.

### F2.9 — Belief staleness / revisit trigger

- **Problem & evidence.** `kg.poisoning_signals()` (kg.py:253-265) computes the correlated-poisoning signature (high-volume, low-independence claim attacking an anchor) but has **zero consumers** (verified: grep finds only the definition). And no belief is revisited on age — `history.series` (history.py:54) has the data but nothing scans it. Balanced autonomy wants auto-re-investigation on staleness/attack.
- **Design.** New `def revisit_pass(kg, ops_dir, max_age_days: int = 90, unsupported_cycles: int = 3) -> dict` (place in `conflicts.py` or a small `memory/revisit.py` — **owned here either way**; prefer `conflicts.py` to avoid a new file). It: (a) reads `kg.poisoning_signals()` — for each anchor under volume-without-independence attack → `inbox.file_handoff("anchor_under_attack", dossier)` (never auto-updates the anchor); (b) uses a new `history.stale_claims(max_age_days, unsupported_cycles) -> [{claim_id, age_days, cycles_unsupported}]` (new query in history.py over `belief_history`) — a non-anchored belief N cycles without new independent support → under Balanced autonomy call `investigation.open_from_conflict(conflict_id=None, evidence_claim_ids=[claim_id])` (FC-1) to auto-re-investigate, OR file a handoff if it touches an anchor. Scheduled from the daemon revisit loop (this lane exposes `revisit_pass`; the daemon/Lane wires the schedule — it already runs a revisit loop per `agents/revisit.py`).
- **Epistemic guardrails.** Anchor attacks NEVER auto-update — they route to human (`file_handoff`). Only non-anchored, non-high-stakes staleness triggers autonomous re-investigation (Balanced posture), and that re-investigation only READS + files, never writes to the self.
- **Required experiment.** trivial — no experiment. Reuses the validated poisoning signature (`experiments/exp_when_protection_matters.py` is the oracle; anchoring retained 100% vs 71% naive — FINDINGS.md). The trigger consumes an already-validated signal; thresholds are knobs.
- **Acceptance criteria.** A synthetic anchor under a volume-without-independence attack files an `anchor_under_attack` handoff and does NOT change the anchor's confidence; a 100-day unsupported non-anchor opens an investigation. Check: `test_revisit.py::test_anchor_attack_routes_human_no_mutation` — reuse `exp_when_protection_matters.py` poisoning fixtures as the oracle.
- **Effort** M · **Dependencies** FC-1, FC-2; `kg.poisoning_signals` (exists).

### F2.10 — Claim-level vector retrieval

- **Problem & evidence.** `vectors.upsert` is called only for synthesis notes (`synthesizer.py:174`, verified as the sole upsert caller); "what do I know about X" retrieves note-granularity, not claim-granularity. `kg.claims_in` (kg.py:267-282) and `crosscheck` give the raw claim material but nothing indexes it semantically. Research: standard dense claim retrieval (RQ-E03 in this repo tested hybrid retrieval; note E03a rejected hybrid *deployment* at +0.010 F1 — so keep this to plain claim-quote upsert, do not add a hybrid retriever).
- **Design.** In `membrane.admit_candidate` (F2.1), on `route=='commit'`, after `kg.add_claim`, call `vectors.upsert(f"claim:{cid}", quote_or_span, {"subject": subj, "object": obj, "sign": sign, "kind": "claim", "claim_id": cid})`. No change to `vectors.py`'s signatures. `search("...")` then returns claim keys alongside note keys; callers already handle `kind`. `# ponytail: reuse existing VectorIndex.upsert/search; no new retriever — RQ-E03a rejected hybrid deployment.`
- **Epistemic guardrails.** Indexes only the exact stored span/quote (grounded text), tagged with `claim_id` so a hit is always traceable back to provenance.
- **Required experiment.** trivial — no experiment. Reuses the existing, tested `VectorIndex`; the retrieval-method question was already settled by RQ-E03a (hybrid rejected). This is a plumbing change.
- **Acceptance criteria.** After committing a claim, `vectors.search(subject)` returns a hit with `kind=='claim'` and the right `claim_id`. Check: `test_claim_vectors.py::test_committed_claim_is_searchable`.
- **Effort** S · **Dependencies** F2.1.

### F2.11 — Provenance-breakdown API (FC-3)

- **Problem & evidence.** Lane 4's epistemic dashboard needs one query for the provenance mix; today it would have to scan `beliefs()` and count by hand, and there is no "never confirmed" or "stale" surface. Nothing exposes `provenance_state` counts (kg.py stores `c.provenance` but no aggregate query).
- **Design.** `kg.py`: `def provenance_breakdown(self) -> dict` (FC-3, verbatim) → `{READ, INFERRED, HUMAN_CONFIRMED, TESTED, never_confirmed:[claim_id], stale:[{claim_id, age_days}]}`. Cypher: `MATCH (c:Claim) WHERE c.valid_to IS NULL RETURN c.provenance, count(*)` for the four counts; `never_confirmed` = live claims with `provenance IN ['READ','INFERRED'] AND anchored=false`; `stale` = joins `history.stale_claims` (F2.9). Pure read.
- **Epistemic guardrails.** Surfaces the honest provenance mix so the UI can render INFERRED/READ with less authority than HUMAN_CONFIRMED/TESTED (honest-uncertainty design rule).
- **Required experiment.** trivial — no experiment (a read query).
- **Acceptance criteria.** On a fixture KG with 2 READ + 1 anchored HUMAN_CONFIRMED, breakdown returns `READ:2, HUMAN_CONFIRMED:1` and lists the READs in `never_confirmed`. Check: `test_provenance_breakdown.py::test_counts_and_never_confirmed`.
- **Effort** S · **Dependencies** F2.9 (for `stale`); provides FC-3.

### F2.12 — Close the human-as-resolver loop (FC-2 inbox + FC-1 on true_refutation)

- **Problem & evidence.** `conflict_reviews` records `true_refutation` (conflict_reviews.py:25) but the review endpoint (app.py:664-693) only appends to the ledger and explicitly refuses to act (`inbox_resolve` returns `contradiction-typing-not-validated`, app.py:696-699). Handoffs are ad-hoc: the "inbox" is entirely conflict-review-shaped (app.py:598-611), there is no general `file_handoff`. So a human `true_refutation` verdict is recorded but never opens an investigation.
- **Design.**
  - New `persona/inbox.py`: `def file_handoff(kind: str, dossier: dict) -> str` (FC-2) — validates `dossier` against the FC-2 schema (fail-loud on missing `decision_requested`/`conflict_type`/`authority_boundary`), appends to an append-only `ops_dir/handoffs.jsonl` (reuse the hash-chain pattern from `conflict_reviews.py:90-213` — do not reinvent), returns `handoff_id`. Plus `def open_handoffs(ops_dir) -> list[dict]` and `def resolve_handoff(handoff_id, resolution) -> dict` for Lane 4's UI. **Reuse `conflict_reviews`' canonical-json + hash-chain helpers** rather than duplicating (`# ponytail: same ledger integrity primitives as conflict_reviews`).
  - `conflict_reviews.py`: on an appended review with `verdict == true_refutation`, call `investigation.open_from_conflict(conflict_id, evidence_claim_ids=[pos, neg])` (FC-1) — but **only after RQ-E02 passes** (guard identical to `inbox_resolve`'s current refusal). Until then, a `true_refutation` files a `file_handoff("true_refutation_pending_gate", dossier)` so it is not lost, without anchoring. This preserves the frozen "candidate_conflict until RQ-E02" contract while wiring the loop end-to-end.
- **Epistemic guardrails.** Every handoff is append-only + hash-chained (tamper-evident); `true_refutation` cannot anchor a belief until the RQ-E02 precision gate passes; the swarm/reviews never mutate a belief directly. Human is the resolver; the loop routes to them.
- **Required experiment.** trivial — no experiment (integration wiring; correctness is an assertion test). The gate it respects (RQ-E02 ≥0.85 precision) is the experiment, owned in F2.5.
- **Acceptance criteria.** `file_handoff` with a valid dossier returns an id and the record hash-chains; a `true_refutation` review files a handoff (and does NOT anchor) while the gate is unpassed. Check: `test_inbox.py::test_file_handoff_hash_chains` and `test_conflict_review_true_refutation_files_handoff_no_anchor`.
- **Effort** M · **Dependencies** FC-1, provides FC-2.

### F2.13 — Belief-level retraction-contamination

- **Problem & evidence.** Retraction is only surfaced as free text in one audit prompt (`meta.get('retracted')`, audit.py:241); no belief is flagged when its evidence *descends* from retracted work, and no contamination path is traced. Research: FC-6 (Lane 3) provides the detector; this lane consumes it at the belief level.
- **Design.** In `conflicts.py`: `def retraction_scan(kg, claim_ids: list | None = None) -> list[dict]` → for each live belief, call `retraction.contamination(claim_id)` (FC-6); when `contaminated` → set `c.contaminated=true` + `c.contamination_path` on the claim (audit field, not deletion), and `inbox.file_handoff("retraction_contamination", dossier={..., conflict_type:'misinformation', authority_boundary:'human-only for high-stakes'})`. High-stakes/anchored contaminated beliefs are **never** auto-updated — routed to human. Also feeds F2.5 `misinformation` typing. **Applicability gate:** if FC-6 returns `retracted: None`/source unresolvable (no DOI/PMID), emit `skipped: unresolvable-provenance`, distinct from "clean".
- **Epistemic guardrails.** Contamination flags, never deletes (audit trail); anchored/high-stakes contaminated beliefs route to human, never auto-update; explicit skipped state when provenance can't be resolved (applicability gate — avoids false "clean").
- **Required experiment.** trivial — no experiment. Consumes a Lane-3-validated detector; the belief-level action is deterministic routing.
- **Acceptance criteria.** A belief whose source DOI is retracted gets `contaminated=true` + a `misinformation` handoff and its anchor confidence is unchanged; a belief with no resolvable DOI emits `skipped`. Check: `test_retraction_contamination.py::test_contaminated_anchor_routes_human_no_mutation` (FC-6 stubbed).
- **Effort** S · **Dependencies** FC-6, F2.5, FC-2.

---

## 4. Sequencing within the lane

**Milestone 0 — land FC stubs first (hour 1, so Lanes 3 & 4 build against us in parallel):**
1. `persona/inbox.py` — `file_handoff`/`open_handoffs`/`resolve_handoff` with FC-2 signature + a working append (not just a stub — it's small and reused everywhere).
2. `kg.py` FC-3 stubs — `provenance_breakdown`, `add_dependency_edge`, `dependency_edges`, `citation_support_ratio` with exact signatures returning typed empty/fixture values.
3. `persona/memory/calibrate.py` — `admit_decision` (FC-5) in cold-start mode (`route='human'`, `reason='calibrator-unfit'`).

**Then feature order (rationale = dependency topology + de-risk earliest):**
- **F2.11, F2.6** (S, no deps) — provenance query + inflation invariant; immediate wins, unblock Lane 4 dashboard.
- **F2.2** (span offsets + entailment) — foundation for F2.1; run RQ-M02 here.
- **F2.3** (calibrate fit) — run RQ-M03; the core statistical guarantee.
- **F2.1** (dual-signal membrane) — composes F2.2 + F2.3; run RQ-M01. This is the headline; it needs the two below it proven first.
- **F2.7** (validity window) → **F2.5** (conflict typing, needs FC-6 + validity) → **F2.13** (retraction, needs F2.5).
- **F2.10** (claim vectors), **F2.4** (feasibility), **F2.8** (drift flag) — plug into the now-working membrane.
- **F2.9** (revisit pass) + **F2.12** (FC-1 wiring on true_refutation) — last, they consume FC-1 which may land later; until then they file handoffs (safe degrade).

## 5. Test & verification plan

- **Unit (assert-based, no framework beyond pytest):** one `test_*.py` per feature as named in each Acceptance block. Money/security-adjacent paths (ledger integrity in `inbox.py`, calibration bound in `calibrate.py`, no-mutation on anchor attack) get their own explicit assertions.
- **Reuse existing oracles:** `experiments/exp_when_protection_matters.py` is the poisoning oracle for F2.9 (anchoring retained 100% vs 71% naive — FINDINGS.md); the RQ-E01a resampling harness style for RQ-M01/M03 splits; `conflict_reviews.py` hash-chain verify (`verify_conflict_reviews`) as the pattern the `inbox.py` ledger must also pass.
- **Integration:** a harvest over a fixture source dir that exercises dual-signal admission → calibrated commit → claim-vector upsert → provenance_breakdown reflects it; a second harvest with a retracted-DOI source → contamination handoff filed, anchor unmutated.
- **New experiments (seeded ≥20, mean ± 95% CI, saved to `experiments/` + `results/FINDINGS.md`):** RQ-M01 (dual-signal), RQ-M02 (span entailment), RQ-M03 (admission calibration), RQ-M04 (feasibility, light). RQ-E02 is the existing gate for F2.5/F2.12 — this lane provides its substrate; the gold-labeled precision run is tracked under RQ-E02.
- **Browser smoke:** none owned here (Lane 4 owns UI). We only assert the FC seams return the contracted shapes; Lane 4's smoke consumes them.
- **Regression guard:** existing 11-test integrity suite must still pass; the frozen `candidate_conflict / unverified` behavior (kg.py:229, app.py:696-699) must be unchanged until RQ-E02.

## 6. Open questions for the master/user

- **F2.2 entailment judge (RQ-M02) — model vs. no-model.** An NLI entailment step is the one place this lane would call a model. The epistemic contract says forensic/statistical checks run in code, never a model. Is a *span-level NLI judge* acceptable (it's a grounding check, not a confidence source), or must F2.2 ship verbatim-only until a non-model entailment signal is validated? Blocks F2.1's textual signal design. **Recommendation:** allow a bounded NLI judge for the *entails/not* boolean only (never for a confidence number), gated by RQ-M02.
- **F2.3 calibration target — who sets `target_error` and abstention?** The conformal gate needs a chosen error target and acceptable abstention rate (a product-risk decision, not a statistical one). Default proposed: error ≤ 0.10 at abstention ≤ 0.30. Confirm or set.
- **F2.9 revisit scheduling.** This lane exposes `revisit_pass`; the daemon (`agents/revisit.py`) owns the schedule. Confirm the daemon lane will call it, or should this lane add the schedule hook (crosses a file boundary → needs a CONTRACT CHANGE PROPOSAL)?
- **F2.8 second call site.** Should the interest-drift throttle in `deliberate.py:147-155` escalate to a review handoff on *repeated* throttling (a one-line additive call, but deliberate.py may be another lane's file)? If yes, propose the boundary edit; if no, F2.9's belief-drift pass covers the durable-record gap.
- **FC-6 timing.** F2.5 (`misinformation` typing) and F2.13 degrade gracefully to `skipped` if `retraction.is_retracted`/`contamination` aren't landed yet. Confirm Lane 3 lands FC-6 stubs at Milestone 0 so our applicability gates can be tested against real (even if empty) returns.
