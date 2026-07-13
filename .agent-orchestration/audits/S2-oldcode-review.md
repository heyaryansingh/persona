# S2 — old-code review log (frozen-contract core audits)

Append-only. Deep reads of pre-existing code against the frozen invariants (HANDOFF).

## Belief-store anchor write-policy (`kg.py::add_claim`, `membrane.py`) — 2026-07-13 → SOUND
Frozen invariant: "READ/INFERRED cannot move a HUMAN_CONFIRMED/TESTED anchor beyond `resist`; only human
sign-off moves an anchor." Traced every write path:
- **No un-anchor on re-observation:** `c.anchored=false` is under `ON CREATE SET` only → re-observing an
  anchored claim leaves `anchored=true` intact. (This was my first suspicion; it's guarded.)
- **Confidence pinned:** `c.confidence = CASE WHEN c.anchored THEN c.confidence ELSE mconf END` — anchored
  belief's confidence never moves; support/independence counts still update. (Impl is a **binary pin**,
  stricter than the contract's "beyond resist" — safer, not a bug. INFO only.)
- **Sign immutable:** `claim_id = sha1(subj|obj|sign)` → a flipped sign is a *different* node; add_claim can't
  mutate an anchored claim's sign.
- **Provenance preserved:** set `ON CREATE` / by `anchor()`; re-observation doesn't overwrite it.
- **Extraction correction refuses anchors:** `membrane.correct_extraction_sign` bails if `old.anchored`.
**Behaviour green:** `test_membrane_poisoning.py` + `test_integrity_boundaries.py` + `test_paper_graph.py`
= **15 passed**. The poisoning-oracle test (CLAUDE.md §4) confirms sign/confidence pinned under attack.
**Verdict:** the system's most critical invariant holds by code AND test. No action.

## Swarm-reader purity (`reading/reader.py`, `reading/batch.py`) — 2026-07-13 → SOUND
Frozen invariant: "swarm READS, never writes to the self. Only the membrane commits."
- **Self access is read-only:** `_objective_anchor()` calls `selfmind.interests()`; `selfmind.allowed_field_ids()`
  — both read accessors, used only to steer the relevance filter. No reader writes `self_dir`/`selfmind`.
- **All durable writes route to `sources/`:** `reader.py`/`batch.py` write `clean.md`, `meta.json`,
  `claims.jsonl`, `claims_rejected.jsonl` under `src_dir` (a source dir) — staged for the membrane's
  `harvest`, not committed to the belief-store directly. The membrane remains the sole commit path.
- **`_relevance_filter` fails OPEN** (keeps all works) with no anchor / no embedding — documented; a
  blank-slate or embedding hiccup can't silently stop reading. Bounded downstream by the membrane. OK.
**Verdict:** reader/self separation holds. No action.

## Escalation / human-gate (`kg.py`, `agents/discover.py`, `app.py /inbox/*`) — 2026-07-13 → SOUND
Frozen invariant: "Ignition is human-gated (contradiction FP ~30%); anchoring needs sign-off; direct
anchor resolution disabled until RQ-E02."
- **No autonomous anchoring:** the *only* caller of `.anchor(` is inside `human_resolve()` itself; and
  `human_resolve()` has **no caller** in the package. Not dead code — it's the gate: `POST /inbox/resolve`
  explicitly returns *"candidate conflicts cannot anchor beliefs until RQ-E02 passes its precision gate,"*
  and `POST /inbox/review` is *"append-only … they never anchor now."* Machinery built+tested, wiring
  intentionally withheld. Matches the Review UI ("anchoring paused") and HANDOFF.
- **Contradictions flagged, not resolved:** `kg.contradictions()` returns `needs_human_review:True`.
- **Experimental leads escalate:** `discover.py` tests only the top *computable* lead, emits an `escalate`
  "needs a human" event for physical ones (human-as-resolver division of labor).
**Verdict:** human-gate holds; anchoring honestly gated behind RQ-E02. No action.

---
### Session assurance summary (3 frozen-contract cores verified SOUND)
anchor write-policy · swarm-reader purity · escalation/human-gate — all hold by code + tests. No defects
in the durable-belief core. Remaining audit surface is thinning; build is human-blocked (S5/S6 parked).
