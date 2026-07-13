# PRD-29 — Research-frontier map artifact

> Owner: implementer lanes **3+4** · Status: DRAFT-for-implementation · Autonomy: **Balanced** · Depends on: **FC-4** (`engine.value_queue`, Lane 3 — this lane's own), **PRD-03 F3.4** (`analysis/trajectory.py` `topic_trajectory`, Lane 3 — must land first), `synthesis/fieldmap.build` (Lane 3, existing), **FC-3** (`kg.provenance_breakdown`, Lane 2)
>
> Backlog: **#114**. New contract: **FC-21**. Optional experiment: **RQ-E45**. Read PRD-00 §2 (epistemic discipline), §4 (FC registry), §8 (reconciliation governs) before coding.

---

## 0. Summary + capability unlocked

A PI cannot subscribe to Persona today. The mind computes trajectory dynamics (PRD-03 F3.4), a value-of-information queue (`analysis/value_queue.py`, FC-4), and a live field map (`synthesis/fieldmap.py`) — but each is a separate screen you must go open, and none composes into the one thing an "always-on colleague" is *for*: a standing, periodically-refreshed **one-page state of the frontier** per interest that answers, at a glance, *what just moved, what's contested, and what's the single highest-leverage open question* — and that a PI can bookmark, export, and check back on like a saved search. This PRD adds `analysis/frontier.py`: a **pure read** (`frontier(topic)`, FC-21) that synthesizes the three existing surfaces into that structured one-pager, a deterministic markdown/PDF **standing artifact** written to a stable per-interest path (the subscribable deliverable), and a Lane-4 surface + export route that renders it. The capability unlocked is the program's headline product promise made concrete — *the deliverable a PI subscribes to* — with zero new epistemics: **every cell is server-derived from real belief-graph state and carries the validation label of its own source** (velocity = deterministic; VoI = RQ-E17-candidate; contradiction = RQ-E02-candidate; provenance mix = FC-3), the artifact renders an explicit **"insufficient data"** state until enough evidence accrues, and it invents **no new metric** — it is a projection, not a scorer. RQ-E45 (optional) checks the *composition* is face-valid against an expert's read of the same subfield; the artifact ships advisory regardless, because it manufactures no confidence its inputs don't already carry.

---

## 1. File ownership (disjoint)

| File | Lane | New/Edit | Notes |
|---|---|---|---|
| `persona/analysis/frontier.py` | **3** | **New** | FC-21 provider: `frontier`, `frontier_all`, `frontier_markdown`, `write_frontier`. Pure/offline read + deterministic render + stable-path write. |
| `persona/analysis/engine.py` | **3** | **Edit — add re-export only** | Add `from .frontier import frontier` to the FC-4 facade so consumers import `engine.frontier` beside `engine.value_queue` (one line, mirrors the existing `dependency_graph`/`value_queue` re-exports). |
| `persona/api/app.py` | **4** | **Edit — NEW routes only** | `GET /frontier`, `GET /frontier/all`, `GET /frontier/export` (§3 F29.3). Do not touch existing route bodies. |
| `persona/api/static/index.html` | **4** | **Edit — NEW surface/JS only** | `surf-frontier` + `openFrontier()`; register in the spine/subtab map. Adds no client-computed metric. |

**Boundary files another lane touches — decoupled by contract, NOT edited here:**

- `persona/analysis/trajectory.py` — **Lane 3, created by PRD-03 F3.4** (`trajectory(claim_id)`, `topic_trajectory(topic)`). `frontier.py` *imports and calls* `topic_trajectory`; it does not create or edit trajectory.py. Same lane, so a direct import — no FC. **Hard sequencing dependency:** until F3.4 lands, the "moved" cell degrades to `insufficient` (see F29.1 guardrail). Flagged in §6 O-1.
- `persona/synthesis/fieldmap.py` — **Lane 3, existing.** `frontier.py` calls `fieldmap.build(kg, notes_dir)` read-only for the contested cell. No edit.
- `persona/memory/kg.py` — **Lane 2 owns.** This lane only *calls* `kg.provenance_breakdown()` (FC-3), `kg.claims_in`, `kg.contradictions`, `kg.citation_support_ratio` (all existing reads). Never edited; a wrong call shape → CONTRACT CHANGE PROPOSAL.
- `persona/daemon/supervisor.py`, `persona/daemon/worker.py` — **Lane 1 owns.** The *periodic-refresh* cadence tick is an **advisory hook (CCP-29a, →Lane 1)**, non-blocking; the artifact is fully usable via the synchronous export route without it (see §2 and §4). This lane does not edit the daemon.

**The FC that decouples 3 from 4:** FC-21. Lane 3 provides `frontier()` and the standing-artifact writer; Lane 4 transports + renders. Lane 4 builds against the FC-21 stub (typed empty `{sufficient:false,...}`) from hour 1 and wires the real payload when F29.1 lands.

---

## 2. Frozen contracts

### PROVIDES — FC-21 (Lane 3), new `persona/analysis/frontier.py`

```
frontier.frontier(topic: str | None = None, *, kg=None, history=None,
                  max_moved: int = 6, max_contested: int = 8) -> {
    "topic": str, "slug": str, "generated_at": str,          # ISO-8601 UTC
    "sufficient": bool, "insufficient_reason": str | None,
    "provenance": "READ",                                     # deterministic projection (INFERRED iff a model narrative is attached; not in v1)
    "moved": [ {claim_id, statement, velocity: float, acceleration: float,
                phase: 'rising'|'plateau'|'declining'|'abandoned',
                independence_drift: float, provenance, label: 'deterministic'} ],
    "contested": [ {subject, object, pos: int, neg: int, pos_claim, neg_claim,
                    both_independent: bool, label: 'candidate-RQ-E02'} ],
    "frontier_question": {question, resolves_claim_id, voi: float,
                          cost_tier: 'public_data'|'cheap_assay'|'expensive',
                          dataset_available: bool, de_risks_n: int, run_action: str,
                          label: 'candidate-RQ-E17'} | None,
    "value_queue_top": [ ...same shape as frontier_question... ],   # next few, ≤5
    "provenance_mix": {READ:int, INFERRED:int, HUMAN_CONFIRMED:int, TESTED:int},
    "counts": {n_claims:int, n_sources:int, n_subtopics:int, n_contested:int},
}
frontier.frontier_all(*, kg=None, history=None) -> [ frontier(i) for (i, _w) in selfmind.interests() ]
frontier.frontier_markdown(front: dict) -> str            # deterministic one-page markdown, no model
frontier.write_frontier(topic: str | None = None, *, deliverables_dir=None,
                        kg=None, history=None) -> {path:str, slug:str, sufficient:bool, sha256:str}
```

Read-only: `frontier`/`frontier_all`/`frontier_markdown` spawn no model, make no network call, mutate no KG. `write_frontier` writes only to the deliverables dir (+ an append-only history sidecar) — never the KG.

### CONSUMES

- **FC-4** (Lane 3, own) — `engine.value_queue(topic) -> [...]` (via `analysis/value_queue.py`, already built).
- **PRD-03 F3.4** (Lane 3, own) — `trajectory.topic_trajectory(topic) -> [{claim_id, velocity, acceleration, phase, independence_drift, ...}]`. **Not yet built** — see §6 O-1.
- **Existing** — `synthesis.fieldmap.build(kg, notes_dir)`; `kg.provenance_breakdown()` (FC-3, Lane 2), `kg.claims_in`, `kg.contradictions`, `kg.citation_support_ratio`; `selfmind.interests()`; `deliverables.document.slug_for` / `compile_source` (render/PDF, no edit).

### CONTRACT CHANGE PROPOSAL — CCP-29a (→ Lane 1, advisory, non-blocking)

Add a `frontier` refresh to the daemon's `OUTPUT_AGENDA` cadence (`supervisor.py`) that calls `analysis.frontier.write_frontier(i)` for each declared interest on a low-frequency tick — **offline, $0, no budget gate** (mirrors the ratified CCP-27a retraction-watch scheduler tick). Optional `frontier` worker task type (`worker.py`, append-only handler registry) for unattended runs. **Ships API-/manual-enqueueable until Lane 1 lands it**; the export route (F29.3) writes the artifact synchronously without the queue, so the subscribable deliverable works day 1. No FC-21 signature change.

*No other contract change.* FC-21 consumes only existing signatures + one same-lane not-yet-built module (F3.4).

---

## 3. Features

---

### F29.1 — `frontier()` synthesizer + insufficient-data gate (`analysis/frontier.py`)

**Problem & evidence.** The three inputs exist but never compose. `analysis/value_queue.py:50` ranks next-experiments (`value_queue(topic)`), `synthesis/fieldmap.py:25` builds subtopics-with-contradictions (`build(kg, notes_dir)`), and PRD-03 F3.4 specs `trajectory.topic_trajectory(topic)` for velocity/phase — but a user must open three surfaces and hold the join in their head. Backlog #114 (`docs/prd/IDEAS_BACKLOG.md:232`): *"Synthesizes trajectory + value-queue + fieldmap into the 'always-on colleague' deliverable a PI would subscribe to."* The existing `agents/knowledge.topic_digest` (`knowledge.py:69`) is the closest precedent — it already joins claims + contradictions + `history.series` evolution into a bundle — but it is a per-query briefing, not a standing per-interest frontier, and it has no VoI/velocity ranking. Research backing: value-of-information decision analysis (Howard 1966) for the "highest-leverage question" cell (already the basis of `value_queue.py`); finite-difference velocity/phase (PRD-03 F3.4) for "what moved."

**Design.**
- New `persona/analysis/frontier.py`. Pure read; no model, no network, no KG write.
- `frontier(topic=None, *, kg=None, history=None, max_moved=6, max_contested=8) -> dict` (FC-21 shape verbatim). Data flow:
  - **kg / history** default to the current persona (`from ..memory.membrane import get_kg`; `from ..context import get_persona` → `get_persona().history`), injectable for tests (same pattern as `value_queue.value_queue`, `dependency.dependency_graph`).
  - **moved** = `trajectory.topic_trajectory(topic)`, filtered to `phase in {'rising','declining','abandoned'}` OR `abs(velocity) > 0`, sorted by `abs(velocity)` desc, top `max_moved`. Each row copies `provenance` from `kg.provenance(claim_id)` and carries `label:'deterministic'`. **If `analysis.trajectory` is not importable (F3.4 not yet landed), `moved=[]` and this contributes an `insufficient_reason` token** (graceful degrade — never a crash).
  - **contested** = from `fieldmap.build(kg, get_persona().paths.notes_dir)`, flatten every subtopic's `contradictions`, keep the topic-matching ones, mark `both_independent = pos>=2 and neg>=2` (the RQ-E02-gated escalation threshold, matching F3.11), sort by `pos+neg` desc, top `max_contested`. `label:'candidate-RQ-E02'`.
  - **frontier_question** = `engine.value_queue(topic)[0]` (highest VoI÷cost); **value_queue_top** = `[:5]`. Copy the row verbatim + attach `label:'candidate-RQ-E17'`. `None` when the queue is empty.
  - **provenance_mix** = `kg.provenance_breakdown()` projected to the four counts (FC-3).
  - **counts** from the assembled cells + `claims_in`.
  - **sufficient / insufficient_reason** (the display gate): `sufficient = counts.n_claims >= MIN_CLAIMS (=5) AND (len(moved) > 0 OR frontier_question is not None)`. Otherwise `sufficient=False` and `insufficient_reason` names the missing input(s) (e.g. `"only 2 claims on this interest — need ≥5"`, `"no trajectory history yet"`). MIN_CLAIMS/max_* are display params (reversible, trivial), not scientific thresholds.
- `frontier_all()` maps `frontier` over `selfmind.interests()` (the per-interest standing set).

**Epistemic guardrails.** **No new metric — this is the whole point.** `frontier()` computes nothing scientific of its own: `velocity` comes from F3.4 (deterministic finite-difference), `voi` from `value_queue.py` (RQ-E17-candidate, self-labelled), `both_independent` from the RQ-E02 threshold, `provenance_mix` from FC-3. **Every cell carries the `label`/`provenance` of its source verbatim** — the "server derives every scientific status; NO client-invented metric" rule (PRD-00 §2) is satisfied structurally: the client renders `label` as-is and may not recompute. Honest-uncertainty: the `insufficient` state fires until real evidence accrues, so a blank-slate interest reads *"insufficient data"*, never a fabricated frontier. No belief mutation: `frontier` is a projection; it inherits F3.4's guardrail that an `abandoned`/`declining` phase is a *hypothesis routed to the value queue*, never an auto belief-downgrade — `frontier` only *displays* the phase, it calls no mutation path.

**Required experiment.** **RQ-E45 (optional, face-validity).** Hypothesis: *the auto-composed frontier one-pager (top-3 `moved`, the `contested` set, and `frontier_question`) agrees with a domain expert's independent read of the same subfield above chance.* Metric/gate: on ≥5 seeded subfields, mean expert agreement — top-3 `moved` overlap (Jaccard) **and** a Likert ≥4/5 that "this is the field's live frontier" — clears a pre-registered bar (proposed: Jaccard ≥0.4 on moved, ≥70% of `frontier_question`s rated "worth asking"), reported with a bootstrap CI over the expert panel. **This gates presentation authority, NOT shipping:** because `frontier()` invents no metric (each cell is already gated/labelled by its own RQ), the artifact ships **advisory** regardless; RQ-E45 only decides whether the summary may be labelled "audited frontier read" vs "auto-generated, unaudited composition." Optional/expert-panel like RQ-E27/E42 (BUILD_PLAN H3.3 face-validity) — no ≥20 synthetic seeds mandated, since the composition is deterministic; the variance measured is the expert panel's. Script `experiments/exp_rq_e45_frontier_facevalidity.py`; results `results/FINDINGS.md#RQ-E45`. Per PRD-00 §2 "do not gold-plate the process," a deterministic projection of already-gated inputs does not warrant a new ≥20-seed metric experiment — RQ-E45 is the right-sized check.

**Acceptance criteria.** (a) `frontier(topic)` returns all FC-21 top-level keys; each `moved` row has a `provenance` + `label:'deterministic'`, each `contested` a `label:'candidate-RQ-E02'`, each queue row a `label:'candidate-RQ-E17'`. (b) A persona with <5 claims on the topic returns `sufficient=False` and a non-empty `insufficient_reason`, and never raises. (c) With `analysis.trajectory` absent, `moved=[]` and no exception (import-guarded). (d) No `kg.*` write method is called (spy asserts zero writes). Runnable check: `persona/tests/test_frontier.py::test_frontier_shape_and_insufficient` (fixture KG + fixture history + a KG-write spy; asserts the label set, the insufficient path, the trajectory-absent degrade, and zero writes).

**Effort** M · **Deps** PRD-03 F3.4 (`topic_trajectory`), FC-4 `value_queue` (built), `fieldmap.build` (built), FC-3 `provenance_breakdown` (Lane 2).

---

### F29.2 — Standing artifact: deterministic render + stable subscribable export (`analysis/frontier.py`)

**Problem & evidence.** "Subscribe" means the frontier must exist as a **stable, refreshable object** a PI bookmarks, not just an ephemeral API response. The repo already has the two pieces: `deliverables/document.py` compiles any markdown source to PDF deterministically offline (`compile_source`, `document.py:304`; `slug_for`, `document.py:313`), and `synthesizer.py`'s note-history discipline (PRD-03 F3.11) shows the append-only sidecar pattern for versioned regeneration. We reuse both — no new render engine, no versioning framework. Backlog #114 calls it a *"publishable as a standing shareable artifact."*

**Design.**
- `frontier_markdown(front: dict) -> str` — deterministic one-page markdown from the F29.1 dict. Sections: title (`# Frontier — <topic>` + `generated_at` + provenance label), **What just moved** (each `moved` row: statement, ↑/↓/– by phase, `velocity`, provenance badge), **What's contested** (`contested` rows: `subject ⇄ object`, `pos` vs `neg` labs, RQ-E02-candidate note), **Highest-leverage open question** (`frontier_question`: the question, `voi`, `cost_tier`, `run_action`, dataset-available flag, RQ-E17-candidate note), a small **provenance mix** footer (READ/INFERRED/HUMAN_CONFIRMED/TESTED counts) and the `insufficient_reason` banner when `sufficient=False`. Pure string assembly — **no model** (an optional model narrative is explicitly deferred; see §6 O-2). Labels are rendered verbatim from the dict, so the markdown cannot present a number more confidently than its source.
- `write_frontier(topic=None, *, deliverables_dir=None, kg=None, history=None) -> dict` — resolve `deliverables_dir` (default `get_persona().paths.deliverables_dir`), compute `slug = document.slug_for(topic or "all-interests")`, render `frontier_markdown(frontier(topic, kg=kg, history=history))`, and write to a **stable path** `deliverables/frontier-<slug>.md` (overwritten each refresh so the subscribe URL never changes). Before overwrite, if the file exists, append its prior body + timestamp to an append-only sidecar `deliverables/.history/frontier-<slug>.jsonl` (the F3.11 note-diff discipline — the "how the frontier evolved" trail). Return `{path, slug, sufficient, sha256}` (sha256 of the new body, for tamper-evidence / change detection). **ponytail: stdlib only — `slug_for` + `document`'s existing pipeline + a jsonl sidecar; no new dep, no scheduler here.**
- PDF export is on demand via the Lane-4 route (F29.3) calling the existing `document.compile_source` on the written markdown — not written eagerly (a PI reads markdown in the UI; PDF is a click).

**Epistemic guardrails.** Append-only history sidecar never mutates prior frontier versions (reproducibility, CLAUDE.md §4) — the standing artifact has a defensible change record. Stable path = a real subscribe target (bookmark once, always current) without a fabricated feed. The `sha256` lets a subscriber detect a genuine change vs a no-op refresh (motion only on real state change, CLAUDE.md §5). Render is model-free, so the artifact cannot drift from the structured cells it claims to summarize.

**Required experiment.** Trivial — deterministic render + file write + `difflib`-free append. No RQ. (Face-validity of the *content* is RQ-E45 under F29.1; this feature only serializes it.)

**Acceptance criteria.** (a) `frontier_markdown(front)` contains the three section headers and, when `sufficient=False`, the insufficient banner. (b) `write_frontier` twice on a changed frontier writes the stable `frontier-<slug>.md` once and appends exactly one prior-version row to `.history/frontier-<slug>.jsonl` on the second call; the returned `sha256` matches the on-disk body. (c) The written markdown compiles via `document.compile_source` (offline). Runnable check: `persona/tests/test_frontier_artifact.py::test_write_is_stable_and_versioned` (temp deliverables dir, fixture frontier, asserts stable filename + one history row + sha256 match).

**Effort** S · **Deps** F29.1, `deliverables.document` (existing, no edit).

---

### F29.3 — Lane-4 render: routes + `surf-frontier` surface + export (`api/app.py`, `static/index.html`)

**Problem & evidence.** FC-21's data has no transport or screen. The SPA already renders sibling read-only surfaces (Map/Fieldmap, topic digest) and has the deliverable-download plumbing (`/deliverable/bundle`, `app.py:1200`; `/deliver`, `app.py:763`). "Every screen answers a question a real researcher asks" (CLAUDE.md §5) — this surface answers *"what is the live frontier of my field right now, and can I take it with me?"*

**Design.**
- New routes in `app.py` (NEW routes only; thin pass-throughs, Lane 3 owns the computation):
  ```python
  @app.get("/api/persona/{pid}/frontier")
  def frontier_read(pid: str, topic: str = ""):
      with context.use(_p(pid)):
          from ..analysis import engine
          return engine.frontier(topic or None)

  @app.get("/api/persona/{pid}/frontier/all")
  def frontier_all(pid: str):
      with context.use(_p(pid)):
          from ..analysis.frontier import frontier_all as _fa
          return {"frontiers": _fa()}

  @app.get("/api/persona/{pid}/frontier/export")
  def frontier_export(pid: str, topic: str = "", fmt: str = "md"):
      """Write/refresh the standing artifact; return md text or a compiled PDF (offline)."""
      p = _p(pid)
      with context.use(p):
          from ..analysis.frontier import write_frontier
          rec = write_frontier(topic or None)
      if fmt == "pdf":
          # reuse the existing document compile → deliverables/ pipeline (app.py:1225 pattern)
          ...  # compile rec['path'] via deliverables.document.compile_source, StreamingResponse(application/pdf)
      return {"ok": True, **rec, "markdown": Path(rec["path"]).read_text(encoding="utf-8")}
  ```
- New surface `surf-frontier` + `openFrontier()` in `index.html`, registered as a **Map subtab** ("Frontier") or a spine destination (Open Q, mirrors PRD-04 Q1). `openFrontier()` → `GET /frontier?topic=<selected interest>` → render three columns (**Moved / Contested / Highest-leverage question**) with, per cell, the server `label` shown verbatim as a badge (deterministic / candidate-RQ-E02 / candidate-RQ-E17) and provenance colour+text (never colour alone — `SCIENTIFIC_WORKBENCH_SPEC` WCAG rule). An interest selector drives `topic`; an **"Export / Subscribe"** button hits `/frontier/export?fmt=md` (copyable stable link) and `fmt=pdf` (download). When `sufficient=false`, render the `insufficient_reason` banner instead of empty columns. Motion only on topic/selection change; honour `prefers-reduced-motion`.
- No client arithmetic on any metric field: the surface renders `velocity`, `voi`, `pos/neg`, `provenance_mix` exactly as returned.

**Epistemic guardrails.** Pure transport/render — every number originates from FC-21 (server), including its validation `label`; the client may not recompute or relabel. The export is a projection of the append-only artifact; no admit/anchor path exists on this surface. `insufficient` renders honestly rather than a padded frontier.

**Required experiment.** Trivial — thin routes + render over a validated FC. No RQ.

**Acceptance criteria.** (a) `GET /frontier?topic=<t>` returns the FC-21 keys; `GET /frontier/all` returns `{frontiers:[...]}`. (b) `GET /frontier/export?fmt=md` returns `{ok, path, slug, sufficient, sha256, markdown}` and the file exists on disk at the stable path. (c) The surface shows the three columns with per-cell label badges, and shows the insufficient banner for a thin interest. Runnable checks: `tests/test_frontier_api.py::test_frontier_routes_shape` (asserts route payloads incl. export) and a `tests/ui_*_smoke.cjs` step asserting the three columns + a label badge render (mirrors `ui_research_smoke.cjs`).

**Effort** M · **Deps** FC-21 (F29.1/F29.2), existing `context.use`/`_p`, `deliverables.document`.

---

## 4. Sequencing

**Milestone 0 (hour 1 — unblock the other track):**
1. Lane 3: land `analysis/frontier.py` FC-21 **stubs** — `frontier(topic)` returns typed `{sufficient:False, insufficient_reason:"stub", moved:[], contested:[], frontier_question:None, value_queue_top:[], provenance_mix:{...0}, counts:{...0}}`; `frontier_all`→`[]`; `frontier_markdown`→a minimal header string; `write_frontier`→writes that header. Add the `engine.frontier` re-export line.
2. Lane 4: land the three routes as thin pass-throughs over the stub + the empty `surf-frontier` surface. Now Lane 4 builds the full screen against fixtures.

**Then:**
- **F29.1 real** once PRD-03 F3.4 (`topic_trajectory`) lands (hard dep) — until then F29.1 ships with `moved=[]` degrade, which is *correct behaviour*, not a blocker; the contested + question cells work immediately on `value_queue`/`fieldmap`.
- **F29.2** immediately after F29.1 (pure render/write, no cross-lane dep).
- **F29.3** wires real payloads as F29.1/F29.2 land (Lane 4 parallel from M0 against fixtures).
- **CCP-29a periodic tick** — advisory, land any time after F29.2; not on the critical path (export route already refreshes on demand).
- **RQ-E45** runs before the surface labels the artifact "audited"; artifact ships advisory before then.

Leaves the repo runnable at every checkpoint (CLAUDE.md §4): stub → contested/question-only frontier → full frontier → auto-refreshed.

## 5. Test plan

**Unit (pure, no network/model):**
- `test_frontier.py` — FC-21 shape; per-cell `label`/`provenance`; `insufficient` path (<5 claims); trajectory-absent degrade (`moved=[]`, no raise); **KG-write spy asserts zero writes** (the projection guarantee).
- `test_frontier_artifact.py` — `frontier_markdown` section headers + insufficient banner; `write_frontier` stable path + exactly-one history row on change + sha256 match; written md compiles offline.

**API / integration:**
- `test_frontier_api.py` — `/frontier`, `/frontier/all`, `/frontier/export` (md) payload shapes against a fixture persona (monkeypatch FC-3/F3.4 providers so the suite runs without Lanes 1–2 complete, per PRD-04's provider-stub pattern).
- Browser smoke — three columns + label badge + insufficient banner render; export button yields a copyable link; **no horizontal overflow** at 1280/760/390 px.

**Experiment oracle:**
- `exp_rq_e45_frontier_facevalidity.py` (optional) — ≥5 subfields, expert agreement + bootstrap CI → `results/FINDINGS.md#RQ-E45`.

**Regression:** existing `test_value_queue.py`, `test_dependency.py`, `fieldmap`/`synthesizer` tests must still pass (this PRD adds a reader + routes; it edits none of their bodies — only a one-line `engine.py` re-export).

## 6. Open questions

- **O-1 (trajectory dependency — cross-feature, blocking `moved`).** `frontier()`'s "what just moved" cell needs PRD-03 F3.4 `trajectory.topic_trajectory(topic)`, which is **not yet built**. Confirm F3.4 lands the exact `topic_trajectory(topic) -> [{claim_id, velocity, acceleration, phase, independence_drift}]` shape (PRD-03 §F3.4 specifies it). Until it does, `moved=[]` and the frontier renders contested + question only — is that acceptable for the first ship, or should F29.1 wait on F3.4? (Recommend: ship degraded — the other two cells are the higher-value ones.)
- **O-2 (model narrative — deferred).** v1 renders a purely deterministic one-pager (no prose synthesis). A `topic_digest`-style model narrative ("the field is converging on X, contested on Y") would read more like a colleague but would be INFERRED and must be labelled + budget-gated. Confirm we defer it (recommend: yes — ship the deterministic artifact first; add an optional `generate=True` narrative later, typed INFERRED, behind the same abstention discipline as `knowledge.topic_digest`).
- **O-3 (subscribe semantics).** "Subscribe" here = a stable per-interest artifact path + on-demand/periodic refresh (a PI bookmarks the export URL). No email/RSS/push. Confirm that's the intended scope (recommend: yes — ponytail; a real feed is a separate backlog item if a user asks).
- **O-4 (nav placement — Lane 4 IA).** New spine destination vs Map subtab (same as PRD-04 Q1). Recommend a Map subtab ("Frontier") to avoid spine crowding. Blocks nothing.
- **O-5 (CCP-29a cadence).** If Lane 1 adopts the periodic tick, what refresh interval — per idle cycle, hourly, or daily? Recommend daily/offline (frontier is a slow-moving summary; the export route covers "I want it now"). Non-blocking.
