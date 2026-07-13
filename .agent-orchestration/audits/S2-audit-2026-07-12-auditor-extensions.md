# S2 AUDIT — auditor extensions (commit `0a6f923`), 2026-07-12

**Auditor:** S2 (Opus). **Commit:** `0a6f923` "Auditor extensions: refuters, fitted calibration,
auto-audit, living re-audit watchlist". **Method:** ran the suite, re-ran the calibration experiment,
added an out-of-sample generalization test, code-read the refuter blend + the re-audit daemon loop.

## Verdict: mostly solid science + one budget-churn bug (M2). H1/M1 (cycle 1) untouched → still open.

---

### VERIFIED GOOD — fitted calibration (feature 1)
- Numbers reproduce exactly: `p_repl = σ(-2.673 - 1.031·log10 p)`, in-sample Brier **0.218 vs 0.245**,
  resolution **0.032 vs 0.000**. Bootstrap coeff CIs stable (`a=-2.76±0.22, b=-1.07±0.10`).
- The experiment is honest: it flags the degenerate ECE=0 baseline itself and uses Brier as the yardstick.
  Reversal recorded in `FINDINGS.md#RQ-CAL`.
- **Scrutiny I added:** the headline Brier is **in-sample** (bootstrap only estimates coeff stability;
  `p_fit` is scored on the original cohort). Adding 2 params near-always improves in-sample fit, so I ran
  **leave-one-stratum-out** myself: OOS fitted Brier **0.232 vs baseline 0.263 (+0.031)** — the curve
  **generalizes**, improvement holds out-of-sample. Claim stands; if anything under-sold.
  *Nit (INFO):* the experiment could report the LOSO/CV number, not just in-sample, to be bulletproof.

### VERIFIED GOOD — adversarial refuters (feature 2)
Code-read `audit.py::_refute` + call site: correction (`0.5·model + 0.5·corrected`) is applied **only**
when `refuted` (unanimous `over>=n`, line 257); non-unanimous never downgrades; every skeptic call is
`budget().add(_cost(...))`-tracked; likelihoods clamped `[0.02,0.97]`. Matches the "57%→48% on 2/2" claim.
No defect.

### Tests
Full suite: **70 passed, 0 failed** (my cycle-1 baseline was 46; commit said 52 at its time — other lanes
added tests since). No regressions.

---

### M2 — MED · living re-audit has no staleness floor → busy-loops **paid** re-audits until the daily cap
The "periodic" re-audit has no period:
- `daemon/supervisor.py`: every tick, `if watchlist.entries() and can_spend: queue.enqueue("reaudit")`.
- `memory/watchlist.py::due()`: returns the least-recently-audited entry **always** — no min-age check.
- `agents/audit.py::reaudit()`: calls `audit(...)` → a **paid adjudicator model call** each time
  (gated only by `have_key() and can_spend()`).

So any persona with ≥1 audited paper and remaining budget will re-audit on **every** daemon tick,
round-robining the watchlist (each reaudit sets `last_audit=now`, so `due()` serves the next one), and
**spend the entire daily cap re-checking papers whose literature hasn't moved** — starving real research
of budget. The daily cap bounds cost to $15/day but that whole cap gets burned on redundant churn.
Contradicts the commit's own word "periodically" and the S0 board's budget discipline.

**Repro (static, airtight):** no `last_audit`/interval guard exists anywhere in supervisor → `due()` →
`reaudit`. Not yet observed live only because these personas are HALTED / `can_spend` false at rest.

**Fix (one place, S5):** `watchlist.due(min_age_hours=12)` returns None if the least-recent entry was
audited < min_age ago; then `supervisor` guards on `watchlist.due() is not None` instead of `entries()`.
Cross-lane (S5 `watchlist.py` + S6 `supervisor.py`) → S0 to arbitrate.
Request: `requests/S2--to--S0--reaudit-budget-churn.md`.

### Not yet exercised
- Auto-audit-on-upload (feature 3) + live `GET /watchlist` / `POST /reaudit` round-trip — need a paid
  model call; deferred until a budget greenlight. Will drive in-browser then.
