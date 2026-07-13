# S2 AUDIT — code-lab + studio-audit + robustness-report (2026-07-12)

**Auditor:** S2 (review/audit/browser · Opus).
**Scope:** the 3 newest commits on `build/persona-v5`:
`07c4f27` code-lab (clone/upload-zip/shell), `deec46c` studio external-paper audit,
`c26ff7e` rich robustness-report UI.
**Method:** static diff review + live app on `127.0.0.1:8137` (Curie `curie-3c33`, 5368 claims)
driven with Playwright. Sandbox verified real: bash + numpy 2.5.1 ran, `--network none` confirmed.

---

## Findings (confirmed)

### H1 — HIGH · `run_shell` mounts the durable *self* read-write → writes bypass the membrane
`persona/api/app.py::run_shell` sets `workdir = p.paths.safe(cwd)` where `cwd` is the frontend's
`FS.path` — **the folder you are currently viewing**. `sandbox.run_python` mounts that dir
`-v {workdir}:/work` **read-write** (`persona/tools/sandbox.py:35`). Open `self/`, run a shell command,
and `/work` == the persona's durable belief-state. `echo x > beliefs.md` / `rm identity.md` persist to
the real self on disk — **outside the membrane, with no provenance, no anchoring check.**

Directly violates the frozen contract (`HANDOFF.md`): *"swarm READS, never writes to the self. Only the
membrane commits."* and `CLAUDE.md`: *"A silent wrong number that propagates into the belief-state is the
worst possible bug in this system."* The shell/`run_code` sandbox protects the **host** and the **network**,
but not the persona's own mind from a keystroke.

**Proof (live):** ran `echo hello && … && ls` while viewing `self/`. The sandbox shim `_run.py`
(the code it executes) was written into `personas/curie-3c33/self/_run.py` on disk, timestamped to the run,
sitting next to `beliefs.md`. A benign `echo probe2` did the same. Mount is rw and persists. (I removed the
shim after.)

**Scope of exposure:** not just `self/` — `paths.safe` accepts any workspace subdir, so `notes/`,
`sources/`, `drafts/`, `projects/`, `deliverables/`, `investigations/` are all shell-writable. The self is
the worst because it is the belief-state.

**Contrast (why this is a regression, not pre-existing):** the older `run_code` hardcodes an isolated
`workdir = workspace/"code"/"run"` — the self is never mounted, safe by design. `run_shell` newly took
`cwd` from the UI and pointed the rw mount at the durable mind.

**Fix (root cause, one place):** in `run_shell`, jail `cwd` to scratch dirs only
(`repos/`, `uploads/`, `code/`, `runs/`, `datasets/`) and reject the durable-mind dirs; **or** run every
shell in a fixed scratch mount like `run_code` does and copy the target repo/upload in. The lab-bar's own
intent ("run a cloned pipeline") only ever needs `repos/`+`uploads/`+`code/`.

---

### H2 — LOW · sandbox shim `_run.py` litters whatever folder you shell in
`run_python` writes `_run.py` into `workdir` and never removes it. `run_code` confines it to `code/run/`;
`run_shell` drops it into the **live folder** (`self/`, a repo, …). It shows up in the user's own `ls`
output ("what is this file I didn't write?") and pollutes the self dir. Fixed by H1's scratch-dir jail;
independently, `run_python` should clean up `_run.py` (or use a temp name outside the mounted tree).

---

### M1 — MED · `clone_repo` allowlist regex accepts *any* https host (SSRF surface + false claim)
`^https://(github\.com|gitlab\.com|bitbucket\.org|[\w.-]+)/[\w.-]+/[\w.-]+` — the 4th alternative
`[\w.-]+` matches every hostname, so the github/gitlab/bitbucket allowlist is dead code. Verified:
`https://internal.corp.local/a/b`, `https://169.254.169.254/latest/meta`, `https://evil.example.com/a/b`
all MATCH. Server-side `git clone` then reaches arbitrary internal hosts (SSRF). The docstring/commit say
"HTTPS git URLs only (github/gitlab/…)" — behavior ≠ claim.
Mitigated by: `--network none` is on the *sandbox*, not this clone (clone runs on the **host**);
app binds `127.0.0.1` so exploit needs local access; `--depth 1` + 120s timeout cap blast radius.
**Fix:** drop the `[\w.-]+` catch-all — keep the explicit host allowlist (add hosts deliberately).
(`http://` and single-path-segment URLs already reject correctly.)

---

### L1 — LOW · UI copy: "eight markdown files" but self has 7
Brain `self/` overview text: *"The durable self — eight markdown files it rewrites…"* — the folder lists
7 (`beliefs, CHANGELOG, identity, interests, open_questions, strategies, taste`) and the sidebar badge
reads **7**. Off-by-one copy; pick the real count or make it dynamic.

### L2 — LOW · studio audit routing heuristic is brittle
`stRun` routes audit input as external-paper text when `t.length>200 || t.includes("\n")`, else as a
named read-paper. A long paper *title*, or any pasted name with a stray newline, misroutes to verbatim
external-text audit. Low impact; consider an explicit toggle instead of a length/newline guess.

---

## Observed once, NOT reproduced (flag for watch — not reported as defects)
- **Possible cross-persona view leak:** after a terminal run in Curie, clicking `Studio` once showed
  **Euclid** (a *running* persona) with `PID==="euclid"`. Could not reproduce: idle through poll cycles
  and re-clicking `Studio`/`Work` both kept `PID==="curie-3c33"`. Likely a stale-DOM automation artifact
  mid-transition. HANDOFF already lists "can leak cached state across personas" as a known risk — worth a
  deliberate repro pass by whoever owns view-state.
- **View jumped to `Map` once** after pressing Enter in the terminal; not reproduced in a clean session
  (surface stayed `brain`).

## What works (verified good)
- Sandbox is real isolation: bash + numpy 2.5.1, `--network none`, read-only root, non-root, resource caps.
- Terminal pane renders stdout/stderr, scrolls, esc-escapes output. Clone/folder wiring present.
- Studio placeholder copy correctly updated for the external-paper flow (`deec46c` renders).
- Genesis + Brain views: calm, editorial, on-brand; no console errors except a `favicon.ico` 404 (trivial).

**Routing:** H1 (and H2) → S6 (owns `app.py`) + sandbox owner. Request filed:
`requests/S2--to--S6--shell-writes-durable-self.md`. M1/L1/L2 in the same request.
