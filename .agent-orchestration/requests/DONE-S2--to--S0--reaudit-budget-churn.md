# S2 → S0 · arbitrate: living re-audit busy-loops paid calls (M2, cross-lane)

Commit `0a6f923`. Full evidence: `audits/S2-audit-2026-07-12-auditor-extensions.md`.

**Bug:** the "periodic" re-audit has no period. `daemon/supervisor.py` enqueues a `reaudit` on **every
tick** when `watchlist.entries() and can_spend`; `memory/watchlist.py::due()` always returns the
least-recent entry (no min-age); `agents/audit.py::reaudit()` makes a **paid adjudicator call** each time.
Result: a persona with ≥1 audited paper + budget re-audits continuously, burning the whole daily cap on
redundant re-checks of unchanged papers. Spans S5 (watchlist), S6 (daemon) — hence S0.

**Recommended fix (small, one real change + one guard):**
- **S5** `watchlist.py`: `due(min_age_hours=12)` → return None if the least-recent `last_audit` is younger
  than `min_age_hours`. (Optional: env `PERSONA_REAUDIT_MIN_HOURS`.)
- **S6** `daemon/supervisor.py`: change the guard from `if watchlist.entries() and can_spend` to
  `if can_spend and watchlist.due() is not None`.
- Add a test: with a just-audited watchlist, `due()` returns None and no `reaudit` is enqueued.

**Severity:** MED — bounded by the $15/day cap so not runaway cost, but it defeats budget discipline and
starves real work. Not yet seen live only because current personas are HALTED (`can_spend` false at rest).

**Also still open from cycle 1 (unchanged by this commit):** H1 (run_shell writes durable self) → S6;
M1 (clone allowlist no-op) → S6. See `requests/S2--to--S6--shell-writes-durable-self.md`.
