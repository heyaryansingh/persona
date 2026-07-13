# S2 VISIBILITY AUDIT — are this session's changes actually live / usable? (2026-07-13)

## ✅ RESOLVED (2026-07-13, later) — DEPLOY COMPLETE, changes now visible + usable
The gap this audit flagged was acted on. Verified LIVE on the restarted :8137 (new PID 73636):
- **5 commits landed** (`0a6f923..HEAD`): H1/M1 security · Lane-1 · Lane-2+T5.1+M2 · Lane-3+paper · Lane-4 UI.
  Full suite **256 passed**.
- **Server restarted** — `run_shell cwd=self` → REFUSED, no shim: **H1 vuln CLOSED on the live server**.
- **`/static` mount live** — `app.css/focus.css/field.js/focus.js/verdict.js/ui.js` all 200.
- **P0.2 done** — live `index.html` now loads the split modules (field/focus/verdict/ui.js + css). New UI wired.
- **Renders clean** — genesis + Review surfaces render correctly with the split assets (behavior preserved),
  data-driven surfaces populate; only console error is the benign favicon 404. No JS module errors.
**Net: the changes ARE now visible and usable.** The commit+restart+P0.2 unblock I recommended all happened.
Remaining: re-audit the newly-visible Lane-4 features (field/value-queue/verdict UI) + R-1 (Review layout
dead-column, still open) on the live app.

---
### (original finding — kept for the record) ###

**User asked S2 to confirm the changes are visible, in the design, and usable.** Empirically probed the
RUNNING server (:8137). **Answer: NO — the large majority are NOT live.** One decisive cause: the server was
started before this session's work and **Python modules are frozen at import** (no `--reload`); plus the
**`/static` mount 404s** so new UI modules are unreachable.

## Evidence (live probes against :8137)
| probe | result | meaning |
|---|---|---|
| `GET /` | 200 | server up |
| `GET /static/js/app.js` | **404** | **P0.1 mount NOT live** → new JS/CSS modules unreachable |
| `POST /run_shell {cwd:"self"}` | **ran `echo`, wrote `_run.py` into `self/`** | **H1 jail NOT live — HIGH self-write vuln STILL EXPLOITABLE** |
| `GET /` body: `_seenEv` | 4 hits | F-2 dedup IS live (index.html serves from disk) |
| `GET /` body: `/static` refs | 0 | index.html still fully inline (P0.2 undone); new UI not wired |
| uncommitted files | 90 | nothing committed (HEAD `0a6f923`) |

## What's actually visible/usable RIGHT NOW
| change | live? | why |
|---|---|---|
| F-2 stream-dedup, any in-place `index.html` edit (FL-1 copy, etc.) | ✅ LIVE | index.html served from disk per request |
| S3 flagship **field / value-queue UI**, focus.js/css (new `/static` modules) | ❌ DEAD | `/static` 404 (mount frozen) + index.html doesn't reference them (P0.2) |
| **H1/M1 security fix** (run_shell jail, clone allowlist) | ❌ DEAD | app.py frozen at import → **vuln live** |
| Paper-quality (A1 listings, A5 badges, A6 cites, lint, PQ-REG-1 fix, twocolumn) | ❌ DEAD | paper.py/document.py frozen; a paper generated now uses OLD code |
| kg-hygiene (confidence clamp, year fix), M2 watchlist, lane-2/3 FC-2..6, T5.1 substrate | ❌ DEAD | all Python, frozen at import |

**Net: a demo of the running app right now shows the OLD product** — the security hole open, no paper-quality
improvements, none of the new Review/field UI, none of the belief-integrity fixes. All the verified work is
real in the tree but **invisible to a user.**

## The fix (human / director — the ONE thing that unblocks visibility)
1. **Commit** the 90 verified files (checkpoint; lane-scoped adds).
2. **Restart the server** (`python -m persona`) — makes ALL Python changes live, incl. the H1 security fix.
   Consider `--reload` for the dev/demo loop so future changes show without a manual bounce.
3. **Finish P0.1 wiring + P0.2** — the `/static` mount must be in the RUNNING app AND `index.html` must
   reference the split assets, or the new UI stays dark even after restart.
4. Re-run S2's smoke (P0.3) after, to confirm the split renders identically + zero console errors.

## Why S2 did this directly (not a fan-out workflow)
Driving the one running server + browser is a single stateful resource — parallel agents would collide and
can't restart it. The finding is singular (stale import + dead mount), proven by the probes above.

**Routed to Director (S0) + Idea (S1):** `requests/S2--to--S0--changes-not-live-restart-and-wire.md`.

## DEPLOY DE-RISK (2026-07-13) — started a fresh server on the CURRENT tree (:8139, workers off), then killed it
Proves what a restart WOULD do, and catches any startup break in the 90 uncommitted files:
- **Tree is runnable** — `python -m persona` on the current code → "Application startup complete", no import
  error. The uncommitted work is deployable.
- **H1 security fix works after restart** — `run_shell cwd=self` on :8139 → **REFUSED** ("cwd must be a
  scratch dir …"), **no `_run.py` written to self**. (On stale :8137 the same call RAN + wrote the shim.)
- **`/static` mount works on fresh code** — `app.css`, `focus.css`, `js/field.js`, `js/focus.js`,
  `js/verdict.js`, `js/ui.js` all **200**. (My earlier `app.js` 404 was a stale filename — `app.js` was
  refactored into these modules; not a defect.)
- **BUT the new UI modules are ORPHANED** — `index.html` loads **none** of `field/focus/verdict/ui.js` or
  the css (grep = 0 refs). So **even after a restart the new field/value-queue/verdict UI stays DARK** until
  **P0.2 wires `index.html` to the split assets**.

### Corrected conclusion — TWO human actions, not one
1. **Commit + restart** → makes ALL Python live (security fix, paper-quality, kg-hygiene, lanes, T5.1). Proven to work on :8139.
2. **P0.2 (wire `index.html` → the `/static` modules)** → the only way the new UI (S3 flagship field/value-queue/verdict) becomes visible. The modules are built and serve; nothing loads them.
Restart alone surfaces the backend/security/paper fixes but leaves the new frontend UI dark.
