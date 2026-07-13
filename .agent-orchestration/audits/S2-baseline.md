# S2 audit — pre-build green baseline

**Captured:** 2026-07-12, session start (S2 review lane).
**Purpose:** freeze the known-good reference so any regression introduced by the 7-session
parallel build is attributable to a specific lane, not lost in the noise.

## Automated baseline (repo root, `build/persona-v5`)

| Check | Command | Result |
|---|---|---|
| Unit/integration suite | `python -m pytest -q` | **46 passed** in 30.02s |
| Byte-compile | `python -m compileall -q persona experiments` | exit 0 (clean) |
| Whitespace | `git diff --check` | clean (no errors) |

> Note: `HANDOFF.md`/`CONTINUATION_HANDOFF.md` record "20 tests" from an earlier checkpoint.
> The live suite is **46**. 46 is the current reference; a drop below it during the build is a regression to flag.

## Tree phase at baseline: **pre-P0**

- `persona/api/app.py` has **no `/static` mount** (grep for `StaticFiles`/`mount` finds only a `/work` docstring). → **P0.1 (S6) not started.**
- `persona/api/static/index.html` is still the monolithic **2073-line** shell; no external `app.css`/`app.js` refs; no `css/` or `js/` subdirs. → **P0.2 (S3) not started.**
- Only `index.html` + `index_v6_backup.html` live under `static/`. `index_v6_backup.html` is **USER-OWNED — untouched.**

## P0.3 byte-check readiness

- The **pre-split `index.html` is preserved at git `HEAD`** — recoverable via `git show HEAD:persona/api/static/index.html`. The "before" render reference is therefore **not ephemeral**; no rushed pre-capture needed.
- **Smoke-harness prerequisites all present** (confirmed read-only):
  - `tests/ui_research_smoke.cjs` (70 lines) · node.exe · pnpm modules · playwright · Chrome + Edge executables.
  - The smoke is the behavior-preservation oracle: drives `openMind`/`setSurface`, asserts session cards / GEO `contested` modal / conflict dossier, and **flags any response ≥400 as a console error** — so a 404 on `/static/css/app.css` or `/static/js/app.js` after the split will auto-fail the gate. This is exactly why **P0.1 (mount) must land before P0.2 (extraction)**.
- `verify_conflict_reviews('personas/curie-3c33/.persona')` → `{ok: True, errors: [], record_count: 0}` (clean empty ledger; expected pre-collection).
- **Pre-existing console errors NOT captured live** — deferred to P0.3. At P0.3 I diff *before* vs *after* console sets and assert **zero NEW errors**, not zero absolute.

## ⚠️ Flag to S0 — unowned server on :8137

- Port **8137 is already LISTENING** (PID **26092** = `python -m persona --port 8137`), from another session or a leftover run.
- Its `PERSONA_WORKERS` value is **not visible from the command line**, so it **may be spending model budget** (cf. CONTINUATION §10: don't run paid agents just to show motion).
- **S2 will NOT kill it** (non-interference protocol; CONTINUATION §8: verify before stopping). At P0.3 I launch my **own** clean `PERSONA_WORKERS=0` server; if 8137 is still occupied then, I coordinate the port/ownership via S0 rather than reaching in.
- **Ask for S0:** confirm whose 8137 server this is and whether workers are on; stop it if it's an orphan burning budget.

## Blocked / waiting

P0.3 (my gate) is blocked on **P0.1 (S6 static mount) → P0.2 (S3 extraction)**. No product code touched by S2. Standing by; will re-run this baseline table as the "after" once P0.2 reports READY.
