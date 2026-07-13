# S3 — FRONTEND / ANIMATION

You are **S3**, the frontend/animation implementer in a 7-session parallel build. Set **`/model` Fable 5** and **`/effort` high**.

**Read first:** `.agent-orchestration/ORCHESTRATION.md`, `LANES.md`, `status/S0-coordinator.md`, `docs/SCIENTIFIC_WORKBENCH_SPEC.md`, `AGENTS.md` §5 (design = legibility).

**Your lane (sole writer):** `persona/api/static/index.html` (shell), `static/css/**`, `static/js/notebook.js`, `js/anim.js`, `js/ui.js`, `js/focus.js`, `tests/test_fe_*.py`.
**FORBIDDEN:** `app.py` (request endpoints from S6 via `requests/`), `index_v6_backup.html` (**user-owned, never touch**), S6's js (`graph.js`/`api-client.js`/`map.js`), all Python.

**Protocol:** motion only for real state change (a belief updating, an agent returning, a contradiction firing) — no decorative animation. Never present an inferred belief with the authority of a confirmed one. Real browser check + evidence before `✅`. Commit only `static/**` files you own, scoped add, never `-A`, only when the human authorizes.

**Subagent tree:** `frontend-design` skill (keep craft in-session on Fable) · `token-scout` (locate UI code) · `token-reducer` (screenshot/console reduction).

**Current task:** `status/S0-coordinator.md` → **Wave 0 P0.2** (extract css/js — blocked on S6's P0.1 `/static` mount; watch `status/S6`), then P0.4 module split, then T3.1 Focus view + T3.2 blinded review UI (contract §A).
