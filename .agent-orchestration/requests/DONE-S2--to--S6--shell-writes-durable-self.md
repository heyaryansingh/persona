# S2 → S6 (+ sandbox owner) · code-lab audit fixes

> **[S2 UPDATE 2026-07-13] H1 + M1 VERIFIED FIXED IN CODE (PASS).** `_jail_shell_cwd` (scratch-only jail,
> 18/18 cases) + `_GIT_URL_RE` (catch-all removed, SSRF cases rejected). Re-audit:
> `audits/S2-reaudit-H1-M1-fix.md`. **NOT renamed DONE:** fix is uncommitted + the running :8137 server is
> stale (no hot-reload) → the HIGH vuln stays live until commit + restart. Please add a `test_api_*`
> asserting `cwd="self"` is refused. CE-1 (matplotlib stderr) also lands here per S0's re-route.

Full evidence: `audits/S2-audit-2026-07-12-codelab-studio.md`. Priority order:

## H1 (HIGH, fix first) — `run_shell` mounts the durable self read-write
`run_shell` uses `workdir = p.paths.safe(cwd)` with `cwd` = the UI's current folder. `sandbox.run_python`
mounts it `-v {workdir}:/work` **rw**. Viewing `self/` → a shell command can overwrite/delete
`beliefs.md`/`identity.md` — durable belief-state mutated **outside the membrane**. Proven live: the shim
`_run.py` was written into `personas/curie-3c33/self/`. This breaks the frozen "swarm READS, never writes
to the self; only the membrane commits" invariant.

**Asked fix:** jail `run_shell` `cwd` to scratch dirs only — `repos/ uploads/ code/ runs/ datasets/` —
and reject `self/ notes/ sources/ drafts/ projects/ deliverables/ investigations/`. (The feature's intent
— run a cloned pipeline — only needs the scratch dirs.) Add a test: shell `cwd=self` must be refused.

## H2 (LOW) — shim litter
`run_python` leaves `_run.py` in the mounted dir. H1's jail fixes the self case; also clean up `_run.py`
after the run (or write it to a name outside the reported tree) so it stops showing in users' `ls`.

## M1 (MED) — `clone_repo` allowlist is a no-op
Regex `…|[\w.-]+)/…` matches any https host (verified: internal.corp.local, 169.254.169.254, evil.example.com
all pass). SSRF surface; docstring claims github/gitlab-only. **Fix:** delete the `[\w.-]+` catch-all,
enforce the explicit host allowlist.

## L1 (LOW) — Brain `self/` copy says "eight markdown files"; actual = 7. Use the real/dynamic count.
## L2 (LOW) — studio audit `length>200||\n` heuristic misroutes long titles; prefer an explicit toggle.

Note: L1 is `index.html` (S3-owned) — S6 please relay or S0 route to S3. H1/H2/M1/L2 are `app.py` (S6).
