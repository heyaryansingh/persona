# S2 audit — H1 + M1 security fixes VERIFIED FIXED (clear for commit)

**When:** 2026-07-13 · S6 landed the fixes in `persona/api/app.py` (uncommitted, working tree).
**Verdict: PASS — both closed. Ready for the scoped commit S0 flagged (TICK 4).**

## H1 (HIGH — run_shell mounted durable self rw) — CLOSED
- **Fix:** `_jail_shell_cwd(paths, cwd)` (app.py L38) resolves `cwd` via `paths.safe` (traversal/symlink jail), rejects the workspace root, then requires `relative_to(ws).parts[0] ∈ _SHELL_SCRATCH = {repos, uploads, code, runs, datasets}`. `run_shell` routes through it (L350). Durable self + knowledge dirs can no longer be a shell cwd → **belief-state can't be mutated outside the membrane.** Root-cause, one place — exactly as filed in `requests/S2--to--S6--shell-writes-durable-self.md`.
- **Regression test proves it** (`tests/test_app_security.py`, 35 cases): `test_shell_cwd_refuses_protected` raises `ValueError` for `self, notes, sources, drafts, projects, deliverables, investigations, .persona, self/beliefs.md, notes/x, .., ., "", ../self, ../../etc`. `test_shell_cwd_allows_scratch` confirms `code/repos/uploads/runs/datasets` (+ nested) still work → the code-lab feature is unbroken.

## M1 (MED — clone_repo allowlist was a no-op / SSRF) — CLOSED
- **Fix:** `_GIT_URL_RE = ^https://(github\.com|gitlab\.com|bitbucket\.org)/[\w.-]+/[\w.-]+` (L35) — the `[\w.-]+` host catch-all is gone; `/` required right after the host blocks look-alike suffixes. `clone_repo` rejects on no-match (L316).
- **Regression test:** `test_clone_url_rejects` rejects `169.254.169.254` (cloud metadata), `metadata.google.internal`, `localhost`, `127.0.0.1`, `internal.evil.com`, `http://` (non-https), `file://`, `ssh://`, and `github.com.evil.com` (look-alike). `test_clone_url_accepts_known_hosts` accepts github/gitlab/bitbucket. Covers every SSRF vector I flagged.

## Verification (S2 ran)
| Check | Result |
|---|---|
| `pytest tests/test_app_security.py -q` | **35 passed** |
| `pytest -q` (FULL) | **118 passed** / 25.5s — floor ≥46 held |
| `compileall -q persona` | exit 0 |

## Notes for S0
- **Ready for the promptly-scoped commit** (TICK 4): `git add persona/api/app.py tests/test_app_security.py` only — never `-A`. Awaits human authorization per HANDOFF.
- **Deviations to note (non-blocking):** (1) S6 did H1/M1 **before P0.1** — security-first is defensible, but **P0.1 (`/static` mount) is STILL undone** and blocks P0.2 / my P0.3 / all frontend Wave-0. (2) S6's `status/S6-api.md` is **stale** ("▶ start now, P0.1 first") — not updated to reflect this work or a `✅`. (3) test header mislabels attribution "Lane 4 / S3" (cosmetic; code + coverage are correct).
- **M2 (reaudit staleness) still OPEN** on S5 (`watchlist.due` floor) + S6 (supervisor guard) — not addressed by this app.py change.
