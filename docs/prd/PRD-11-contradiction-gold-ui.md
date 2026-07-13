# PRD-11 — Multi-rater contradiction gold acquisition (unblock RQ-E02)

> **Owner lane:** 2 (ledger/acquisition) + 4 (review UI, endpoints, experiment) · **Status:** DRAFT-for-implementation · **Autonomy:** human-gated collection; **zero autonomous escalation until RQ-E02 passes ≥0.85 precision** · **Depends-on:** PRD-00 FCs (authoritative), `persona/conflict_reviews.py`, `persona/api/app.py` inbox routes, `docs/RESEARCH_QUALITY_PROGRAM.md` §RQ-E02, `docs/CONTINUATION_HANDOFF.md` §7.1 / §11.

---

## 0. Summary + capability unlocked

`conflict_reviews.py` is today a single-process, append-only, hash-chained ledger of human conflict labels with **no reviewer identity, no assignment/batch, no blinding, no side-order control, no duplicate-review guard, and only a process-local `threading.Lock`** (`persona/conflict_reviews.py:20`, `:202`). The ledger is empty (no real labels), so RQ-E02 — the experiment that decides whether Persona may *ever* autonomously escalate a candidate conflict — cannot run. This is the single gate on all autonomous contradiction escalation (`RESEARCH_QUALITY_PROGRAM.md:155`, `CONTINUATION_HANDOFF.md:259`).

**This PRD adds exactly the missing acquisition layer and its review UI, then runs RQ-E02 — and stops honestly if no real reviewers exist.** Concretely:

1. **Ledger (Lane 2):** pseudonymous `reviewer_id`, `batch_id`, `assignment_id`, a per-item **frozen randomized `side_order`**, **duplicate-review prevention** per `(reviewer_id, conflict_id, batch_id)`, and an **OS-level cross-process advisory lock** replacing the process-local lock. A **blinded stratified export bundle** whose content SHA-256 is **frozen before any label is collected** (preregistration discipline, mirroring the repo's own frozen-data practice — `CONTINUATION_HANDOFF.md:148`).
2. **UI (Lane 4):** the existing Review-surface inbox and dossier modal (`index.html:2021-2068`) gain a pseudonymous reviewer identity, batch/assignment selection, a **blinded A/B dossier** (no `+/−` sign, randomized sides), and a duplicate/mismatch-safe submit. **No new tab** (consistent with commit `353662b`).
3. **Agreement + gold (Lane 2/4):** deterministic inter-rater agreement (Cohen's κ for 2 raters, percent agreement always) and an **adjudicated gold file** that unanimous items fill automatically but that **refuses to invent a label** where reviewers disagree.
4. **RQ-E02 (Lane 4):** sign-collision vs one-verifier vs two-verifier+exact-span, scored against the human gold, gated at **≥0.85 precision**.

**Capability unlocked:** a measured, defensible answer to "can Persona escalate candidate conflicts at ≥0.85 precision?" — the precondition for `open_from_conflict` autonomy (FC-1), `calibrate.admit_decision` routing to `human` vs `commit` (FC-5), and any authoritative contradiction claim in the UI.

**Hard stop (epistemic):** if fewer than two real, independent human reviewers label a batch, ship the blinded bundle + UI and **STOP**. Never synthesize labels, never fabricate agreement, never run RQ-E02 on model-generated gold.

---

## 1. File ownership (disjoint)

| File | Lane | New? | Notes |
|---|---|---|---|
| `persona/conflict_reviews.py` | **2** | edit | ledger schema + lock + batch/blinding/agreement/gold functions |
| `persona/api/app.py` | **4** | edit (new routes only) | new `/inbox/batch*` routes; extend existing `/inbox/review` (`app.py:685`) |
| `persona/api/static/index.html` | **4** | edit (Review surface only) | reviewer identity + blinded dossier + batch picker in existing modal (`:2021-2068`) |
| `experiments/exp_rq_e02_contradiction_typing.py` | **4** | new | the RQ-E02 harness |
| `results/rq_e02_contradiction_typing.json` (+ `.png`) | **4** | new | immutable result record |
| `tests/test_conflict_reviews_multirater.py` | **4** | new | concurrency + blinding + dedupe + tamper regressions |
| `personas/<pid>/.persona/review_batches/<batch_id>.json` | **2** (data, written via ledger fns) | new | frozen blinded bundle |
| `personas/<pid>/.persona/gold/<batch_id>.json` | **2** (data) | new | adjudicated gold |

**Boundary files & the FC that decouples them.** `app.py` and `index.html` (Lane 4) call functions in `conflict_reviews.py` (Lane 2). Lane 4 already calls `append_conflict_review` directly (`app.py:698`) and `summarize_conflict_reviews` (`app.py:627`). Changing `append_conflict_review`'s signature and adding new module functions is therefore a **cross-lane interface change** → **CONTRACT CHANGE PROPOSAL CCP-11a** (§2). The two lanes are decoupled by treating `conflict_reviews.py`'s public function set as the frozen seam; UI/endpoints consume it, never re-implement ledger logic. Bundle/gold JSON files are **written only by Lane 2 functions**; Lane 4 reads them via endpoints.

---

## 2. FCs provided / consumed + CONTRACT CHANGE PROPOSAL

**Consumed (unchanged):**
- **FC-3** (`kg.py`): `candidate_conflicts(limit)` → rows `{subject, object, pos_sources, neg_sources, pos_claim, neg_claim, status, conflict_type, needs_human_review}` (`kg.py:229`, cols at `:226`); `provenance(claim_id)` for the dossier (`kg.py:234`). Read-only; no change requested.
- **FC-5** (`calibrate.admit_decision`): *downstream consumer* of the RQ-E02 verdict — its `route:'human'` branch is what this gate protects. No signature touch here.

**Provided (new, Lane 2 — `persona/conflict_reviews.py`):**

> **CONTRACT CHANGE PROPOSAL CCP-11a** — extend the review-append seam and add batch/agreement functions. Additive + one signature extension on an **empty ledger** (no migration cost). Must be acked by any lane building on `/inbox/review` before landing.

```python
# EXTENDED (was: pos_claim, neg_claim, verdict, rationale, confidence, qualifier="", next_check="")
def append_conflict_review(
    ops_dir, *,
    pos_claim_id: str, neg_claim_id: str,
    verdict: ConflictVerdict | str, rationale: str, confidence: float,
    reviewer_id: str,          # NEW — required; pseudonymous, non-PII, validated /^[A-Za-z0-9_-]{3,64}$/
    batch_id: str,             # NEW — required; must name an existing frozen batch
    side_order: str,           # NEW — required; "AB"|"BA"; MUST equal the batch's frozen side_order for this pair
    qualifier: str = "", next_check: str = "",
) -> dict: ...
# raises DuplicateReviewError | BlindMismatchError | LedgerIntegrityError | ValueError

# NEW functions
def freeze_review_batch(ops_dir, *, batch_id: str,
                        conflict_pairs: list[tuple[str, str]],   # [(pos_claim_id, neg_claim_id), ...]
                        seed: int, strata: dict[str, str] | None = None) -> dict
    # -> {"batch_id", "bundle_sha256", "n_items", "seed",
    #     "items":[{"assignment_id","conflict_id","claim_ids":[pos,neg],
    #               "side_order":"AB"|"BA","stratum":str}], "frozen_at"}
    # Deterministic per (batch_id, seed): RNG seeded from f"{batch_id}:{seed}" assigns side_order.
    # Writes review_batches/<batch_id>.json ONCE; refuses overwrite (append-only discipline).

def load_review_batch(ops_dir, batch_id: str) -> dict
    # Reads the frozen bundle, RECOMPUTES bundle_sha256 over canonical item content,
    # raises LedgerIntegrityError if it != stored hash (tamper evidence).

def batch_agreement(ops_dir, batch_id: str) -> dict
    # -> {"batch_id","n_items","reviewers":[reviewer_id...],
    #     "per_conflict":[{"conflict_id","labels":{reviewer_id:verdict},
    #                      "unanimous":bool,"majority":str|None}],
    #     "percent_agreement":float,
    #     "cohens_kappa":float|None,   # only when exactly 2 reviewers, else None
    #     "n_reviewers":int, "complete":bool}   # complete = every item has >=2 labels
    # Pure/deterministic; NO model. Returns n_reviewers<2 => cohens_kappa=None, complete=False.

def adjudicate_gold(ops_dir, batch_id: str, *,
                    adjudications: dict[str, dict] | None = None) -> dict
    # adjudications: {conflict_id: {"verdict":str,"rationale":str,"adjudicator_id":str}}
    # Unanimous items -> gold automatically. Disagreements -> filled ONLY from `adjudications`;
    # otherwise left status:"unresolved". NEVER invents a label. Writes gold/<batch_id>.json.
    # -> {"batch_id","n_gold","n_unresolved","provenance":"HUMAN_CONFIRMED",
    #     "items":[{"conflict_id","gold_verdict"|None,"source":"unanimous"|"adjudicated"|"unresolved"}]}
```

**No FC-2 change.** `inbox.file_handoff` (general human handoff) is untouched; adjudication of a disagreement *may* optionally file an FC-2 handoff for a third rater, but that is out of scope (YAGNI).

---

## 3. Features

### F11.1 — Cross-process ledger lock

**Problem & evidence.** `_LOCK = threading.Lock()` (`conflict_reviews.py:20`) guards the read-verify-append critical section (`:202-213`), but a `threading.Lock` protects only one process. Two reviewers behind separate API workers, or a horizontal deploy, can interleave `_verify_unlocked` → append and **corrupt the hash chain** (each computes `prev_sha256` from the same tail). The handoff calls this out explicitly as the blocker before multi-rater collection (`CONTINUATION_HANDOFF.md:100`, `:184`).

**Design.** Add a stdlib advisory file lock on a sidecar `conflict_reviews.jsonl.lock`, held for the whole critical section, composed with the existing in-process `threading.Lock` (in-process reentrancy + cross-process exclusion):

```python
# persona/conflict_reviews.py
import msvcrt if os.name == "nt" else fcntl   # (written as a normal try/branch)

@contextmanager
def _cross_process_lock(ledger_path: Path):
    lock_path = ledger_path.with_suffix(ledger_path.suffix + ".lock")
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(lock_path, os.O_RDWR | os.O_CREAT, 0o644)
    try:
        _acquire(fd)     # msvcrt.locking(fd, LK_LOCK, 1) | fcntl.flock(fd, LOCK_EX) — blocking
        yield
    finally:
        _release(fd); os.close(fd)
```

`verify_conflict_reviews` / `append_conflict_review` wrap their body in `with _LOCK, _cross_process_lock(path):`. Reads (`read_conflict_reviews`) also take it so a read never sees a half-written tail (the existing `ledger-truncated` check at `:109` already defends the on-disk state, but the lock avoids the transient false positive).

> `# ponytail: whole-file advisory lock held during read-verify-append. Serial appends only; a two-rater gold set has trivial contention. Upgrade path — single-writer append service if throughput ever matters.`

**Epistemic guardrail.** The lock does not weaken tamper evidence: hash-chain verification (`_verify_unlocked`) still runs inside the lock before every append. A crash mid-append leaves a truncated last line that `ledger-truncated` (`:109`) rejects on next open — fail-loud, never silently continue.

**Required experiment.** *Trivial* (correctness, not a modeling choice) — proven by a concurrency regression, not a seeded study (§5, F11.1 test).

**Acceptance + runnable check.** `tests/test_conflict_reviews_multirater.py::test_concurrent_appends_preserve_chain` spawns N≥8 processes (`multiprocessing`) each appending a distinct valid review to one ledger; afterward `verify_conflict_reviews(ops)["ok"] is True` and `record_count == total appended`. **Effort:** S. **Deps:** none.

---

### F11.2 — Reviewer identity, assignment, batch & blinded side-order in the record

**Problem & evidence.** Records carry only `claim_ids, verdict, rationale, confidence, qualifier, next_check, reviewed_at` + chain fields (`conflict_reviews.py:191-200`). There is no way to know *who* reviewed, *which assignment/batch*, or *whether the sides were blinded/randomized* — so inter-rater agreement and order-bias control are impossible. Handoff §11 names exactly these missing fields (`CONTINUATION_HANDOFF.md:269`).

**Design.**
- **Record schema += `reviewer_id`, `batch_id`, `assignment_id`, `side_order`** (all required for new appends). Added as plain keys; `_canonical_json` sorts keys and `_record_sha256` hashes all-but-`record_id` (`:34`, `:90`), so the hash chain is unchanged in mechanism. Validate each in `_verify_unlocked` (`:142-155`) alongside the existing schema checks: `reviewer_id` matches `^[A-Za-z0-9_-]{3,64}$` (pseudonymous, non-PII), `side_order ∈ {"AB","BA"}`, `batch_id`/`assignment_id` non-empty.
- **`freeze_review_batch`** samples/records the blinded bundle: for each `(pos, neg)` pair it computes `conflict_id` (existing, `:53`), draws `side_order` from an RNG seeded by `f"{batch_id}:{seed}"` (reproducible, auditable), tags a `stratum`, and writes `review_batches/<batch_id>.json`. `assignment_id = f"{batch_id}:{i:03d}"`. The bundle's `bundle_sha256` is computed over the canonical-ordered item list and **stored in the file** — frozen before any label.
- **`append_conflict_review` validates against the frozen batch**: loads the batch (F11.4), asserts the `(pos,neg)` pair is present and that the submitted `side_order` equals the frozen one → else `BlindMismatchError`. This makes the blinding non-forgeable: a reviewer cannot re-order sides to leak the stored sign.

**Data flow.** `freeze_review_batch` (curator, once) → `review_batches/<id>.json` (frozen) → UI serves blinded assignment (F11.5) → reviewer submits `{assignment_id, side_order, verdict,...}` → `append_conflict_review` re-validates side_order vs frozen → append.

**Epistemic guardrail.** Randomized side presentation is standard annotation blinding to remove order/anchoring bias; freezing the bundle hash before collection is preregistration against gold-set contamination (repo precedent: frozen GEO data hashes, `CONTINUATION_HANDOFF.md:148-151`; frozen 62-pair snapshot SHA `b967…`, `RESEARCH_QUALITY_PROGRAM.md:152`). Reviewer IDs are pseudonymous tokens; **no PII** is stored or required.

**Required experiment.** *Trivial* — blinding/side-randomization and the SHA-freeze are established methodology, not a Persona-specific hypothesis. Correctness is a unit test (side_order determinism + mismatch rejection).

**Acceptance + runnable check.** `test_frozen_batch_side_order_is_deterministic_and_enforced`: `freeze_review_batch(...,seed=7)` twice yields identical `bundle_sha256` and identical per-item `side_order`; an `append_conflict_review` with a flipped `side_order` raises `BlindMismatchError`; tampering one byte of `review_batches/<id>.json` makes `load_review_batch` raise `LedgerIntegrityError`. **Effort:** M. **Deps:** F11.1.

---

### F11.3 — Duplicate-review prevention per (reviewer, conflict, batch)

**Problem & evidence.** Nothing stops one reviewer labeling the same conflict twice, which would fake "agreement" and inflate n. The append path already reads+parses every prior record for verification (`_verify_unlocked` → `records`, `:159`), so the dedupe check is **free** — no extra scan.

**Design.** Inside the locked append, after `prior = _verify_unlocked(path)`, scan `prior["records"]` for any row with matching `reviewer_id` **and** `conflict_id` **and** `batch_id`; if found, raise `DuplicateReviewError` (new subclass of `ValueError`) → API returns HTTP 409. Cross-reviewer duplicates are allowed and desired (that *is* the second independent rating).

**Epistemic guardrail.** Independence of raters is the whole point of κ; a silent duplicate would be a fabricated-agreement bug — fail loud (`CLAUDE.md` §4 "a silent wrong number … is the worst possible bug").

**Required experiment.** *Trivial* (guard + test).

**Acceptance + runnable check.** `test_duplicate_review_rejected_same_reviewer_allowed_other`: same `(reviewer_id, conflict_id, batch_id)` twice → second raises `DuplicateReviewError`; a *different* `reviewer_id` on the same conflict/batch appends fine. **Effort:** S. **Deps:** F11.2.

---

### F11.4 — Blinded stratified bundle: freeze & tamper-checked load

**Problem & evidence.** RQ-E02 requires a "stratified 20-case blinded human gold set" over the frozen 62-pair snapshot (`RESEARCH_QUALITY_PROGRAM.md:152`, `:156`). No sampler/exporter exists.

**Design.** `freeze_review_batch` accepts the curator-chosen `conflict_pairs` and a `strata` map (`conflict_id → stratum`). Default stratification key (when `strata=None`): bucket by `min(pos_sources, neg_sources)` from `candidate_conflicts` rows (`kg.py:226`) — `{0,1}` = single-source, `≥2` = corroborated — so the gold set covers both fragile and well-sourced conflicts. Sampling *count* (20) and *which* pairs is the curator's call (kept out of the function — YAGNI); the function's job is deterministic freeze + hash. `load_review_batch` recomputes and compares `bundle_sha256` on every read → tamper evidence.

> `# ponytail: curator picks the 20 stratified pairs; the function just freezes+hashes. A built-in stratified sampler is one helper away if batches get frequent — not now.`

**Epistemic guardrail.** The frozen hash is the contamination firewall: once labels start, the sampled set and its side-order cannot change without detection. Blinded dossiers "may be shown for label acquisition" only while `candidate conflict / unverified` (`RESEARCH_QUALITY_PROGRAM.md:155`).

**Required experiment.** *Trivial* (covered by F11.2 determinism/tamper test).

**Acceptance + runnable check.** `python -c "from persona.conflict_reviews import freeze_review_batch, load_review_batch; b=freeze_review_batch(OPS, batch_id='e02-pilot', conflict_pairs=PAIRS, seed=1); assert load_review_batch(OPS,'e02-pilot')['bundle_sha256']==b['bundle_sha256']"`. **Effort:** S (folds into F11.2). **Deps:** F11.2.

---

### F11.5 — Lane-4 blinded review UI (existing Review surface, no new tab)

**Problem & evidence.** The current dossier modal renders **stored positive / stored negative with the effect sign** (`dossierSide(...,'stored positive','pos')` and `… sign ${p.effect_sign}`, `index.html:2035`, `:2049`) — the opposite of blinded. The inbox and review form live at `index.html:2021-2068`; the review POST sends only `{pos_claim,neg_claim,verdict,rationale,confidence,qualifier,next_check}` (`:2065`) with no reviewer/batch/side. `/inbox/dossier` (`app.py:640`) hands back `positive`/`negative` explicitly.

**Design (reuse the modal; extend, don't rebuild).**
- **Reviewer identity:** a one-time pseudonymous `reviewer_id` prompt stored in `localStorage` (`persona.reviewer_id`), shown/editable in the Review-surface header. No auth server (YAGNI); pseudonymity is the requirement, not authentication.
- **Batch picker:** Review surface lists frozen batches (`GET /inbox/batches`) with per-batch progress (your assignments done / total, n reviewers). Selecting a batch renders its **assignments** in the existing `irows` inbox list (`:2024`).
- **Blinded dossier:** new `GET /inbox/batch/{batch_id}/assignment?assignment_id=…` returns the two evidence packets as neutral **Side A / Side B in the frozen `side_order`, with `effect_sign` and the pos/neg labels stripped**. A new `dossierSideBlinded(pkt,'A'|'B')` renders sources/quotes/qualifier-gaps only. The review `<select>` keeps the four verdicts (`extraction_error, true_refutation, context_divergence, insufficient_evidence`, `:2053`) — those are sign-agnostic, so blinding is preserved.
- **Submit:** `recordConflictReview` (`:2062`) adds `reviewer_id, batch_id, assignment_id, side_order` to the payload; a 409 (duplicate) or 422 (blind mismatch) shows the server `detail` via the existing `toast(data.detail…)` path (`:2067`).

**Data flow.** batch pick → blinded assignment fetch → label → POST `/inbox/review` (extended) → server re-validates side_order vs frozen bundle → append.

**Epistemic guardrail.** The UI must never display the stored sign or the pos/neg role during blinded collection; the un-blinded `contraEvidence` dossier (`:2041`) stays available **only** on the non-batch inbox (exploration), never inside a batch assignment. "Belief unchanged" copy (`:2058`, `:2065`) is retained.

**Required experiment.** *Trivial* UI — proven by the browser smoke (§5), not a study.

**Acceptance + runnable check.** `PERSONA_WORKERS=0` browser smoke (extend `tests/ui_research_smoke.cjs` or a sibling): open a frozen batch, assert a rendered assignment shows "Side A/Side B" and contains **no** `+`/`−`/"positive"/"negative" role text, submit a label with a `reviewer_id`, and confirm the ledger gained one record via `verify_conflict_reviews`. **Effort:** M. **Deps:** F11.2, F11.6.

---

### F11.6 — Batch endpoints (Lane 4, new routes only)

**Problem & evidence.** `app.py` inbox routes (`:619` list, `:640` dossier, `:685` review, `:717` resolve, `:723` investigate) have no batch/blinding/agreement surface.

**Design (new routes, additive).**
- `GET  /api/persona/{pid}/inbox/batches` → `[{batch_id, n_items, n_reviewers, complete, frozen_at}]` (from `load_review_batch` + `batch_agreement`).
- `POST /api/persona/{pid}/inbox/batch/freeze` `{batch_id, conflict_pairs, seed, strata?}` → curator-only freeze via `freeze_review_batch`. Guard: refuse if batch already frozen (409).
- `GET  /api/persona/{pid}/inbox/batch/{batch_id}/assignment?assignment_id=…` → **blinded** A/B packet (strips sign/role; orders by frozen `side_order`).
- `POST /api/persona/{pid}/inbox/review` — **extend existing** (`:685`): read `reviewer_id, batch_id, assignment_id, side_order` from payload, pass to `append_conflict_review`; map `DuplicateReviewError`→409, `BlindMismatchError`→422 (the existing `LedgerIntegrityError`→500 / `ValueError`→422 handling at `:708-711` stays).
- `GET  /api/persona/{pid}/inbox/batch/{batch_id}/agreement` → `batch_agreement(...)`; **the UI shows numbers only when `n_reviewers ≥ 2`** (else "awaiting a second independent reviewer").

**Epistemic guardrail.** `/inbox/resolve` stays the hard "no anchoring until RQ-E02" wall (`app.py:717-720`) — unchanged. Agreement/gold endpoints are read/label-only; none mutate a belief.

**Required experiment.** *Trivial* (endpoint wiring; covered by F11.5 smoke + F11.7 unit tests).

**Acceptance + runnable check.** `test_review_endpoint_requires_reviewer_and_batch`: POST `/inbox/review` without `reviewer_id` → 422; a duplicate → 409. **Effort:** M. **Deps:** F11.2, F11.3.

---

### F11.7 — Agreement + adjudicated gold (never synthesized)

**Problem & evidence.** RQ-E02 needs measured inter-rater agreement and a human gold file before the typing experiment (`RESEARCH_QUALITY_PROGRAM.md:152`; handoff §11 "compute agreement and an adjudicated gold file", `:269`). None exists.

**Design.** `batch_agreement` computes percent agreement over all items with ≥2 labels and **Cohen's κ when exactly two reviewers** (Cohen 1960; Landis & Koch 1977 for interpreting κ bands), returning `cohens_kappa=None` otherwise. `adjudicate_gold` fills gold from unanimous items; disagreements are filled **only** from an explicit `adjudications` map (a human tie-breaker's verdict + rationale + adjudicator_id) and are otherwise left `status:"unresolved"`. Both are pure and deterministic — **no model anywhere**.

> `# ponytail: Cohen's κ for the 2-rater case + percent agreement always. Krippendorff's alpha (handles >2 raters & missing labels) is the upgrade path when batches exceed two reviewers — not built until a third rater exists.`

**Epistemic guardrail (the load-bearing one).** `adjudicate_gold` **must refuse to invent a label**: no majority-of-two auto-resolution beyond true unanimity, no model fallback. Gold provenance is stamped `HUMAN_CONFIRMED`; `n_reviewers < 2` ⇒ `complete=False` and RQ-E02 refuses to run (F11.8). This is the `CLAUDE.md` "NEVER synthesize human labels" invariant made mechanical.

**Required experiment.** *Trivial* — κ and unanimity are deterministic; verified by a fixture with a hand-computed κ.

**Acceptance + runnable check.** `test_agreement_and_gold_never_synthesized`: a 4-item fixture (3 unanimous, 1 split) → `cohens_kappa` matches the hand-computed value (±1e-9), `adjudicate_gold` with no `adjudications` yields 3 gold + 1 `unresolved`; supplying the adjudication resolves the 4th. `n_reviewers==1` ⇒ `complete is False`, `cohens_kappa is None`. **Effort:** S. **Deps:** F11.2.

---

### F11.8 — RQ-E02 experiment (the gate)

**Problem & evidence.** The registered open experiment (PRD-00 §6 RQ-E02; `RESEARCH_QUALITY_PROGRAM.md:149-156`): does typed contradiction beat sign-collision at escalation precision, ≥0.85 required before autonomous escalation.

**Design.** `experiments/exp_rq_e02_contradiction_typing.py`:
- **Input:** the adjudicated `gold/<batch_id>.json` (F11.7) over the frozen 62-pair snapshot (SHA `b967cf4bfe6c24733a76cf7c69703d6ade9f1c2f48f4474e957fd98c6bbd68a9`, `RESEARCH_QUALITY_PROGRAM.md:152`).
- **Arms:** (a) **sign collision** — every candidate escalates (the current `candidate_conflicts` behavior, `kg.py:229`); (b) **single verifier** — one model typing pass; (c) **two independent verifiers + deterministic exact-span gate** — reuse the exact-span validator from `reading/extract.py` (RQ-E01a, `CONTINUATION_HANDOFF.md:48-54`) as the deterministic gate.
- **Metrics (against gold):** precision at escalation, macro-F1, false-escalation rate, abstention, cost, latency, calibration (`RESEARCH_QUALITY_PROGRAM.md:154`).
- **Seeds/CI:** ≥20 seeded stratified bootstraps over the gold set for mean ± 95% CI on precision (per `CLAUDE.md` §2.4).
- **Gate:** **precision ≥ 0.85** (lower CI bound reported); below → product stays `candidate conflict / unverified` only, autonomous escalation stays OFF (`RESEARCH_QUALITY_PROGRAM.md:155`).

**Hypothesis + metric + gate.** *Two-verifier+exact-span achieves escalation precision ≥ 0.85 on the human gold, and > sign-collision precision, at bounded cost.* Gate = 0.85 precision (95% CI lower bound) AND precision(arm c) > precision(arm a).

**Epistemic guardrail (STOP condition).** The script **asserts gold provenance is `HUMAN_CONFIRMED` and `n_reviewers ≥ 2` and `complete`** before running; otherwise it exits with "insufficient real labels — bundle+UI shipped, RQ-E02 pending" and writes **no** result. Model verifier passes are provisional proxies scored *against* human gold, never a substitute for it. Do not celebrate a confirming number without re-running seeds (`CLAUDE.md` §1).

**Required experiment.** This *is* RQ-E02.

**Acceptance + runnable check.** `python experiments/exp_rq_e02_contradiction_typing.py --batch e02-pilot` writes `results/rq_e02_contradiction_typing.json` with per-arm precision ± CI and a `gate_passed` bool; a `--self-test` mode runs the three arms on a tiny synthetic-but-labeled fixture (clearly marked non-gold) to prove the harness math, and **refuses** to emit a real result when gold is incomplete. **Effort:** L. **Deps:** F11.7 + real human labels.

---

## 4. Sequencing

Interface-first, then fill, then (only with real reviewers) run.

1. **F11.1** cross-process lock — unblocks any concurrent append; smallest, highest-safety. 
2. **F11.2 + F11.4** record schema + frozen blinded bundle (freeze/load) — the acquisition substrate. 
3. **F11.3** duplicate guard (folds into F11.2's append path). 
4. **F11.6** batch endpoints, then **F11.5** blinded UI — reviewers can now label. **← Ship-and-stop line if no real reviewers.** 
5. **F11.7** agreement + gold — after ≥2 real reviewers finish a batch. 
6. **F11.8** RQ-E02 — only once `adjudicate_gold` reports `complete` & `HUMAN_CONFIRMED`. 

**Milestone-0 stub (parallelism):** land CCP-11a signatures + empty/typed returns in `conflict_reviews.py` first so Lane 4 builds endpoints/UI against them from hour 1.

---

## 5. Test plan

| Check | Proves | Feature |
|---|---|---|
| `test_concurrent_appends_preserve_chain` (N≥8 procs) | cross-process lock keeps the hash chain valid | F11.1 |
| `test_frozen_batch_side_order_is_deterministic_and_enforced` | seeded side_order reproducible; blind mismatch + bundle tamper rejected | F11.2/F11.4 |
| `test_duplicate_review_rejected_same_reviewer_allowed_other` | dedupe per (reviewer,conflict,batch); cross-reviewer allowed | F11.3 |
| `test_review_endpoint_requires_reviewer_and_batch` | endpoint enforces identity/batch; 409/422 mapping | F11.6 |
| `test_agreement_and_gold_never_synthesized` | κ correct; gold never invented; n<2 ⇒ incomplete | F11.7 |
| `exp_rq_e02_contradiction_typing.py --self-test` | harness math on a labeled fixture; refuses incomplete gold | F11.8 |
| `PERSONA_WORKERS=0` browser smoke | blinded A/B render (no sign/role leak); submit lands one real record | F11.5 |
| existing `python -m pytest -q` (20 tests) + `verify_conflict_reviews(ops)` | no regression to the append-only ledger | all |

All existing ledger invariants (canonical JSON, per-record hash, chain, schema — `conflict_reviews.py:132-157`) must still hold after the schema extension.

## 6. Open questions

1. **CCP-11a ack** — extending `append_conflict_review` and adding batch functions touches the seam Lane 4 calls at `app.py:698`/`:627`. Needs Lane-4 ack in the HANDOFF dispatch log before landing. *(Blocks Lane 4 endpoint/UI work if the signature shifts.)*
2. **Batch curation authority** — who selects the 20 stratified pairs and calls `/inbox/batch/freeze`? Proposed: curator-only, out-of-band (not a reviewer action). Needs a one-line policy; does it require an auth gate beyond pseudonymity for the *freeze* route specifically? *(Affects F11.6 route guarding.)*
3. **Reviewer recruitment** — RQ-E02 (F11.8) cannot run without ≥2 real independent reviewers. If none are available, the deliverable is the frozen bundle + UI and a documented STOP — confirm this is acceptable for the current slice (it matches handoff §11).
4. **κ vs Krippendorff's alpha** — spec ships Cohen's κ (2 raters) + percent agreement. If a batch will have >2 raters or missing labels, α is the correct metric; flag whether a third rater is planned before F11.7 lands. *(Non-blocking; upgrade path noted.)*
5. **Reuse of exact-span gate** — arm (c) reuses `reading/extract.py`'s span validator (Lane-1-owned file). Confirm read-only reuse in the experiment is fine, or expose it via a small helper. *(Blocks F11.8 arm c if the import boundary is contested.)*
