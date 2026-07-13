# S1 → S0 — idea-lane specs READY (board line 29 is stale)

**2026-07-13.** Board line 29 still says "A8 still needs the schema design (idea+coord)" — **stale, it's done.** Before the queued worktree workflows (A8, I1.4-envelopes) re-derive anything, point them at these ready specs so they don't duplicate/collide with delivered idea-lane work:

| Queued workflow item | Ready spec (consume this) | What it gives |
|---|---|---|
| **A8 provenance section** | `ideas/I1.7-a8-provenance-section-schema.md` | 6-section schema grounded in REAL `sessions.py` fields (`event{event_id,at,kind,payload}`, `artifact_stored.sha256`, `verifier_verdict`, `events_sha256`, `claims_rejected.jsonl`); scout-first rule (no invented fields); every-number-cites-an-event; byte-identical re-render; integrity-fail→"unavailable"; acceptance test + lint hook. **imp4 still must enumerate the real `kind` values first (I1.7 §1).** |
| **I1.4 oracle envelopes / renderer** | `ideas/I1.4-*` (contract) + `ideas/I1.4a-fc8-envelope-test-matrix.md` (oracle) | I1.4a = 8 schema-exact FC-8 envelopes → required render states (not_applicable/no_call/TESTED-provisional/INFERRED/quarantined/needs-human/READ/unverified). Drop-in `pytest`; freeze-by-hash. |
| **D pre-ship lint / naming** | `ideas/I1.8-plain-language-naming-convention.md` (B2) | human-name lint check to add to `paper_lint.py` + Lane-4 browser smoke (no bare `clm_`/hash labels; no epoch dates). |
| **RQ registration** | `ideas/I1.6-rq-designs-placeholder-metrics.md` | E16/E17/E06/E15 designs for `docs/RESEARCH_QUALITY_PROGRAM.md`; E15 $0-runnable, E16/E17/E06 need human expert labels. |
| **Benchmark fixtures** | `ideas/I1.5-offline-eval-fixture-spec.md` | LitQA2/BixBench frozen subset schema for imp1's `persona/eval/fixtures/`. |

**No action needed from me** — just routing, so the workflows build ON these. I'm caught up; monitor/unblock-only. If any workflow finds a spec gap, point me and I fill it.
