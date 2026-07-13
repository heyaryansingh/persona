# S4 — READING / REASONING / SWARM ENGINE

You are **S4**, the engine implementer in a 7-session parallel build. Set **`/model` Sonnet 5** and **`/effort` high**.

**Read first:** `.agent-orchestration/ORCHESTRATION.md`, `LANES.md`, `status/S0-coordinator.md`, `AGENTS.md` §§1–4, `docs/CONTINUATION_HANDOFF.md` §§4,7.

**Your lane:** `persona/reading/**`, `research/**`, `analysis/**`, `agents/**`, plus the self (`selfmind.py`, `persona_obj.py`, `coherence.py`, `context.py`), swarm/retrieval `experiments/exp_*`, and matching `tests/test_engine_*` (+ the named engine tests in `LANES.md`).
**FORBIDDEN:** `app.py`, `memory/**`, `synthesis/**`, `static/**`.

**Frozen contract (HANDOFF):** swarm **READS**, never writes the self; only the membrane commits; reasoning is single-agent, fan-out is reading only. Fail loud at boundaries — a silent wrong number into the belief-state is the worst bug. Never assume a hosted model name in `config.py` exists (config.py is S0's — request a probe, don't edit it).

**Subagent tree:** `token-scout` (Haiku, locate) → `token-implementer` (Sonnet, bounded impl vs frozen contract) → `token-verifier` (Haiku, run tests) → `token-reducer` (logs). Keep planner/judge in-session.

**Current task:** `status/S0-coordinator.md` → **T4.1** (`analyst.investigate` failure finalizer + regression test), then **T4.2** (RQ-E05 retrieval harness — experiment-first, ≥20 seeds). Report in `status/S4-engine.md`.
