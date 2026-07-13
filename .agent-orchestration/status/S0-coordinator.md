# S0 — COORDINATOR BOARD  (live directives — S1–S6 read this)

Updated: 2026-07-12 · session start. **This is the single source of direction.** Re-read on every wake.
Report by writing ONLY your own `status/S{n}-*.md`. Cross-lane needs → `requests/`. Never edit another lane.

---

# 🔧 TERMINOLOGY FIX + LANE-2 REDISTRIBUTION — 2026-07-13 (user: "4 impl agents, no agent 5")

**Canonical labels (S-numbers RETIRED — "S5" was NOT a 5th agent, it is imp3):**
`idea` (was S1) · `review` (was S2) · `imp1` (was S3 → Lane 4 Legibility) · `imp2` (was S4 → Lane 1 Teams) · `imp3` (was S5 → Lane 2 Membrane) · `imp4` (was S6 → Lane 3 Engine). **Four implementers = imp1–imp4. No agent 5.**

**imp3 / Lane 2 (Membrane) has been DARK all session → work REDISTRIBUTED so the epistemic core ships continuously (single owner each, collision-safe):**
- `memory/kg.py` (**FC-3**), `memory/{membrane,calibrate*,coherence,history,vectors,watchlist}.py` (**FC-5**) → **imp4 / Engine** (its FC-4 builds on FC-3 — natural owner).
- `conflict_reviews.py`, `inbox.py*` (**FC-2**), conflict-typing → **imp2 / Teams** (owns `open_from_conflict` — conflict flow adjacent).
- **✅ Lane-2 Milestone-0 LANDED** (workflow `wwktpsurb`, **14 tests pass, $0**): FC-3 `kg.py` (provenance_breakdown / add_dependency_edge / dependency_edges / citation_support_ratio) · FC-5 `memory/calibrate.py` (admit_decision; thresholds PLACEHOLDER pending RQ-E16) · FC-2 `persona/inbox.py` (file_handoff, append-only, content-hash id) · M2 `watchlist.py` `due(min_age_hours=12)` floor (busy-loop fixed — supervisor already gates on it, no daemon change). **🔓 UNFROZEN → `memory/*` is imp4's, `conflict_reviews.py`+`inbox.py` are imp2's — build ON these FC stubs, don't duplicate.** Commit-ready (ledger #6). **✅ review-PASS** (S2 deep-check: membrane poisoning-oracle intact, kg additive +97/-0, no anchoring change; suite 204). **ATTRIBUTION:** this M0 = **coordinator workflow** output — the S5/S6 *terminals* are dark (their status files stale because they're not running; the code is the workflow's, not theirs). **§A(v2) multi-rater substrate — `conflict_reviews.py` T5.1** (RQ-E02 gate): ✅ **LANDED — 6/6 S2 checks pass (self-verify), 20 tests, $0** (workflow `wxlyzqclh`): server-issued reviewer_id (`secrets.token_hex`), blinded assignments + sealed pos/neg map, frozen side_order (pure fn of frozen seed), cross-process file lock (msvcrt/fcntl), blinded N-pair export, NEVER synthesizes labels. Tests = S2's 6 pre-registered checks. **🔓 `conflict_reviews.py` UNFROZEN** — T5.1 landed **additively**: the existing `conflict_reviews.jsonl` schema/behavior is UNCHANGED; T5.1 added a SEPARATE `multirater_labels.jsonl` ledger + reviewers file, so imp2/imp3 existing paths are untouched (resolves the collision concern). **Commit-ready (ledger #9). S2's §A(v2) 6-check gate now fires — independent review filed.** RQ-E02 (sign-collision vs 1-/2-verifier at ≥0.85 precision) is now unblocked — but needs REAL reviewers; if none, stop at the frozen blinded bundle (never synthesize). **Reconcile note:** S2's UNBLOCK-PLAN proposes the blinding live in a NEW `persona/conflict_gold.py` (only additive changes to S5's ledger) to minimize collision if S5 restarts mid-write; my workflow implements it in `conflict_reviews.py`. Both satisfy §A(v2) F1–F6 + the 6 checks — pick the least-collision layout at review; if S5 restarts before the workflow lands, it MUST NOT touch `conflict_reviews.py`.
- A real imp3 terminal, if it revives, reclaims Lane 2 via the board.
- **FC provider update:** FC-2/FC-3/FC-5 now provided by imp2/imp4 (+ coordinator M0), not a dead lane.

---

## 🧹 QUALITY PUNCH-LIST — S2 critique (user-reported paper/legibility defects) 2026-07-13
Full: `audits/S2-paper-quality-and-legibility-critique.md`. **`persona/deliverables/*` assigned to imp4 (Lane 3 — was unowned).** Owners re-mapped to imp-labels:
- **imp4 (deliverables):** A1 code-blocks→`listings`(wrap) · A2 headings/long-tokens→`microtype`/`url`/`seqsplit` · A3 figure min-font(≥8pt)+full-width embed · A4 1-/2-col `layout` param · A5 `**[OPEN]**`→styled badges · A6 citations renumber **contiguous** · B1 readable filenames (word-boundary, drop `latex-document-<hash>`) · A8 "Provenance & Process" section (grounded in logged events) · **D pre-ship paper lint** (blocks ship on A1/A2/A3/A5/A6/A7/A8/B1). · A7 `kg.py` year→`None` not `0` (after Lane-2 workflow frees `kg.py`).
- **imp1 (Lane 4):** A7 frontend dates → "n.d." (never 1970/epoch) · **C1 Review tab actionable** — per-conflict buttons (open dossier / request review / label / launch investigation / escalate) + **live action feed** (admitted X / flagged Y / queued Z) + clickable value-queue item.
- **imp2 (Lane 1):** C1 review-workflow actions backend (label/dossier/investigate already wired — expose to imp1).
- **idea + coord:** B2 plain-language naming convention (publish; all lanes conform) · A8 provenance-section schema design (grounded/reproducible).
- **✅ Paper-quality `deliverables` M0 LANDED** (workflow `wpmntkc2i`, **26 tests, $0**): `document.py` (A1 listings-wrap, A2 microtype/url/sloppy, A3 full-width/landscape figures, A4 1/2-col `layout`) · `paper.py` (A5 styled status badges+legend, A6 contiguous citation renumber, B1 word-boundary+ISO-date filenames) · new `paper_lint.py` (D pre-ship lint: A1/A2/A5/A6/A7/B1). **🔓 UNFROZEN → `persona/deliverables/*` is imp4's.** Commit-ready (ledger #7). **imp4 follow-ups:** (1) wire `paper_lint.lint_paper()` into `paper.py` compile path (fail a PDF that violates); (2) fix `document.py::slug_for` mid-word truncation (A6/B1 residual); (3) **compile-smoke regression test** — `compile_source` on a code-fence doc must return `ok=True` (a template break must fail a test, not silently ship no-PDF; the lesson from PQ-REG-1 below).
- **🔴→✅ PQ-REG-1 FIXED (S2 caught, S0 fixed):** the workflow's `microtype` (A2) broke **all** PDF compiles (bitmap-font sandbox → fatal). Fixed to `\usepackage[expansion=false]{microtype}` (S2-verified compiles a 24 KB PDF). **Lesson: the paper-quality workflow's verify tested LaTeX strings, not a real compile — deliverables workflows must compile-smoke.** Pending S2 recompile-confirm. **A8 (Provenance section) still needs the schema design (idea + coord) before imp4 implements.**
- **A9 (discovered by the Lane-2 verify) — Persona GENERATES syntactically-broken analysis scripts.** 12 SyntaxErrors in `personas/*/analysis/step_*.py` (positional-after-keyword `np.random.gamma(...,n)`; `sol=(n//4, n//4*?)`; `from sympy import __file__ if False else None`). Real bug in the code-run loop → **imp2** (`compile()`-validate generated code before the sandbox run — fail loud, don't run broken code) + **imp4** (sandbox returns a clear error on a non-compiling script, never silent success; the robustness auditor should flag any result built on code that didn't compile).
- **A10 (discovered by Lane-3 `value_queue`) — live KG has claims with `confidence > 1`** (had to clamp to [0,1] to avoid negative VoI). Confidence must be a probability ∈[0,1]; >1 = a write-path bug. → **imp2/imp4:** find the writer (reader/membrane) storing `confidence>1`, fix it, and add a boundary validation (fail loud at the write) so it can't recur. **[self-loop half (L-DEP-1) FIXED by S0 in `kg.py`; `confidence>1` root-cause still OPEN → imp2/imp4.]**

### A8 DESIGN — "Provenance & Process" paper section (coord+idea design; imp4 implements; workflow-queued after T5.1)
The biggest user-requested item. A structured section auto-populated from **real logged run/session data (NOT model prose)** — every number cites its source event; reproducible:
1. **Reading funnel:** N fetched → N passed relevance gate → N read → N claims extracted → **N admitted by membrane / N rejected** (reject-reason breakdown). Source: session events + membrane log. *("scale of reading, discipline of believing.")*
2. **Agent contributions:** the pipeline that ran (director → readers×N → extractor → membrane → synthesizer → auditor), each with items-processed count. Source: run/agent event log.
3. **Sources:** admitted (DOIs) vs quarantined (reasons). Source: `claims.jsonl` / `claims_rejected.jsonl`.
4. **Computations:** each sandbox run — what it checked + input/script/image **hashes** + pass/fail. Source: session artifacts (ties to I1.4 capsule).
5. **Robustness verdict:** auditor band + likelihood + interval + failing checks. Source: `audit.py`.
6. **Traceability:** each headline claim → evidence IDs → sources (grounded derivation).
**Blocked-by:** imp4 must first **scout the actual session/event schema** (what's really logged) before implementing — do NOT invent fields. A workflow will scout + implement after T5.1 lands.

---

## 🗺️ COVERAGE-AUDIT GAP MAP (workflow `w8be58zy1`, 2026-07-13) — full detail in the run output
**Root cause of ~30 gaps = the 2 DARK terminals** (imp3/Membrane, imp4/Engine): only coord-workflow M0 stubs landed; no live builder for their tails. No idea is lost; all PRDs routed. Routing:

**→ LIVE lanes, ROUTE NOW (actionable, no restart needed):**
- **imp2:** **F1.6 surprise-ranked tension queue** (the one truly-unrouted live item) · F2.5+F2.13 `conflicts.py` (`type_conflict()` + retraction_scan) · F2.12 wire `true_refutation→open_from_conflict` into inbox · F1.3/1.7/1.8 (its Next-list).
- **imp1:** **C1 actionable Review-tab UI** (buttons + live action feed; imp2 backend already wired) · **A7 frontend `n.d.` dates** · **I1.4 renderer** (start vs frozen envelope matrix) · **FL-1** floor overstates activity on halted mind (design-5 honesty) · **R-1** review dead-column layout · **L1** "eight md files"→dynamic · Lane-4 phased 4.2–4.10.

**→ DARK lanes — S0 now IMPLEMENTING via WORKTREE-isolated workflows (terminals not implementing):** batch-1 `w5okvv9rp` (6 worktree agents) building: **3.9 GEO/dataset resolution · 3.7 auditor-session · 3.8 forensics gates · 3.4 trajectory · 3.5 darklit · 2.1 dual-signal membrane.** More batches to follow (A8, D-lint, 2.6 no-inflation, 3.3, 3.1/3.2-full, I1.1-derivation, I1.4-envelopes).
**Prioritized backlog:**
- ✅ **A10/L3-CONF** confidence clamp [0,1] + **A7** kg year→None **FIXED** (belief-integrity workflow `wy0yffols`, 22 tests, fail-loud on NaN/non-numeric; membrane-poisoning + integrity suites green; review-pending, **ledger #10**). Remaining dark-Membrane: **2.6** evidence-monotonic no-inflation guard.
- 🔴 **2.1/2.2** dual-signal `admit_candidate` + exact-span `_entailment` (the "discipline of believing" headline) · **2.4/2.7/2.8/2.9/2.10** belief invariants (poisoning_signals still 0 consumers) · **2.3** real conformal thresholds.
- 🔴 **3.9** GEO/dataset resolution (Persona's acting loop can't resolve datasets to disk!) · **3.3/3.4(trajectory)/3.5(darklit)/3.7(auditor ResearchSession)/3.8(forensics DEBIT)/3.10/3.11** · **3.1/3.2 full** (beyond M0) · **I1.1 derivation core** · **A8 provenance section** · **A9 imp4 half** · **D lint-into-compile-path** · **B1 residuals** · **CE-1** matplotlib stderr (`tools/sandbox.py`).

**→ HUMAN-ONLY (the leverage):** commit the 8 ledger sets (**H1/M1 still a LIVE vuln**) · restart imp3+imp4 · (later) 2 human reviewers for RQ-E02 + expert labels for RQ-E06/E16/E17.

**→ OFF-BOARD findings now ON-board (routing gap fixed):** R-1→imp1 · FL-1→imp1 · CE-1→imp4 · L2→imp1 (frontend JS, post-pivot).

## 🎯 DISPATCH — idea lane (S1) + FC-8 answer (2026-07-13)
**→ idea/S1:** I1.3 + I1.4 both **accepted** (I1.3 imp1 built; I1.4 → imp1 renderer + imp4 envelopes). **Next idea-lane work (highest-leverage, collision-free, do now):**
1. ~~Offline eval fixture spec (I1.5)~~ ✅ **DELIVERED** (`ideas/I1.5`: frozen real-benchmark subset, hash-pinned, abstention-aware scoring, ships `n:0` if unfetchable — never fabricates gold) → **routed to imp1** (place `persona/eval/fixtures/*` + implement `run_oracle` scoring; empty fixture is fine, keeps pipeline green).
2. ~~RQ designs for the PLACEHOLDER metrics (I1.6)~~ ✅ **DELIVERED** (`ideas/I1.6`) → **imp4**: register all 4 in `docs/RESEARCH_QUALITY_PROGRAM.md`. **RQ-E15 (abstention magnitudes) is $0-runnable NOW** (synthetic policies + I1.5 fixture). **RQ-E16 (calibrate conformal) / E17 (voi vs expert) / E06 (load_bearing vs expert) need HUMAN EXPERT LABELS** — a real human-as-resolver dependency (same class as RQ-E02 blinded gold; never self-label & call it expert). **Until each RQ's gate passes, its metric stays advisory — must NOT gate autonomy** (the RQ-E12b lesson: verified computation ≠ validated interpretation).
3. Then refine the **A8 provenance-section schema** (draft on board) into a ready spec for imp4.
**→ imp1 (FC-8 envelope, answering `S3--to--S6--fc8-verdict-envelope-shape`):** the envelope shape is **frozen in I1.4 §2** — build the renderer against that matrix now; imp4 (dark) lands the real oracle envelopes later (Lane-3 M1). Coordinate the matrix via `requests/`, don't wait on imp4.

## 📈 IMPROVEMENTS LOG (shipped + verified — coordinator-maintained; newest first)
| When | Lane | Improvement | Status |
|---|---|---|---|
| 07-13 | coord | **T5.1 §A(v2) multi-rater / RQ-E02 substrate** (blinded conflict-gold: sealed sign map, frozen side_order, cross-proc lock, additive separate ledger) | ✅ **review-PASS** — S2 independent gate (200-reviewer blinding · 48-label 6-process concurrent append · tamper/dedup/determinism/no-KG) · commit-ready. RQ-E02 next = **2 real human reviewers** (else stop at frozen bundle) |
| 07-13 | coord | Lane-3 Engine M0 (FC-4 dependency_graph + value_queue, FC-6 retraction) + `engine` facade | ✅ **review-PASS** (read-only + cycle-safe verified) · L-DEP-1 self-loop guard fixed · unblocks imp1 flagship |
| 07-13 | coord | Paper-quality deliverables (listings / contiguous cites / badges / filenames / pre-ship lint) | ✅ **review-PASS** (real Docker compile, 42 KB PDF) · PQ-REG-1 caught+fixed · commit-ready |
| 07-13 | imp1 | Iteration-4: `/static` mount (P0.1) + 5 non-mutating epistemic routes (eval FC-7, dependency, value_queue, handoff, gate_decisions) | ✅ verified (147) · commit-ready |
| 07-13 | imp2 | RQ-HT01 branch-vs-linear scaffold (real step counts, paid-gated) | ✅ verified |
| 07-13 | idea | **I1.4 — FC-8 one Oracle-Verdict renderer** (honest envelope: applicability / provenance authority / sensitivity strip / reproduction capsule / control quarantine / high-stakes→human) | ✅ accepted → imp1 renderer (scaffold vs frozen envelope matrix) + imp4 oracle envelopes (Lane-3 M1, dark → future workflow). **FC-8 accepted as a contract addition.** |
| 07-13 | imp1 | Iteration-5 abstention-aware scoring (RQ-E15: correct>abstain>wrong — rewards honest uncertainty) | ✅ verified |
| 07-13 | coord | **Lane-2 Membrane M0** (FC-2 inbox / FC-3 kg APIs / FC-5 calibrate + M2 watchlist floor) | ✅ **review-PASS** · membrane intact · commit-ready |
| 07-13 | imp1 | **Flagship 4.1** (Field-rests-on-this dep-map + value queue; no invented scores — server-value passthrough) + FC-7 eval oracles | ✅ verified (132) · commit-ready · fixtures |
| 07-13 | imp1/imp4 | **H1 durable-self jail + M1 clone-SSRF** (security) | ✅ double-verified · commit-ready · deploy = commit + restart :8137 |
| 07-13 | imp2 | **Lane-1 FC-1**: `open_from_conflict`, verify/debate queue, `span_weighted_consensus` (protected dissent) | ✅ verified · commit-ready |
| 07-13 | imp2 | F1.1 branch/DAG investigations (real-queue join, byte-identical fallback) | ✅ verified (127) · commit-ready |
| 07-12 | imp2 | RQ-E06 qualifier extraction + evidence-tree exp; E07c team-physics harness (budget-gated) | ✅ verified |
| 07-12 | imp2 | T4.1 investigate finalizer (no session stuck `running`) + regression test | ✅ verified · commit-ready |
| 07-12 | review | Frozen-core audit: anchor write-policy + reader purity **SOUND** (poisoning oracle holds) | ✅ verified |
| — | all | **Test floor 46 → 232 passing** | ✅ |

---

# 🔀 SCHEME PIVOT — 2026-07-12 · ALIGN TO PRD (user-decided). Lanes retitled imp1–imp4 above.

**Authoritative now:** `docs/prd/PRD-00…04` + **FC-1…FC-7** + the HANDOFF `2026-07-12 Feature-expansion` dispatch bus. The module `LANES.md`/§A/§B are being re-mapped onto the PRD. **KEEP the live ops layer:** this board, the monitor, the S2 review lane, the scoped-commit rule.

**✅ CONFIRMED lane→terminal map (human authorized 2026-07-12 — "proceed"). ROLES: idea=S1 · review=S2 · imp1=S3 · imp2=S4 · imp3=S5 · imp4=S6.**
| Terminal | was | → PRD Lane | Owns (PRD-00 §3) |
|---|---|---|---|
| **S3** (Fable) | frontend | **Lane 4 — Legibility (flagship)** | `api/app.py` (new routes), `api/static/index.html` (surfaces), `sessions.py` (RO-Crate add), `eval/*`, `experiments/*` (new), `tests/*` (new) |
| **S4** (Sonnet) | engine | **Lane 1 — Teams** | `agents/{verifier*,debate*,analyst,critic,revisit,director,discover,deliberate}`, `research/investigation.py`, `daemon/{supervisor,queue}`, `reading/{extract,reader}` |
| **S5** (Sonnet) | data | **Lane 2 — Membrane** | `memory/{membrane,kg,coherence,history,vectors,calibrate*,conflicts*}`, `conflict_reviews.py`, `inbox.py*` |
| **S6** (Sonnet) | api | **Lane 3 — Engine** | `analysis/{forensics,dependency*,trajectory*,value_queue*,darklit*}`, `agents/audit.py`, `synthesis/{fieldmap,synthesizer,consolidator}`, `ingest/{sources,retraction*}`, `tools/{science,datasets}` |
| **S1** (Fable) | brainstorm | **Ideation / PRD** (authored PRD-00) | `docs/prd/*`, `ideas/*` |
| **S2** (Opus) | review | **Reviewer** | `audits/*`, `tests/test_audit_*` |

**DURING TRANSITION — until the map line says CONFIRMED:**
- **KEEP working files that STAY in your lane** (unambiguous): S5→`memory/*`+`conflict_reviews.py`, S4→`agents/{analyst…}`+`reading/`+`research/`, S3→`index.html`, S6→`synthesis/*`.
- **🧊 FREEZE files whose owner CHANGES under the re-map — no edits until CONFIRMED:** `api/app.py` (S6→S3), `daemon/*` (S6→S4), `ingest/*`+`tools/*` (S5→S6), `analysis/*` (S4→S6), `agents/audit.py` (S4→S6). Do NOT discard in-flight uncommitted edits to these; hold them.
- **Contracts:** FC-1…FC-7 (PRD-00 §4) replace §A/§B. §A(multi-rater) → maps to Lane 2 conflict-typing + FC-2 inbox. §B(qualifiers) → Lane 1 `extract` emit + Lane 3 dependency consume.

**Re-routed findings (fix the $0 ones now; frozen-file ones resume on CONFIRMED):**
- **Budget-churn M2** (`0a6f923` re-audit busy-loop, $0 — personas halted): `memory/watchlist.py` add `due(min_age_hours=12)` → **Lane 2 / S5**; `daemon/supervisor.py` guard `due() is not None` → **Lane 1 / S4** (daemon frozen till CONFIRMED — S4 stage the guard, land on confirm). + regression test.
- **H1 (run_shell writes durable self) + M1 (clone SSRF):** `app.py` → **Lane 4 / S3**; `tools/sandbox.py` → **Lane 3 / S6**. Both frozen till CONFIRMED, then TOP priority.

## TRANSITION TICK — 2026-07-12 (map pending human confirm; keep unambiguous work moving)
- ✅ **Frozen files: none touched** — clean transition, no collisions.
- **S4 (→Lane 1) cleared its whole queue** (T4.1+T4.2+RQ-E06 a/b + team-physics harness — green, $0). **NEXT ($0, unambiguous — `agents/`+`research/` are yours under both schemes): Lane-1 Milestone-0 FC-1 stubs.** Land exact signatures + typed fixture returns for: `investigation.open_from_conflict(conflict_id, evidence_claim_ids=None) -> Investigation`; queue task types `"verify"`,`"debate"`; consensus record `{claim, admit_votes:int, weighted_support:float, dissent:[{claim_id,span,weight}]}`. Interface-first → unblocks Lanes 2/3. Then hold for CONFIRMED to fill implementations.
- **🔴 S5 (→Lane 2) STILL PARKED** (status frozen 23:04, no code). **TOP BOTTLENECK** — Lane 2 (membrane/epistemic core) is dark and blocks: multi-rater, the budget-churn `watchlist` fix, and S4's 2 open contract requests. **Needs the human to restart its loop / give it a turn — a parked session can't read this board.**
- **S6 (→Lane 3):** status stale (23:04). `synthesis/*` stays yours (unambiguous) — work there meanwhile; `analysis/audit/ingest/tools` land on CONFIRMED. Post your status.
- Requests: `p02-lines` → RESOLVED (drift-proof extraction). `qualifier-emit-shape` + `reaudit-staleness` (S4→S5) → **blocked on parked S5**; S0 acks via FC/§B once S5 is live.

## ✅ MAP CONFIRMED — DISPATCH (2026-07-12, human said "proceed")

**Roles locked:** idea=**S1** · review=**S2** · imp1=**S3**→Lane 4 · imp2=**S4**→Lane 1 · imp3=**S5**→Lane 2 · imp4=**S6**→Lane 3. `LANES.md` rewritten to PRD-00 §3. **FC-1…FC-7 (PRD-00 §4) are the contract layer; §A/§B retired into them.**

**🔓 UNFROZEN — new owner takes each now (preserve in-flight uncommitted edits, continue them):** `api/app.py`→**S3(L4)** · `daemon/*`→**S4(L1)** · `ingest/*`+`tools/*`→**S6(L3)** · `analysis/*`→**S6(L3)** · `agents/audit.py`→**S6(L3)**.

**Milestone-0 FIRST (every lane): land your *provided* FC stubs — exact signatures + typed fixture returns — commit-in-place so the others build against them from hour 1** (PRD-00 §5). Then first-fill:
- **imp2/S4 · Lane 1** provides **FC-1**. Fill: **1.10 `open_from_conflict`** (unblocks L2/L3) → 1.2 verifier. Your T4.1/RQ-E06/team-physics fold in as Lane-1 assets. Also owns `daemon/` now → stage the budget-churn guard.
- **imp3/S5 · Lane 2** provides **FC-2, FC-3, FC-5**. Fill: **2.5 conflict-typing + 2.11 provenance API** (unblocks L4) → 2.3 calibrate. Your §A multi-rater work = the conflict-typing substrate. Also `memory/watchlist.py` min-age (budget-churn). ⚠️ **PARKED — needs restart.**
- **imp4/S6 · Lane 3** provides **FC-4, FC-6**. Fill: **3.1 dependency + 3.2 value_queue** (unblocks flagship) → 3.6 retraction. Consumes FC-3 stubs from S5. Now owns `tools/sandbox.py` → the M1 SSRF + H1 sandbox side. ⚠️ **PARKED — needs restart.**
- **imp1/S3 · Lane 4** provides **FC-7**. Fill: **flagship 4.1** (Field-rests-on-this dep-map + value queue) vs FC-4 fixtures + **4.8 benchmarks** (self-contained). Owns `app.py` now → **H1 (run_shell durable-self) + M1 (clone SSRF) is yours, TOP priority.**

**Read your own `docs/prd/PRD-0X.md` for the full feature list.** Acceptance unchanged: real test + evidence per feature; 46→57 test floor; `$0`/`PERSONA_WORKERS=0` until budget greenlight; commit only on human OK, lane-scoped.

## 🔒 SECURITY STATUS — H1/M1 FIXED-IN-CODE, **NOT LIVE** (2026-07-13)
- **H1** (run_shell durable-self write) + **M1** (clone SSRF) → **FIXED + S2-verified PASS** (`_jail_shell_cwd`, `_GIT_URL_RE`; 18 jail + 7 URL cases correct; H2 shim-litter also mitigated).
- **⚠️ NOT LIVE:** uncommitted (HEAD `0a6f923`) + the :8137 server is stale (no hot-reload) → **the OLD vulnerable `run_shell` is still being served.** To close the live HIGH vuln: **(1) human authorizes a scoped commit** (`app.py` + regression test), **(2) restart :8137.**
- **Regression test EXISTS + verified:** `tests/test_app_security.py` → **35 passed**; full `pytest -q` → **118 passed** (floor 57→118); compileall 0. Double-verified (S6 self + S2 independent).
- **COMMIT-READY (awaiting human auth):** lane-scoped `git add persona/api/app.py tests/test_app_security.py` — never `-A`. Then **restart :8137** to make it live. Request `shell-writes-durable-self` = **VERIFIED, pending deploy**.
- **Attribution note:** S6 did this H1/M1 fix on `app.py` pre-pivot; **`app.py` is now S3/Lane 4** — S3 owns it going forward, S6 → Lane 3 (`analysis/synthesis/audit/tools`). S6: update `status/S6` (stale at 23:04 despite this work) and start Lane-3 FC-4/FC-6.
- **P0.1 `/static` mount → NOW imp1's own task (imp1 owns `app.py` under Lane 4).** imp1's flagship JS (`field/ui/focus.js`) is stranded in fixtures until served → **imp1: add the `StaticFiles` mount to `app.py` (build on the uncommitted H1/M1 fix already there — commits together as one Lane-4 scoped commit), then wire the modules into `index.html`.** No longer cross-lane / no longer blocked on anyone. (The full Wave-0 CSS/JS *split* stays deprioritized — single owner, no parallelism need.)
- **Still open:** M2 reaudit-staleness (S5 `watchlist.due` min-age + S4 `daemon/supervisor` guard). **S5/Lane 2 still shows no code — the one genuinely-dark lane; restart needed.**

## 📦 COMMIT-READY LEDGER (S2-verified · $0 · 118 tests pass · awaiting human auth — lane-scoped, never `-A`)
1. **Security H1/M1** → `persona/api/app.py` + `tests/test_app_security.py`. Closes live HIGH vuln (also **restart :8137** to deploy).
2. **S4 / Lane-1 FC-1 + M2-daemon** → `persona/research/investigation.py` · `persona/daemon/queue.py` · `persona/daemon/supervisor.py` · `persona/agents/consensus.py` + their tests. Unblocks L2/L3 (FC-1 live) + the daemon half of M2.
3. **S4 earlier** (T4.1 finalizer + RQ-E06) → `persona/agents/analyst.py` · `persona/reading/extract.py` + tests + `experiments/exp_rq_e0{5,6,7c}*` + `results/*`.
4. **imp1 flagship 4.1 + FC-7** → `persona/api/static/js/{field,ui,focus}.js` · `persona/eval/*` · `focus-demo.html` + `tests/test_fe_field.cjs` · `test_fe_focus_render.cjs` · `test_eval_oracles.py`.
5. **imp2 F1.1 branch/DAG** → `persona/research/investigation.py` + `tests/test_investigation_branch.py`.
6. **Lane-2 M0** → `persona/memory/{kg,calibrate,watchlist}.py` · `persona/inbox.py` + `tests/test_data_{fc3_kg,fc5_calibrate,fc2_inbox,m2_watchlist}.py`.
7. **Paper-quality M0** (incl. PQ-REG-1 fix + stale-test fix) → `persona/deliverables/{document,paper,paper_lint}.py` + `tests/test_deliv_{document_quality,paper_quality,paper_lint}.py`.
8. **Lane-3 M0** → `persona/analysis/{dependency,value_queue,engine}.py` · `persona/ingest/retraction.py` + `tests/test_engine_fc4_{dependency,value_queue}.py` · `test_engine_fc6_retraction.py`. (+ `kg.py` L-DEP-1 self-loop guard.)
9. **T5.1 multi-rater** → `persona/conflict_reviews.py` (additive) + `tests/test_data_multirater_t51.py` (pending S2 §A(v2) gate).
→ On `commit` (or `commit security` / `commit all`) S0 commits these in order, scoped. HANDOFF: only on human OK.
→ **imp1:** FC-4 is real now — wire the `engine/dependency` + `engine/value_queue` routes to `from persona.analysis import engine; engine.dependency_graph(topic)` / `engine.value_queue(topic)` (was returning `available:false`). Flagship goes live end-to-end.
→ **`analysis/*` + `ingest/*` UNFROZEN → imp4's** (build on the FC-4/FC-6 stubs).

**→ S4 (non-blocking follow-up):** confirm the `"staleness"` queue task type is defined in `daemon/queue.py` — FC-1 lists 3 types, S2 verified only `verify`+`debate`.

---

Legend: ▶ active · ⛔ blocked (waiting on dep) · ✅ READY (tests green, awaiting S0/human commit) · 🔬 needs S2 audit

---

## COORDINATOR RESPONSES — 2026-07-12 (dispatch ack; re-read your section)

**All lanes: LANES.md + `prompts/S{n}-*.md` now exist — you are unblocked. Boot and execute your current task.**

- **→ S3:** your +3 line-drift recon is accepted as **canonical** — the P0.2 row below now uses your numbers (CSS content L11–586, JS content L873–2070; replace `<style>` L10–587 and `<script>` L872–2071; `defer` approved). Your S6 one-liner FYI is correct; posted to S6. Proceed the instant `status/S6 = ✅ P0.1`.
- **→ S4:** first task is **T4.1 (investigate finalizer + regression test) — it is $0, no paid calls, start immediately.** Then **T4.2 = SCAFFOLD ONLY** (harness + fixtures + seeds wiring) at $0. **Any live/paid model run (swarm-physics live trial, RQ-E05 eval execution) is GATED on explicit human budget + a live model-name/cost probe — do NOT spend yet.** Confirmed: `persona/agents/**` + self files are **yours alone** this cycle; no other lane edits them.
- **→ S1:** provisional mapping in `ideas/001` is **correct** — conflict substrate → **S5** (T5.1/T5.2), API → **S6** (T6.1), UI → **S3** (T3.2). `ideas/001` is now the **design input for S5's T5.1**; S5 reads it. Keep producing down the §7 list: next = **I1.1 (Map view + evidence-tree RQ-E06)**, then I1.2. Don't over-produce past I1.2 until S0 triages.
- **→ S5:** read `ideas/001-multirater-conflict-substrate.md` (S1's architecture) before starting T5.1; build to **§A** below.
- **→ ALL:** paid model calls require human budget authorization + a live model probe (never trust a `config.py` name). Default everything to `PERSONA_WORKERS=0`, $0, until S0 posts a budget greenlight here.

---

## COORDINATOR TICK 2 — 2026-07-12 (keep all 6 moving; work divided, no overlap)

**Who is active on what — all $0, start/continue NOW:**
- **S6 ▶ P0.1 is the KEYSTONE — do it first, this instant.** It unblocks S3 (P0.2) *and* S2 (P0.3). Use S3's verified one-liner: add `from fastapi.staticfiles import StaticFiles` + `app.mount("/static", StaticFiles(directory=_STATIC), name="static")`. Post `✅ P0.1`. Then T6.1 endpoints (§A).
- **S4 ▶ T4.1** (investigate finalizer + regression test) — pure $0, independent. Should be coding now; confirm in `status/S4`.
- **S5 ▶ T5.1** (multi-rater layer) — **read `ideas/001-multirater-conflict-substrate.md` first** (S1's architecture), then code to §A, $0. Confirm in `status/S5`.
- **S3 ▶ PARALLEL non-blocking task while P0.1 pends (do NOT idle):** prototype `static/js/focus.js` + `static/js/ui.js` as standalone modules driven by **mock data** — the Focus-view stream (T3.1) + blinded-review UI (T3.2, contract §A). Pure new files in your lane; **do not touch `index.html`/`app.py`**, do not wire in until P0.3 clears. This makes T3.1/T3.2 drop-in-ready the moment Wave 0 finishes.
- **S1 ▶** ship **I1.1** (Map view + evidence-tree RQ-E06) to `ideas/` now. `ideas/001` accepted → it's S5's input.
- **S2 ▶** baseline frozen. Standing suite on every `✅`.

**Regression floor: `pytest` must stay ≥ 46 passed** (S2's real baseline; stale docs said 20). A drop = the committing lane's regression → S2 flags, owner fixes before commit.

**:8137 orphan — RESOLVED, do NOT kill.** Idle (zero cost writes in 15 min, ~157 MB RSS) → harmless; may be a live UI window. For the P0.3 gate, **S2 launches its clean `PERSONA_WORKERS=0` server on :8138**: in `tests/ui_research_smoke.cjs` (your file) change hardcoded `127.0.0.1:8137` → `process.env.PERSONA_SMOKE_BASE || 'http://127.0.0.1:8137'`, run with `PERSONA_SMOKE_BASE=http://127.0.0.1:8138`. Sidesteps the orphan; no process killed.

---

## COORDINATOR TICK 3 — 2026-07-12 · I1.1 TRIAGED → **ACCEPTED** (Wave 2, on-deck; must NOT preempt Wave 1)

`ideas/I1.1` (Map + evidence-tree RQ-E06) is accepted — grounded in real `kg.py`/`checker.py`, defends novelty vs scite/PaperQA2/OpenTargets/MedKGent/KARMA, has falsifiable gates + no-go + anti-gaming guard. Lane split confirmed (matches LANES.md). **Queue as each lane's ON-DECK — start only when that lane posts its current Wave-1 slice `✅`. One active task per lane; no concurrent overload.**

- **S4 on-deck:** qualifier extraction in `reading/extract.py` (exact-span, additive, **$0**) + `experiments/exp_rq_e06_evidence_tree.py` (≥20 seeds; paid synthesis arm **budget-gated**).
- **S5 on-deck:** `Claim.qualifiers` in `memory/kg.py` (additive — identity stays `subject|object|sign`, convergence preserved) + derivation nodes/edges (`SynthesisStatement`, `InferenceStep`, `VIA`/`FROM_PREMISE`) + qualifier-compatibility rule (**$0**, deterministic).
- **S6 on-deck:** derivation-constrained synthesizer folding `checker.py` into a *structural* unsupported gate + Map export in `graph.js`/`map.js`. **Derivation extraction may be a 2nd paid pass → budget-gated; measure token cost vs the current single Haiku checker (I1.1 §7).**
- **S3 on-deck (after P0.4):** Map shell + 3 projections (Argument/Evidence/Trajectory). Coordinate the `map.js` data↔shell seam with S6 via `requests/`.

**§B — FROZEN qualifier contract (S4 extracts → S5 stores; changes only via `requests/…--to--S0`):**
```
Claim.qualifiers = { population, model_system ∈ {in_vivo,in_vitro,post_mortem,cohort},
  direction ∈ {+,-,na}, magnitude, timepoint, n:int|null, qual_source: exact_span_ref }
```
6 fields frozen. Every qualifier MUST cite an exact source span or it's rejected (RQ-E01a discipline). Incompatible qualifiers on same-identity claims = `context_divergence` (ties to §A conflict labels).

**→ S1:** I1.1 accepted. Produce **I1.2** (equal-token team-physics trial) next, then **hold** for triage — do not run past I1.2.

---

## COORDINATOR TICK 4 — 2026-07-12 · 🔴 SECURITY HOTFIX + §A→v2 + I1.2 accepted

**§A patched to v2** (below) folding S2's F1–F6. **S5/S6/S3: re-read §A(v2); stop building against v1.**

**🔴 PRIORITY HOTFIX — S2 live-proved a frozen-contract breach in committed code** (`audits/S2-audit-2026-07-12-codelab-studio.md`). This is the "worst possible bug" class (belief-state mutated outside the membrane) — jump the queue:
- **H1 (HIGH) → S6 owns fix (`app.py`), S5 owns `tools/sandbox.py`:** `run_shell` mounts the durable self **rw**; a shell cmd while viewing `self/` overwrites `beliefs.md` outside the membrane (proven: `_run.py` written into `curie-3c33/self/`). **Fix at root, one place:** jail `run_shell` cwd to scratch dirs (`repos/ uploads/ code/ runs/ datasets/`); reject `self/ notes/ sources/ drafts/ projects/ deliverables/ investigations/`. Regression test: `cwd=self` → refused. **S6 order: P0.1 (30s, unblocks S3/S2) → H1 → M1 → then T6.1.** If the fix needs the sandbox mount made ro / scratch-copied, S6 files `requests/…--to--S5` — coordinate, don't cross-edit `sandbox.py`.
- **M1 (MED SSRF) → S6:** `clone_repo` regex `[\w.-]+` catch-all matches any host (169.254.169.254 metadata, internal). Drop the catch-all; keep explicit allowlist. Test: metadata/internal host → rejected.
- **H2 (LOW) → S6:** `run_python` leaves `_run.py`; clean up post-run.
- **L1 (LOW) → S3:** `index.html` says "eight markdown files"; self has 7 → make it dynamic.
- **L2 (LOW) → S6:** studio `length>200||\n` routing heuristic → explicit toggle.
- **WATCH (not a defect, needs repro):** possible cross-persona view leak (Euclid PID shown once in Curie, not reproduced). S3+S6: deliberate repro pass on view-state when you touch those surfaces.

**I1.2 (team-physics live trial) ACCEPTED — fully budget-gated.** Deliver the **frozen harness + preregistration now ($0)** as **S4 on-deck-2** (after RQ-E06); live execution waits for human budget + a live cost probe. S1's small-B pilot is the circuit breaker.

**→ S1:** I1.1 + I1.2 accepted. **Hold new proposals** until S0 requests. **→ S2:** exceptional work — run your 6 §A checks + the H1 regression on the relevant `✅`.

**Commit note:** the H1/M1 security fix, once S2-verified, should be committed promptly (scoped to `app.py` + its test) — S0 will ask the human to authorize that specific commit.

---

## COORDINATOR TICK 5 — 2026-07-12 · ATTRIBUTION + reconcile uncommitted work + S5 nudge

**Working tree is dirty across lanes** (uncommitted): `agents/analyst.py`, `agents/audit.py`(+174), `agents/mywork.py`, `api/app.py`, `api/static/index.html`(+14 audit-UI), `daemon/supervisor.py`, `daemon/worker.py`, `results/FINDINGS.md`, `tests/ui_research_smoke.cjs`. Looks like in-flight **robustness-auditor** work (calibration prior + adversarial red-team) spanning S4/S3/S6 lanes. **DO NOT discard or reset anyone's changes.**

- **ATTRIBUTION — every lane, in your `status/S{n}`, list the exact working-tree files you currently hold uncommitted edits in.** S0 needs this to detect two sessions on one file. If a file above isn't claimed by anyone in 1 sweep, S0 flags it to the human as orphan uncommitted work.
- **`index.html` is dirty (audit-UI edits) but frozen.** Whoever holds those edits: claim them. **S3's P0.2 must extract the CURRENT index.html content** (behavior-preserving works on current bytes). **Nobody else edits `index.html` until its holder is named + P0.3 clears.**
- **`app.py` is dirty.** S6: your P0.1 mount + H1 jail land on top of the current app.py — confirm the +18 uncommitted lines are yours before adding more, else file `requests/…--to--S0` to reconcile.
- **`results/FINDINGS.md` (S0-owned) was edited by a lane** — whoever appended a finding, note it in status; shared-file edits route through S0 (I'll fold legit findings, but don't edit it directly again).
- **🟡 S5 — are you looping?** Your status is stale (23:04) and `conflict_reviews.py` is untouched. **T5.1 (multi-rater, build to §A-v2) is critical-path Wave-1.** Post status + start now. If you're not receiving turns, the human will restart your loop.
- **S4 / S6:** you're clearly working (tree shows your edits) — **post `status` on every `✅`** so S2 gates and S0 authorizes the scoped commit. Heads-down is fine; just checkpoint on completion.

---

## COORDINATOR TICK 6 — 2026-07-12 · S4 ✅ VERIFIED (T4.1 + T4.2) → advance to RQ-E06

- **S2 gated S4: PASS** (`audits/S4-T4.1-T4.2.md`). Suite **57 passed** (46→57, floor held). T4.1 finalizer = full-body guard + genuine oracle test (no session left `running`); T4.2 RQ-E05 = $0 scaffold, paid stages hard-gated, 2 real wiring bugs caught by self-check. No CONTINUATION §10 violations.
- **COMMIT-READY (awaiting human auth):** lane-scoped —
  `git add persona/agents/analyst.py tests/test_engine_investigate_finalizer.py experiments/exp_rq_e05_retrieval.py tests/test_engine_e05_scaffold.py results/rq_e05_retrieval.json results/rq_e05_retrieval.png` — **never `-A`.** Committing now also **de-risks the mixed dirty tree** (isolates S4's clean slice from the uncommitted auditor work). S0 surfacing to human.
- **S4 next (ACTIVE): Wave-2 RQ-E06 qualifier extraction** in `reading/extract.py` (exact-span additive, **$0**, build to **§B**; S5 stores — coordinate the seam via §B, not by editing `memory/`). I1.2 team-physics harness stays on-deck-2 (budget-gated). Post `status/S4` on pickup.

---

## WAVE 0 — `index.html` split (BLOCKING, strictly sequenced). Do this before any other frontend work.

| Step | Lane | Task | Gate |
|---|---|---|---|
| P0.1 | **S6** ▶ | Add a `StaticFiles` mount for `/static` in `app.py` (there is **none** today). Drop `static/health.txt`; assert `GET /static/health.txt` → 200. Keep root `/` still serving `index.html`. | tests green → set `status/S6 = ✅ P0.1` |
| P0.2 | **S3** ⛔(needs P0.1) | Behaviour-preserving extraction ONLY (S3's canonical lines, index.html=2073 L): CSS content **L11–586** → `static/css/app.css`; JS content **L873–2070** → `static/js/app.js`; replace `<style>` L10–587 + `<script>` L872–2071 with `<link href="/static/css/app.css">` + `<script src="/static/js/app.js" defer>`. **No logic changes.** Do NOT touch `index_v6_backup.html`. | `status/S3 = ✅ P0.2 🔬` |
| P0.3 | **S2** ⛔(needs P0.2) | Browser byte-check: `tests/ui_research_smoke.cjs` + Playwright screenshot before/after. Assert render identical + zero new console errors. **Only S2 clears Wave 0.** | `audits/P0-static-split.md` + `status/S2 = ✅ or ✗` |
| P0.4 | **S3 + S6** ⛔(needs P0.3) | Split `app.js` → `notebook.js`+`anim.js`+`ui.js` (**S3**) and `graph.js`+`api-client.js` (**S6**). After this, S3 & S6 edit disjoint frontend files → parallel-safe. | each sets `status = ✅ P0.4` |

**Until P0.3 clears, `index.html` + `app.py` are frozen to S3/S6 respectively; no other UI edits.**

---

## WAVE 1 — real slices (start the parts that don't depend on Wave 0 NOW; frontend parts wait for P0.3)

### S4 — ENGINE  ▶ start now (independent of Wave 0)
**T4.1 (safety, bounded, first):** add a failure finalizer to `persona/agents/analyst.py::investigate` so an unexpected model/FS exception → session marked **invalidated**, never left `running`. Add regression test `tests/test_engine_investigate_finalizer.py` that injects an exception mid-investigation and asserts the session ends `invalidated` + replay still verifies. (CONTINUATION §4 follow-up.)
**T4.2 (after T4.1):** scaffold RQ-E05 real-retrieval harness under `experiments/exp_rq_e05_retrieval.py` — iterative retrieval + reranking + citation traversal + exact-span verification over Persona questions (+ LitQA2 if fixture available). Metrics: correctness, citation precision/recall, abstention, primariness, cost, latency. **Experiment-first per AGENTS.md §2 (≥20 seeds where stochastic).** No deployment claim yet.

### S5 — DATA  ▶ start now (THE best next slice — CONTINUATION §11)
**T5.1:** build the **multi-rater conflict-review acquisition layer** in `persona/conflict_reviews.py`: pseudonymous reviewer IDs, blinded assignment/batch IDs, fixed **randomized side order**, duplicate-review prevention (per reviewer/conflict/batch), and a **cross-process OS file lock** (replace the process-local lock). Preserve the append-only hash chain. Test concurrent appends + tamper refusal (`tests/test_data_conflict_multirater.py`).
**T5.2:** blinded export: freeze **20 stratified candidate pairs**; write the blinded bundle with hashes **frozen before collection**. **NEVER synthesize labels.** If no real reviewers exist, stop at the frozen bundle + hand the UI workflow to S3.
→ Build against **FROZEN CONTRACT §A below.** Coordinate schema changes with S6/S3 via `requests/`, not by editing their files.

### S6 — API/SYNTH  ▶ after P0.1, run in parallel with your Wave-0 duties
**T6.1:** endpoints for the multi-rater layer (per **§A**): `GET /api/review/assignment?reviewer=` (blinded next pair, randomized side order), `POST /api/review/label` (append one of 4 non-mutating labels; reject duplicates), `GET /api/review/verify` (ledger hash-chain status). Endpoints **never anchor the KG.** Tests `tests/test_api_review.py`.
**T6.2 (later):** executable-paper session→LaTeX slice (RQ-E12) using the repaired deterministic compiler (`deliverables/paper.py` + `tools/sandbox.py`). Exact claim citations, numeric reproduction, clean rerun gate.

### S3 — FRONTEND  ⛔ blocked on P0.3 for new UI; after that:
**T3.1:** **Focus view** — living notebook (timestamped real moves) + "next decisions" list. Remove synthetic metrics, fake ambient agents, "raises/lowers" wording on every surface you touch.
**T3.2:** **blinded review workflow UI** (consumes §A + S6 endpoints): show why the pair was raised, both exact evidence packets, missing PICO/context fields, discriminating checks, the 4 non-mutating labels, **randomized side order preserved**. No KG mutation from the UI.

### S1 — BRAINSTORM  ▶ start now
**I1.1:** spec the **Map view** (argument / evidence / trajectory graph) + **evidence-tree design (RQ-E06)**: atomic claims w/ qualifiers + explicit premise→inference edges; target ≥50% fewer unsupported synthesis statements + ≥10-pt qualifier-recall gain. Drop `ideas/I1.1-map-and-evidence-tree.md` — a real design contract (data model, interactions, novelty vs scite/PaperQA2/MedKGent), not vibes. S0 triages into S3/S5 tasks.
**I1.2:** design the **equal-token large-team-physics live trial** (parallel breadth vs sequential reasoning, hierarchical cells, DAG handoffs, reducer bottleneck, marginal-evidence stopping). Metric = effective team size + validated novelty, NOT agent count. → `ideas/I1.2-team-physics-trial.md`.

### S2 — REVIEW  ▶ standing job + first gate
**R2.0 (first):** gate Wave 0 (P0.3 above).
**R2.STANDING:** on every lane `✅`, run the verification suite and report to `audits/`:
`python -m pytest -q` · `python -m compileall -q persona experiments` · `git diff --check` · `verify_conflict_reviews(...)` · `ui_research_smoke.cjs` (with `PERSONA_WORKERS=0`, no paid calls). Cross-check against the "claims the next agent must not make" list (CONTINUATION §10). File one `audits/<lane>-<slice>.md` per review: PASS / findings (severity-tagged) / repro.

---

## §A (v2) — FROZEN CONTRACT: multi-rater conflict-review record  [amended per S2 F1–F6, 2026-07-12]

S5 store · S6 API · S3 UI. Any change = `requests/…--to--S0`. **v2 SUPERSEDES v1 — build against THIS; re-read if you started on v1.**

```
assignment_id  = sha256(canonical_json[batch_id, conflict_id, reviewer_id])   # (F4) 1:1; both lanes import ONE shared helper
reviewer_id    = server-issued opaque token, allocated at enrolment            # (F5) NEVER client-chosen free text

# FROZEN AT BATCH-FREEZE from a recorded seed, hashed into the manifest (deterministic, NO wall-clock):
BlindedAssignment = { assignment_id, batch_id, conflict_id, reviewer_id, schema_version,
                      packet_A, packet_B }   # packets ALREADY permuted per the sealed side_order
   # (F1) side_order is APPLIED to which claim becomes A vs B — it is NOT a served field.
   #      The A/B↔pos/neg map is SEALED server-side keyed by assignment_id, in NO reviewer-visible field.
   #      No served field (packet text/order, conflict_id, discriminating_checks) may correlate with stored sign.
   # (F3) S6's GET /api/review/assignment READS the frozen assignment; it never mints side_order per request.

# COLLECTED LIVE (post-freeze, outside the frozen manifest):
ReviewLabel = { assignment_id, reviewer_id, batch_id, conflict_id, schema_version,   # (F2) dedup keys denormalized ON the label
                label ∈ {extraction_error, true_refutation, context_divergence, insufficient_evidence},
                rationale, ts }   # (F6) ts is the ONLY live/wall-clock field

Ledger     = append-only, hash-chained, canonical-JSON, fsync; CROSS-PROCESS OS file lock (not threading.Lock); NO KG mutation ever.
Invariants = exactly one label per (reviewer_id, conflict_id, batch_id), enforced from the label's own denormalized keys
             + verified against the sealed assignment on append; export+manifest hashes frozen BEFORE collection;
             labels NEVER synthesized; the server-side pos/neg map never appears in any served field.
```
S2 will run 6 pre-registered checks on `✅`: blinding-correlation ≤ chance · duplicate-reject 4xx+no-append · multi-process concurrent append · tamper refusal · seed→byte-identical determinism · KG-snapshot-hash unchanged.

## Global rules (all lanes)
- Edit only your `LANES.md` files. Commit only your lane, scoped `git add <paths>`, **never `-A`**. Commit only when the human authorizes.
- Real test + pasted evidence before `✅`. Non-trivial modeling choice → AGENTS.md science loop first.
- Blocked / colliding / need another lane? → write it in your `status` + a `requests/` note. S0 unblocks.
