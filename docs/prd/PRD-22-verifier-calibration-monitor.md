# PRD-22 — Verifier-calibration monitor

> Owner: implementer lane 1 · Status: DRAFT-for-implementation · Autonomy: Balanced · Depends on: PRD-01 F1.2 (`agents/verifier.py`), the verified ledger (`memory/verified.py`) + revisit loop (`agents/revisit.py`) · Provides: **FC-14** (verifier-calibration read API), a new sidecar approval log, and a within-lane routing/quarantine guard.

---

## 0. Summary and the capability unlocked

The lane-1 charter promises "scale of reading, **discipline of believing**": a dedicated Verifier that re-runs the actual check on contested claims (PRD-01 F1.2, `agents/verifier.py`). But a verifier is only as good as its *own* calibration — the research is explicit that **a weak verifier gives false assurance** and that verification is net-positive **only selectively** ("When Does Verification Pay Off", arXiv:2512.02304). Today nothing watches the watcher: `verify()` emits `supported`/`refuted` verdicts, a `supported` computational verdict writes a TESTED-provisional ledger entry (`verifier.py` → `verified.record(..., source="verify")`), and the revisit loop later flips that entry `verified → weakened/refuted` (`agents/revisit.py:45`), yet **no one asks whether the verifier's *approvals* are the ones that keep reversing**. A rubber-stamp verifier — one that approves everything and never refutes — would sail through undetected, minting false-confidence TESTED beliefs.

This PRD adds a **verifier-calibration monitor** (Backlog #6): a new lane-1 module `agents/verifier_monitor.py` that (a) logs every actionable verify verdict against a *verifier identity* and the ledger entry it produced, (b) uses the **revisit outcomes already in the ledger as a ground-truth oracle** to compute a per-verifier **rubber-stamp score** = how often a verifier's approvals later reverse, relative to the population reversal rate, (c) **routes expensive verification only where it pays off** (the supervisor skips/downgrades a verifier whose approvals add no discrimination), and (d) **flags + quarantines a mis-calibrated verifier** — its `supported` verdicts are downgraded to `inconclusive` and the fact is surfaced to the legibility layer and to a human. The capability unlocked: Persona can now *catch its own verifier drifting into a rubber stamp* from real revisit history, instead of silently trusting it — the same epistemic move (judgment is evidence, not truth; caught, never silently trusted) that the charter applies to readers, now applied to the verifier itself.

---

## 1. File ownership (this lane's DISJOINT set)

**New files (this lane creates, lane 1):**
- `persona/agents/verifier_monitor.py` — the monitor: approval logging + per-verifier calibration/rubber-stamp scoring + quarantine guard (this PRD).
- `experiments/exp_e35_verifier_calibration.py` — RQ-E35 fault-injection harness (new experiment; `experiments/*` is shared-additive, owned by the creating lane per PRD-00 §3 "new-file ownership rule").

**Edited files (this lane owns the edits — all lane-1 files):**
- `persona/agents/verifier.py` — one additive call: after a verdict is produced (and after the `supported`-computational `verified.record(...)` at the F1.2 record site), call `verifier_monitor.record_verdict(verifier_id, result, ledger_key=entry["key"] if recorded else None)`. No signature change to `verify()`.
- `persona/daemon/supervisor.py` — in F1.2's selective `verify`-routing path, consult `verifier_monitor.is_quarantined(verifier_id)` before spending on a verifier that pays off, and pass every returned verdict through `verifier_monitor.guard_verdict(...)`. **Additive guard only** — coordinate the exact insertion point with PRD-01's own `supervisor.py` edits (same lane, single owner, no cross-lane contract needed).

**New sidecar artifact (lane-1 owned, written only via the monitor):**
- `self/verifier_approvals.jsonl` — append-only `{verifier_id, ledger_key, claim_id, verdict, check_kind, ran_code, at}`, one row per actionable verdict. Lives beside `self/verified.jsonl` (same `paths.self_dir`, `verified.py:28`). Append-only and reversible-by-nature (never mutated), mirroring the ledger's own append discipline.

**Boundary files another lane also touches — decoupled by a contract:**
- `persona/memory/verified.py` — **READ ONLY from this lane** (`verified.entries()`; the ledger `key` is obtained from the dict `verified.record()` already returns, `verified.py:64` — this lane never calls the private `_key` and never writes the ledger). No edit, no schema change. The join is entirely on the sidecar log + the ledger's existing `status`/`revisits` fields.
- `persona/api/app.py` (Lane 4) + `persona/api/static/index.html` (Lane 4) — Lane 4 renders the per-verifier scorecard via **FC-14**, mirroring the existing read-only `GET /api/persona/{pid}/verified` route (`app.py:295`). This lane provides the read functions; Lane 4 adds the route + surface. **This new cross-lane interface is flagged as a CONTRACT CHANGE PROPOSAL in §6.**

---

## 2. Frozen contracts provided / consumed

### FC-14 — this lane PROVIDES (new; `persona/agents/verifier_monitor.py`)

```python
# WRITE seam — called by verifier.py once per actionable verdict (not called for not_applicable):
def record_verdict(verifier_id: str, result: dict, *, ledger_key: str | None = None) -> None
    # result is the F1.2 verify() return: {verdict, check_kind, ran_code, claim_id, ...}
    # Appends one row to self/verifier_approvals.jsonl. Idempotent per (verifier_id, ledger_key, claim_id, at-bucket) — a re-log with the same ledger_key replaces, never duplicates.

# READ seam — consumed by Lane 4 (render) and by RQ-E35:
def scorecard() -> list[dict]
    # one row per verifier_id seen:
    # {verifier_id, n_verdicts, n_approved, n_revisited, reversal_rate, baseline_reversal,
    #  rubber_stamp_score, ci_low, ci_high, refute_rate, status, at}
    # status ∈ {'trusted','watch','quarantined','insufficient'}.
def calibration(verifier_id: str) -> dict   # the single-verifier row (or an 'insufficient' stub).

# ROUTE seam — consumed by supervisor.py (same lane):
def is_quarantined(verifier_id: str) -> bool
    # True only when status=='quarantined' AND the auto-enforce gate ops_dir/rq_e35.passed exists.
    # Advisory (always False for enforcement) until RQ-E35 passes — see guardrails.

# QUARANTINE transform — applied to every verdict the supervisor routes:
def guard_verdict(verifier_id: str, result: dict) -> dict
    # If the verifier is quarantined+enforced: downgrade result['verdict'] 'supported'->'inconclusive',
    # tag result['quarantined']=True and result['note']+=reason; otherwise return result unchanged.
    # Mirrors the FC-8 oracle-guard quarantine transform (CCP-16a: verdict->inconclusive) — same shape,
    # applied to the verifier instead of a science oracle.
```

`verifier_id` default (single verifier today): the model id driving the F1.2 router — `config.MODEL_READER` for the analyst/math route (`config.py:39`), so distinct model configs get distinct ids automatically. **Ponytail: one id today, keyed by id so multi-verifier variants score independently later — no multi-verifier orchestration built that doesn't exist yet.**

### Consumed
- **PRD-01 F1.2** — `agents/verifier.py::verify(...) -> {ok, claim_id, verdict, check_kind, ran_code, artifact_ids, span, note}` (verbatim from `verifier.py:16-25`). The monitor consumes this shape; it does not change it.
- **verified ledger** — `verified.entries() -> list[{key, statement, method, status, verified, source, revisits, last_revisit, revisit_note, at, ...}]` (`verified.py:35-46`, `record` shape `verified.py:58-61`). Read-only.

### CONTRACT CHANGE PROPOSAL — CCP-22a (FC-14 render, → Lane 4)
FC-14's read functions (`scorecard`/`calibration`) are a **new cross-lane interface**: Lane 4 adds a read-only `GET /api/persona/{pid}/verifiers` route rendering the scorecard (mirroring `app.py:295`) and a trust-tab surface (PRD-04 F4 per-agent cost-vs-yield / PRD-15 reliability panel). Flagged for master + Lane 4 ack per PRD-00 §4. Until acked, the monitor is fully functional headless (writes the log, computes scores, emits a `belief_update`/`control` event on flag) and blocks nobody.

---

## 3. Features

### F22.1 — Attributable verify-approval log

- **Problem & evidence.** The verified ledger records *that* a result was tested and its later revisit status, but **not which verifier approved it**. `verified.record(...)` (`verified.py:49`) stores `source` (a free string like `"verify"` / `"analyst"`) and `method` (`lean`/`sympy`/`analyst`) — enough to know the *route*, not the *verifier identity*, and there is no row-level link from a `verify()` verdict to the ledger entry it minted. Without that link you cannot ask "of the claims **this** verifier approved, how many reversed?" — the exact question arXiv:2512.02304 says decides whether verification pays off. `verify()` today returns `{verdict, check_kind, ran_code, ...}` and, on a `supported` computational claim, records to the ledger via the analyst path (PRD-01 F1.2 guardrails, `verifier.py` record site) but **drops the returned `entry["key"]` on the floor**.
- **Design.**
  - New `verifier_monitor.record_verdict(verifier_id, result, *, ledger_key=None)` appends one JSONL row to `self/verifier_approvals.jsonl`: `{verifier_id, ledger_key, claim_id, verdict, check_kind, ran_code, at}`. Called from `agents/verifier.py` for every **actionable** verdict — `supported` / `refuted` / `inconclusive` — and **not** for `not_applicable` (a skipped applicability gate is not an approval or a rejection, so it must not pollute the rate; this honors the "skipped ≠ passed" boundary from `verifier.py:1-4`).
  - The verifier passes `ledger_key = entry["key"]` when (and only when) it just wrote a ledger entry (`supported` computational), else `ledger_key=None`. The `key` is already returned by `verified.record()` (`verified.py:64`) — **reuse it, don't recompute** (`# ponytail: the key comes back from record(); no dependency on verified._key`).
  - `verifier_id` is threaded from the verify router: the model id (`config.MODEL_READER`) for the analyst/math route today. One additive argument passed at the call site; `verify()`'s public signature is untouched.
  - Idempotency: a re-log with the same `(verifier_id, ledger_key)` overwrites the prior row (dedup on read), so a re-run of `verify()` on the same claim does not double-count — same discipline as `verified.record`'s dedup-by-key (`verified.py:57`).
- **Epistemic guardrails.** The log is **provenance-neutral telemetry**, not a belief: it never writes the KG or the self, and `record_verdict` cannot change a verdict. `not_applicable` verdicts are excluded so an out-of-domain skip is never mistaken for an approval. Append-only + reversible (a row is never mutated), matching the ledger's own audit posture (`verified.py` append discipline).
- **Required experiment.** trivial — no experiment. This is append-only structured logging of an already-computed verdict, joined on a key the ledger already returns; correctness is structural, covered by the F22.2/F22.3 checks and one round-trip unit test. `# ponytail: log a row, don't build an event bus.`
- **Acceptance criteria.** (1) A `not_applicable` verdict appends **zero** rows. (2) A `supported` computational verdict appends exactly one row carrying the same `ledger_key` the ledger entry has. (3) Runnable check: `pytest tests/test_verifier_monitor.py::test_not_applicable_not_logged_supported_logged`.
- **Effort** S · **Dependencies** PRD-01 F1.2 (the verdict + record site).

---

### F22.2 — Per-verifier rubber-stamp / calibration score from revisit outcomes

- **Problem & evidence.** The revisit loop is a **ready-made ground-truth oracle for "was this approval wrong?"**: it re-tests a standing result and flips it `verified → weakened/refuted` when later evidence disagrees (`revisit.py:36-46`, `verified.update_status`, `verified.py:67-82`; entries carry `revisits`/`last_revisit`/`revisit_note`). A verifier's *approvals that later reverse under revisit* are its false-assurances. Research: **"When Does Verification Pay Off"** (arXiv:2512.02304) — a weak verifier gives false assurance and verification is net-positive only when the verifier actually discriminates; **VerifiAgent** (arXiv:2504.00406) and **CRITIC** (arXiv:2305.11738) — verifier quality must be measured against external outcomes, not assumed. In-repo precedent for outcome-oracle-driven flags with a CI gate: FC-13 / RQ-E34 (over-drawn flag predicts later reversal, `AUC lower-CI > 0.5`) and RQ-E30 (control-injection catches a broken oracle, detection ≥ 0.95).
- **Design.** In `verifier_monitor.py`, `scorecard()` / `calibration(verifier_id)` compute, per `verifier_id`, from the approval log ⋈ `verified.entries()` (join on `ledger_key`):
  - **Outcome per approval.** An approval is *resolved* only if its ledger entry was revisited (`entry["revisits"] > 0`); un-revisited approvals are **outcome-unknown and excluded** (never counted as "held" — that would understate reversal). `reversed = entry["status"] in {"weakened","refuted"}`.
  - **reversal_rate** = reversals / resolved-approvals (`n_revisited`). **baseline_reversal** = reversal rate over **all** revisited ledger entries (population prior, robust to the pathological "verifier approved everything" case where a per-verifier control group would be empty).
  - **rubber_stamp_score** = `reversal_rate / max(baseline_reversal, ε)` — ≈ 1 ⇒ the verifier's approvals reverse as often as the untouched population ⇒ **it filtered nothing (rubber stamp)**; ≪ 1 ⇒ its approvals hold far better than baseline ⇒ **it discriminates**. Report a bootstrap 95% CI `(ci_low, ci_high)` on the score (resample resolved approvals + population, ≥1000 draws, seeded — no fabricated confidence, it's a measured rate ratio).
  - **refute_rate** = fraction of a verifier's actionable verdicts that are `refuted`/`inconclusive` (from the log alone). A corroborating legibility signal — a verifier that *never* refutes is suspicious but not proof; the reversal-based score is the primary metric.
  - **status** — `insufficient` when `n_revisited < min_resolved` (default 12; abstain, exactly like the applicability gate — don't judge a verifier on 2 approvals); else `quarantined` when `rubber_stamp_score` CI lower bound ≥ `τ_quarantine` (default 0.85 — approvals reverse ≥85% as often as baseline, i.e. essentially no discrimination) **and** `refute_rate ≤ refute_floor` (default 0.02); `watch` in a soft band below that; else `trusted`.
- **Epistemic guardrails.** The score is a **measured rate ratio with a CI over a real outcome oracle (revisit)**, never a model self-report — the "no fabricated confidence" rule. Abstention (`insufficient`) below the sample floor is first-class. It targets the **rubber-stamp / false-assurance** failure the task names (approves things that reverse); the opposite failure (a verifier that refutes everything) is explicitly out of scope and left `trusted` unless its (empty) approval set trips nothing. A verifier's verdict remains **evidence, not truth**: the monitor grades the grader, and the human still anchors any high-stakes reversal.
- **Required experiment.** **RQ-E35 — fault-injection: an intentionally-lenient verifier must be detected.** See §3 F22.4 (the shared experiment for this feature and F22.3).
- **Acceptance criteria.** (1) A verifier whose approvals reverse at the population base rate scores `rubber_stamp_score ≈ 1.0`; a verifier whose approvals never reverse scores `≈ 0.0`. (2) `n_revisited < min_resolved` ⇒ `status == "insufficient"` and the verifier is **not** quarantined. (3) Runnable check: `pytest tests/test_verifier_monitor.py::test_rubber_stamp_score_and_insufficient_abstain` on two synthetic approval/ledger fixtures (all-reverse vs none-reverse) + a below-floor fixture.
- **Effort** M · **Dependencies** F22.1; read-only `verified.entries()`.

---

### F22.3 — Route where it pays off + flag/quarantine a mis-calibrated verifier

- **Problem & evidence.** F1.2 already routes `verify` **selectively** to contested/high-stakes claims (PRD-01 F1.2, `supervisor.py`), but it spends the same on a verifier whether or not that verifier is *earning* the spend. arXiv:2512.02304's whole point is that verification cost is only justified when the verifier discriminates — so a rubber-stamp verifier's `verify` calls are pure waste **and** actively harmful (they mint false-confidence TESTED entries). The system needs to (a) stop paying a verifier that adds no discrimination and (b) stop *trusting* its `supported` verdicts. In-repo precedent for the quarantine transform: the FC-8 oracle-guard (CCP-16a) already defines "verdict → inconclusive, provenance → abstain" for a broken oracle — the same move, applied to a verifier.
- **Design.**
  - **Route (advisory → gated).** In `supervisor.py`'s F1.2 verify-routing path, before enqueuing a `verify` for a given `verifier_id`, consult `verifier_monitor.is_quarantined(verifier_id)`; if quarantined-and-enforced, skip the spend (the claim stays at its current provenance / routes to the existing human path) and log "skipping verify — verifier <id> quarantined (rubber-stamp)". This reuses the existing selective-routing seam — **no new scheduler**, one guard (`# ponytail: one guard in the existing route, not a new dispatcher`).
  - **Quarantine transform.** Every verdict the supervisor does route is passed through `guard_verdict(verifier_id, result)`: a quarantined+enforced verifier's `supported` → `inconclusive`, `result["quarantined"]=True`, reason appended to `note`. Downstream (the F1.2 ledger-record path) already only records TESTED on `supported`, so a downgraded verdict **writes no belief** — the false-assurance is stopped at the source without deleting anything.
  - **Flag / surface.** On the transition into `quarantined`, emit one legible event `log().emit("belief_update", f"verifier {vid} flagged as rubber-stamp: approvals reverse {score:.0%} vs baseline", actor="verifier_monitor")` (`events.py:58`), and surface the scorecard row to the legibility layer via FC-14 (Lane 4 render). A quarantined verifier is a **needs-human** signal, not an automatic deletion of its past beliefs — those remain, provenance-typed, for a human/revisit to resolve.
- **Epistemic guardrails.** Quarantine **caps trust, it does not erase belief** — past TESTED entries the verifier minted keep their provenance and revisit history (append-only); quarantine only stops *new* `supported` verdicts from that verifier being trusted, and routes the decision to a human. **Auto-enforcement is gated on RQ-E35** (`ops_dir/rq_e35.passed`, mirroring FC-13's `ops_dir/rq_e34.passed`): until the monitor is proven to catch a lenient verifier without false-quarantining a calibrated one, `is_quarantined` returns `False` for enforcement and `guard_verdict` is a pass-through — the scorecard is **advisory-only** (surfaced to humans), never silently acting. Balanced autonomy: it flags and surfaces autonomously; it only *acts* (skip/downgrade) once the gate is earned, and never anchors.
- **Required experiment.** **RQ-E35** (shared, F22.4) is the gate for this feature's enforcement.
- **Acceptance criteria.** (1) With `ops_dir/rq_e35.passed` **absent**, a quarantined verifier still routes and `guard_verdict` is a pass-through (advisory-only). (2) With the gate present, a quarantined verifier's `supported` verdict comes back `inconclusive` + `quarantined=True`, and `record`-to-ledger is not reached for it. (3) Runnable check: `pytest tests/test_verifier_monitor.py::test_quarantine_advisory_until_gate` (gate absent → pass-through; gate present → downgrade).
- **Effort** M · **Dependencies** F22.2; PRD-01 F1.2 supervisor route (same lane, coordinate insertion).

---

### F22.4 — RQ-E35 fault-injection experiment (the gate)

- **Problem & evidence.** The load-bearing, genuinely-uncertain claim is: *the monitor detects a mis-calibrated verifier from revisit outcomes without falsely condemning a good one.* This is exactly the fault-injection posture RQ-E30 uses for a broken oracle (detection ≥ 0.95 AND false-quarantine == 0). It must be tested on ≥20 seeds before quarantine is allowed to act.
- **Design.** `experiments/exp_e35_verifier_calibration.py` (seeded, ≥20 trials):
  - **Fault-injected (lenient) verifier:** approves (`supported`) every claim it sees, never refutes. Feed it a stream where a known fraction of the underlying claims are false and thus reverse under a simulated revisit oracle (reuse the ledger's `verified.record` + `verified.update_status` on an isolated temp `self_dir`, or an in-memory fixture mirroring `entries()` — deterministic, no model, no FalkorDB, matching the offline style of `exp_poisoning.py`).
  - **Control (calibrated) verifier:** approves only claims that hold and refutes the false ones; its approvals reverse far below baseline.
  - **Metrics (mean ± 95% CI over ≥20 seeds):** detection-rate = P(lenient verifier reaches `status=="quarantined"`); false-quarantine-rate = P(calibrated verifier reaches `quarantined`); plus `rubber_stamp_score` separation between the two arms.
  - **Go/no-go gate:** **detection-rate ≥ 0.95 AND false-quarantine-rate == 0** across ≥20 seeds → write `ops_dir/rq_e35.passed`, enabling auto-enforcement (F22.3). Else quarantine stays advisory-only and the reversal is logged in `results/FINDINGS.md`. Results JSON to `results/rq_e35_verifier_calibration.json`; cite the run in a `# see experiments/exp_e35_...` comment at the `τ_quarantine`/`min_resolved` constants.
- **Epistemic guardrails.** The oracle is the **revisit outcome**, not a model judge; thresholds (`τ_quarantine`, `min_resolved`, `refute_floor`) are chosen *from this experiment*, not imported. The false-quarantine == 0 half of the gate is as important as detection — condemning a good verifier is the correctness boundary (out-of-domain false positive), so it is a hard zero.
- **Acceptance criteria.** (1) The lenient arm quarantines ≥ 95% of seeds; the calibrated arm quarantines 0. (2) The experiment is reproducible across `PYTHONHASHSEED` values. (3) Runnable check: `python experiments/exp_e35_verifier_calibration.py` prints the two rates and asserts the gate; a fast `pytest tests/test_verifier_monitor.py::test_e35_smoke` runs a 3-seed reduced version.
- **Effort** M · **Dependencies** F22.2/F22.3 (scores the arms).

---

## 4. Sequencing within the lane

1. **F22.1 (approval log)** — the substrate; land `record_verdict` + the one additive call in `verifier.py` first. Everything joins on this.
2. **F22.2 (scoring)** — `scorecard`/`calibration` over the log ⋈ ledger. Pure, testable on fixtures; no gate needed to compute (advisory).
3. **F22.4 (RQ-E35)** — run the fault-injection gate; it needs F22.2's scorer. Blocks *enforcement* only.
4. **F22.3 (route + quarantine)** — the supervisor guard + `guard_verdict`; ships advisory-only immediately, flips to enforcing when F22.4 writes `ops_dir/rq_e35.passed`.
5. **CCP-22a render** — hand FC-14 to Lane 4 once the scorer is stable (unblocks the trust-tab surface; headless-functional meanwhile).

Rationale: log → score → prove → act, so the system is legible and correct at every checkpoint and never acts on an unproven score (Balanced autonomy).

---

## 5. Test & verification plan

**Unit (`tests/test_verifier_monitor.py`, pytest only — ponytail):**
- `test_not_applicable_not_logged_supported_logged` (F22.1) — skip is not an approval; supported carries the ledger_key.
- `test_rubber_stamp_score_and_insufficient_abstain` (F22.2) — all-reverse ⇒ score ≈ 1; none-reverse ⇒ ≈ 0; below `min_resolved` ⇒ `insufficient`, not quarantined.
- `test_quarantine_advisory_until_gate` (F22.3) — gate absent ⇒ pass-through; gate present ⇒ `supported`→`inconclusive` + `quarantined=True`.
- `test_e35_smoke` (F22.4) — 3-seed reduced fault-injection asserts lenient detected, calibrated clean.

**Experiment / oracle:**
- `experiments/exp_e35_verifier_calibration.py` — the real ≥20-seed gate; the **revisit outcome is the oracle** (offline, deterministic, no model / no FalkorDB — same posture as `exp_poisoning.py`). Result JSON + `results/FINDINGS.md` entry; reversal logged if the gate fails.

**Integration:**
- End-to-end on a temp `self_dir`: seed a verified entry via `verified.record(..., source="verify")`, log a matching approval, flip it to `refuted` via `verified.update_status` (as `revisit` would, `revisit.py:45`), then assert `scorecard()` shows the reversal and the score moves — no mocks on the ledger.

**Browser smoke:** none in this lane (headless — the monitor emits a `log().emit` event and exposes FC-14; the trust-tab render is Lane 4's smoke under CCP-22a).

---

## 6. Open questions for the master/user

- **CCP-22a (FC-14 render) — blocks Lane 4 only, not this lane.** The scorecard read API is a new cross-lane interface; Lane 4 must add `GET /api/persona/{pid}/verifiers` + a trust-tab surface (mirroring `app.py:295` / PRD-15 reliability panel). **Confirm** the master routes this to Lane 4 and acks the FC-14 signatures. Monitor is fully headless-functional meanwhile.
- **`verifier_id` granularity — genuine choice, affects the score's meaning.** Default = the router's model id (`config.MODEL_READER`) so model configs score separately. Alternatives: one id per *route* (`analyst` vs `reason.prove`), or per (model × route). Proposed: model id today (single verifier), keyed so variants split later. **Confirm** we don't want per-route split now (it would fragment already-scarce revisit outcomes across buckets and push more verifiers below `min_resolved`).
- **`min_resolved` floor vs revisit throughput.** The score needs ≥`min_resolved` *revisited* approvals; revisit is a slow background loop (`revisit.py` re-tests one entry per tick). If real revisit volume is low, most verifiers sit `insufficient` for a long time (safe, but the monitor is quiet). **Confirm** Balanced autonomy is comfortable with "abstain until enough outcomes accrue" (it is the honest posture), or whether the supervisor should prioritize revisiting a verifier's *own* approvals to accrue calibration outcomes faster (a small F1.9/revisit-scheduling tweak, flag as a follow-up).
- **`refute_floor` corroboration.** The quarantine rule ANDs `rubber_stamp_score` with `refute_rate ≤ refute_floor`. A verifier could rubber-stamp yet occasionally refute (score high, refute_rate above floor) and escape quarantine. Proposed: keep the AND (conservative — reversal-lift alone can be noisy at small n), and let RQ-E35 tune `refute_floor`; **confirm** we prefer conservative (fewer false-quarantines) over aggressive here — consistent with the `false-quarantine == 0` gate.
