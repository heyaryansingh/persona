# S2 RE-AUDIT — H1 + M1 fix (S6), 2026-07-13

**Trigger:** monitor fired — `run_shell` body changed in `app.py`. Re-audited per the cycle-1 plan.
**Method:** read the new code + imported the ACTUAL symbols (`_jail_shell_cwd`, `_GIT_URL_RE`,
`_SHELL_SCRATCH`) and exercised 18 jail cases + 7 URL cases against a real persona `Paths`.

## UPDATE 2026-07-13 — COMMITTED as `0af1dd4` + regression tests, verified. Deploy still pending.
Commit `0af1dd4` "Secure code-lab: jail run_shell + fix clone_repo SSRF" — diff **exactly matches** what I
verified (no scope creep): `_jail_shell_cwd` scratch-dir jail + `_GIT_URL_RE` catch-all removed. It ALSO
added my recommended regression test: `tests/test_app_security.py` ("35 cases: cwd=self refused, traversal,
SSRF/metadata/look-alike hosts") + `test_epistemic_api.py` → **38 passed**. Fix is now checkpointed + tested.
**STILL NOT DEPLOYED:** the running :8137 server is stale — `run_shell cwd=self` there STILL runs + writes a
shim. Commit ≠ restart. The HIGH vuln remains live on the running server until it is restarted (tracked in
`audits/S2-visibility-audit.md` + `requests/S2--to--S0--changes-not-live-restart-and-wire.md`). Request →
DONE (the fix is done); deploy is a separate server-restart action.

## VERDICT: both fixes CORRECT — PASS. But NOT yet live (uncommitted + server stale).

### H1 (HIGH) — durable-self write hole → FIXED
`_jail_shell_cwd(paths, cwd)`: `paths.safe()` (traversal/symlink jail) → refuse workspace root → require
`relative_to(ws).parts[0] ∈ _SHELL_SCRATCH {code,datasets,repos,runs,uploads}`. Endpoint catches
`ValueError` → `{ok:False, reason}`.
All 18 cases correct:
- REFUSED: `self, notes, sources, drafts, deliverables, investigations, projects`, `code/../self`
  (resolves into self), `selfx` (no prefix-substring bypass), `../../etc` (traversal), `""`, `.` (root).
- ALLOWED: `code, repos/foo, uploads/x, runs, datasets`, `self/../code` (resolves into code).
The shell can no longer mount or write the durable self → the frozen membrane invariant holds.
**H2 (shim litter) also mitigated:** `_run.py` now only lands in scratch dirs (same as `run_code`), never `self/`.

### M1 (MED) — clone SSRF / dead allowlist → FIXED
`_GIT_URL_RE = ^https://(github\.com|gitlab\.com|bitbucket\.org)/[\w.-]+/[\w.-]+` — the `[\w.-]+` host
catch-all is gone (comment cites the 169.254.169.254 metadata risk). Verified: `internal.corp.local`,
`169.254.169.254`, `evil.example.com` now REJECTED; github/gitlab/bitbucket accepted; `http://` rejected.

## ⚠️ NOT LIVE YET — deploy gap
- Fix is **uncommitted** (HEAD still `0a6f923`); the running server on :8137 was started earlier and does
  **not** hot-reload, so it still serves the OLD vulnerable `run_shell`. **The HIGH vuln is live until the
  fix is committed AND the server restarted.** S0 notes S6 is parked/needs restart.
- **Recommend S6:** add a regression test (`test_api_*`) asserting `run_shell cwd="self"` → `ok:False`, and
  that no `_run.py` appears in `self/` after the attempt. I verified behaviourally; a committed test locks it.

Request `S2--to--S6--shell-writes-durable-self.md` → **VERIFIED-IN-CODE, pending commit+restart** (not
renamed DONE until deployed). CE-1 (matplotlib stderr) re-routed by S0 to S6 (same `sandbox.py`).
