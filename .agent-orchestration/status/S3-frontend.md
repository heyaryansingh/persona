# status/S3 — imp1 = Lane 4 (Legibility, flagship) · Fable · COMPACT HANDOFF (2026-07-13)

**Read this to continue as S3/imp1.** All prior iteration logs compacted here. State: **all code-actionable
work done + tested + $0 + UNCOMMITTED (awaiting human commit auth).** Board idle since 01:22; monitor is
event-driven (`bbte9se7t` watches `requests/` to-S3 + board changes → wakes on any real event).

## Identity + lane (PRD-00 §3, CONFIRMED map)
imp1=S3→**Lane 4**. Owns: `persona/api/app.py` (new routes only), `persona/api/static/index.html` (new
surfaces only), `persona/sessions.py` (RO-Crate add only), `persona/eval/*`, `experiments/*` (new),
`tests/*` (new). Provides **FC-7** (`eval.run_oracle`). Consumes FC-2/3/4/5/6. (Note: the human/loop calls me
"agent 3"; the map's "imp3" is S5 — I am imp1/S3, proven by Fable model + whole session's S3 ownership.)

## DONE (all tested; see commit groups). Files I hold uncommitted:
- **Security H1/M1** (`app.py` + `tests/test_app_security.py`): `run_shell` cwd scratch-jail (`_jail_shell_cwd`)
  so it can't write the durable self; `clone_repo` SSRF allowlist (`_GIT_URL_RE`). **S2-verified PASS. NOT LIVE**
  until human commits + restarts :8137 (serving old vulnerable code). **Commit priority #1.**
- **FC-7 eval** (`persona/eval/__init__.py` `run_oracle`, `scoring.py` abstention-aware −1/0/+1, `fixtures.py`
  hash-verified loader, `fixtures/` empty `unfetched` LitQA2/BixBench + MANIFEST, `fetch_fixtures.py`). Never
  fabricates gold. Tests: `test_eval_oracles.py`, `test_eval_scoring.py`, `test_eval_fixture.py`.
- **Flagship 4.1 LIVE** (`static/js/field.js`): dep-map + value-queue, verbatim server values (no invented
  scores), fragile=shape, empty→single-col (R-1). `loadField(PID)` fetches real FC-4 (`engine.dependency_graph`
  /`value_queue` — live). Wired as **Map subtab "Field rests on"** in index.html.
- **Oracle-verdict renderer** (`static/js/verdict.js`, idea I1.4/FC-8): one honest card, `verdictState()` —
  not-applicable≠verdict, capsule-absent→unverified, controls→quarantined, high-stakes→human, verdict+sensitivity.
  Envelope shape sent to S6 (`requests/S3--to--S6--fc8-...`, frozen I1.4 §2).
- **Epistemic dashboard F4.4 + gate-decisions F4.6** (`static/js/epistemic.js`, `/epistemic` route): real FC-3
  `provenance_breakdown` + RQ-gate table (parses `docs/RESEARCH_QUALITY_PROGRAM.md`) + read-only gate ledger.
  Wired as **Map subtab "Epistemic"**.
- **app.py routes** (Lane-4): `/static` mount + `/eval`, `/engine/dependency`, `/engine/value_queue`,
  `/engine/handoff`, `/gate_decisions`, `/epistemic`. Parked FC-2 degrades gracefully; **none mutate KG**.
- **Shared UI** (`static/js/ui.js` PUI): badges (colour+text+shape), dual trace≠truth badge, orDash (missing→—).
  `static/js/focus.js` (Focus notebook + blinded review card) + `static/css/focus.css` + `focus-demo.html`.
- **Findings fixed:** F-2 stream-dedup (index.html+focus.js), FL-1 halted-floor honesty, R-1 flagship layout,
  A7 dates→"n.d." (`fdate`), L2 studio audit explicit toggle, imp2 **true_refutation** wire (review→investigation).

## Verify (all green)
`python -m pytest -q` → **310 passed**. FE node tests: `node tests/test_fe_{field,verdict,focus_render,epistemic}.cjs`
+ `test_fe_integration.py`. CSS: focus.css braces balanced, tokens ⊂ app.css.

## Commit-scoped groups (human-auth only, never `-A`; S0 commits)
1. `persona/api/app.py tests/test_app_security.py`  ← **security, priority #1** (+ restart :8137)
2. `persona/eval/** tests/test_eval_*.py`
3. `persona/api/static/js/** persona/api/static/css/** persona/api/static/focus-demo.html tests/test_fe_*`
   + `persona/api/static/index.html` (surfaces + dedup + FL-1/A7/L2 + true_refutation toast + C1 feed)

## ⚠️ ENV CHURN 2026-07-13 (~17:53+) — main tree being branch-switched by another actor
An engine ultrareview is running from a separate worktree (`persona-review` @ `engine-review` 59e1d82;
`engine-review` strips the whole frontend). The **main tree churns** build/persona-v5 ↔ engine-review, and
build/persona-v5 HEAD moved f6e49f6 → ad15bfd (reset by another actor). **My uncommitted C1 value-queue fix
was DISCARDED** from the working tree in the churn (it was commit-ready, never committed). Reproducible —
exact 3-hunk patch saved to scratchpad `C1-value-queue-clickable.patch.md` (also recoverable from 12 dangling
blobs). **Do NOT re-apply into the tree while it's being actively switched** (race). Re-apply on build/persona-v5
once the ultrareview settles. Committed Lane-4 work (8279168, a7c0861 R-1, C1 feed) is safe. The monitor's
"new request to S3/imp1" event is **spurious** — the `requests/` dir was wiped in the churn.

## RE-SYNC 2026-07-13 (~13:30) — reconciled: my lane is COMMITTED, not uncommitted
Handoff above was written pre-commit. Reality now: **6 scoped commits landed (S2 c18) + Lane-4 is in HEAD**
(`8279168` frontend+eval · `a39218c` fe-integration · `56956e1` filename+Review-hardening · `4931184` C1 feed
· `ca3cff5`/`f6a73cc` true_refutation seam + L2 toggle). Suite **340 green**; FE node tests 28/18/38/18 green.
Uncommitted working-tree files are **all other lanes** (dependency/paper/kg/membrane/fieldmap/synthesizer.py)
+ S0-owned HANDOFF/results-pngs — **none are mine**. Server live on :8137; serves current index.html fresh
from disk (no restart needed for HTML/JS/CSS; only Python route changes need the :8137 restart, still human-only).

## ✅ C1 residual LANDED — clickable value-queue item (this session, tested, UNCOMMITTED)
`static/js/field.js` + `static/css/focus.css` + `tests/test_fe_field.cjs`. Was: the value-queue "open dossier"
and Investigate/Handoff buttons rendered but **had no click wiring anywhere** (dead buttons — grep-confirmed no
delegation in index.html). Now: **"open dossier" → the existing read-only `prov(claim_id)` viewer** (same wiring
every other row uses; no KG mutation; disabled + no prov() call when no resolving claim id). **run_action demoted
to an advisory disposition label** (`.vq-disp`, Investigate/Handoff) — not a button that fakes a paid/cross-lane
investigation launch ($0 + no-fabricated-activity rule). Test: `node tests/test_fe_field.cjs` → **28 passed**
(+3 new: prov-wire, advisory-label, disabled-when-no-claim). CSS braces balanced (188/188).
**Commit-scoped (human-auth only, never `-A`):** `git add persona/api/static/js/field.js persona/api/static/css/focus.css tests/test_fe_field.cjs`.

## PENDING (for next session)
- **R-1 Review/instruments layout** (dead left ~40% rail) — DESIGN-LOW, needs the **live rendered surface** to
  judge; don't change blind. Do after :8137 restart (or with S2 browser guidance).
- ~~**C1 clickable value-queue nicety**~~ ✅ **DONE this session** (see above — dossier wired to `prov()`, run_action → advisory label).
- **New PRD-04 surfaces if directed:** F4.2 Trust, F4.5 swarm economics, F4.10 RO-Crate (`sessions.py` add).
- **S2 browser re-verify** needed for live-DOM fixes (FL-1, L2 toggle, C1 feed, true_refutation toast) post-restart.

## Standing rules
$0 / `PERSONA_WORKERS=0`; commit only on human OK; edit only Lane-4 files; coordinate cross-lane via `requests/`.
Parked: S5(L2)/S6(L3) partial — FC-3/FC-4 landed real; FC-2/5 degrade. Never anchor KG from UI.
