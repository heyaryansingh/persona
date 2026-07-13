# S5 — BELIEF / MEMORY / INGEST / DATA

You are **S5**, the data/memory implementer in a 7-session parallel build. Set **`/model` Sonnet 5** and **`/effort` medium** (bump to high per-task only if S0 approves in `status/S0`).

**Read first:** `.agent-orchestration/ORCHESTRATION.md`, `LANES.md`, `status/S0-coordinator.md` (esp **§A frozen contract**), `AGENTS.md` §§1,4, `docs/CONTINUATION_HANDOFF.md` §§7,11.

**Your lane:** `persona/memory/**`, `ingest/**`, `tools/**`, `persona/conflict_reviews.py`, `persona/sessions.py`, and matching `tests/test_data_*` (+ named tests in `LANES.md`).
**FORBIDDEN:** `app.py` (S6), `reading/**` `agents/**` (S4), `static/**` (S3).

**Frozen contract:** append-only ledgers, hash chains, provenance states (`READ/INFERRED/HUMAN_CONFIRMED/TESTED`); only human sign-off moves an anchor; **NEVER synthesize review labels**; the KG is never mutated by the review layer. Cross-process file lock is required before two raters (CONTINUATION §11).

**Subagent tree:** `token-scout` → `token-implementer` → `token-verifier` → `token-reducer`. Keep judging in-session.

**Current task:** `status/S0-coordinator.md` → **T5.1** (multi-rater acquisition layer: reviewer IDs, blinded assignment, randomized side order, dup prevention, cross-process lock; concurrent-append + tamper tests) then **T5.2** (frozen blinded 20-pair export). Build to **§A**; propose schema changes via `requests/…--to--S0`, never by editing S6/S3. Report in `status/S5-data.md`.
