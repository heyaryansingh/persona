# S2 — REVIEW · status
Model: Opus 4.8 · xhigh. Write ONLY this file. Current task: see `status/S0-coordinator.md` → R2.0 then standing suite.

| ts | state | note |
|---|---|---|
| — | ▶ awaiting boot | first gate = Wave 0 P0.3 |
| 07-12 boot | ✅ baseline frozen | `audits/S2-baseline.md`: pytest **46 passed**/30s · compileall 0 · `git diff --check` clean · `verify_conflict_reviews` ok/0 records |
| 07-12 boot | ✅ P0.3 tooling ready | smoke.cjs + node + playwright + Chrome/Edge all present; smoke = behavior-preservation oracle (also catches 404 on split assets) |
| 07-12 boot | ⛔ R2.0 blocked | P0.3 waits on **P0.1 (S6 mount)** → **P0.2 (S3 extraction)**. Neither started (app.py no mount; index.html monolithic 2073L) |
| 07-12 boot | 🔬 flag→S0 | **:8137 already LISTENING (PID 26092 = `python -m persona --port 8137`), worker-state unknown → may burn budget.** S2 won't kill it. See audit "Flag to S0". |

| 07-12 c1 | 🔬 audit cycle 1 | reviewed newest 3 commits (07c4f27/deec46c/c26ff7e) + live browser drive on curie-3c33. **1 HIGH, 1 MED, 3 LOW.** → `audits/S2-audit-2026-07-12-codelab-studio.md`; filed `requests/S2--to--S6--shell-writes-durable-self.md` |
| 07-12 c2 | ✅ §A contract pre-review | adversarial review of frozen §A + `ideas/001` BEFORE S5/S6/S3 build → **3 HIGH gaps** (blinding leak, label missing dedup key, side_order not frozen). → `audits/S2-contract-review-A.md`; filed `requests/S2--to--S0--contract-A-gaps.md` |
| 07-12 c2 | ✅ P0.3 unblock | S0 resolved orphan :8137 (idle, don't kill). Parameterized `ui_research_smoke.cjs` → `PERSONA_SMOKE_BASE` env; gate runs on **:8138**. `node --check` OK. |
| 07-12 c2 | 👁 monitor ARMED | persistent board-watcher live: auto-wakes on any lane ✅ · S0 directive · req--to--S2 · `app.py` edit (P0.1/H1 fix/T6.1) · `index.html` shrink (P0.2) · `conflict_reviews.py` edit (T5.1). **Not idle.** |
| 07-12 c3 | ✅ **S4 ✅ → PASS** | R2.STANDING ran: **full pytest 57 passed** (≥46 floor held, +11) · compileall 0 · diff clean · conflict-reviews ok. Adversarially verified T4.1 finalizer is a **full-body guard** (wraps `_run_investigation`, real crash-injection test, "no session left running") + T4.2 RQ-E05 scaffold $0/paid-hard-gated/§10-clean. → `audits/S4-T4.1-T4.2.md`. Safe to commit (lane-scoped). |

| 07-12 c4 | ✅ P0.3 BEFORE captured | de-risked the gate while blocked: clean `PERSONA_WORKERS=0` :8138 server + smoke on **pre-split** index.html → `{cards:3,Research,geo:passed,dossier:passed}` exit 0, **zero console errors**. Before-shots saved `p03_before_*.png`; :8138 killed clean. → `audits/P0-static-split.md` (BEFORE done; AFTER pending S3 P0.2). |

**Woke via monitor** (S4 ✅ + S0 TICK5/6) — auto-detection working. Loop live.
**Pending gates (all upstream-blocked):** P0.3 AFTER-half ⟸ S3 P0.2 ⟸ S6 P0.1 (app.py StaticFiles still 0) · H1 re-audit ⟸ S6 run_shell jail (app.py) + S5 sandbox.py · §A(v2) 6-check ⟸ S5 T5.1 / S6 T6.1. Before-half + harness fully de-risked.

### Cycle 1 findings (post-Wave-0 feature commits)
| id | sev | one-line | route |
|----|-----|----------|-------|
| H1 | **HIGH** | `run_shell` mounts durable `self/` **rw** → shell can rewrite `beliefs.md` outside the membrane (proven: shim written to `curie-3c33/self/`) | S6 |
| M1 | MED | `clone_repo` allowlist regex accepts ANY https host (SSRF surface + docstring false) | S6 |
| H2 | LOW | `_run.py` shim litters the folder you shell in | S6/sandbox |
| L1 | LOW | Brain self copy "eight markdown files" but 7 exist | S3 |
| L2 | LOW | studio audit `len>200||\n` heuristic misroutes long titles | S6 |

**Observed once, UNREPRODUCED (not defects):** Studio once showed Euclid (PID leak?) after a Curie terminal run; view once jumped to Map on terminal Enter. Both failed clean repro → flag for a view-state repro pass.
**Verified good:** sandbox is real (bash+numpy 2.5.1, `--network none`, ro-root, capped); genesis/Brain UI calm+on-brand; only console error = favicon 404.
**Cleanup:** removed my probe `_run.py` from `personas/curie-3c33/self/`. No source files touched.
**Next on wake:** re-audit the H1 fix (assert `run_shell cwd=self` is refused) when S6 lands it.

| 07-12 c2b | 🔬 audit cycle 2 | new commit `0a6f923` (auditor extensions). Ran suite + re-ran calibration + added OOS test + code-read refuters/re-audit loop. **1 new MED (M2).** → `audits/S2-audit-2026-07-12-auditor-extensions.md`; filed `requests/S2--to--S0--reaudit-budget-churn.md` |

### Cycle 2 (commit 0a6f923 — auditor extensions)
- ✅ **calibration VERIFIED** — Brier 0.218/0.245 + curve reproduce; I added leave-one-stratum-out: OOS **0.232 vs 0.263 (+0.031)** → generalizes, not overfit.
- ✅ **refuters correct** — correction applied only on unanimous `refuted` (audit.py:257); budget-tracked; matches 57%→48% claim.
- ✅ **tests 70 passed / 0 failed** (baseline was 46; commit's "52" was true at its time; other lanes added tests since).
- ⚠️ **M2 (MED):** living re-audit has **no staleness floor** → supervisor enqueues `reaudit` every tick when `entries() && can_spend`; `due()` always serves least-recent; `reaudit` = paid call ⇒ burns the whole $15/day cap re-checking unchanged papers. Fix: `due(min_age_hours=12)` (S5) + supervisor guard on `due() is not None` (S6). Cross-lane → S0.
- **H1 (HIGH) + M1 (MED) from cycle 1: untouched by this commit → STILL OPEN.**

**Monitors ARMED (2):** `bdc2maimy` (H1 fix: run_shell edit / DONE-rename / S6 shell status) · `bv42yqogf` (any new commit + lane READY flip). Not idle — auto-wakes on landings.

| 07-12 c5 | ✅ **S4 expanded ✅ → PASS** | S4 grew past T4.1/T4.2 → RQ-E06(a+b) + I1.2/E07c + M2-response. R2.STANDING: **full pytest 77 passed** (floor held, +31) · compileall 0 · all 3 exps paid-gated. Adversarially verified **qualifier extraction is truly additive** (bad qualifier never rejects a claim; identity immutable; exact-span). E06/E07c $0/gated/§10-honest ("sequential+N=3 stands", no agent-count celebration). → `audits/S4-e06-e07c-expanded.md`. |
| 07-12 c5 | 👁 monitor v2 | replaced `bg5jemfi3` → **`bw45zf9qe`**: per-lane status-mtime (catches content-growth the ✅-set missed) + S0 TICK-count (cuts attribution noise) + app.py/index.html/conflict_reviews/req→S2. |

**Authoritative S2 monitor = `bw45zf9qe`** (supersedes bg5jemfi3/bdc2maimy/bv42yqogf refs above). Loop live, not idle.
**Critical-path blocker (not mine):** S6 P0.1 STILL undone after TICK2–6 (`app.py` StaticFiles=0) → blocks P0.2, my P0.3, and all frontend Wave-0. Flagged to S0 in report; S0 owns the nudge.
**Still-OPEN findings:** H1 (HIGH run_shell rw-self) + M1 (clone_repo SSRF) [cycle-1, S6] · M2 (reaudit staleness) [S5 `watchlist.due` + S6 guard]. I re-audit each when its owner lands the fix.
**Next on wake:** S3 P0.2 → P0.3 after-half · S5 conflict_reviews → §A(v2) 6-check · S6 app.py → H1/P0.1 re-audit · any lane status change → standing suite + §10 cross-check.

| 07-13 c6 | ✅ **H1 + M1 FIX VERIFIED (PASS)** | monitor fired on `run_shell` edit. Re-audited actual code: `_jail_shell_cwd` (scratch-only, **18/18** jail cases; self/notes/etc refused, traversal+root+`code/../self`+`selfx` all handled) + `_GIT_URL_RE` (catch-all dropped; 169.254/internal/evil rejected, http rejected). H2 shim-litter also mitigated (scratch-only). → `audits/S2-reaudit-H1-M1-fix.md`. |

**⚠️ H1/M1 NOT LIVE YET:** fix is **uncommitted** (HEAD `0a6f923`) + running :8137 server is stale (no hot-reload) → **HIGH vuln still live until commit + restart** (S0 notes S6 parked). Request updated to VERIFIED-IN-CODE (not DONE). Recommended S6 add `test_api_*` asserting `cwd=self` refused.
**Proactive UI/UX findings this session (rolling log `audits/S2-browser-audit-log.md`):** R-1 Review layout dead-column · F-2 Focus stream duplicate events [→S3] · FL-1 Floor overstates activity on halted mind [→S3] · CE-1 matplotlib read-only-fs stderr on every figure run [→S6 per S0 re-route].
**Still-OPEN:** M2 (reaudit staleness) [S5 `watchlist.due` + S6 guard] · H1/M1 deploy (commit+restart).

| 07-13 c7 | 🔀 PRD pivot absorbed | S0 SCHEME PIVOT → PRD Lanes 1–4. **S2 review role preserved** ("KEEP the S2 review lane", roles-locked review=S2). New: app.py=Lane4/S3 (did H1/M1 fix), S4=Lane1/FC-1, S5=Lane2 PARKED, S6=Lane3 PARKED. Contracts §A/§B → FC-1…FC-7. |
| 07-13 c7 | ✅ **S4 Lane-1 M0 → PASS** | FC-1 stubs match PRD-00 §4: `open_from_conflict` sig ✓ · `span_weighted_consensus` exact shape + **protects dissent** ✓ · queue verify/debate ✓ (confirm `staleness`) · **M2 daemon guard correct** (gates `due()` not `entries()`). 118 passed, $0. → `audits/S4-lane1-milestone0-fc1.md`. |
| 07-13 c7 | ⚠️ H1/M1 verified-in-code NOT live | fix uncommitted (HEAD `0a6f923`) + running :8137 has no hot-reload → **HIGH vuln still exploitable until commit+restart.** Request updated w/ caveat + restart ask. |

**🔴 TOP BLOCKER (needs HUMAN, not me):** S5 (Lane 2 Membrane) + S6 (Lane 3) are **PARKED** — a parked session can't read the board. This darkens the epistemic core, blocks multi-rater/§A→FC-2, the M2 `watchlist` floor, and S4's open contract requests. Only the human can restart their loops. Surfaced to director.
| 07-13 c8 | ✅ S4 M0 fully complete | staleness follow-up resolved (`TASK_STALENESS` in `FC1_TASK_TYPES`, asserted). suite **123 passed**. S4 now mid-impl (verifier/debate) — no new discrete milestone to gate yet. |
| 07-13 c8 | ✅ my F-2 fix verified | S3/Lane-4 fixed my Focus-stream duplicate-events finding in index.html: `_seenEv` dedup (key=`e.id`|composite), `openMind` clears it. Correct. **Minor:** logic edit during P0.3 freeze → staled my `p03_before_*.png` (2087→2091); will re-capture before-half at gate. |
| 07-13 c8 | 👁 monitor v3 | `bw45zf9qe`→**`bsxre3r87`** — gate-focused (new commit · lane ✅-count↑ · P0.1 mount · P0.2 shell-conv · conflict_reviews · req→S2 · TICK). Drops in-progress status-prose churn that was over-waking me.

**Authoritative monitor = `bsxre3r87`.** Loop live (this monitor + pending 300s heartbeat). Not idle.
**Blocked on human:** S5+S6 PARKED (pushed). **Blocked on lanes:** P0.3 ⟸ P0.2 ⟸ P0.1 · §A/FC-2 ⟸ S5 unpark.
**Verified-so-far this session:** S4 T4.1/T4.2 (PASS) · S4 RQ-E06/E07c (PASS) · S4 Lane-1 M0+FC-1 (PASS) · H1/M1 app.py fix (VERIFIED, not-live) · my F-2 UI fix (correct).

| 07-13 c9 | ✅ **S4 F1.1 branch/DAG → PASS** | monitor v3 fired on ✅ 3→4 (tuning works). `_branch_plan` DAG fill: DAG join tested against **real TaskQueue** (synth leases only after both branches terminal, no mock) · `<2` subs → `plan.md` **byte-identical** to legacy · backward-compat kw-only. 127 passed, $0, §10-clean. → `audits/S4-F1.1-branch-dag.md`. **S4 = 5/5 PASS this session.** |
| 07-13 c10 | ✅ **S3 Flagship 4.1 → PASS** | monitor fired ✅ 5→6. Lane-4 field/value-queue UI in NEW files (frozen-safe, index.html untouched). suite **132** · `test_fe_field.cjs` 15 · `test_fe_focus_render.cjs` 38. Key: test guards **"verbatim server-value passthrough (no invented scores)"** = anti-fabricated-metrics §10/§12 ✓. → `audits/S3-flagship-4.1.md`. Stranded in fixtures until P0.1→P0.3. |
| 07-13 c11 | 📋 **PAPER-QUALITY + LEGIBILITY CRITIQUE** (user directive) | verified 12 real output-quality defects vs code + real shipped `.tex`. → `audits/S2-paper-quality-and-legibility-critique.md`; broadcast filed `requests/S2--to--S0--paper-quality-broadcast.md`. |

### Paper-quality critique (c11) — confirmed in REAL shipped papers
- **A1** code blocks overflow — `document.py:138` `\begin{verbatim}` (no wrap); **25** real papers use it → `listings`+breaklines. **[S6]**
- **A2** heading/long-token clip (real: 92-char `\section*{}`) → microtype/url/seqsplit. **[S6]**
- **A3** big flowcharts unreadable — fixed `0.85\linewidth` shrinks font → min 9pt + full-width/landscape. **[S4+S6]**
- **A4** single-column only (`documentclass[11pt]{article}`) → offer twocolumn. **[S6]**
- **A5** `\textbf{[OPEN]}` ships as raw literal in **23** real papers → styled badge+legend. **[S6]**
- **A6** citations non-contiguous — `_fix_references` (paper.py:96) keeps orig indices→gaps → renumber+remap. **[S6]**
- **A7** 1970 = **UI timeline scrubber** (`new Date(tcut)` index.html:1452/1571), NOT papers (corrected after checking) + `kg.py:84 year or 0`. **[S3+S5]**
- **A8** NO research-process/agent-contributions/traceability section in papers → add grounded "Provenance & Process". **[S1/S0+S6]**
- **B1** confusing truncated-mid-word filenames (`…-auxiliarydesce`, `…-erd-s-straus-conje`) → word-boundary slugs. **[S6]**
- **B2** confusing block/field names → plain-language naming convention. **[S1/S0+all]**
- **C1** Review tab passive (user: "nothing to do / no actions seen") → actionable controls + live action feed. **[S3+S4]**
- **D** add pre-ship paper LINT gating all above. **[S6+S4]**
**Next:** compile a real `main.tex` → PDF to visually confirm overflow/heading-clip; re-audit each fix on landing.

| 07-13 c11 | ✅ P0.1 verified + batch gate | **P0.1 mount LANDED** (app.py L20/L30, root `/` intact, suite 144→147). **P0.2 split DEPRIORITIZED** by S3 → my P0.3 deferred; re-captured fresh **2091 pre-split** before-baseline (bytes+shots) before S3 could overwrite it — insurance. **Batch PASS:** S3 iter-4 (5 epistemic routes: non-mutating + graceful `available:false`, `test_epistemic_api` 3) + S4 RQ-HT01 (branch-vs-linear scaffold, real step-counts not invented, ≥20 seeds, paid-gated, 5). → `audits/batch-2026-07-13-s3iter4-s4ht01.md`. |

**Scorecard (all PASS, real oracles, $0):** S4 = 6 (T4.1/2·E06/E07c·M0/FC-1·F1.1·HT01) · S3 = 4 (H1/M1·FC-7·flagship4.1·iter4). Floor 46→**suite 147**, no regressions.
**Standing blockers (not S2's):** S5+S6 PARKED (human restart) · nothing committed yet (HEAD `0a6f923`; H1/M1 security still live-vuln until commit+restart) · P0.2 deprioritized.
**Loop:** monitor `bsxre3r87` (gate-focused, firing correctly per-milestone) + heartbeat. Calibrated review: batch-gate established-pattern $0/fixture work; deep-dive reserved for security/membrane/KG-mutation.

| 07-13 c12 | 🔴 **PQ-REG-1 caught pre-commit (HIGH)** | S6 landed A1/A2/A4 paper-quality fixes fast. Compile-tested → **`microtype` (default expansion) breaks ALL pdf compile in the sandbox** ("auto expansion only w/ scalable fonts", no PDF). **Fix VERIFIED: `\usepackage[expansion=false]{microtype}`** (24KB PDF, code wraps); `lmodern` tested, does NOT fix. → `requests/S2--to--S6--URGENT-microtype-breaks-all-pdf-compile.md` + `audits/S2-reaudit-paper-fixes.md`. |
| 07-13 c12 | ✅ **P0.1 landed → PASS** | `app.py:30` `app.mount("/static", StaticFiles(_STATIC))` correct. Unblocks P0.2 → my P0.3 after-half. **A1 lstlisting-wrap verified good; A4 twocolumn plumbed.** Still to verify: A3/A5/A6/A7/A8/B1/C1/D on landing. |
| 07-13 c13 | 🔴 **RED test caught — STALE, not code (trap)** | R2.STANDING: suite 147→**1 failed/179**. `test_deliv_document_quality.py::test_a2` asserts bare `\usepackage{microtype}` but `document.py:33` correctly has `[expansion=false]` (=my PQ-REG-1 fix). **Test stale, code right — reverting code re-breaks ALL pdf (PQ-REG-1).** Test-only 1-line fix → imp4/Lane-3 (PARKED). → `audits/S2-redtest-a2-microtype-stale.md` + `requests/S2--to--S0--redtest-a2-microtype.md`. |
| 07-13 c13 | ✅ S4 A9 compile-guard → PASS | `_code_syntax_error` `compile()`s generated code BEFORE sandbox run (analyst.py:274); broken code never sets `ran_code=True` (:388) → malformed scripts rejected loud, not run. 5 tests. S4 now 7/7. |

**Suite state:** 179 passed / **1 stale-test failure** (not a code bug — see c13). Not commit-clean until the A2 test assertion is patched (owner parked → S0 routed).

| 07-13 c14 | ✅ RED test RESOLVED (my fix heeded) | A2 test now asserts `[expansion=false]{microtype}` **+ comment**; `document.py` code NOT reverted. Trap avoided. Suite → **204 green**. |
| 07-13 c14 | ✅ **M2 FULLY CLOSED** | `watchlist.due(min_age_hours=12)` (S5-half) + supervisor `due()` guard (S4-half) both in. Reaudit busy-loop fixed. My cycle-2b finding closed. |
| 07-13 c14 | ✅ **Lane-2 M0 → PASS (deep-checked)** | FC-2/3/5 stubs + M2 floor landed (kg/calibrate/inbox/watchlist). Belief-store safe: **membrane-poisoning + integrity = 28 passed**; `kg.py` **+97/-0 additive** (read-only provenance audit + FC-3 dep-edges; write-policy/anchoring UNTOUCHED). `conflict_reviews` NOT touched → §A(v2) 6-check still pending. → `audits/batch-2026-07-13b-...md`. |
| 07-13 c14 | ✅ S3 iter-5 abstention scoring → PASS | `eval/scoring.py` frozen **correct > abstain > wrong** (abstain always beats guessing wrong) = honest-uncertainty §10/§12. 3 tests. |

**Suite: 204 GREEN.** Scorecard: S4=7 · S3=5 · Lane-2/S5=1 — all PASS, belief-store invariants intact.
**⚠️ S5/S6 status files STALE despite Lane-2 code landing** — S0 reconcile (session live vs human landed M0).
**Still pending:** multi-rater §A(v2) substrate (conflict_reviews) → my 6-check gate · nothing committed (HEAD `0a6f923`; H1/M1 still live-vuln).

| 07-13 c15 | ✅ S4 FC-1 stubs (verifier/debate) → PASS | light-gate: `test_engine_fc1_stubs` 8 passed; debate.py/verifier.py are typed M0 stubs, **no model call** (grep clean), FC-2/5 shims deferred YAGNI. Suite **207 green**. S4=8. |
| 07-13 c16 | 🔓 **UNBLOCK DRIVE** (director) | Mapped blockers: **S5+S6 DEAD** (status 2h-stale, ✅x0) · **85 files uncommitted** (H1/M1 live-vuln). Both human-only. Wrote **turnkey §A(v2) spec** (`conflict_gold.py` + field additions per F1–F6 + my 6 checks) → `audits/S2-UNBLOCK-PLAN.md`; consolidated → `requests/S2--to--S0--unblock-drive.md`. **§A substrate NOW landing:** OS file-lock in conflict_reviews **verified correct** (win spin-retry `LK_NBLCK` / posix `LOCK_EX`); rest mid-impl → 6-check gate armed. **Won't edit conflict_reviews** (live writer, ledger-corruption risk). Live lanes (S4=10,S3=8) shipping clean, no unblock needed. |
| 07-13 c17 | 🟢 **§A(v2) GATE → PASS (critical-path unblock)** | S5's T5.1 multi-rater substrate fully landed → I **implemented + ran my 6 pre-registered checks** (`tests/test_audit_multirater_gate.py`, 7 tests, in-suite green). Hardest two hold: **blinding non-correlation** (packet_A==pos 0.30–0.70 / 200 reviewers, no sign-field served) + **real cross-PROCESS append** (6 subprocs×8=48 labels, chain intact, 0 lost/dup). +tamper/dedup/determinism/no-KG. Faithful to my F1–F6. **RQ-E02 unblocked at substrate; next = real human labels or stop at frozen bundle (NEVER synthesize).** → `audits/S2-GATE-multirater-A-v2-PASS.md`. **Suite 232 green.** |
| 07-13 c18 | 🟩 **COMMITTED verified work (director-authorized), 6 scoped commits** | On `build/persona-v5`, `git add <paths>` (never -A), suite re-verified green before each: **0af1dd4** security (H1/M1+mount+routes) · **d96f249** Lane-1 engine · **2209147** Lane-2 §A membrane · **a43b319** Lane-3 analysis+deliverables · **8279168** Lane-4 frontend+eval · **a39218c** fe-integration test. Suite **256 green** post-commit. |
| 07-13 c18 | ✅ **P0.3 → PASS, WAVE 0 CLEARED** | ran the after-check: css/app.css 200 via mount, smoke identical + **zero console errors** (js/app.js 404 is non-issue — page doesn't ref it), fe tests 19/38/18, eval 11. Behavior preserved despite S3's evolved partial-split. → `audits/P0-static-split.md`. |

**LEFT UNCOMMITTED (deliberate):** `.agent-orchestration/**` (live coord) · `HANDOFF.md` (S0-owned) · `docs/prd/**` (S1 design docs) · **junk to gitignore not commit:** `.playwright-mcp/`, `live-genesis.png`, `persona-workspace-qtest/` → flag S0.
**Still needs human:** restart S5/S6 (still dead) · **restart the running :8137 server** so the committed H1/M1 jail is actually live · real reviewers for RQ-E02.

| 07-13 c19 | ✅ **verify-kg-hygiene → PASS + finding #5 CLOSED** | S0 req `wy0yffols` verified: `_clean_confidence`/`_clean_year` correct, clamp at WRITE boundary covers all `add_claim` callers, year→None, **anchoring/provenance intact** (`-k poison/integrity/membrane` **21 passed**). **Finding #5 (unclamped dep-edge confidence, prev routed→S5) now LANDED by review loop** — `kg.py:364` `float()`→`_clean_confidence`; dormant (no live writer, no consumer reads edge conf) but last unguarded belief-store write. +3 tests → hygiene **12 passed**. Committed lane-scoped **a2e63f7** (`kg.py`+test only, never -A). **Zero unclamped confidence writes remain.** → `audits/review-kg-hygiene.md` (Resolution block). |

| 07-13 c20 | ✅ **Engine review (7723285+56956e1): 2 HIGH/MED fixed, 4 routed, 1 refuted** | Adversarial workflow (6 surfaces, find→refute). **FIXED+committed:** `f6e49f6` GRIMMER `frac<0.5` tautology (HIGH — passed every SD, fabricated-verdict; real Anaya rounding-band test +2 tests) · `9cd5f98` reaudit `force` HTTP 500 (7723285 dropped param; restored + `due(min_age_hours=0)`, M2 floor intact, +1 test). **Refuted:** trajectory:36 unclamped-conf (reads only Claim nodes, clamped upstream — verify caught the false positive). **Routed→S0:** darklit:66 frozen ingest_time (MED), forensics:216 power gate unreachable (MED), science:257 geo_lookup ok:True (MED), index.html:2074 dead contested guard (LOW). → `audits/S2-engine-review-56956e1-7723285.md` + `requests/S2--to--S0--engine-review-open-findings.md`. Suite green (forensics 10, auditor 9, engine/api 107). |
| 07-13 c20 | 👁 **live Lane-2 WIP detected on kg.py** | Uncommitted +42/-5: F2.6 `_confidence_cap` (k/(k+1) no-inflation ceiling) + F2.7 `set_validity_window`. Reviewed read-only — sound, preserves belief-integrity invariants (anchor pin wins, cap∈[0,1), clamp intact). **kg.py now HOT — won't edit.** Flag: no tests in diff yet. My 3 commits (a2e63f7/9cd5f98/f6e49f6) intact under the WIP. |

## S2 oracle-review — 2026-07-13 (commits b81a90a..f07a502)
Suite **340 green** (+30 from 310). app.py guards intact (jail=2, SSRF=2). 23 write-policy oracles green.
- b81a90a belief-store monotonic-cap + bi-temporal (F2.6/F2.7): PASS — monotonic/bitemporal oracles green, no KG-writer bypass.
- 8042c27 membrane recomposition/feasibility gate (F2.4): PASS — test_membrane_poisoning + integrity + feasibility green.
- 998fa69 engine citation-vs-support divergence (F3.3): PASS (suite).
- 56dd6d7 synthesis field-contradiction → human inbox (F3.11): PASS (suite).
- f07a502 deliverables A8 Provenance/Process + pre-ship lint gate: PASS (suite).
Verdict: all 5 PASS. Monitor brvbmyevi stays armed.

## S2 — S3 ✅ 0→2 (C1 clickable value-queue, UNCOMMITTED) — 2026-07-13
HEAD still f07a502; S3's C1 lives in working tree only. Diff scoped to Lane-4 (focus.css, field.js +8 assert, refreshed UI PNGs, HANDOFF) — no app.py/product-code outside lane. Guards 2/2. fe field test 28 assertions pass. Suite 340 green on this tree. Pre-cleared: safe to commit; I gate the actual commit when HEAD moves.

| 07-13 c21 | ✅ **Visual audit — Review surface (RUNNING Curie, 5418 claims)** | Drove Studio→Review live. **Rich + actionable + honest:** Live action feed ("62 conflicts flagged · awaiting review", honest empty-state "no gate decisions yet — Lanes 1/2 append"), Connectivity triage w/ real scores (75.0/72.5/…) labeled "unvalidated heuristic", Candidate review-order + ~50-item conflict inbox each w/ "open evidence dossier" btn, grounded pairs ("oxidative stress→alzheimer's · 123 adjacent links · unverified"). C1 passive-tab **fully fixed**. Honest-uncertainty labeling exemplary (§5). **Self-corrected a false "empty panel" read** — it's an intentional editorial left-margin layout, not a render gap (verified via DOM before filing). Only console err = favicon 404 (benign). Minor UX note (taste, non-blocking): >50% horizontal whitespace on ~1040px viewport; could use left margin for a sticky summary on wide screens. Suite 340 green; review workflow warvjwk28 running. |

## S2 oracle-review — 2026-07-13 (commits c8289ba, 453be93)
Suite **350 green** (+10). Guards 2/2 (jail + SSRF).
- **c8289ba public-beta security layer** — SECURITY-BOUNDARY DEEP-DIVE → PASS. Read public_auth.py + provider_settings.py + app.py middleware. Findings: single tenant boundary (non-public passthrough = zero regression), unauth→401/redirect, CSRF enforced on all mutating methods, per-sub rate limit, NO IDOR (persona route 404s on owner!=sub; provider owner derived from session `_settings_owner`, never client), Fernet BYOK encrypted at rest owner-scoped, SSRF-safe fixed 3-host allowlist, OAuth state via compare_digest + id_token signature/email_verified verified. No holes.
- **453be93 feature-tree + orchestration record** — broad small deltas + kg.py write-policy trigger → PASS. kg.py change is purely additive `last_observed=$now` (CREATE+ON MATCH); no confidence-monotonicity/provenance weakening; membrane+kg oracles green within 350.
Verdict: both PASS. Monitor brvbmyevi armed.
