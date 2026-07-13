# PRD-04 — Legibility, flagship UI, API & self-benchmarking

> Owner: implementer lane 4 · Status: DRAFT-for-implementation · Autonomy: Balanced
> Provides: **FC-7** (`eval.run_oracle`)
> Consumes: **FC-3** (`kg.provenance_breakdown`), **FC-4** (`engine.dependency_graph`, `engine.value_queue`), **FC-5** (`calibrate.admit_decision` bound), **FC-2** (`inbox.file_handoff` dossiers), **FC-6** (`retraction.contamination`)

---

## 0. Summary and how this lane advances the vision

The product thesis is legibility: a mind at work whose reasoning, failures, costs and corrections are inspectable. Today the backend already computes most of that story but the SPA under-surfaces it. The robustness auditor (`POST /audit`, `POST /prove`) is reachable only through a "check my work" upload; the handoff inbox has API endpoints (`/inbox`, `/inbox/dossier`, …) but no navigation home; and the Review surface presents **client-side degree heuristics** for "load-bearing" and "value-of-information" (`index.html:2009`, `2012`) that the Research Quality Program explicitly flagged as unvalidated (`RESEARCH_QUALITY_PROGRAM.md` §2, "Evolution is not evolution"). This lane turns those buried capabilities into first-class, honest surfaces and adds the two things a reviewer still cannot get: a **server-computed** field-dependency + value-of-information screen (over Lane 3's FC-4, never a client metric), and a **self-benchmark harness** (FC-7: LitQA2 exact-paper retrieval with sure/unsure abstention, plus a few BixBench executable capsules) that makes the membrane's "scale of reading, discipline of believing" claim falsifiable against public oracles that penalize confident-wrong over honest-abstain. It also closes the reproducibility loop by emitting a Workflow-Run RO-Crate per closed-loop run so any belief update is independently re-executable and FAIR-citable. Every surface renders real server state, pairs colour with text/shape for WCAG AA, and moves only on genuine state change — the discipline in `SCIENTIFIC_WORKBENCH_SPEC.md`. Nothing in this lane anchors a belief or invents a scientific metric; anchoring stays human-gated behind RQ-E02.

---

## 1. File ownership (this lane's disjoint set)

| File | New/Edit | Notes |
|---|---|---|
| `persona/api/app.py` | **Edit — NEW routes only** | Add the routes in §3. Do **not** modify existing route bodies. Boundary note below on 4.5. |
| `persona/api/static/index.html` | **Edit — NEW surfaces/JS only** | Add surfaces + `open*()` functions; register in `SURF_DEST`/`SUBTABS`/spine (`index.html:632-637`, `964-965`). Replace only the three "unvalidated heuristic" blocks (`2009-2013`) whose data this lane now sources from the server. |
| `persona/sessions.py` | **Edit — ADD export only** | Add `workflow_run_crate(...)`; do not alter `_write_crate` / `verify_session` (Lane-shared integrity check). |
| `persona/eval/__init__.py` | **New** | FC-7 dispatcher `run_oracle`. |
| `persona/eval/litqa2.py` | **New** | LitQA2 oracle. |
| `persona/eval/bixbench.py` | **New** | BixBench capsule oracle. |
| `persona/eval/scorecard.py` | **New** | Cost-adjusted scorecard + snapshot pinning. |
| `experiments/exp_rq_e15_abstention_scoring.py` | **New** | Required experiment for 4.8 scoring rule. |
| `experiments/oracle_litqa2.py`, `experiments/oracle_bixbench.py` | **New** | CLI entry points / fixtures for the oracles. |
| `tests/test_eval_oracles.py`, `tests/test_epistemic_api.py`, `tests/test_workflow_run_crate.py` | **New** | Eval + API smokes. |
| `tests/ui_legibility_smoke.cjs` | **New** | Browser smoke for the four new surfaces (mirrors `tests/ui_research_smoke.cjs`). |

**Boundary files another lane also touches:**

- **`persona/api/app.py` (`GET /swarm`, `app.py:166`)** — feature 4.5 wants per-agent cost/model/yield on the swarm floor. The queue/daemon rows are produced by Lane 1's runtime, and the existing `/swarm` dict shape is consumed by `openSwarm()` (`index.html:1025`). To respect "NEW routes only" and avoid breaking that contract, this lane adds a **new** companion route `GET /swarm/economics` that joins the queue snapshot with `type:"cost"` events (already read by `/spend`, `app.py:128-139`) rather than mutating `/swarm`. Decoupled by: no FC needed (read-only over the event log + queue snapshot both lanes already expose). If Lane 1 later adds `model`/`cost` fields directly to task rows, this route consumes them opportunistically.
- **Gate-decisions JSONL (feature 4.6)** — Lanes 1/2 persist relevance/drift "why did it skip this paper" decisions to a jsonl under the persona ops dir. This lane only **reads** it via `GET /gate_decisions`. Decoupled by: a filename contract (see Open Questions Q3) — this lane degrades to an empty list if the file is absent, so it can ship before Lanes 1/2 write it.

---

## 2. Frozen contracts (verbatim)

**PROVIDES — FC-7** (Lane 4, new `persona/eval/`):
`eval.run_oracle(name:'litqa2'|'bixbench'|...) -> {metric:str, score:float, n:int, per_item:[...]}`

**CONSUMES:**

- **FC-3** (Lane 2, `persona/memory/kg.py`): `kg.provenance_breakdown() -> {READ:int,INFERRED:int,HUMAN_CONFIRMED:int,TESTED:int, never_confirmed:[claim_id], stale:[{claim_id,age_days}]}`; `kg.citation_support_ratio(claim_id) -> {support:int,contrast:int,mention:int,ratio:float}`; `kg.dependency_edges(topic=None) -> [{src,dst,rel_type,confidence,span}]`.
- **FC-4** (Lane 3, `persona/analysis/`): `engine.dependency_graph(topic) -> {nodes:[{claim_id,statement,load_bearing:float,independent_labs:int,support_ratio:float,provenance,fragile:bool}], edges:[{src,dst,rel_type,confidence,span}]}`; `engine.value_queue(topic) -> [{question, resolves_claim_id, voi:float, cost_tier:'public_data'|'cheap_assay'|'expensive', dataset_available:bool, de_risks_n:int, run_action:str}]`.
- **FC-5** (Lane 2, `persona/memory/calibrate.py`): `calibrate.admit_decision(candidate:dict) -> {admit:bool, calibrated_p:float, route:'commit'|'human'|'reject', reason:str, bound:float}`.
- **FC-2** (Lane 2, `persona/inbox.py`): `inbox.file_handoff(kind:str, dossier:dict) -> handoff_id:str`. Dossier schema = `{decision_requested, why_unresolvable, disagreeing:[{claim_id,span,qualifiers}], conflict_type:'temporal'|'semantic'|'misinformation'|'insufficient', cheapest_test:{action,cost_tier,dataset}, expected_updates:[{outcome,belief_change}], uncertainty, authority_boundary}`.
- **FC-6** (Lane 3, `persona/ingest/retraction.py`): `retraction.contamination(claim_id) -> {contaminated:bool, path:[claim_id]}`.

---

## 3. Features

### F4.1 — Flagship "Field-rests-on-this + value queue" screen

**Problem & evidence.** The current Review surface computes load-bearing as `degree ÷ independent_sources` and VoI as `graph degree` entirely in the client (`index.html:1999-2001`), self-labelled "unvalidated heuristic" (`index.html:2009`, `2012`). RESEARCH_QUALITY_PROGRAM.md §2 ("Evolution is not evolution") mandates server-computed, versioned metrics and forbids client-invented epistemic scores (§8: "No client-created metric is presented as scientific fact"). Research backing: dependency/fragility mapping = "Replication and fragility map" use-case (RQP §7.5); value-of-information action ranking = RQP Step 3 ("compute next actions from expected information gain") and Google AI co-scientist's verification-heavy ranking (deepmind.google/blog/co-scientist).

**Design.**
- New routes in `app.py`, thin pass-throughs over FC-4 (Lane 3 owns the computation; this lane owns transport + render):
  ```python
  @app.get("/api/persona/{pid}/engine/dependency")
  def engine_dependency(pid: str, topic: str = ""):
      with context.use(_p(pid)):
          from ..analysis import engine
          return engine.dependency_graph(topic or None)

  @app.get("/api/persona/{pid}/engine/value_queue")
  def engine_value_queue(pid: str, topic: str = ""):
      with context.use(_p(pid)):
          from ..analysis import engine
          return {"queue": engine.value_queue(topic or None)}
  ```
- New surface `surf-field` in `index.html` + `openField()`; registered as a **new spine destination** ("Rests-on") or as a Map subtab (Open Q1). Data flow: `openField()` → `GET /engine/dependency?topic=` + `/engine/value_queue?topic=` → render.
- **Dependency map:** node radius ∝ `load_bearing`; fill hue by `independent_labs` bucket (1 / 2 / 3+) using the state palette (`--contra`/`--human`/`--live` families); `fragile:true` (1-lab load-bearer) gets a **shape** marker (hollow diamond outline) so colour never carries state alone (`SCIENTIFIC_WORKBENCH_SPEC.md:128`). Click a node → detail panel: statement (serif), `claim_id`/metrics (mono), and "if this fell, **N** downstream weaken" computed from the returned `edges` (count of edges whose `src` transitively reaches the node — done client-side over the server-supplied edge list; this is presentation of server data, not a new metric). Each source span reachable in ≤2 clicks via existing `prov(claim_id)` (`index.html`, calls `/provenance/{id}`).
- **Value queue (paired column):** each row = `{question, voi, cost_tier, dataset_available, de_risks_n, run_action}`. Sort by `voi`. Two one-click actions per row: **Hand to Tester** → `POST /investigate` with the row's `run_action`/question (existing route, `app.py:816`); **Open dossier** → files an FC-2 handoff via a new `POST /engine/handoff` (below) then routes to the Review dossier surface (F4.3).
  ```python
  @app.post("/api/persona/{pid}/engine/handoff")
  def engine_handoff(pid: str, payload: dict):
      """File a value-queue item as a human dossier (FC-2). Never anchors a belief."""
      with context.use(_p(pid)):
          from ..inbox import file_handoff
          hid = file_handoff(payload.get("kind", "value_queue"), payload.get("dossier", {}))
      return {"ok": True, "handoff_id": hid}
  ```
- Aesthetic: adopt the spec's dark editorial tokens (`#07080B`/`#0E1015`, borders `#22262F`) scoped to this surface (see Open Q2 re: the current light `:root`), mono for IDs/metrics, serif for the clicked conclusion, motion only when the topic/selection changes; honour `prefers-reduced-motion`.

**Epistemic guardrails.** Every number originates from FC-4 (server, versioned) — the surface renders `load_bearing`, `voi`, `fragile` as returned and shows the provenance/`support_ratio` fields verbatim; it never recomputes them. "N downstream" is a labelled derived count over server edges, not a scientific score. Handoff files a dossier for human judgement; no admit/anchor path exists here.

**Required experiment.** Trivial for this lane — no experiment. (The metric validity is Lane 3's FC-4 obligation; this lane only transports/renders. If FC-4 ships an unvalidated `load_bearing`, it must self-label per RQP §2 and this surface must echo that label — see Acceptance.)

**Acceptance criteria.** (1) With a seeded persona, `GET /engine/dependency?topic=<t>` returns ≥1 node with `load_bearing`, `fragile`, `provenance` fields and the surface renders each `fragile` node with a distinct **shape** (not colour alone). (2) Clicking a node shows "if this fell, N downstream weaken" with N matching a hand-count over the returned edges. (3) No client-side arithmetic produces a value labelled as a score without a server field backing it (grep the new JS for `/` on metric fields → none). Runnable check: `tests/test_epistemic_api.py::test_engine_routes_shape` asserts both routes return the FC-4 keys against a fixture persona.

**Effort** M · **Dependencies** FC-4, FC-2.

---

### F4.2 — Robustness-auditor "Trust" tab

**Problem & evidence.** `POST /audit` (`app.py:378`) and `POST /prove` (`app.py:444`) are fully built — deterministic statecheck/GRIM/GRIMMER/p-curve forensics + calibrated replication likelihood + adversarial red-team + trust ledger, rendered by `renderAudit()` (`index.html:1948`) — but reachable only after a manual upload/slug audit. There is no browsable home. Research backing: PaperQA2 (arXiv:2409.13740) claim-level citation validation; RQP §7.8 "Executable peer review … distinguishes verified issues from suspicions".

**Design.**
- No new backend needed for the core (audit results already carry `checks {pass/warn/fail}`, `flags[]` with `span`, `interval`, `band`, `ledger`, `red_team`, `external`). Add one convenience route so the tab can populate without a re-upload:
  ```python
  @app.get("/api/persona/{pid}/audits")
  def audits_list(pid: str):
      """Every paper the persona has already audited + its verdict history (no re-run)."""
      p = _p(pid)
      with context.use(p):
          from ..memory import watchlist
          return {"summary": watchlist.summary(), "entries": watchlist.entries()}
  ```
  (This reuses the existing watchlist store already surfaced by `/watchlist`, `app.py:411`; the new route is a semantic alias so the Trust tab reads naturally. If redundant, the tab may call `/watchlist` directly and this route is dropped — mark `ponytail:` in code.)
- New surface `surf-trust` + `openTrust()`: lists audited papers from `/audits`; clicking one renders the stored verdict via `renderAudit()` (reused verbatim); a search box audits a new slug/query via existing `POST /audit`. Show per-claim adjudication (`r.claims[]`), the **skipped-vs-passed** check breakdown (F4.2 must render `checks.pass/warn/fail` **and** any check whose applicability gate returned skipped — see guardrail), replication interval + band, contamination (call FC-6 `retraction.contamination` per central claim via a new `GET /contamination/{claim_id}`), and the trust ledger footer (already in `renderAudit`, `index.html:1970`).
  ```python
  @app.get("/api/persona/{pid}/contamination/{claim_id}")
  def contamination(pid: str, claim_id: str):
      with context.use(_p(pid)):
          from ..ingest import retraction
          return retraction.contamination(claim_id)
  ```

**Epistemic guardrails.** The forensic checks are code-run (never a model) — the tab must render a check's **skipped/not-applicable** state as visually distinct from **passed** (RQP forensic discipline: false positives from out-of-domain application are the correctness boundary). Concretely: the render distinguishes three states with text+icon (pass ✓ / warn △ / fail ✕) and adds a fourth **skipped ⊘** row so an inapplicable GRIM on non-integer data never reads as a pass. Contamination path is shown as evidence, not as an auto-retraction of the belief.

**Required experiment.** Trivial — surfaces an existing validated backend. No experiment. (If `audit.audit()` does not already emit a skipped state per check, that is a backend gap to file against the auditor owner, not new modelling here — flag in Open Q4.)

**Acceptance criteria.** (1) Opening Trust with a persona that has an audit in its watchlist shows the paper and its band without any upload. (2) A check that is not applicable renders with the `skipped` marker, not `pass`. Runnable check: `tests/ui_legibility_smoke.cjs` (Trust step) asserts the tab lists ≥0 audits and, on a fixture audit JSON containing a skipped check, the DOM shows the skipped marker.

**Effort** S · **Dependencies** FC-6; existing `/audit`, `/watchlist`.

---

### F4.3 — First-class handoff-inbox surface

**Problem & evidence.** `/inbox`, `/inbox/dossier`, `/inbox/review`, `/inbox/resolve`, `/inbox/investigate` exist (`app.py:598-721`) and a rich dossier modal is built (`contraEvidence()`, `index.html:2037`), but the inbox is buried inside the Review/instruments surface (`index.html:2018-2022`) with no nav home answering "what needs my judgment". Research backing: RQP §4 "Human resolution dossier" and RQP RQ-E14 (dossier reduces decision time); anchoring gated by RQ-E02 (`app.py:696-699` returns `contradiction-typing-not-validated`).

**Design.**
- Backend already complete. Optionally expose FC-2 dossiers alongside candidate conflicts so the inbox shows both machine-filed handoffs (from F4.1 value queue, F4.1 `run_action`) and sign-collision candidates:
  ```python
  @app.get("/api/persona/{pid}/handoffs")
  def handoffs_list(pid: str):
      """Human-decision dossiers filed via FC-2 (distinct from raw candidate conflicts)."""
      with context.use(_p(pid)):
          from ..inbox import list_handoffs   # Lane 2 to expose; degrade to [] if absent
          try:
              return {"handoffs": list_handoffs()}
          except (ImportError, AttributeError):
              return {"handoffs": []}
  ```
- New surface `surf-inbox` + `openInbox()` promoted to a **spine destination** ("Judgment", replacing/renaming the Review tab, Open Q1). For each item render, per the FC-2 dossier schema: typed `conflict_type`, the cheapest discriminating `cheapest_test {action,cost_tier,dataset}`, `expected_updates` (belief-shift per outcome), and the `authority_boundary`. Actions row: **[defer]** (no-op log), **[request context]** (records a `insufficient_evidence` review), **[contest]** (opens `contraEvidence` dossier / pinned investigation via `/inbox/investigate`), **[confirm → anchor]**. The **confirm→anchor** button is rendered **disabled** with a tooltip citing RQ-E02, and stays disabled until (a) RQ-E02 precision gate passes AND (b) a non-empty rationale is supplied — mirroring `SCIENTIFIC_WORKBENCH_SPEC.md:119`. Reuse `contraEvidence()`, `recordConflictReview()`, `investigateConflict()` verbatim.

**Epistemic guardrails.** Anchoring is human-gated and double-locked (RQ-E02 + rationale). Every dossier reaches an exact source span in ≤2 actions (via `/inbox/dossier` → `positive`/`negative` provenance). Reading a dossier never mutates a belief (`/inbox/dossier` docstring, `app.py:621`; `/inbox/resolve` refuses, `app.py:696`). `candidate_conflict` is labelled "unverified", never "contradiction".

**Required experiment.** Trivial — reuses validated endpoints and the pilot dossier flow. No experiment.

**Acceptance criteria.** (1) The inbox is a top-level nav destination; opening it lists candidate conflicts and (if any) FC-2 handoffs. (2) The `confirm → anchor` control is disabled and its tooltip names RQ-E02. (3) A dossier reaches an exact quote in ≤2 clicks. Runnable check: `tests/ui_legibility_smoke.cjs` (Inbox step) asserts the anchor button has the `disabled` attribute and the RQ-E02 tooltip text.

**Effort** S · **Dependencies** FC-2; existing inbox routes.

---

### F4.4 — Epistemic-status / RQ-gate dashboard

**Problem & evidence.** There is no single place a reviewer sees "which gate backs each claim type" or the calibration bound. RQP §8 requires the UI to "clearly distinguish evidence, inference, human confirmation, and tests" and to never infer status in the client. FC-3 (`provenance_breakdown`) and FC-5 (`bound`) exist to supply this; the RQ registry lives in `docs/RESEARCH_QUALITY_PROGRAM.md` §5 (RQ-E01…E14 with per-gate status strings like "E01a complete; E01b pending").

**Design.**
- New route assembling three server sources + the parsed registry:
  ```python
  @app.get("/api/persona/{pid}/epistemic")
  def epistemic(pid: str):
      p = _p(pid)
      with context.use(p):
          from ..memory.kg import provenance_breakdown        # FC-3
          from ..memory.calibrate import admit_decision        # FC-5 (bound only)
          pb = provenance_breakdown()
          # conformal bound from a neutral probe candidate (no admission side effect)
          bound = admit_decision({"probe": True}).get("bound")
      return {"provenance": pb, "calibration_bound": bound,
              "gates": _parse_rq_gates()}
  ```
- `_parse_rq_gates()` (module-level helper in `app.py`): read `docs/RESEARCH_QUALITY_PROGRAM.md`, regex each `### RQ-E\d+ — <title> — **<status>**` heading into `[{id, title, status, gate}]` where `status` is the bold trailer (defaulting to "pending" when absent) and `gate` is the line beginning `- **Gate:**`. Pure string parsing, no model. Cache on mtime.
- New surface `surf-epistemic` + `openEpistemic()` (Map subtab): render the provenance breakdown as a labelled bar (READ/INFERRED/HUMAN_CONFIRMED/TESTED counts, each with its state colour **and** text label), a "**N** beliefs never human-confirmed / **M** stale" callout from `never_confirmed`/`stale`, the conformal `calibration_bound` as "admission holds to a ±`bound` coverage guarantee" (mono), and the RQ gate registry as a status table (pass=green+✓, pending=amber+△, failed=red+✕).

**Epistemic guardrails.** Confidence shown is the conformal `bound` from FC-5 (validated on held-out data), never a model self-report (RQP "No fabricated confidence"). Provenance counts come straight from FC-3. Gate statuses are quoted from the living doc, not asserted by the UI. `stale`/`never_confirmed` surface the honest-uncertainty state the CLAUDE.md design principles demand.

**Required experiment.** Trivial — assembles existing validated server state + a doc parse. No experiment.

**Acceptance criteria.** (1) `GET /epistemic` returns `provenance` with all four FC-3 keys, a numeric `calibration_bound`, and a `gates` list whose ids match the `RQ-E\d+` headings in the doc. (2) The surface labels every provenance segment with text (not colour alone). Runnable check: `tests/test_epistemic_api.py::test_epistemic_parses_gates` asserts `gates` contains `RQ-E02` with a non-empty status and the four provenance keys are present.

**Effort** M · **Dependencies** FC-3, FC-5.

---

### F4.5 — Per-agent cost-vs-yield on the swarm floor

**Problem & evidence.** `GET /swarm` (`app.py:166`) returns live task rows but no cost/model/claim-yield, so the "scale of reading, discipline of believing" funnel cost story is invisible. Cost events (`type:"cost"`, `data.task_type`, `data.cost`) already exist and are read by `/spend` (`app.py:128-139`). Research backing: Anthropic multi-agent research system (~15× tokens) → cost must be inspectable, not hidden; RQP rule 9 "scale stops when marginal unique verified evidence per 1,000 tokens is non-positive".

**Design.**
- New companion route (keeps `/swarm` untouched — see §1 boundary note):
  ```python
  @app.get("/api/persona/{pid}/swarm/economics")
  def swarm_economics(pid: str):
      """Cost / model / validated-yield per task-type, joined from the event log."""
      p = _p(pid)
      with context.use(p):
          from ..events import log
          evs = log().since(max(0, log().latest_id() - 2000))
      by_type: dict[str, dict] = {}
      for e in evs:
          if e.get("type") == "cost":
              d = e["data"]; t = d.get("task_type", "?")
              row = by_type.setdefault(t, {"spend": 0.0, "n": 0, "model": d.get("model")})
              row["spend"] += float(d.get("cost", 0) or 0); row["n"] += 1
          if e.get("type") == "harvest":                 # membrane admissions = validated yield
              t = e["data"].get("task_type", "harvest")
              by_type.setdefault(t, {"spend": 0.0, "n": 0, "model": None})
              by_type[t]["validated"] = by_type[t].get("validated", 0) + 1
      rows = [{"task_type": t, **v,
               "usd_per_validated": (v["spend"] / v["validated"]) if v.get("validated") else None}
              for t, v in by_type.items()]
      return {"economics": sorted(rows, key=lambda r: -r["spend"])}
  ```
  (Field names `harvest`/`cost` verified against `SW_VERB` at `index.html:997` and `/spend` at `app.py:134-138`. If the daemon emits a richer per-task cost row later, this route consumes it without a shape change.)
- `openSwarm()` (`index.html:1025`) gains a small economics strip under `#swarmsummary`: per task-type spend, model, and `usd_per_validated` when known — mono, no motion (updates only on the existing 1.5 s poll).

**Epistemic guardrails.** "Validated yield" = membrane `harvest` admissions only (crossed the membrane), never raw reads — honest funnel. `usd_per_validated` is `null` (rendered "—") when no admission occurred, not zero, so a costly-but-fruitless task-type is visibly distinct from a free one.

**Required experiment.** Trivial — arithmetic over the existing event log. The `usd_per_validated` ratio has a one-line `__main__` assert in the test (below). No RQ.

**Acceptance criteria.** (1) `GET /swarm/economics` returns rows with `spend`, `n`, and `usd_per_validated` (null when no validated admission). (2) The floor strip shows at least one task-type's spend after a run. Runnable check: `tests/test_epistemic_api.py::test_swarm_economics` feeds a fixture event log (2 cost + 1 harvest) and asserts `usd_per_validated == spend/1`.

**Effort** S · **Dependencies** none (event-log read).

---

### F4.6 — Gate-decisions ledger surface

**Problem & evidence.** "Show the funnel, not just the output" (CLAUDE.md §5) — the relevance/drift "why did it skip this paper" decisions are persisted by Lanes 1/2 to a jsonl but never surfaced, so the discipline of *rejection* is invisible. RQP §2 "Activity is not reasoning" wants the real decision stream shown, not ambient telemetry.

**Design.**
- New read route over the agreed jsonl (Open Q3 fixes the exact path; default `ops_dir/gate_decisions.jsonl`):
  ```python
  @app.get("/api/persona/{pid}/gate_decisions")
  def gate_decisions(pid: str, limit: int = 200):
      p = _p(pid)
      f = p.paths.ops_dir / "gate_decisions.jsonl"
      if not f.exists():
          return {"decisions": [], "available": False}
      rows = []
      for line in f.read_text(encoding="utf-8", errors="replace").splitlines()[-limit:]:
          try: rows.append(json.loads(line))
          except json.JSONDecodeError: continue
      return {"decisions": rows, "available": True}
  ```
- Rendered inside the Floor surface (a collapsible "admitted / skipped" ledger under the economics strip) or the Focus stream — reusing existing card CSS. Each row: candidate id/title, decision (`admit`/`skip`), reason (relevance score / drift), and timestamp. Read-only.

**Epistemic guardrails.** Read-only projection of an append-only ledger written by other lanes; this surface never writes or re-decides. Absence degrades to `available:false` (empty, honest) rather than a fabricated funnel.

**Required experiment.** Trivial — reads a jsonl. No experiment.

**Acceptance criteria.** (1) With a fixture `gate_decisions.jsonl`, `GET /gate_decisions` returns the rows and `available:true`; with no file, `available:false` and `[]`. Runnable check: `tests/test_epistemic_api.py::test_gate_decisions_missing_and_present`.

**Effort** S · **Dependencies** Lanes 1/2 write the jsonl (soft — degrades gracefully).

---

### F4.7 — Confidence-over-time (provSpark) reuse on Map/Fieldmap

**Problem & evidence.** `provSpark()` (`index.html:1390`) renders a confidence-over-snapshots sparkline from `/history/{claim_id}` (`app.py:592`) but is only invoked in the provenance modal (`index.html:1399`). The Map/Fieldmap surfaces show no trajectory, so "where is the argument heading" is not answerable at a glance (RQP §2 "Evolution is not evolution").

**Design.** Pure frontend. In `openFieldmap()`/`openGraph()` node and belief rows, when a claim has ≥2 history points, render the existing `provSpark(pts)` inline (fetch `/history/{claim_id}`, cache per claim to avoid re-fetch). No new route (history route already exists). Reuse the existing SVG generator verbatim.

**Epistemic guardrails.** Trajectory is the real temporal belief history from `/history` (server), not a client heuristic — this is exactly the "use temporal belief history" fix RQP §2 demands over the degree heuristics.

**Required experiment.** Trivial — reuses an existing component + route.

**Acceptance criteria.** A fieldmap/map claim with ≥2 history snapshots shows an inline sparkline. Runnable check: `tests/ui_legibility_smoke.cjs` asserts a `.spark` element appears on the map surface for a fixture claim with history (or gracefully absent when none).

**Effort** S · **Dependencies** none.

---

### F4.8 — Self-benchmark harness (FC-7)

**Problem & evidence.** The membrane/auditor's core claim — "discipline of believing" — is currently only argued, not measured against an external oracle. There is no standing regression that would catch a membrane that starts admitting confident-wrong answers. Research backing: **AstaBench** (arXiv:2510.21652) holistic agent eval; **LitQA2 / LAB-Bench** (arXiv:2407.10362) exact-paper retrieval with a sure/unsure abstention option; **BixBench** (arXiv:2503.00096) executable bioinformatics reanalysis capsules with known answers. Optional: SciClaimHunt_Num / SciVer for numeric claim checking.

**Design.**
- `persona/eval/__init__.py` — FC-7 dispatcher, exact signature:
  ```python
  def run_oracle(name: str, *, n: int | None = None, seed: int = 0,
                 persona: str | None = None) -> dict:
      """FC-7. -> {metric:str, score:float, n:int, per_item:[...]}"""
      if name == "litqa2":  from .litqa2 import run_litqa2;  return run_litqa2(n=n, seed=seed, persona=persona)
      if name == "bixbench": from .bixbench import run_bixbench; return run_bixbench(n=n, seed=seed, persona=persona)
      raise ValueError(f"unknown oracle {name!r}")
  ```
- `persona/eval/litqa2.py`:
  ```python
  def run_litqa2(*, n=None, seed=0, persona=None) -> dict: ...
  def score_litqa2(pred: dict, gold: dict) -> float: ...   # abstention-aware, see experiment
  ```
  Loads a **frozen local fixture** subset of LitQA2 (bundled JSONL under `experiments/fixtures/litqa2_frozen.jsonl` with document hashes; full set gated by licence/network like RQ-E12 — Open Q5). For each item, runs the persona's grounded retrieval (`ask_graph`/`topic_digest` path) which already returns a sure/unsure signal via the abstention discipline; scores retrieval precision **and** abstention: **confident-wrong penalised harder than honest-abstain** (rule fixed by the required experiment). `metric = "precision_at_coverage"`.
- `persona/eval/bixbench.py`: `run_bixbench(*, n=None, seed=0, persona=None) -> dict` — runs a few BixBench capsules in the existing offline sandbox (`persona/tools/sandbox.py`, reused by `/run_code`, `app.py:343`), compares numeric output to the capsule's known answer within tolerance; `metric = "capsule_pass_rate"`.
- New route to run an oracle on demand and stream the scorecard into the eval surface (or reuse the Trust/Epistemic surface):
  ```python
  @app.post("/api/persona/{pid}/eval")
  def run_eval(pid: str, payload: dict):
      _p(pid)
      from ..eval import run_oracle
      name = payload.get("oracle", "litqa2")
      return run_oracle(name, n=payload.get("n"), seed=payload.get("seed", 0), persona=pid)
  ```
- CLI entry points `experiments/oracle_litqa2.py` / `oracle_bixbench.py` for standing regression (run in CI-lite / by hand).

**Epistemic guardrails.** The oracle is an **external** ground truth (public benchmark answers), not a model self-report — it is the honest falsifier for the membrane. Abstention is rewarded relative to confident-wrong so the harness cannot be gamed by a system that always answers. Frozen document hashes pin reproducibility (RQP §5). A model judge, if ever used for open-ended scoring, is labelled a proxy, never ground truth (RQP §5).

**Required experiment.** **RQ-E15 — abstention-aware oracle scoring.**
- *Hypothesis:* a scoring rule that penalises confident-wrong more than honest-abstain ranks a calibrated-but-abstaining system above a confident-always system on LitQA2-style items, whereas plain accuracy does not.
- *Metric / gate:* on ≥20 seeded shuffles of a synthetic answer set (mix of correct / wrong / abstain), the abstention-aware score must rank an "abstain-when-unsure" policy strictly above a "always-answer" policy with the same underlying knowledge in ≥95% of seeds (mean ± 95% CI reported), while plain accuracy fails to. Go/no-go: if the rule does not separate them, fall back to LAB-Bench's published precision-at-coverage exactly rather than inventing one.
- *Seeds:* ≥20, saved to `results/rq_e15_abstention_scoring.json`; script `experiments/exp_rq_e15_abstention_scoring.py`. Cite the chosen rule in `score_litqa2` via a `# see experiments/exp_rq_e15…` comment.

**Acceptance criteria.** (1) `eval.run_oracle("litqa2", n=5)` returns `{metric, score, n, per_item}` with `n==5` and `metric=="precision_at_coverage"`. (2) A confident-wrong fixture scores strictly below an honest-abstain fixture. (3) `run_oracle("bixbench", n=1)` returns a `capsule_pass_rate` after a real sandbox run. Runnable check: `tests/test_eval_oracles.py::test_litqa2_abstention_ordering` and `::test_run_oracle_contract` (asserts the FC-7 key set).

**Effort** L · **Dependencies** FC-7 (self), sandbox, frozen fixtures.

---

### F4.9 — Cost-adjusted scorecard

**Problem & evidence.** No view plots membrane-admitted-belief accuracy against dollars, and eval runs are not pinned to dated data snapshots, so oracle scores are not reproducible over time. RQP §5 requires equal-budget conditions and saved raw results; CLAUDE.md §4 requires pinned caches for the demo.

**Design.**
- `persona/eval/scorecard.py`:
  ```python
  def scorecard(runs: list[dict]) -> dict:
      """Join FC-7 oracle results with their $ cost -> accuracy-vs-dollars points + a Pareto front."""
  def pin_snapshot(source: str, date: str) -> dict:
      """Record a dated Europe PMC / Open Targets snapshot id so an eval is re-runnable."""
  ```
  `scorecard` takes a list of `run_oracle` outputs (each annotated with the run's `cost_usd` from the session/event log) and returns `{points:[{oracle, score, cost_usd}], pareto:[...]}`. `pin_snapshot` writes `{source, date, snapshot_id}` to `runs_dir/eval_snapshots.json` so a given scorecard cites exactly which Europe PMC / Open Targets state produced it.
- Rendered as a small accuracy-vs-$ chart on the Epistemic (F4.4) or a new Eval surface — points coloured by oracle, Pareto front outlined; axes labelled; no colour-only encoding.

**Epistemic guardrails.** Accuracy is external-oracle accuracy (F4.8), not self-reported. Cost is the real session `cost_usd`. Snapshots are pinned + dated for reproducibility; a scorecard without a pinned snapshot is labelled "unpinned — not reproducible".

**Required experiment.** Trivial — deterministic join + plotting. No RQ (the *scoring* validity is RQ-E15 under F4.8).

**Acceptance criteria.** `scorecard([...])` returns `points` and a `pareto` subset that is monotone (no point dominates another on both axes). Runnable check: `tests/test_eval_oracles.py::test_scorecard_pareto` asserts the Pareto set is non-dominated.

**Effort** M · **Dependencies** F4.8 outputs.

---

### F4.10 — Workflow-Run RO-Crate export per closed-loop run

**Problem & evidence.** `sessions.py` already emits an RO-Crate 1.3 metadata file listing session + artifacts (`_write_crate`, `sessions.py:31-49`) and `verify_session` checks its context (`sessions.py:266-275`). But it is a static *object* crate, not a **Workflow-Run** crate: it does not model the run as a workflow with typed input→output actions, so a belief update is not independently re-executable/provenanced end-to-end. Research backing: **Workflow-Run RO-Crate** (arXiv:2312.07852) — the standard profile for capturing a computational run's provenance (workflow entity + `CreateAction`s + input/output roles).

**Design.**
- Add to `sessions.py` (export-only; do **not** touch `_write_crate` or `verify_session`, both Lane-shared):
  ```python
  def workflow_run_crate(root: Path, meta: dict) -> dict:
      """Build a Workflow Run Crate profile graph over an existing session (arXiv:2312.07852).
      Enriches the base @graph with a ComputationalWorkflow entity and CreateAction steps
      linking question -> claims/evidence -> code/artifacts -> verifier verdict. Returns the
      crate dict; callers may write it into an export bundle (never overwrites the canonical
      ro-crate-metadata.json)."""
  ```
  It reuses the base entities from `_write_crate` (same RO-Crate 1.3 context so `verify_session` still passes if ever written), adds `conformsTo` the Workflow Run Crate profile, a workflow entity typed `["File","SoftwareSourceCode","ComputationalWorkflow"]` pointing at the run's code artifacts, and one `CreateAction` per session step (`session_started` → `artifact_stored` → `verifier_verdict`) with `object`/`result` roles referencing artifact `@id`s already in `meta["artifacts"]`.
- New route emitting the bundle as a zip (mirrors `deliverable_bundle`, `app.py:1175`):
  ```python
  @app.get("/api/persona/{pid}/sessions/{session_id}/rocrate")
  def session_rocrate(pid: str, session_id: str):
      """Download a Workflow-Run RO-Crate zip (metadata + artifacts) for a closed-loop run."""
      p = _p(pid); from ..sessions import read_session, workflow_run_crate
      data = read_session(p.paths.runs_dir, session_id)
      if data is None: raise HTTPException(404, "session not found")
      crate = workflow_run_crate(p.paths.runs_dir / session_id, data["session"])
      # zip: ro-crate-metadata.json (workflow-run profile) + events.jsonl + session.json + artifacts/
      ...
      return StreamingResponse(buf, media_type="application/zip", headers={...})
  ```
- Wire a "Export RO-Crate" button into the existing Work/session detail view (which already calls `/sessions/{id}` and `/sessions/{id}/verify`).

**Epistemic guardrails.** Export-only projection over the append-only trace — no event is rewritten (matches the `append_session_artifact` discipline, `sessions.py:187`). The canonical `ro-crate-metadata.json` and `verify_session` are untouched, so the shared integrity gate is preserved. The crate binds to the sealed `events_sha256` so the bundle is tamper-evident.

**Required experiment.** Trivial — deterministic metadata assembly against a published profile. No RQ.

**Acceptance criteria.** (1) `workflow_run_crate` returns a dict whose `@graph` contains exactly one `ComputationalWorkflow` entity and ≥1 `CreateAction`, and whose `@context` is RO-Crate 1.3. (2) The zip round-trips (every artifact `@id` in the graph exists in the zip). Runnable check: `tests/test_workflow_run_crate.py::test_profile_shape` builds a crate over a fixture session and asserts the workflow + action entities and that `verify_session` on the original session still passes (regression guard).

**Effort** M · **Dependencies** none (over existing sessions).

---

## 4. Sequencing within the lane

1. **Milestone 0 — FC-7 stub first** (unblocks Lane 3/master coherence checks): land `persona/eval/__init__.py` `run_oracle(name, ...)` returning a typed empty fixture `{"metric":"", "score":0.0, "n":0, "per_item":[]}` plus `litqa2.py`/`bixbench.py`/`scorecard.py` signatures with `NotImplementedError`-free empty returns. Ship the four new **routes as thin stubs** returning empty typed payloads (`/engine/dependency`, `/engine/value_queue`, `/epistemic`, `/eval`, `/swarm/economics`, `/gate_decisions`, `/contamination/{id}`, `/audits`, `/handoffs`, `/sessions/{id}/rocrate`) so the frontend + other lanes can build against them from hour 1. Each consumed FC is wrapped in a try/except that degrades to empty until its provider lands.
2. **F4.10 RO-Crate + F4.6 gate ledger + F4.7 provSpark** (S, zero cross-lane dependency) — bank early wins, all read-only over existing data.
3. **F4.2 Trust tab + F4.3 Inbox** (S, reuse built modals/renderers) — depend only on FC-6/FC-2 which degrade gracefully.
4. **F4.4 Epistemic dashboard + F4.5 swarm economics** (M/S) — as FC-3/FC-5 land.
5. **F4.1 Flagship field/value screen** (M) — after FC-4 lands; the marquee surface, built last so it sits on validated metrics.
6. **F4.8 harness + RQ-E15 + F4.9 scorecard** (L) — parallelisable with the UI track; RQ-E15 experiment runs before `score_litqa2` is finalised.

Rationale: read-only surfaces first (always-demoable, per CLAUDE.md §4 "leave the repo runnable at every checkpoint"); the two features gated on the newest FCs (FC-4 flagship, FC-3/5 dashboard) come once their providers stub-land; the L-effort eval harness runs on its own thread so it never blocks the UI checkpoints.

---

## 5. Test & verification plan

**Unit / API (pytest, new `tests/`):**
- `test_epistemic_api.py`: `/engine/dependency`+`/engine/value_queue` key shape (F4.1); `/epistemic` provenance keys + RQ-gate parse incl. `RQ-E02` (F4.4); `/swarm/economics` `usd_per_validated` math on a fixture log (F4.5); `/gate_decisions` present+missing (F4.6). Use a fixture persona via `manager()` or monkeypatched FC providers so the suite runs without Lanes 1-3 complete.
- `test_eval_oracles.py`: FC-7 contract (`run_oracle` returns the 4 keys); LitQA2 abstention ordering (F4.8); scorecard Pareto non-dominance (F4.9).
- `test_workflow_run_crate.py`: profile shape + **regression guard that `verify_session` on the untouched session still passes** (F4.10) — this reuses the existing integrity oracle in `sessions.py` as the seam-test, exactly as CLAUDE.md §4 prescribes reusing real oracles.
- `experiments/exp_rq_e15_abstention_scoring.py`: ≥20 seeds, mean±95% CI, saved to `results/`.

**Integration / browser smoke (`tests/ui_legibility_smoke.cjs`, mirrors `tests/ui_research_smoke.cjs`):** boot the app with no workers; open each of the four new surfaces; assert: fragile node renders a shape marker (F4.1); Trust lists an audit and shows a `skipped` marker on a fixture (F4.2); Inbox anchor button is `disabled` with the RQ-E02 tooltip (F4.3); Epistemic labels each provenance segment with text (F4.4); a map claim with history shows a `.spark` (F4.7). Assert **no horizontal overflow** at 1280/760/390 px (spec acceptance) and that keyboard `Esc` closes any opened dossier (reuses existing handler, `index.html:2076`).

**Existing suite:** `test_integrity_boundaries.py`, `test_calibration.py`, `test_forensics.py`, and the research smoke must still pass unchanged (this lane adds routes/surfaces; it must not regress them).

---

## 6. Open questions for the master/user

- **Q1 (nav shape).** The spine has 6 fixed destinations (`index.html:632-637`). This lane adds three reviewer-facing screens (Field/value, Trust, Inbox, Epistemic). Do we (a) add new top-level spine buttons (risks crowding), or (b) fold them as **subtabs** under Map (Epistemic, Field) and rename **Review→Judgment** for the Inbox + Trust? Recommendation: (b). Blocks nothing but affects final IA.
- **Q2 (theme divergence).** The spec mandates a **dark** editorial palette (`#07080B`/`#0E1015`), but the current `:root` is a **light** theme (`index.html:12-13`). Do the new surfaces adopt the dark tokens (scoped), or does the whole app migrate? Recommendation: scope dark tokens to the flagship F4.1 surface first, propose a full migration separately. Does not block other lanes.
- **Q3 (gate-decisions path — cross-lane).** F4.6 reads a jsonl written by Lanes 1/2. Confirm the exact path/filename (proposed `ops_dir/gate_decisions.jsonl`) and row schema (`{candidate_id, title, decision:'admit'|'skip', reason, score, at}`). This is the one soft cross-lane contract; naming it lets F4.6 ship non-empty.
- **Q4 (auditor skipped-state — cross-lane).** F4.2 requires each forensic check to expose a `skipped/not-applicable` state distinct from `pass`. Does `audit.audit()` already emit this per check, or must the auditor owner add it? If not present, F4.2 renders only pass/warn/fail and this becomes a filed backend gap.
- **Q5 (benchmark data access).** LitQA2/BixBench full sets may be licence/network-gated (like RQ-E12's AstaBench access). Confirm we ship a **frozen local fixture subset** (with document hashes) for the offline demo and reserve the full set for gated runs. Blocks nothing if the fixture path is accepted.
