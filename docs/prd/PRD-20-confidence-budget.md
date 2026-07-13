# PRD-20 — Belief confidence-budget / evidence accounting

> **Owner lane:** 2 (Dual-signal calibrated membrane & belief core) · **Status:** DRAFT-for-implementation (2026-07-13) · **Autonomy:** Balanced — file a human handoff on any over-drawn belief immediately (always safe); *auto-demote* (clamp stored confidence to the evidence ceiling) only for non-anchored beliefs and only once **RQ-E30** passes. Anchored / HUMAN_CONFIRMED / TESTED beliefs are never demoted. · **Depends-on:** PRD-02 F2.3 (`calibrate.admit_decision`, FC-5), PRD-02 F2.6 (evidence-monotonic write invariant), PRD-02 F2.1 (`membrane.admit_candidate`), FC-2 (`inbox.file_handoff`). Complements PRD-15 (calibration panel) as an over-drawn *stratum*.

---

## 0. Summary + capability unlocked

Persona's headline discipline is **"no fabricated confidence."** PRD-02 F2.6 makes that a *write-path* invariant — a re-assertion or synthesis step can never raise a belief's confidence without a new independent lab (`kg.add_claim` recompute, `kg.py:125-131`; PRD-02 §F2.6). But F2.6 only guards *changes going forward*. It does not answer the standing question: **for a belief that already sits at confidence _p_, is _p_ actually justified by the independent evidence that belief has "spent"?** Legacy beliefs written before F2.6, beliefs whose supporting labs later thinned (retraction, retraction-contamination via FC-6, or a superseding claim under F2.7's validity window), and any belief whose stored number simply drifted above what its evidence buys are all invisible today.

This PRD adds the **accounting layer**: for every live belief it computes an **evidence-justified ceiling** — the maximum calibrated confidence its *evidence profile alone* (independent labs, span-grounding, provenance) justifies under the FC-5 calibrator — and flags any belief whose stored confidence exceeds that ceiling as **over-drawn**. Over-drawn beliefs (a) file a human handoff (FC-2), (b) feed the calibration panel (PRD-15) as a stratum, and (c) once RQ-E30 certifies the flag predicts real reversals, auto-demote to the ceiling. The metaphor is literal: independent evidence is a budget, confidence is a withdrawal, and a withdrawal larger than the balance is a structural violation — not a vibe, a **number with a ceiling**.

**Capability unlocked:** Persona can point at any belief and show its *evidence account* — "this belief claims p=0.88 but its evidence (1 independent lab, 1 span, READ) justifies at most 0.61; it is over-drawn by 0.27, filed for human review." "No fabricated confidence" becomes a per-belief invariant that is audited, surfaced, and (when validated) self-corrected — the empirical proof of `CLAUDE.md` §2 pushed down to the individual belief.

---

## 1. File ownership (disjoint)

| File | New? | Owner | Note |
|---|---|---|---|
| `persona/memory/budget.py` | **New** | Lane 2 | The whole accounting layer: ceiling, over-drawn detection, per-belief ledger, scheduled audit pass. Pure over on-disk KG + calibrator state; no model, no network. |
| `experiments/exp_rq_e30_confidence_budget.py` | **New** | Lane 2 | RQ-E30 sandbox (does over-drawn predict reversal). |
| `tests/test_confidence_budget.py` | **New** | Lane 2 | Runnable check. |

**Boundary files (within Lane 2 — same lane as PRD-02, so no cross-lane FC; coordinate the one edit in the HANDOFF dispatch log):**
- `persona/memory/membrane.py` — **ONE additive line** in `admit_candidate` (PRD-02 F2.1, `membrane.py` admission path) that clamps `calibrated_p` to the evidence ceiling and routes `human` when it was exceeded. PRD-02 owns `admit_candidate`; PRD-20 lands this line *after* F2.1/F2.3 exist. Flagged as a within-lane coordinated edit, not a parallel rewrite.
- `persona/memory/calibrate.py` — **read-only reuse, no edit.** `budget.evidence_ceiling` computes the ceiling by calling FC-5 `calibrate.admit_decision(...)` on an *evidence-only* candidate (reasoning/re-assertion signals zeroed) and taking its `calibrated_p`. The "calibrate.py ceiling" seam is satisfied by *reusing FC-5 verbatim*, which is the whole point of F2.3's calibrated map — no signature added to a PRD-02-owned file. `# ponytail: ceiling = FC-5 calibrator applied to evidence-only features; no new calibrator, no imported constant.`
- `persona/memory/kg.py` — **read-only reuse, no edit.** `budget` reads live beliefs via existing public `kg.beliefs(min_independent=1, limit=…)` (`kg.py:204-215`) and `kg.provenance(claim_id)` — the independence counts (`independent_source_count`) and `anchored` flag already exist there (task seam: "independence counts already exist"). No new Cypher owned by PRD-20.

**Consumed by Lane 4 (PRD-15 calibration panel):** `budget.overdrawn_beliefs()` / the per-belief `over_drawn` flag — see FC-12 (§2) and Open Question Q3.

---

## 2. FCs provided / consumed

**Provides — CONTRACT CHANGE PROPOSAL FC-12 (new; Lane 2 provides, Lane 4 consumes):**
Two read-only accounting APIs the PRD-15 panel and any legibility surface can render. New file `persona/memory/budget.py`:

```python
def evidence_ceiling(candidate: dict) -> dict:
    """Max calibrated confidence the belief's EVIDENCE ALONE justifies.
    candidate carries the same feature dict FC-5 admit_decision consumes
    (independent_labs, support_ratio, textual_ok/span-grounded, provenance, crosscheck_counts),
    with reasoning/re-assertion signals excluded. Returns:
      {ceiling: float, basis: 'calibrator'|'coldstart', applicable: bool, n_independent: int}
    basis=='coldstart' + applicable=False when the FC-5 calibrator is unfit (see §3 F20.1)."""

def confidence_ledger(claim_id: str) -> dict:
    """Per-belief evidence account for the UI/panel. Returns:
      {claim_id, stored_conf: float, ceiling: float, overdraw: float, over_drawn: bool,
       spent: {independent_labs: int, span_grounded: bool, provenance: str},
       basis: str, applicable: bool, anchored: bool}
    overdraw = max(0, stored_conf - ceiling); over_drawn = applicable and overdraw > tolerance and not anchored."""

def overdrawn_beliefs(tolerance: float = 0.05, min_independent: int = 1) -> list[dict]:
    """Standing audit over LIVE beliefs. Each row = confidence_ledger(...) shape, over-drawn only,
    sorted by overdraw desc. Excludes anchored/HUMAN_CONFIRMED/TESTED (protected by construction)."""

def audit_pass(*, tolerance: float = 0.05, parent_id=None) -> dict:
    """Scheduled pass. Files a handoff per over-drawn belief (always safe); demotes ONLY when
    RQ-E30 has passed (else demote=[] with skipped_gated=True). Returns:
      {scanned:int, over_drawn:int, filed_handoffs:[handoff_id], demoted:[claim_id],
       skipped_unfit:bool, skipped_gated:bool}"""
```

*Rationale for a new FC rather than folding into FC-3/FC-5:* the accounting is a distinct concern from the graph reads (FC-3) and the admit decision (FC-5); it composes both. It is Lane-2-provided, Lane-4-consumed → a genuine cross-lane interface, so it is proposed as **FC-12** and must be acked by the master + Lane 4 before Lane 4 wires the panel stratum. Until acked, Lane 4 renders against the FC-12 fixture shape above (contract-first, exactly as PRD-15 renders `insufficient` first).

**Consumes:**
- **FC-5** (`calibrate.admit_decision`, `calibrate.load`) — the ceiling *is* the calibrator applied to evidence-only features. Verbatim reuse, no change.
- **FC-2** (`inbox.file_handoff`) — over-drawn beliefs file a `"confidence_overdrawn"` handoff.
- **FC-3** existing reads (`kg.beliefs`, `kg.provenance`) — independence counts + anchored flag. No change requested.
- **FC-6** (`retraction.contamination`) — *optional* signal that thins the evidence budget (a lab whose work is retracted stops counting toward the ceiling). Additive; degrades gracefully if unavailable (§3 F20.2 applicability gate).

**No other contract changes.** The membrane clamp (§1) is a within-lane additive line, not an FC change (the admission route enum `commit|human|reject` is unchanged; over-drawn just selects `human`).

---

## 3. Features

### F20.1 — Evidence ceiling + over-drawn detection (the accounting core)

**Problem & evidence.**
- `kg.add_claim` writes `c.confidence = avg(r.conf)` over SUPPORTED_BY sources (`kg.py:125-131`) — pre-F2.3 this is the extractor self-report; post-F2.3 it is `admit_decision.calibrated_p` (PRD-02 F2.1). Either way, **the stored number and the independent-evidence count (`independent_source_count`, distinct labs, `kg.py:128-129`) are stored side-by-side but never reconciled.** A belief can carry high confidence on one lab; nothing flags it.
- F2.6 (PRD-02 §104-106) enforces *monotonicity on write* ("confidence may only increase when a new distinct lab is added; INFERRED is read-only"). It does **not** audit the *level* of already-stored beliefs, nor beliefs written before F2.6, nor beliefs whose labs later thinned. PRD-20 is the complementary *level* audit F2.6 leaves open — the two together are the full "no fabricated confidence" invariant (F2.6 = the derivative, PRD-20 = the integral).
- Research: ECon (arXiv:2410.04068) — reasoning steps must not manufacture confidence absent new evidence (the source F2.6 already stands on); Kadavath et al. 2022 (*Language Models (Mostly) Know What They Know*) — models systematically over-report confidence relative to evidence, motivating an external ceiling; the ceiling estimator is the same calibrated map (Guo et al. 2017, ECE, arXiv:1706.04599) FC-5 fits, evaluated against replication hold-rates (OSC 2015, Science 349:aac4716) — the sources already in-repo via `analysis/calibration.py`. **The ceiling itself imports no constant** (CLAUDE.md §2, PRD-02 F2.3): it is the FC-5 calibrator fit on Persona's own adjudicated outcomes.

**Design.** New `persona/memory/budget.py` (pure; no model, no network):

- **`evidence_ceiling(candidate)`** — build an *evidence-only* feature dict from the belief (independent_labs, span_grounded=textual_ok, support_ratio, provenance, crosscheck_counts) with any reasoning/re-assertion signal zeroed, then `p = calibrate.admit_decision(evidence_only)["calibrated_p"]`. That `p` is by definition the max the calibrator will license from evidence alone → the ceiling. **Cold-start** (calibrator unfit — F2.3 ships a cold-start stub): fall back to a conservative closed-form monotone in independence, `ceiling = 1 - (1 - p_lab) ** n_independent` clamped to `[0, C_MAX]` with a deliberately conservative `p_lab` and `C_MAX=0.9`, tagged `basis='coldstart', applicable=False` — surfaced but never auto-acted-on until the calibrator is fit AND RQ-E30 passes. `# see experiments/exp_rq_e30_confidence_budget.py — ceiling validated by reversal-prediction, not asserted.`
- **`confidence_ledger(claim_id)` / `overdrawn_beliefs(tolerance)`** — read live beliefs via `kg.beliefs(min_independent=1)` + `kg.provenance`, compute `overdraw = max(0, stored_conf - ceiling)`, flag `over_drawn = applicable and overdraw > tolerance and not anchored`. Anchored / HUMAN_CONFIRMED / TESTED are excluded up front (a human/test *spent real budget*; the ceiling does not apply — an explicit not-applicable, not a pass).
- **`audit_pass(...)`** — scan; for each over-drawn belief `inbox.file_handoff("confidence_overdrawn", dossier)` where the dossier (FC-2 schema) carries `{decision_requested:"confirm or demote over-drawn belief", why_unresolvable:"stored confidence exceeds evidence-justified ceiling by {overdraw}", disagreeing:[{claim_id, span, qualifiers}], conflict_type:"insufficient", cheapest_test:{action:"add independent replication or human-confirm", cost_tier:"public_data"}, expected_updates:[{outcome:"demote", belief_change:"confidence→ceiling"},{outcome:"confirm", belief_change:"anchor"}], uncertainty:overdraw, authority_boundary:"anchor stays human"}`. **Demotion (clamp `stored_conf` → ceiling via `kg.add_claim`'s F2.6-guarded path) fires only when RQ-E30 has passed** (a persisted `ops_dir/rq_e30.passed` flag, mirroring how F2.3/FC-4 gate autonomy on their RQs); otherwise `demoted=[], skipped_gated=True`.

**Data flow:** membrane admit (F20.3, forward beliefs) → clamp at write, over-drawn impossible for new beliefs · scheduled `audit_pass` (daemon revisit loop, alongside PRD-02 F2.9 `revisit_pass`) → legacy/thinned beliefs → handoff + panel · Lane 4 panel (PRD-15) reads `overdrawn_beliefs()` for the stratum.

**Epistemic guardrails.**
- The ceiling is the FC-5 calibrator on evidence-only features — **no imported constant, no model self-report** enters it; it is validated on Persona's own outcomes.
- **Applicability gate is explicit** (skipped ≠ passed, PRD-00 §2): anchored/HUMAN_CONFIRMED/TESTED → `applicable=False` ("protected, ceiling N/A"); calibrator-unfit → `basis='coldstart', applicable=False` (advisory only). Neither is silently treated as "not over-drawn."
- **Confidence can never exceed the evidence bound** (the PRD-02 F2.6 tie): F2.6 blocks *raising* without a new independent span; PRD-20 blocks *standing above* the bound. A reasoning/synthesis step raises nothing (F2.6) and cannot lift the ceiling (the ceiling ignores reasoning signals by construction).
- **Human anchors high-stakes.** Over-drawn → handoff, never auto-anchor; auto-demote is gated (RQ-E30) and never touches an anchor.

**Required experiment — RQ-E30 (new; registry currently ends at E29).**
- **Hypothesis:** beliefs flagged **over-drawn** are later **reversed** (weakened/refuted on verified-ledger revisit, or auditor band → `fragile` after new independent literature) at a higher rate than non-over-drawn beliefs — better than chance.
- **Oracle (real outcomes only, reused verbatim from PRD-15):** verified-ledger revisit transitions (`verified.entries()` → `status ∈ {verified, weakened, refuted}` after `revisits>0`; `verified.py:67`, `revisit.py:36` band) and auditor re-adjudication (`watchlist.entries()` with `support+contradict ≥ 1`). `reversed = 1` iff `weakened|refuted` (verified) or band `fragile` (auditor); `0` iff still `verified` / `robust`.
- **Metric:** (i) reversal-rate(over-drawn) − reversal-rate(rest), 95% bootstrap CI; (ii) AUC of `overdraw` (continuous) predicting `reversed`.
- **Gate:** rate-difference 95% CI excludes 0 **AND** AUC lower-CI > 0.5, over **≥20 bootstrap resamples** (seeded) of the resolved-outcome set; if `<` MIN_OUTCOMES (20) resolved outcomes exist, RQ-E30 is `insufficient` — over-drawn stays advisory (surfaced, handoff, panel) and **auto-demote never fires** (no `rq_e30.passed` flag). Results → `/results/FINDINGS.md`; script → `experiments/exp_rq_e30_confidence_budget.py`. Cited in a `budget.py` comment.
- Register in `docs/RESEARCH_QUALITY_PROGRAM.md`: `RQ-E30 | Lane 2 | Over-drawn flag predicts later reversal better than chance | rate-diff CI>0 ∧ AUC-lowCI>0.5, ≥20 seeds, verified-ledger+auditor oracle`.

**Acceptance + one runnable check.**
- A belief with `stored_conf=0.9`, 1 independent lab, calibrator giving `ceiling≈0.6` → `confidence_ledger.over_drawn == True`, `overdraw≈0.3`, files one `"confidence_overdrawn"` handoff. An anchored belief at 0.99 → `applicable==False`, never over-drawn. Before RQ-E30 passes, `audit_pass().demoted == []` and `skipped_gated==True`.
- **Runnable check:** `python -m persona.memory.budget` (its `demo()` asserts: over-drawn detected on a synthetic high-conf/low-evidence belief; anchored excluded; monotonicity — ceiling non-decreasing in `n_independent`; demote gated off without the flag) **and** `tests/test_confidence_budget.py::test_overdrawn_flag_and_handoff`.

**Effort.** M (one pure module ~120 lines reusing FC-5/FC-3/FC-2 + one experiment + one test). **Deps.** F2.3 (calibrate), F2.6 (write invariant), FC-2.

---

### F20.2 — Evidence-budget thinning on retraction / supersession (optional signal)

**Problem & evidence.** A belief's independent-lab budget is computed from *current* SUPPORTED_BY sources (`kg.py:128`), but a lab whose work is later **retracted** (FC-6, PRD-03) or whose claim is **superseded** by a newer validity-window claim (PRD-02 F2.7) should stop counting toward the ceiling — otherwise a belief keeps a budget it no longer has. This is precisely how an over-draw *appears over time* rather than at write.

**Design.** In `evidence_ceiling`, before building the evidence-only feature dict, discount the independence count: `n_effective = n_independent − |labs whose sole supporting source is retracted (retraction.contamination) or whose claim is superseded (valid_to set)|`. **Applicability gate:** if FC-6 is unavailable or no source carries a DOI/PMID, emit `basis` note `retraction-check-skipped` and use the raw count — an explicit skipped state, never a silent pass. Pure; no new write.

**Epistemic guardrails.** Thinning only ever *lowers* the ceiling (raises over-draw) — it cannot manufacture confidence. Skipped-when-inapplicable is explicit.

**Required experiment.** **Trivial** — deterministic set arithmetic over existing FC-6 / `valid_to` reads; correctness pinned by `test_confidence_budget.py::test_retraction_thins_budget` (a belief with 2 labs, one retracted → ceiling drops → becomes over-drawn). No autonomy driven by this alone (it feeds F20.1's flag, which is itself RQ-E30-gated).

**Acceptance + one runnable check.** A 2-lab belief where one lab's only source is retracted → `n_effective==1`, ceiling drops, `over_drawn` flips true. Check: `test_confidence_budget.py::test_retraction_thins_budget`. **Effort.** S. **Deps.** F20.1; FC-6.

---

### F20.3 — Membrane admit-time ceiling clamp (make over-drawn impossible going forward)

**Problem & evidence.** F20.1 audits *stored* beliefs; the clean fix is to never *create* an over-drawn belief. PRD-02 F2.1 `admit_candidate` already computes `calibrated_p` via FC-5 and writes it (PRD-02 §50-51). One line makes the invariant structural at the source.

**Design.** In `membrane.admit_candidate` (PRD-02-owned; within-lane coordinated edit), after `admit_decision`:
```python
ceil = budget.evidence_ceiling(candidate)          # evidence-only features
if ceil["applicable"] and calibrated_p > ceil["ceiling"] + TOL:
    route = "human"                                 # over-drawn at birth → human, never a silent commit
calibrated_p = min(calibrated_p, ceil["ceiling"])  # written confidence never exceeds the bound
```
`# see budget.evidence_ceiling / RQ-E30 — a belief may not be born over-drawn.` This is additive: the `commit|human|reject` enum is unchanged; the clamp only ever *lowers* the written number (so it composes with F2.6's monotonic recompute — a subsequent new-lab write recomputes and re-clamps).

**Epistemic guardrails.** Clamp is monotone-down only (never inflates). Over-drawn-at-birth routes to human (safe), consistent with Balanced autonomy. Anchored path untouched (`applicable=False`).

**Required experiment.** **Trivial** — one guarded clamp on an existing decision; its behavior is the F20.1 ceiling already gated by RQ-E30. Pinned by `test_confidence_budget.py::test_admit_clamps_to_ceiling` (a candidate whose `calibrated_p` would exceed its evidence ceiling is written at the ceiling and routed `human`).

**Acceptance + one runnable check.** Candidate with `calibrated_p=0.85`, evidence ceiling `0.6` → written `confidence≈0.6`, `route=='human'`. Check: `test_confidence_budget.py::test_admit_clamps_to_ceiling`. **Effort.** S (one line + test). **Deps.** F20.1, PRD-02 F2.1/F2.3.

---

## 4. Sequencing

1. **After** PRD-02 lands F2.3 (`calibrate.admit_decision` real or cold-start stub) and F2.6 (write invariant) — PRD-20 stands on both. Until then, `budget.py` builds against the FC-5 cold-start stub (`route='human'`, `bound=None`), which yields `basis='coldstart', applicable=False` everywhere — safe and honest.
2. Land `persona/memory/budget.py` (F20.1) with `demo()` self-check + the FC-12 fixture shape committed so Lane 4 (PRD-15) can render the over-drawn stratum against it.
3. `experiments/exp_rq_e30_confidence_budget.py` + register RQ-E30 in `docs/RESEARCH_QUALITY_PROGRAM.md` as `open`. It reads only real on-disk outcomes → renders `insufficient` until ≥20 accrue (exactly like PRD-15). No `rq_e30.passed` flag until the gate is met.
4. F20.2 (retraction thinning) once FC-6 (`retraction.contamination`, PRD-03) is available; degrades gracefully before then.
5. F20.3 (membrane clamp) — the one coordinated line in `admit_candidate`, landed after F2.1 exists (flag in HANDOFF dispatch log).
6. Wire `audit_pass` into the daemon revisit loop next to PRD-02 F2.9 `revisit_pass` (Lane 2 owns both; one additive scheduled call).

All Lane-2-internal except the FC-12 read (Lane 4 consumes) and the F20.3 line (within-lane coordinated). Nothing blocks Lane 1/3.

---

## 5. Test plan

- **`tests/test_confidence_budget.py`** (new, Lane 2):
  - `test_overdrawn_flag_and_handoff` — synthetic high-conf/low-evidence belief → `over_drawn==True`, `overdraw≈stored−ceiling`, `audit_pass` files exactly one `"confidence_overdrawn"` handoff; a well-supported belief at/below ceiling → not flagged.
  - `test_anchored_never_overdrawn` — anchored belief at 0.99 → `applicable==False`, absent from `overdrawn_beliefs()`, never demoted.
  - `test_ceiling_monotone_in_evidence` — `evidence_ceiling` non-decreasing as `n_independent` rises (0→1→2→3), cold-start closed form and calibrator path both.
  - `test_demote_gated_on_rq_e30` — no `ops_dir/rq_e30.passed` → `audit_pass().demoted==[]`, `skipped_gated==True`; with the flag → non-anchored over-drawn beliefs demoted to ceiling, anchors still untouched.
  - `test_retraction_thins_budget` (F20.2) — 2-lab belief, one lab's source retracted → `n_effective==1`, ceiling drops, flips over-drawn; FC-6 unavailable → `retraction-check-skipped` note, raw count used.
  - `test_admit_clamps_to_ceiling` (F20.3) — candidate whose `calibrated_p` exceeds its evidence ceiling is written at the ceiling and routed `human`.
- **`experiments/exp_rq_e30_confidence_budget.py`** — RQ-E30: assemble resolved (over_drawn, reversed) pairs from the verified-ledger + auditor oracle; ≥20 seeded bootstrap resamples; assert the gate (rate-diff CI>0 ∧ AUC-lowCI>0.5) or emit `insufficient`. Writes `/results` + a one-line reversal note.
- **No regressions:** PRD-02's `test_membrane_dual_signal.py`, `test_calibrate.py`, and `test_calibration.py` (PRD-15) pass unchanged — PRD-20 only adds a module, one guarded membrane line, and read APIs.

---

## 6. Open questions

- **Q1 (ceiling estimator — the one load-bearing choice).** The ceiling = FC-5 calibrator on evidence-only features. Is "evidence-only" best defined as (a) *drop* reasoning/re-assertion features from the candidate, or (b) fit a *separate* evidence-only calibrator head? (a) is the lazy, zero-new-fit default and is what F20.1 specs; (b) only if RQ-E30 shows (a)'s ceiling is systematically mis-set. Reversible; does not block other lanes. **Decision deferred to RQ-E30 evidence.**
- **Q2 (tolerance & cold-start `p_lab`).** `TOL=0.05` and the cold-start `p_lab`/`C_MAX=0.9` are conservative starting knobs (hardware-calibration reflex: leave the knob). RQ-E30 sweeps `TOL` for the best reversal-prediction operating point; cold-start values are advisory-only (`applicable=False`) so they can never drive autonomy before the calibrator is fit. Not blocking.
- **Q3 (FC-12 ack + PRD-15 stratum).** FC-12 (`overdrawn_beliefs`, `confidence_ledger`) is a new Lane-2→Lane-4 read. **Blocks Lane 4 only for the over-drawn stratum on the PRD-15 panel** — needs master + Lane-4 ack in the HANDOFF dispatch log. Until acked, Lane 4 renders against the fixture shape in §2 (contract-first). The panel itself (PRD-15 F15.1) ships without this stratum; PRD-20 adds it as an additive `by_source`-style split (over-drawn beliefs should show predicted ≫ observed). No change to PRD-15's signatures.
- **Q4 (auto-demote autonomy).** Even after RQ-E30 passes, is clamping a *non-anchored, non-TESTED* belief's stored confidence down to its ceiling within Balanced autonomy, or should *every* demotion also file a handoff (surface-then-demote)? Spec'd conservative: demote fires post-gate but each demotion still emits a legible `belief_update` event and a handoff; a stricter policy (human-confirm every demotion) is a one-line change to `audit_pass`. Does not block other lanes.
