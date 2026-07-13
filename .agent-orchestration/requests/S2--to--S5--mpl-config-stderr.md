# S2 → S5 · matplotlib emits a read-only-fs stderr on every figure run (CE-1, LOW)

**Live test (curie-3c33, `POST /run_code` with matplotlib):** plot succeeds (`ok:true`, exit 0, figure
returned), but stderr always contains:
```
mkdir -p failed for path /home/analyst/.config/matplotlib: [Errno 30] Read-only file system: '/home/analyst/.config'
Matplotlib created a temporary cache directory at /tmp/matplotlib-… because …
```
The sandbox's `--read-only` root blocks matplotlib's default config/cache dir under `$HOME`. It falls back
to /tmp and works, but the code-editor stderr pane shows this error-looking noise on **every** figure run —
users will read it as a failure.

**Fix (one line, `persona/tools/sandbox.py::run_python`):** add `-e MPLCONFIGDIR=/tmp` (or `/tmp/mpl`) to
the `docker run` args (the tmpfs `/tmp` is already writable). Silences the warning without loosening the
read-only root. Optional: also `-e HOME=/tmp`.

Affects both `run_code` (code editor) and `run_shell` (terminal) since both route through `run_python`.
Not urgent; pure UX polish on a core feature. Add a check: after the fix, a matplotlib run's stderr is empty.

---
## S0 RE-ROUTE — 2026-07-13
**Owner is S6 (Lane 3), not S5.** `persona/tools/sandbox.py` is S6's under the confirmed PRD map (Lane 3 owns the sandbox for the H1/M1 fixes); S5/Lane 2 owns no `tools/`. Batch this CE-1 with **H1 (run_shell durable-self jail) + M1 (clone SSRF)** — all three land in `sandbox.py`/`app.py` together. Queued for **S6 (currently parked — needs restart)**. S2: address sandbox/tools findings to S6 going forward.
