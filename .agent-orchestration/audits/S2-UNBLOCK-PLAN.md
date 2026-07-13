# S2 UNBLOCK PLAN — 2026-07-13 (prioritize unblocking, per director)

The two things gating the most work are **human-only**. The rest I've made turnkey below.

## 🔴 HUMAN ACTIONS (only you can do these — highest leverage, do in order)

1. **Restart S5 (Lane-2 Membrane) and S6 (Lane-3 Engine).** Both sessions are DEAD — status frozen at 23:04 (~2h), ✅x0, receiving no turns. S5's M0 code landed but nothing since. **S5 blocks the entire critical path:** multi-rater §A / RQ-E02 ("best next slice" per CONTINUATION §11), conflict-typing, FC-2/3/5 real fills. S6 blocks Lane-3 (dependency/value_queue/synthesis/analysis). A parked session cannot read the board — only you can relaunch their loops.

2. **Authorize the first scoped commits** (nothing is committed; 85 dirty files; HEAD `0a6f923`). Priority order:
   - **H1/M1 security** (`git add persona/api/app.py tests/test_app_security.py`) — the rw-self `run_shell` fix is S2-VERIFIED but **still live-vuln until commit + server restart**. Ship first.
   - **S4 clean slice** (analyst/investigation/daemon/consensus/verifier/debate + their tests) — 8 S2-PASS milestones, isolates the clean engine work from the dirty tree.
   - **S3 Lane-4 slice** (eval/, static/js, epistemic routes + tests) — 5 S2-PASS.
   - Commit isolates verified work and de-risks the 85-file mixed tree (TICK-5 concern).

## 🟢 TURNKEY — §A(v2) multi-rater substrate (so restarted S5 ships T5.1 in minutes)

This is the critical-path unblock. `conflict_reviews.py` is S5's hash-chained ledger (I won't edit it — collision-corruption risk if S5 restarts mid-write). Exact spec to implement, built to my frozen §A(v2) F1–F6:

**New module `persona/conflict_gold.py`** (blinding + batch freeze; keeps the ledger append-only):
- `freeze_batch(pairs, *, seed) -> {batch_id, assignments:[ReviewAssignment], manifest_sha256}` — deterministic (no wall-clock; F6). Each assignment: `assignment_id = sha256(canonical[batch_id, conflict_id, reviewer_id])` (F4); `side_order` ∈ {"AB","BA"} from the seeded permutation, **frozen here not at serve** (F3); `packet_A`/`packet_B` carry the pos/neg claims **relabeled by side_order** so no served field reveals sign (F1); the A/B→pos/neg map sealed server-side keyed by assignment_id.
- `blinded_export(batch_id) -> bundle + .sha256` frozen **before** collection.

**Extend `conflict_reviews.py` (S5)** — additive to the record schema + hash chain:
- `ReviewLabel` gains `batch_id` + `conflict_id` (F2 — its own dedup key) + `schema_version` (F6).
- `reviewer_id` = server-issued opaque token, not client free-text (F5).
- Reject duplicate `(reviewer_id, conflict_id, batch_id)` (F2).
- Replace `threading.Lock()` with an OS advisory file lock (`msvcrt.locking` Win / `fcntl.flock` POSIX) at the append/verify seam.

**My 6 pre-registered acceptance checks (the S5/S6 ✅ gate):**
1. Blinding: across a frozen batch, served packet-order does NOT correlate with stored sign above chance.
2. Dedup: same reviewer re-labels same (conflict,batch) → rejected, no ledger append.
3. Multi-process concurrent append (≥2 real processes) → `verify_conflict_reviews` ok, zero lost/dup, chain intact.
4. Tamper: flip 1 bundle byte → manifest check fails; flip 1 ledger line → replay fails.
5. Determinism: fixed seed → batch freeze + side permutation byte-identical on rerun.
6. No KG mutation across a full assign→label→verify cycle.

**Then RQ-E02:** sign-collision vs 1-verifier vs 2-verifier+exact-span at the ≥0.85-precision gate. **NEVER synthesize labels** — if no real reviewers, stop at the frozen blinded bundle + hand the UI to S3.

## Status of the live lanes (no unblock needed — shipping clean)
S4 (9 ✅) + S3 (8 ✅) + Lane-2 M0 all S2-PASS; suite 207 green. They're building against fixtures correctly while S5/S6 are down. Once you restart S5/S6 + authorize commits, the whole board converges.
