# PRD-14 — Sleep-consolidation pass (ReMem-Refine)

> **Owner lane:** 2 (Membrane & belief core) · **Status:** DRAFT-for-implementation (2026-07-13) · **Autonomy:** BALANCED — merge/prune/demote of **non-verified, non-anchored** beliefs runs autonomously into soft, reversible states; anything touching an anchored / `HUMAN_CONFIRMED` / `TESTED` / lean-verified belief is hard-excluded and (where relevant) filed to human. · **Depends-on:** FC-2 (`inbox.file_handoff`, optional), FC-3 (`kg.add_dependency_edge` for abstraction edges — Lane 2's own), PRD-02 F2.9 (`history.stale_claims` — same lane, coordinate), the validated poisoning oracle (`experiments/exp_poisoning.py`).

---

## 0. Summary + capability unlocked

Persona reads continuously and its belief graph only grows. Three sources of rot accumulate that no current pass removes:

1. **Near-duplicate beliefs** — not exact-identity duplicates (those already collapse: `kg.add_claim` MERGEs on a deterministic `claim_id = "clm_"+sha1(canon(subj)|canon(obj)|sign)`, kg.py:99–121), but *semantic* duplicates created by **canonicalizer drift**. `Canonicalizer.canon` (canon.py:65–91) is lazy and embedding-clustered; as its index grows the same concept can resolve to different canonical strings over a run, so one real belief ends up as two `Claim` nodes with different `pair_key`/`claim_id`. Nothing ever reconciles them.
2. **Stale READ candidates** — low-support, never-re-supported `READ`/`INFERRED` claims that were admitted once and never corroborated. `history.series` (history.py:54) holds the evidence to detect this but nothing scans it (verified: only F2.9 plans to).
3. **Interfering beliefs** — a low-support claim that `CONTRADICTS` a much stronger claim on the same `pair_key`, left at full confidence, muddying the field view.

**Capability unlocked:** a scheduled, cadence-gated **sleep-consolidation pass** ("ReMem-Refine") that merges semantic duplicates, soft-prunes stale unsupported candidates, abstracts recurring evidence patterns into higher-level `INFERRED` beliefs, and demotes interfering ones — **every action soft, node-preserving, hash-chain-logged, individually reversible, and emitted as a legible `consolidation` event** — while provably never dropping a verified/anchored belief. This is cheaper than re-reading and directly legible (the consolidation log *is* the story of the mind tidying itself).

**Research grounding.** ReMem / Evo-Memory (arXiv:2511.20857) — memory refinement via merge/abstract/forget cycles that keep an agent's store compact without losing load-bearing content. Learning to Forget (arXiv:2603.14517) — interference-driven demotion rather than deletion. Persona's adaptation keeps the field's *forget* operation but makes it **soft + reversible + audited** (deletion is never allowed; a "forgotten" belief is `valid_to`-retired with a `MERGED_INTO`/`PRUNED_STALE` provenance tag and can be restored), which is what the epistemic contract requires.

---

## 1. File ownership (disjoint)

| File | Status | Lane | Note |
|---|---|---|---|
| `persona/memory/consolidate_sleep.py` | **new** | 2 | Orchestrator + append-only reversible consolidation log. Provides **FC-10**. |
| `persona/memory/kg.py` | edit (add writers only) | 2 | New soft-mutation writers: `merge_claims`, `prune_stale_claim`, `demote_claim`, `restore_claim`, read helper `dedup_candidates_raw`. Additive; no existing signature changes. |
| `persona/memory/history.py` | edit (add query only) | 2 | `stale_claims(...)`. **Shared with PRD-02 F2.9** (same lane) — see §2 + §4. |
| `experiments/exp_rq_e26_sleep_consolidation.py` | **new** | 2→(4 registry) | RQ-E26 protection + reduction experiment. `experiments/*` is nominally Lane 4, but the epistemic-gate experiments for a lane's own feature are authored by that lane and registered by Lane 4 in `docs/RESEARCH_QUALITY_PROGRAM.md` (same convention as RQ-E16/E17). |
| `tests/test_sleep_consolidation.py` | **new** | 2→(4 registry) | Runnable checks (§5). |

**Boundary files (NOT edited by this lane — decoupled by FC-10):**

- `persona/synthesis/consolidator.py` (**Lane 3**) — one additive call inside the existing `consolidate()` to trigger the refine pass on its cadence gate. Lane 3 owns the edit; this PRD only specifies the call. **Flagged as a CONTRACT CHANGE PROPOSAL** (adds FC-10; see §2).
- `persona/daemon/worker.py` / `persona/daemon/supervisor.py` (**Lane 1**) — *not* touched under the primary design (the pass piggybacks the already-scheduled `consolidate` task). Only touched under the rejected alternative in §2.

---

## 2. FCs provided / consumed + CONTRACT CHANGE PROPOSAL

**Consumed:**
- **FC-2** — `inbox.file_handoff(kind, dossier)` for the one case the pass must escalate rather than act (a *verified* belief found duplicated/interfering — the pass refuses to touch it and files it). Degrades safely to a logged `consolidation` event if inbox not yet landed.
- **FC-3** — `kg.add_dependency_edge(src, dst, rel_type='generalizes', confidence, span)` for the abstraction feature (Lane 2's own writer; if not yet landed, F14.3 abstraction is skipped, not blocked).
- **PRD-02 F2.9** — `history.stale_claims(...)`. Same lane. If F2.9 lands first, consume it verbatim; if this PRD lands first, it *defines* `stale_claims` and F2.9 consumes it. Either way one definition — coordinate in HANDOFF, no cross-lane FC.

**Provided — CONTRACT CHANGE PROPOSAL → new FC-10 (Lane 2 provides):**

```python
# persona/memory/consolidate_sleep.py
def run(kg=None, ops_dir=None, *, max_age_days: int = 90, unsupported_cycles: int = 3,
        dup_threshold: float = 0.93, min_gap_hours: float = 20.0,
        parent_id: int | None = None) -> dict
#   -> {"ok": bool, "ran": bool, "reason"?: str,
#       "merged": int, "pruned": int, "abstracted": int, "demoted": int,
#       "protected_skips": int, "records": [record_id, ...]}
#   Cadence-gated: if the last successful run was < min_gap_hours ago (read from the log),
#   returns {"ok": True, "ran": False, "reason": "cadence"} without mutating anything.

def revert(record_id: str, ops_dir=None) -> dict
#   -> {"ok": bool, "action": str, "restored": [claim_id, ...]}  # undoes one logged action
```

**Who calls `run`:** the existing `consolidator.consolidate()` (Lane 3) appends **one** line at the end of a successful run — `from ..memory import consolidate_sleep; consolidate_sleep.run(parent_id=parent_id)`. Because `run` self-gates on `min_gap_hours`, calling it on every `consolidate` task yields an effectively **nightly** heavy pass regardless of how often `consolidate` fires (supervisor.py enqueues `consolidate` on idle/output agendas + unconditionally at supervisor.py:145). This is why no supervisor/worker edit is needed.

**Rejected alternative (documented):** a dedicated `"consolidate_sleep"` worker task type (worker.py append-only handler per the Lane-1 boundary convention at worker.py:384) + a supervisor cadence enqueue. Gives an independently schedulable/visible task type but costs a **non-append-only** `supervisor.py` edit (Lane 1) and a second scheduling knob. Rejected for the primary path (ponytail: fewest cross-lane edits; the cadence gate already delivers "nightly"). Adopt only if the team wants the pass decoupled from note-synthesis cadence — then it is a CCP to **FC-1** (add task type `"consolidate_sleep"`), routed to Lane 1.

---

## 3. Features

### F14.1 — Semantic-duplicate merge

- **Problem & evidence.** Exact-identity duplicates cannot exist (deterministic `claim_id`, MERGE at kg.py:110). The real leak is canonicalizer drift (canon.py:65–91, lazy embedding clustering with per-run first-seen canonical names) producing two `Claim` nodes for one belief. No reconciler exists.
- **Design.**
  - `kg.dedup_candidates_raw(limit: int = 400) -> [{claim_id, subject, object, effect_sign, independent_source_count, confidence, provenance, anchored, ingest_time}]` — pure read of live (`valid_to IS NULL`), **non-anchored**, `provenance IN ['READ','INFERRED']` claims. (Verified beliefs are excluded from candidacy at the query, so they can never be a merge *loser*.)
  - `consolidate_sleep._find_duplicates(rows, dup_threshold)` — for each pair with **equal `effect_sign`**, embed `f"{subject} || {object}"` via the existing `embed.encode` (embed.py:20) and merge only when cosine ≥ `dup_threshold` **AND** `canon._symbol_sig(subject)`+`_symbol_sig(object)` match on both endpoints (reuse canon.py:31–33 — this is the guard that stopped IL‑6/IL‑1 false-merges; do not re-derive it). `# ponytail: reuse canon's symbol-signature guard, not a new one — the digit-token false-merge is the worst bug here.`
  - Survivor = higher `independent_source_count`, tie-break older `ingest_time`. `kg.merge_claims(loser_id, survivor_id, reason, session_id) -> dict`: **refuses (returns `{ok:False,reason:'protected'}`) if either side is anchored or `provenance IN ['HUMAN_CONFIRMED','TESTED']`**; else re-points the loser's `SUPPORTED_BY` edges onto the survivor (`MERGE` so quotes dedupe), recomputes survivor `support_count`/`independent_source_count`/`confidence` with the exact block already at kg.py:125–131 (extract to a private `_recompute(cid)` and call from both sites — one definition), and soft-retires the loser: `valid_to=$now, provenance='MERGED_INTO', merged_into=$survivor_id` (node preserved for audit + revert).
- **Epistemic guardrails.** Verified/anchored claims are excluded as candidates *and* re-refused inside the writer (defense in depth). If a verified belief is found duplicated by a non-verified one, the non-verified side is merged *into* the verified survivor (support strengthens the anchor; confidence stays pinned because the survivor is anchored — the existing `CASE WHEN c.anchored` clause at kg.py:130 already protects it). Nothing is deleted; `restore_claim` reverses a merge.
- **Required experiment.** Covered by RQ-E26 (§F14.5) — the merge threshold `dup_threshold` is load-bearing (too loose = catastrophic false-merge of distinct beliefs) and is gated there.
- **Acceptance + check.** Two live READ claims that canon-drifted apart (same `pair_key`-equivalent concept, same sign) merge into one live survivor whose `independent_source_count` is the union; a claim differing only by symbol token (IL‑6 vs IL‑1) does **not** merge. Check: `test_sleep_consolidation.py::test_merge_unions_support_and_respects_symbol_guard`.
- **Effort** M · **Deps** embed.py (exists), canon.py (reuse), FC-10 log.

### F14.2 — Stale-candidate soft-prune

- **Problem & evidence.** Never-re-supported READ candidates linger at admission confidence. `belief_history` (history.py:20–52) records support-over-time but nothing queries it for staleness.
- **Design.**
  - `history.stale_claims(max_age_days: int = 90, unsupported_cycles: int = 3) -> [{claim_id, age_days, cycles_unsupported}]` — over `belief_history`: `age_days` from the earliest `ts`; `cycles_unsupported` = count of trailing snapshots with no `independent` increase. (Verbatim the FC-3-adjacent query PRD-02 F2.9 also needs — **single definition**, §4.)
  - `kg.prune_stale_claim(claim_id, reason, session_id) -> bool` — **refuses anchored / `HUMAN_CONFIRMED` / `TESTED`**; else soft-retire `valid_to=$now, provenance='PRUNED_STALE'` (reuses the exact soft-retire shape of `retire_extraction_claim`, kg.py:168–179, but with a distinct provenance tag so audit can tell *why* it left the live set). Only prunes claims that are BOTH stale (from `stale_claims`) AND weak (`independent_source_count < 2`).
- **Epistemic guardrails.** Verified/anchored never pruned (writer-level refusal). Soft only — node + all `SUPPORTED_BY` edges retained; `restore_claim(claim_id)` un-retires. Pruning a stale claim that participates in a `CONTRADICTS` pair with a verified belief is **skipped and filed** via FC-2 (removing a contradiction silently would hide a real tension).
- **Required experiment.** trivial — reuses validated staleness signal; thresholds are knobs. The zero-verified-loss property is covered by RQ-E26.
- **Acceptance + check.** A 100-day, `independent=1`, never-re-supported READ claim is pruned (goes `valid_to != null`, `provenance='PRUNED_STALE'`); an anchored claim of the same age is not. Check: `test_sleep_consolidation.py::test_prune_stale_weak_only_and_reversible`.
- **Effort** S · **Deps** F2.9 `stale_claims` (or defines it), FC-2 (optional).

### F14.3 — Abstract recurring evidence into a higher-level belief

- **Problem & evidence.** When many distinct subjects share the same `(object, effect_sign)` (a recurring pattern, e.g. "≥k drugs each *reduce* mortality"), the field view has no node saying "this is a general pattern." ReMem's *abstract* op.
- **Design.** In `consolidate_sleep`, group live claims by `(canon(object), effect_sign)`; when `≥ ABSTRACT_MIN_SUBJECTS` (default 5) *distinct, independent-lab-backed* subjects share it, create one `INFERRED` belief via `kg.add_claim({subject: "<class>", object, effect_sign, provenance:'INFERRED', confidence: <bounded, from constituent mean>}, source_slug='consolidator')` and link each constituent with `kg.add_dependency_edge(constituent_id, abstract_id, 'generalizes', confidence, span)` (FC-3). The abstract belief is typed `INFERRED`, **never anchored**, and rendered with less authority than READ/verified (honest-uncertainty rule).
- **Epistemic guardrails.** `INFERRED` provenance means it can never masquerade as observed/confirmed. It is derived, not asserted from a source span, so it carries no fabricated quote. Fully reversible (retire the abstract node + its `generalizes` edges via the log). Lowest-priority feature — **skipped, not blocked, if FC-3 `add_dependency_edge` hasn't landed** (guarded by `hasattr`).
- **Required experiment.** trivial (creates a derived, clearly-typed node; correctness is "≥k distinct independent subjects" — a counting rule, not a modeling choice). Contributes zero verified-belief loss by construction (it only *adds* an INFERRED node).
- **Acceptance + check.** 5 distinct subjects with `object='mortality', sign='-'` produce one INFERRED abstract claim with 5 `generalizes` edges. Check: `test_sleep_consolidation.py::test_abstract_creates_inferred_generalization`.
- **Effort** M · **Deps** FC-3 `add_dependency_edge`.

### F14.4 — Demote interfering beliefs

- **Problem & evidence.** A low-support claim that `CONTRADICTS` a much stronger one on the same `pair_key` sits at full confidence (`contradictions()`, kg.py:217–227 already surfaces the pairs). Learning-to-Forget: demote interference rather than delete.
- **Design.** For each `CONTRADICTS` pair among live non-anchored claims where one side has `independent_source_count ≥ 2×` the other AND ≥2 absolute, `kg.demote_claim(weak_id, new_confidence, reason, session_id) -> bool`: **refuses anchored/verified**; else set `confidence = max(DEMOTE_FLOOR=0.2, confidence - DEMOTE_STEP=0.2)` (bounded, never to zero, never below floor). The stronger side is untouched. Recorded with `before=old_confidence` so `revert` restores exactly.
- **Epistemic guardrails.** Never demotes across an anchor (an anchor under attack routes to F2.9's `anchor_under_attack` handoff, not here — this pass explicitly *skips* any pair containing an anchored/verified side and files it). Confidence-only, reversible; the `CONTRADICTS` edge stays (the tension remains visible). Motion-only-for-real-state-change: a demote fires only on a measured support asymmetry.
- **Required experiment.** trivial — bounded, reversible confidence nudge on a measured asymmetry. Zero-verified-loss covered by RQ-E26 (demote must refuse verified sides).
- **Acceptance + check.** In a `+`/`−` pair with labs 5 vs 1, the weak side's confidence drops by one step (floored) and the strong side is unchanged; if the strong side is anchored, neither moves and a handoff is filed. Check: `test_sleep_consolidation.py::test_demote_weak_side_only_and_skips_anchored`.
- **Effort** S · **Deps** existing `CONTRADICTS` edges, FC-2 (optional).

### F14.5 — RQ-E26 protection-and-reduction gate + reversible consolidation log

- **Problem & evidence.** The whole pass is only safe if it **provably never drops a verified belief** while still reducing rot. The repo's validated protection oracle is `experiments/exp_poisoning.py` (anchor retained 100% vs naive 71% under correlated poisoning — FINDINGS.md; note the brief's `exp_when_protection_matters.py` is this file's aspirational name — the *real* protection oracle in-repo is `exp_poisoning.py`, reuse it).
- **Design — the log (FC-10 internals).** `consolidate_sleep` appends every action to an append-only, hash-chained `ops_dir/consolidation_log.jsonl` **reusing `conflict_reviews`' integrity primitives verbatim** (`_canonical_json`, `_record_sha256`, the `prev_sha256` chain, `verify_*` gate before append — conflict_reviews.py:34–213). `# ponytail: same ledger integrity primitives as conflict_reviews; do not reinvent the hash chain.` Row: `{action:'merge'|'prune'|'demote'|'abstract', claim_ids:[...], survivor_id?, before:{confidence?|valid_to?}, reason, session_id, at, prev_sha256, record_id}`. `revert(record_id)` reads the row and calls `kg.restore_claim` / resets confidence from `before`. Each action also emits `log().emit("consolidation", <human sentence>, actor="consolidator", parent_id=...)` (new event type on the existing legible stream, events.py:58) — the visible consolidation-log entry the brief requires.
- **Epistemic guardrails.** The log is the reversibility substrate: nothing the pass does is unrecoverable. Integrity is verified before every append (a corrupted log fails loud, `LedgerIntegrityError`, before any mutation).
- **Required experiment — RQ-E26 (new; register in `docs/RESEARCH_QUALITY_PROGRAM.md`).**
  - **Hypothesis:** the sleep pass strictly reduces (duplicate + stale + interfering) belief count **without dropping a single anchored / `HUMAN_CONFIRMED` / `TESTED` belief**, across seeded synthetic graphs.
  - **Metric:** (a) `verified_loss` = # of anchored/verified beliefs that became non-live OR changed sign OR lost confidence after the pass; (b) `reduction` = live-belief count before − after (should be > 0 from merges+prunes); (c) `false_merge` = # of merges joining claims with mismatched symbol signature or genuinely distinct concepts (from the seeded ground truth).
  - **Gate:** `verified_loss == 0` on **every** seed (hard, zero-tolerance) **AND** mean `reduction > 0` **AND** `false_merge == 0`. Only when all three hold does the pass run autonomously; until then it runs in **dry-run** mode (computes + logs proposed actions, mutates nothing).
  - **Seeds:** ≥20. Each seed builds a fresh FalkorDB graph (reuse `exp_poisoning.py`'s `KG(name=...)` + `DETACH DELETE` fixture pattern, exp_poisoning.py:19–20) seeded with: N anchored + M `HUMAN_CONFIRMED`/`TESTED` beliefs (must survive), a controlled set of canon-drift duplicates, stale-weak candidates, IL‑6/IL‑1-style near-misses (must NOT merge), and `+`/`−` interference pairs including one with an anchored strong side (must file, not demote).
  - File: `experiments/exp_rq_e26_sleep_consolidation.py`; results appended to `results/FINDINGS.md`.
- **Acceptance + check.** RQ-E26 passes its gate at ≥20 seeds; the pass is `dry_run` until it does. Runnable check (fast, no ≥20 loop): `test_sleep_consolidation.py::test_pass_never_touches_verified` seeds one anchored + one HUMAN_CONFIRMED belief among rot and asserts both are byte-for-byte unchanged (sign, confidence, `valid_to`, anchored) after `run(...)`, and that the log verifies + every action reverts cleanly.
- **Effort** M · **Deps** all of F14.1–F14.4, conflict_reviews primitives (reuse), exp_poisoning.py (oracle).

---

## 4. Sequencing

1. **FC-10 stubs first** (Milestone-0 rule): land `consolidate_sleep.run`/`revert` returning typed empty results + the `kg` writer stubs (refuse-verified logic in place, no-op bodies), so the Lane-3 one-line call and RQ-E26 harness can build against them.
2. `history.stale_claims` — coordinate with F2.9 in HANDOFF **before writing** (one definition; whichever PRD lands first owns it).
3. The append-only log (F14.5 substrate) — needed by every mutating feature for reversibility; build immediately after stubs.
4. F14.2 (prune) + F14.4 (demote) — simplest, reuse existing soft-retire / confidence shapes.
5. F14.1 (merge) — the load-bearing one; do not enable outside dry-run until RQ-E26 passes.
6. F14.3 (abstract) — last, `hasattr`-guarded on FC-3.
7. Lane-3 boundary call in `consolidator.consolidate()` — after `run` is real and dry-run-safe (CCP acked).

The pass ships **dry-run by default**; flipping to live is gated on RQ-E26 (§F14.5), exactly like FC-4 auto-dispatch is gated on RQ-E17.

---

## 5. Test plan

- `test_sleep_consolidation.py::test_merge_unions_support_and_respects_symbol_guard` (F14.1)
- `test_sleep_consolidation.py::test_prune_stale_weak_only_and_reversible` (F14.2)
- `test_sleep_consolidation.py::test_abstract_creates_inferred_generalization` (F14.3, skipif no FC-3)
- `test_sleep_consolidation.py::test_demote_weak_side_only_and_skips_anchored` (F14.4)
- `test_sleep_consolidation.py::test_pass_never_touches_verified` — **the protection oracle** (F14.5): reuses `exp_poisoning.py` fixture style; asserts zero verified mutation, log verifies, `revert` restores each action.
- `test_sleep_consolidation.py::test_cadence_gate_skips_within_min_gap` — a second `run` within `min_gap_hours` returns `ran=False` and mutates nothing.
- Full gate: `python experiments/exp_rq_e26_sleep_consolidation.py` (≥20 seeds, prints `VERDICT: PASS` only if `verified_loss==0 ∧ reduction>0 ∧ false_merge==0`).
- All KG tests need FalkorDB on :6379 (same as `exp_poisoning.py`); mark `@pytest.mark.falkor` for skip when absent.

---

## 6. Open questions

1. **CCP-10 (blocks Lane 3):** approve `consolidator.consolidate()` (Lane-3 file) appending the single `consolidate_sleep.run(parent_id=parent_id)` call at end-of-run, decoupled by FC-10? Or does the team prefer the dedicated `consolidate_sleep` worker task type (rejected alt, §2 — costs a Lane-1 supervisor edit)? Default assumed: the one-line Lane-3 call.
2. **`history.stale_claims` ownership (Lane 2 internal, blocks F14.2 + F2.9):** which PRD defines it — this one or PRD-02 F2.9? Must be one definition. Needs a HANDOFF line before either writes it.
3. **`min_gap_hours` = "nightly"?** Default 20h so a daemon that idles frequently still runs the heavy pass ~once/day. Confirm the daemon's real idle cadence makes 20h deliver roughly-nightly, else expose as config.
4. **Abstraction scope (F14.3):** is subject-class naming ("≥k drugs") worth an LLM label, or keep it mechanical (`f"{k} subjects"`)? Ponytail default: mechanical string, no model call — upgrade to an LLM label only if the UI needs a prettier name.
5. **Dry-run duration:** RQ-E26 gates live mutation. Confirm the team is fine with the pass logging proposed-but-unapplied actions (still legible) until the ≥20-seed gate is green.
