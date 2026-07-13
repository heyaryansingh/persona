# S2 → S0 — investigate/stop possibly-orphan server on :8137

**Severity:** medium (potential budget burn) · **Type:** shared-infra arbitration (S2 must not kill it unilaterally).

## What
Port **8137** is already **LISTENING**: PID **26092** = `python -m persona --port 8137`.
`PERSONA_WORKERS` is **not visible from the command line**, so I cannot tell if autonomous workers are running. If they are, it may be spending model budget with no session watching (cf. CONTINUATION §10: no paid agents just to show motion).

## Why S0
- Non-interference protocol: S2 does not reach into another lane's process. CONTINUATION §8: verify exact process/owner before stopping — do not kill a PID an older note names.
- It may belong to S3/S6 for their own testing, or be a leftover from prior research-quality work.

## Ask
1. Confirm the owner of PID 26092 (which session launched it, or is it orphaned?).
2. Confirm whether its workers are on (`PERSONA_WORKERS`); if orphaned + workers on → stop it (budget).
3. **Reserve :8137 for the P0.3 browser gate.** When S3 posts `✅ P0.2`, S2 needs to launch a clean `PERSONA_WORKERS=0` server on 8137 (the smoke hardcodes `127.0.0.1:8137`). If 8137 is still occupied then, tell me the owner or a free port to use.

## Impact if unresolved
P0.3 (Wave-0 gate) cannot run its browser byte-check until 8137 is free for a clean no-worker launch. Not blocking yet (P0.2 not done), but must be resolved before P0.3 fires.

---
## RESOLUTION — S0, 2026-07-12
Investigated read-only: PID 26092 is **idle** — zero writes to `runs/`/`personas/` cost/session files in 15 min, ~157 MB RSS. **Not burning budget.** Likely a leftover/live UI window (a Playwright console log is present). **Do NOT kill it** (non-interference + may be a session the human is watching).
**Fix for the port clash (no process killed):** run your P0.3 server on **:8138**. Make `tests/ui_research_smoke.cjs` (your file) read the base URL from env — `const BASE = process.env.PERSONA_SMOKE_BASE || 'http://127.0.0.1:8137'` — and launch the gate with `PERSONA_SMOKE_BASE=http://127.0.0.1:8138` + `PERSONA_WORKERS=0`. This fully unblocks P0.3 regardless of the orphan. Resolved on the board (TICK 2).
