# S2 → S0 — H1 + M1 security fixes VERIFIED, ready for the scoped commit

**Severity:** action — the "worst possible bug" class (belief-state mutable outside the membrane) is now CLOSED and verified.
**Full evidence:** `audits/S6-H1-M1-security-verified.md`.

## Verified
- **H1** (run_shell rw-self) CLOSED — `_jail_shell_cwd` jails cwd to scratch dirs; `cwd=self`/notes/…/`.persona` + traversal all refused. Proven by `tests/test_app_security.py`.
- **M1** (clone_repo SSRF) CLOSED — host allowlist github/gitlab/bitbucket only; 169.254 metadata / localhost / look-alike / non-https all rejected.
- `pytest tests/test_app_security.py` → **35 passed**; `pytest -q` (full) → **118 passed**; `compileall` → 0.

## ⚠️ VERIFIED-IN-CODE ≠ LIVE — vuln still exploitable until commit + RESTART
The fix is **uncommitted** (HEAD is still `0a6f923`, pre-fix) and the running :8137 server (PID 26092) loaded the **old** `app.py` — Python has no hot-reload, so **that live instance still has the rw-self `run_shell`.** The HIGH vuln is closed in source only. It is not actually mitigated until (1) the commit lands and (2) any running server is restarted. Treat "ready to commit" as necessary-but-not-sufficient.

## Ask (per your TICK-4 commit note)
1. Commit promptly, **lane-scoped**: `git add persona/api/app.py tests/test_app_security.py` — **never `-A`**. Awaits human authorization (HANDOFF rule).
2. After commit, **restart any live persona server** (or confirm none is serving untrusted shell input) so the running instance picks up the jail.
**Attribution note (post-pivot):** `app.py` is now **Lane 4 / S3** (test header "Lane 4 / S3" is correct); the `tools/sandbox.py` H1 side is **Lane 3 / S6** (PARKED). This app.py half is fully verified regardless of which lane authored it.

## Flag while you're here (non-blocking)
1. **P0.1 STILL undone** — S6 did H1/M1 before the `/static` mount. P0.1 is the keystone blocking P0.2, my P0.3, and all frontend Wave-0. Please re-nudge S6 to land the one-line mount.
2. **`status/S6-api.md` is stale** — still "▶ start now"; doesn't reflect the H1/M1 work or a `✅`. Attribution unclear (test header says "Lane 4 / S3").
3. **M2 (reaudit staleness) still OPEN** on S5 `watchlist.due` + S6 supervisor guard.
