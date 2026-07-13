# PRD-15 — Self-calibration reliability panel

> **Owner lane:** 4 (Legibility, API & self-benchmarking) · **Status:** DRAFT-for-implementation (2026-07-13) · **Autonomy:** none — read-only display; drives no belief update, no anchor, no dispatch · **Depends-on:** existing `agents/audit.py`→`memory/watchlist.py` history, `memory/verified.py` revisit transitions, `api/app.py` route pattern. Complements PRD-04 F4.4 (`/epistemic`). No new FC.

---

## 0. Summary + capability unlocked

Persona's headline discipline is *"no fabricated confidence."* Today that is a **rule**; this panel makes it a **trending number**. Once real ground-truth outcomes accrue — auditor replication verdicts that were later re-adjudicated against new independent literature, and verified-ledger entries whose revisit loop marked them still-verified / weakened / refuted — we compute a **reliability diagram** (predicted-vs-observed), **Expected Calibration Error (ECE)**, and **Brier score** over Persona's *own* past verdicts, and render them.

The one non-negotiable: **only real outcomes**. Until enough resolved outcomes exist, the panel renders an explicit *"insufficient outcomes — N of 20 needed"* state, never a fabricated curve. The ECE/Brier arithmetic is standard and exact (done in code, no model); the only judgment is *what counts as a realized outcome*, which is defined conservatively and disclosed in the UI.

**Capability unlocked:** Persona can answer *"when I say 40%, does it replicate ~40% of the time?"* about itself — self-calibration as an auditable, versioned metric, not a claim. This is the empirical proof of the epistemic thesis (`CLAUDE.md` §2: "no fabricated confidence… validated on held-out data, never a model self-report").

---

## 1. File ownership (disjoint)

| File | New? | Lane | Note |
|---|---|---|---|
| `persona/eval/calibration_report.py` | **New** | 4 | The computation. Lane 4 owns `persona/eval/*` (PRD-00 §3). |
| `persona/api/app.py` | edit (new route only) | 4 | Add `GET /api/persona/{pid}/calibration`. Lane 4 owns "new routes only" in `app.py` (PRD-00 §3). |
| `persona/api/static/index.html` | edit (new surface only) | 4 | New sub-surface under the Epistemic tab (F4.4). Lane 4 owns "new surfaces only". |
| `tests/test_calibration_report.py` | **New** | 4 | Lane 4 owns `tests/*` (new). |

**Boundary / read-only dependencies (no editing, no FC):**
- Reads `persona/memory/watchlist.py::entries()` — auditor verdict history (predicted likelihood + re-audit band/support/contradict). Already read cross-lane by `app.py:432 /watchlist`; a stable public read API.
- Reads `persona/memory/verified.py::entries()` — verified-ledger transitions (status verified/weakened/refuted, `revisits`). Already read cross-lane by `app.py:291 /verified`.
- No shared *write* target → **no parallel-edit collision, no new FC required.** `calibration_report.py` is pure over on-disk state, exactly as `verified.summary()`/`watchlist.summary()` are.

---

## 2. FCs provided / consumed

- **Provides:** none. This is an internal Lane-4 read-and-render feature; nothing else consumes it.
- **Consumes:** no FC. It reads two existing public functions (`watchlist.entries()`, `verified.entries()`) that are already surfaced through existing routes. It does **not** touch FC-3/FC-5 or PRD-04 F4.4's `/epistemic` route — it is an *additive sibling* route.
- **CONTRACT CHANGE PROPOSAL:** none. (See Open Question Q1 for a soft read-stability note on `watchlist.entries()`/`verified.entries()`.)

---

## 3. Features

### F15.1 — Reliability report over Persona's own past verdicts

**Problem & evidence.**
- The auditor produces a real predicted probability per paper — `likelihood ∈ [0,1]` (`agents/audit.py:261`, `_write_report` at `audit.py:344`) — and its self-correction loop records movement against new independent literature in `watchlist.record_reaudit(...)` (`memory/watchlist.py:79`), which stores `history[]` = `{likelihood, band, at, support, contradict}`. **These predictions and their later re-adjudications exist on disk but are never scored for calibration.**
- The verified ledger records TESTED results and the revisit loop transitions them (`memory/verified.py:67 update_status`; `agents/revisit.py:36` computes `still-verified / weakened / refuted` by re-running the machine check). **These transitions are real outcomes that are never aggregated into a calibration number.**
- `analysis/calibration.py` already *fits* a replication prior on external labeled data and reports its own Brier/reliability in the module docstring (`calibration.py:12`) — but there is **no measurement of Persona's own emitted verdicts.** The rule "any surfaced number is validated on held-out data" (PRD-00 §2) is asserted for the *prior*, not yet proven for *Persona's outputs*.
- Research backing: ECE with equal-width binning + reliability diagrams — Guo et al. 2017 (*On Calibration of Modern Neural Networks*, ICML, arXiv:1706.04599); Brier 1950 (*Verification of forecasts expressed in terms of probability*, Mon. Wea. Rev. 78:1). Replication-outcome calibration strata this panel is measured against: OSC 2015 (Science 349:aac4716), Gordon 2021 (PLOS ONE 16:e0248780) — the same sources `calibration.py` cites. These are standard, uncontested estimators; no novel method.

**Design.**

New module `persona/eval/calibration_report.py` (pure, no model, no network):

```python
MIN_OUTCOMES = 20   # below this → "insufficient" state; matches the ≥20 discipline (CLAUDE.md §2)
N_BINS       = 10   # equal-width reliability bins over [0,1]
_VERIFIED_P  = 1.0  # DISCLOSED convention: a claim the system labeled "verified" asserted p≈1.0.
                    # Not a fabricated number — it reads the system's own categorical assertion.
                    # Surfaced in the UI so the top-bin composition is auditable.

def outcome_pairs(persona=None) -> list[dict]:
    """Realized (prediction, outcome) pairs from Persona's OWN past verdicts. Pure over on-disk state.
    Each pair: {p: float, y: float, source: 'auditor'|'verified', id: str, at: str, resolved_by: str}.
    Only RESOLVED outcomes are returned (see per-source gates below); unresolved verdicts are omitted."""

def reliability(pairs: list[dict], n_bins: int = N_BINS) -> dict:
    """Standard, exact. Returns:
      {n:int, ece:float, brier:float,
       bins:[{lo,hi,p_mid,p_mean,obs,n}]}   # obs = mean(y) in bin; empty bins have n==0, obs==None
    ECE   = Σ_bins (n_bin/N) * |obs_bin − p_mean_bin|
    Brier = mean((p − y)^2)."""

def report(persona=None) -> dict:
    """Top-level payload for GET /calibration.
      {status:'ok'|'insufficient', n:int, needed:int,
       ece:float|None, brier:float|None, bins:[...],
       by_source:{auditor:{n,ece,brier}, verified:{n, survival}},
       notes:[str],            # discloses the _VERIFIED_P convention + auditor-outcome definition
       generated:str}
    status=='insufficient' whenever n < MIN_OUTCOMES; ece/brier/bins are then omitted (None/[]),
    n/needed are populated so the UI can render 'N of 20'."""

def demo() -> None:   # __main__ self-check (see Acceptance)
```

**Outcome resolution (the one epistemic judgment — conservative + disclosed):**

*Source A — auditor (`watchlist.entries()`):* for each entry with `reaudits > 0` **and** a later `history` point carrying external evidence (`support + contradict ≥ 1` — only `record_reaudit` writes those, so this proves the re-adjudication saw *new independent literature*, not a model re-read):
- `p` = `history[0]["likelihood"]` (the original prediction),
- `y` = `1` if the latest `band == "robust"`, `0` if `"fragile"`; **`"contested"` → unresolved, omitted**,
- `resolved_by` = `"reaudit:{support}+/{contradict}-"`.

*Source B — verified ledger (`verified.entries()`):* for each entry with `revisits > 0` (the revisit loop actually re-tested it):
- `p` = `_VERIFIED_P` (disclosed convention),
- `y` = `1.0` still `verified` · `0.5` `weakened` · `0.0` `refuted`,
- `resolved_by` = `"revisit×{revisits}"`.

`report()` computes `reliability()` over the **combined** pairs and a per-source breakdown so the top bin's composition (auditor real-prob vs verified p=1.0) is visible. `by_source.verified.survival` = mean(y) over verified pairs = the plain "of the beliefs I marked TESTED, what fraction survived re-test" hold-rate, which stands on its own even when the combined diagram is still insufficient.

New route (`api/app.py`, mirrors `/verified` at `app.py:291`):
```python
@app.get("/api/persona/{pid}/calibration")
def calibration_panel(pid: str):
    """Reliability of Persona's OWN past verdicts: predicted-vs-observed + ECE + Brier over
    resolved auditor re-adjudications and verified-ledger revisit transitions. Renders an explicit
    'insufficient — N needed' state until MIN_OUTCOMES real outcomes accrue (never a fabricated curve)."""
    with context.use(_p(pid)):
        from ..eval import calibration_report
        return calibration_report.report()
```

**Data flow:** `openEpistemic()` (F4.4 surface) → `GET /calibration` → if `status=='insufficient'` render the "N of 20 needed" callout; else render a reliability diagram (predicted x-axis, observed y-axis, `y=x` perfect-calibration diagonal, per-bin dots sized by `n`, empty bins drawn as "no data" not as 0%) + two tiles (ECE, Brier) + the disclosure `notes`. Colour is never the only encoding (over/under-confident also labeled in text). Rendering is trivial (an existing chart idiom in `index.html`; reuse whatever the audit/history sparks already use — no new dependency).

**Epistemic guardrails.**
- **Only real outcomes.** `outcome_pairs` returns *nothing* for verdicts that were never re-adjudicated (auditor) or never revisited (verified). No synthetic outcomes, no imputed labels, no model self-report ever enters `y`.
- **Insufficient state is mandatory, not optional.** `status=='insufficient'` (curve omitted) below `MIN_OUTCOMES=20`. The UI shows the count, never a curve fit to <20 points.
- **The auditor outcome is a re-adjudication against *new independent literature*, not an external replication registry** — gated on `support+contradict ≥ 1` so it reflects evidence that accrued *after* the prediction. This is Persona's best in-repo "did it hold up" proxy; the UI `notes` disclose it verbatim and RQ-E26 (below, optional) is the path to validate it against a real external replication label set before this number is ever allowed to *drive* anything.
- **The `p=1.0` convention for TESTED claims is disclosed**, not hidden: `by_source` exposes the top-bin composition and `notes` states it. Reading a claim the system itself labeled "verified" as an assertion of ~certainty is interpreting its own output, not inventing a probability.
- **Standard estimators, cited in code** (`# ECE: Guo 2017 arXiv:1706.04599; Brier 1950`). Exact, deterministic, no model in the file.

**Required experiment.** **Trivial** — ECE/Brier are standard closed-form estimators and the panel drives no autonomy (read-only display); per CLAUDE.md "do not gold-plate the process," a reversible display needs no seeded sweep. The computation's correctness is pinned by `demo()`/pytest below (perfectly-calibrated synthetic set → ECE≈0; a miscalibrated set → ECE>0; Brier within [0,1]). **RQ-E26 (new, optional, Lane 4, non-blocking):** *"Does the auditor re-adjudication outcome (band-after-new-literature) agree with an external replication label where one exists?"* — Gate: only required **if** this calibration number is ever wired to influence a threshold or dispatch (it is not, in this PRD). Register in `docs/RESEARCH_QUALITY_PROGRAM.md` as `open (advisory)`.

**Acceptance + one runnable check.**
- (1) On a fresh/low-outcome persona, `GET /calibration` returns `{status:'insufficient', n:<20, needed:20}` with **no** `ece`/`brier` curve — the fabricated-curve failure mode is structurally impossible.
- (2) With ≥20 resolved pairs on disk, it returns `status:'ok'` with numeric `ece`, `brier`, a `bins` list of length `N_BINS`, and `by_source` with both source counts.
- (3) `reliability()` on a perfectly-calibrated synthetic set gives `ece < 1e-9`; on a maximally-miscalibrated set (all p=0.9, all y=0) gives `ece ≈ 0.9` and `brier ≈ 0.81`.
- **Runnable check:** `python -m persona.eval.calibration_report` (its `demo()` asserts (3) + the insufficient-gate + Brier∈[0,1]) **and** `tests/test_calibration_report.py::test_insufficient_then_ok` (fixture persona with 0 outcomes → insufficient; monkeypatch/seed 20 pairs → ok with FC-shaped keys). Mirrors `test_calibration.py` style.

**Effort.** S (one pure module ~90 lines + one thin route + one small surface + one test).

**Deps.** None blocking. Accrues signal only after the auditor re-audit loop (`agents/audit.py::reaudit`) and the verified revisit loop (`agents/revisit.py`) have run enough — but the panel ships and renders the honest "insufficient" state from hour 1.

---

## 4. Sequencing

1. Land `persona/eval/calibration_report.py` with `demo()` self-check (self-contained, no cross-lane dep).
2. Add `GET /calibration` route in `app.py` (thin, mirrors `/verified`).
3. Add the Epistemic-tab sub-surface in `index.html` (renders `insufficient` first; the diagram path is exercised by a seeded fixture).
4. `tests/test_calibration_report.py`.

All four are Lane-4-internal; no other lane blocks or is blocked. Fits PRD-04 §4 step "F4.4 Epistemic dashboard" wave — this is a sibling panel on that surface.

---

## 5. Test plan

- **`tests/test_calibration_report.py`** (new, Lane 4):
  - `test_reliability_exact` — perfectly-calibrated synthetic (10 bins, p=y in each) → `ece < 1e-9`; miscalibrated (p=0.9,y=0) → `ece≈0.9`, `brier≈0.81`; empty `bins` handled (n==0 bin has `obs is None`, not 0.0).
  - `test_insufficient_then_ok` — fixture persona, 0 outcomes → `status=='insufficient'`, no `ece`; seed 20 auditor+verified pairs on disk → `status=='ok'` with all keys present.
  - `test_outcome_pairs_only_resolved` — a watchlist entry with `reaudits==0` and a verified entry with `revisits==0` produce **zero** pairs (no synthetic outcomes).
  - `test_verified_convention_disclosed` — `report().notes` mentions the `p=1.0` convention; `by_source.verified.survival` equals mean(y) over revisited entries.
- **Browser smoke** (extend `tests/ui_legibility_smoke.cjs`, PRD-04 §5): open Epistemic tab with a fresh persona → the calibration panel shows the "N of 20 needed" text (not a curve); assert no horizontal overflow at 1280/760/390 px.
- **No regressions:** `test_calibration.py`, `test_forensics.py`, `test_epistemic_api.py` (F4.4) must pass unchanged — this PRD only *adds* a route/module/surface.

---

## 6. Open questions

- **Q1 (soft read-stability, non-blocking).** `calibration_report` reads `memory.watchlist.entries()` and `memory.verified.entries()`. Both are already read cross-lane by `app.py` routes (`/watchlist`, `/verified`), so they are de-facto stable public read APIs. Confirm no lane plans to change the `history[]`/`revisits` field names; if so, this panel degrades gracefully (missing fields → entry yields no pair) but the count drops silently. *No FC requested; flagging only so a future rename pings Lane 4.*
- **Q2 (auditor outcome oracle — the one epistemic judgment).** Is "latest band after ≥1 new independent result" a fair realized outcome, or must the auditor outcome require a **human** confirmation (via `conflict_reviews.py` / inbox review) before it counts? Current spec uses the re-adjudication (conservative gate: external evidence must have moved) and discloses it. If the team wants a stricter oracle, the pair-source for auditor becomes "human-confirmed replication outcome only" — a one-line change to `outcome_pairs`'s Source-A gate, and it simply raises `MIN_OUTCOMES` time-to-first-curve. **Does not block other lanes.**
- **Q3 (render home).** Sub-surface under the Epistemic tab (F4.4) as specced, or a standalone spine destination? Assumed sub-surface (fewest surfaces; it *is* the epistemic story). Reversible.
