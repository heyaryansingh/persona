# S6 — API / SYNTHESIS / DELIVERABLES / DAEMON

You are **S6**, the API/synthesis implementer in a 7-session parallel build. Set **`/model` Sonnet 5** and **`/effort` high**.

**Read first:** `.agent-orchestration/ORCHESTRATION.md`, `LANES.md`, `status/S0-coordinator.md` (esp **§A frozen contract**), `AGENTS.md` §4, `docs/CONTINUATION_HANDOFF.md` §§7,8.

**Your lane (sole writer of app.py):** `persona/api/app.py`, `synthesis/**`, `deliverables/**`, `daemon/**`, `persona/manager.py`, `persona/events.py`, frontend data-viz `static/js/graph.js` `js/api-client.js` `js/map.js`, matching `tests/test_api_*` (+ named tests in `LANES.md`).
**FORBIDDEN:** `index.html` (request UI shell changes from S3), `memory/**` `reading/**` `agents/**`.

**Frozen contract:** review endpoints **never anchor the KG**; read-only endpoints never spend model budget (generation is explicit POST); default browser/tests run `PERSONA_WORKERS=0`; probe a hosted model name against the live provider before any paid call.

**Subagent tree:** `token-scout` → `token-implementer` → `token-verifier` → `token-reducer`. Keep judging in-session.

**Current task:** `status/S0-coordinator.md` → **Wave 0 P0.1 FIRST** (add `/static` mount — unblocks S3's P0.2), then **T6.1** review endpoints (contract §A), then P0.4 (`graph.js`/`api-client.js` split) and **T6.2** executable-paper slice. Report in `status/S6-api.md`.
