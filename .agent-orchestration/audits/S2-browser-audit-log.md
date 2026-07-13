# S2 — rolling browser audit log (user-perspective surface walk)

Append-only. One entry per surface driven live. Sev: DESIGN/LOW unless marked.

## Review surface ("Instruments · the intellectual engine") — 2026-07-12
**Good:** honest-uncertainty labeling throughout — "unvalidated heuristic", "not a measured
value-of-information score", "absence of conflict does not imply publication bias or a buried null",
"direct anchoring is paused until the contradiction-typing experiment passes". Provenance states
(observed/corroborated/tested/anchored) shown with p-values + lab counts + status badges. Matches the
legibility/honest-uncertainty design principles. No console errors.
**Finding R-1 (DESIGN/LOW):** layout is unbalanced — all 5 panels occupy the right ~60%; the left ~40%
column is dead whitespace holding only a rotated section label. On wide screens this wastes ~40% of the
viewport. Rebalance to a full-width 2–3 col grid, or use the left rail for section nav/summary.
Surfaces still to drive: Floor, robustness-report card render (c26ff7e), code-editor Run,
clone flow, watchlist UI.

## Focus surface (living notebook: self · stream · swarm/membrane) — 2026-07-12
**Good:** strong "mind at work" legibility — self in first-person monospace, weighted interests,
timestamped color-coded stream (daemon/self/reader), swarm/membrane metrics + provenance-badged observed
claims. Very on-brand.
**Finding F-2 (LOW, real bug) → S3:** the stream renders duplicate events. Confirmed in DOM: 2 exact
consecutive dupes in 177 rows (`01:06:29 reflecting…`, `01:07:08 trinucleotide repeat…`) — not a blanket
double-subscribe (only boundary events). Root cause: `addEvent` (index.html:1155) appends with **no
event-id dedup**, and `backfillStream` (1128) paints recent history right before the live EventSource
opens → events present in both render twice. The living notebook is the product's audit surface, so dupes
undercut its credibility. Fix filed: `requests/S2--to--S3--stream-dedup.md` (Set-based key dedup in
addEvent, cleared on openMind). S3's file is mid-P0.2 split → routed, not edited.

## Floor surface ("research floor · agent teams working in parallel") — 2026-07-12
**Finding FL-1 (LOW-MED, honesty) → S3:** on a HALTED persona the Floor overstates activity.
- Header: "**4 agents in flight** · 0 live (cap 8)" — "4 in flight" contradicts "0 live" + halted.
  Director row likewise claims "4 agents on background reading & upkeep" while all 4 upkeep tasks show ✓ done.
- "JUST COMPLETED" lists **5×** "scouting the literature → queued **0** readers" + "collecting reads →
  checked 0, collected 0" + "batch-reading → nothing new" — no-op completions presented as accomplishments.
Both violate design §5 (motion/claims only for real state change; honest uncertainty) and match HANDOFF's
known "UI invents ambient agents" risk. Likely a stale in-flight counter not reset on halt + rendering
zero-output tasks as achievements. Fold fix into the same S3 request. Not data-corrupting; user-facing
credibility. (Note: server is running committed code; verify against post-P0.2 build too.)

## Code-editor Run (matplotlib path) — 2026-07-13
**Verified good:** `run_code` matplotlib flow works end-to-end — `ok:true`, exit 0, stdout captured,
figure returned at `code/run/probe.png` (isolated dir; no self pollution — matches the code review).
**Finding CE-1 (LOW) → S5 (tools/sandbox.py):** every matplotlib run emits a scary stderr —
`mkdir -p failed for path /home/analyst/.config/matplotlib: Read-only file system` — the sandbox's
read-only root blocks matplotlib's config/cache dir. The plot still succeeds (falls back to /tmp), but the
user sees an error-looking line in the stderr pane on every figure run. Fix: pass `-e MPLCONFIGDIR=/tmp`
in the docker args of `sandbox.run_python`. Filed: `requests/S2--to--S5--mpl-config-stderr.md`.

## Lane-4 value-queue ("Field rests on", Map sub-tab) — LIVE on deployed :8137 — 2026-07-13
**Verified visible + usable** (post-deploy). Right panel "Highest-value experiments" ranks real experiments
by VoI ÷ cost (0.9/0.7/0.45…), honest "advisory until RQ-E17 passes" label, EXPENSIVE cost badge, de-risk
count, actionable "open dossier". The legibility differentiator renders live. No JS errors (only favicon).
**Nits (LOW → S3/S1):**
- R-1 recurs: left "Field rests on" column is dead space when the dep-graph is empty ("no dependency graph
  yet" + rotated label, ~40% width). Rebalance / collapse when empty.
- "de-risks 0" is uniform across all experiments here (qtest has no dependency edges) — a user reads it as
  "the metric doesn't work". Consider hiding de-risk when the dep-graph is empty, or an empty-state hint.
- Auto-generated question grammar is awkward: "Does glp-1 receptor agonists lower…" (subject-verb
  disagreement) + "(resolving de-risks 0 downstream beliefs)" reads oddly. Polish the question template. → S4/S6.
**UX (pre-existing, → S1 idea):** the app uses native `prompt()` for ALL input (ask/URL/budget/database/
goal/build — index.html:1250-1426) — jarring, unstyled, blocking, no inline validation. Replace with in-page
fields for a professional feel (ties to the user's polish/usability theme).

## FL-1 + R-1 → FIXED & VERIFIED (commit a7c0861) — 2026-07-13
S3 fixed both my findings correctly:
- **FL-1 (floor over-activity):** in-flight now = real `active+queued` agents (not the stale server counter);
  `idle` detection; `isNoOp` predicate suppresses "queued 0 readers / checked 0 / nothing new" completions.
  Matches design §5 ("claims only for real state change"). Exactly the fix I recommended.
- **R-1 (dead column):** empty dependency graph → `fieldwrap-single` (1fr), the "Field rests on" column is
  omitted entirely + a hint; no more ~40% dead space.
Verified: `node tests/test_fe_field.cjs` → **25 assertions pass** (incl. "empty dep → no dead column",
no-op suppression). Frontend/disk-served → live immediately. Both RESOLVED.
Still open: CE-1 (matplotlib stderr, needs restart to test), A8 (provenance section — unbuilt), the
epistemic `/epistemic` 404 deploy-lag (needs restart/--reload), native `prompt()` UX.

## A7 (dates→1970) → PARTIALLY FIXED (commit a889008) — 2026-07-13
Good: new `fdate()` guard ("n.d." for missing/invalid/epoch) + `ftime`/`born` guarded.
**Incomplete (LOW → S3):** the two timeline scrubbers I originally flagged still render raw dates:
- `gxScrub` index.html:1499 → `new Date(GX.tcut).toISOString().slice(0,10)` (no guard)
- `evScrub` index.html:1618 → `new Date(t).toISOString().slice(0,16)` (no guard)
On an empty/no-timestamp graph (GX.tmin/tmax 0/NaN) dragging the slider off "live" still shows "1970-01-01".
Fix: route both through `fdate()` / guard `tcut`/`t` for `<=0`/NaN before `new Date`. Edge case; low sev.
