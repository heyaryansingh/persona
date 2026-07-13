# ORCHESTRATION — 7-session parallel build (Persona)

> Master coordination contract for **7 concurrent Claude Code sessions** sharing ONE working tree
> on branch `build/persona-v5`. Read this + `LANES.md` + your own `prompts/S{n}-*.md` before doing
> anything. Companion to `HANDOFF.md` (frozen research contract — still binding).
>
> **The one rule that prevents all breakage:** you edit ONLY files your lane owns (see `LANES.md`),
> and you communicate ONLY by writing your own `status/S{n}-*.md`. Never edit another session's files.

---

## 1. The tree

```
YOU (human) ─ talk only to S0
   │
   ▼
S0  COORDINATOR / MONITOR / DIRECTOR      Fable 5 · xhigh   (this session)
   │  reads all status/ + requests/, arbitrates, sequences, commits
   │
   ├── S1  BRAINSTORM / ARCHITECT         Fable 5 · xhigh   → writes ideas/,  status/S1
   ├── S2  REVIEW / AUDIT / BROWSER       Opus 4.8 · xhigh  → writes audits/, status/S2
   │
   └── IMPLEMENTERS (disjoint file lanes — see LANES.md)
        ├── S3  FRONTEND / ANIMATION      Fable 5 · high    → status/S3
        ├── S4  READING / REASONING ENGINE Sonnet 5 · high  → status/S4
        ├── S5  BELIEF / MEMORY / DATA     Sonnet 5 · medium → status/S5
        └── S6  API / SYNTH / DELIVERABLES Sonnet 5 · high   → status/S6
```

Two layers of delegation:
- **Layer 1 (this file):** S0 directs S1–S6 asynchronously through files. Sessions are peers; only S0 arbitrates.
- **Layer 2 (per-session subagent tree, §7):** each session spawns its own cheap subagents to save context.

## 2. Models & efforts

| Session | Role | Model | Effort | Why this model |
|---|---|---|---|---|
| S0 | Coordinator/monitor/director | **Fable 5** | **xhigh** | holds the whole board, arbitrates conflicts, merges lanes |
| S1 | Brainstorm / architecture / new features | **Fable 5** (`best`) | **xhigh** | divergent + novel evidence-backed design; a *thinking* role, pay for the ceiling |
| S2 | Review / audit / browser-test / reports | **Opus 4.8** | **xhigh** | adversarial rigor; a *different* model from the implementers → catches what a same-model author misses |
| S3 | Frontend / animation / design craft | **Fable 5** | **high** | 2,000-line UI craft + motion; hardest-to-review surface, worth the ceiling |
| S4 | Reading / reasoning / swarm engine | **Sonnet 5** | **high** | bounded impl vs a frozen contract — Sonnet's sweet spot |
| S5 | Belief-store / memory / ingest / tools | **Sonnet 5** | **medium** | more mechanical, well-scoped modules |
| S6 | API routes / synthesis / deliverables / daemon | **Sonnet 5** | **high** | route + artifact + data-viz JS |

Set model/effort at each session's start (`/model`, `/effort`). Escalate a Sonnet lane to Fable **per-task** only when S0 approves it in that session's `status` (record why).

## 3. The non-interference protocol (read twice)

1. **Own your lane only.** Edit only files listed under your session in `LANES.md`. Touching another lane's file, a shared/root file, or another session's `status/` is the one unforgivable move — it's how parallel sessions corrupt each other.
2. **No shared write-target.** There is deliberately **no single board file** everyone edits (that would just move the collision). You write **only** `status/S{n}-*.md`. S0 reads all of them and maintains the merged view in `status/S0-coordinator.md`.
3. **Cross-lane need → a request, not an edit.** Need an endpoint from S6? a UI hook from S3? a schema field from S5? a new dependency? Drop a file in `requests/` named `S{from}--to--S{to}--<slug>.md` (or `--to--S0` for shared/root/dep changes). Do **not** reach into the other lane. S0 routes and arbitrates.
4. **Never `git commit`.** In a shared tree, interleaved commits shred each other's half-saved work. When your lane is done: set your `status` to `READY` + list exact files + paste the passing test evidence. **S0 commits** with a lane-scoped `git add <paths>` (never `git add -A`), after review, and **only when the human authorizes** (per `HANDOFF.md`).
5. **Test before READY.** Every increment runs a real test (assert-based or driven end-to-end), per `AGENTS.md` §2 and `HANDOFF.md` validation rule. Paste the command + result into your `status`. No green test → not READY.
6. **Stay scoped.** Non-trivial modeling/architecture choice? Follow the `AGENTS.md` science loop (hypothesize → search → sandbox experiment ≥20 seeds → then build). If it's load-bearing and cross-lane, kick it to S1 (brainstorm) or S0 first.

## 4. Shared hotspots — locked owners

| File(s) | Sole writer | Everyone else |
|---|---|---|
| `persona/api/static/index.html` (shell) | **S3** | request UI changes via `requests/…--to--S3` |
| `persona/api/app.py` (routes, static mount) | **S6** | request endpoints via `requests/…--to--S6` |
| `requirements.txt`, `pyproject.toml`, `pytest.ini` | **S0** | any new dep = `requests/…--to--S0` (prevents dep-war) |
| root docs: `CLAUDE.md` `AGENTS.md` `BUILD_PLAN.md` `README.md`, all of `.agent-orchestration/` | **S0** | propose via `requests/…--to--S0` |
| `tests/` | file-per-lane | own the test files that touch your module; new files get your lane prefix (`test_fe_*`, `test_engine_*`, `test_data_*`, `test_api_*`) so two sessions never edit one test file |

## 5. Phase-0 — the `index.html` split (FROZEN, coordinator-sequenced, do this FIRST)

The frontend is one 2,070-line `index.html` (inline `<style>` 10–587, inline `<script>` 872–2068).
`app.py` has **no `/static` mount today** — extracted assets 404 until one exists. So the split spans
two lanes and MUST run in order. Until P0.3 passes, `index.html` + `app.py` are frozen to their owners
and no other frontend work begins.

- **P0.1 — S6:** add a `StaticFiles` mount for `/static` in `app.py` (currently absent). Test: drop `static/health.txt`, assert `GET /static/health.txt` → 200. Set `status/S6 = READY P0.1`.
- **P0.2 — S3:** behaviour-preserving extraction only (no logic changes):
  `<style>`(10–587) → `static/css/app.css`; `<script>`(872–2068) → `static/js/app.js`;
  `index.html` becomes a shell with `<link rel="stylesheet" href="/static/css/app.css">` + `<script src="/static/js/app.js" defer></script>`. Keep `index_v6_backup.html` untouched.
- **P0.3 — S2:** browser byte-check. Run `tests/ui_research_smoke.cjs` + Playwright screenshot before/after; assert render identical + zero new console errors. Report to `audits/`. Only S2 clears P0.
- **P0.4 — S3 + S6:** split `app.js` into disjoint modules → `notebook.js` `anim.js` `ui.js` (**S3**) and `graph.js` `api-client.js` (**S6**). Now the two frontend owners edit disjoint files → parallel-safe (§4 shell rule still holds: only S3 edits `index.html`).

After P0.4 the lane map in `LANES.md` is fully live.

## 6. Commit discipline (shared tree — sessions already commit autonomously)

The tree is shared (not worktrees), so the danger is **cross-lane contamination in one commit**, not commits themselves. Rules:

- **Commit ONLY your own lane's files, with an explicit scoped add:** `git add persona/memory/kg.py persona/memory/membrane.py`. **`git add -A`, `git add .`, and `git commit -a` are forbidden** — they sweep in other sessions' in-progress work and break them.
- **Before commit:** `git status --short` and confirm every staged path is in *your* `LANES.md` list. If a shared/root/other-lane file shows staged, unstage it (`git restore --staged <path>`).
- **Shared/root files** (`config.py`, `requirements.txt`, docs, `.agent-orchestration/`) → only **S0** commits them; request via `requests/…--to--S0`.
- **Commit only when the human authorizes it** (HANDOFF rule) — set `status = READY` first; the human tells S0, S0 greenlights.
- **Never** `git push`, `reset --hard`, `rebase`, or `checkout --` a path you don't own. Merge/branch arbitration is S0's.
- Upgrade path if lanes start colliding: move S3/S6 frontend work to per-session **git worktrees** (`using-git-worktrees` skill). Not needed while lanes stay file-disjoint.

## 7. Per-session subagent trees (Layer 2 — save context)

Each session delegates its own legwork to cheap agents (per user global `token-smart-orchestration`):

- **S1 brainstorm** → `frontier-planner` (deep architecture, `best`/Fable), `Explore` + `token-scout` (recon), `scientific-brainstorming` / `brainstorming` skills. Drops proposals in `ideas/`.
- **S2 review** → `feature-dev:code-reviewer` or `caveman:cavecrew-reviewer` (findings), `token-verifier` (run checks, raw evidence), Playwright MCP (browser), `token-reducer` (crush logs/outputs before reading). Drops reports in `audits/`.
- **S3 frontend** → `frontend-design` skill (in-session craft, keep on Fable), `token-scout` (locate UI code), `token-reducer` (screenshot/console reduction).
- **S4 / S5 / S6 impl** → `token-scout` (Haiku, locate), `token-implementer` (Sonnet, bounded impl vs frozen contract), `token-verifier` (Haiku, run tests), `token-reducer` (logs). Classic scout→implement→verify.

Keep the **planner/judge role in-session**; push scouting, bounded impl, log-reduction, and verification to subagents.

## 8. How S0 monitors

S0 watches `status/` + `requests/` (file mtimes) and is re-invoked on any change: reads deltas, arbitrates
conflicts, routes requests, updates `status/S0-coordinator.md` with directives, and commits READY lanes.
The human talks only to S0; S0 relays direction to S1–S6 via `status/S0-coordinator.md` + targeted `requests/`.

## 9. Directory map

```
.agent-orchestration/
  ORCHESTRATION.md   ← this file (S0-owned)
  LANES.md           ← file-ownership contract (S0-owned)
  HANDOFF.md         ← frozen research contract (S0-owned)
  status/  S0..S6    ← one file per session; you write ONLY your own
  requests/          ← S{from}--to--S{to}--<slug>.md cross-lane asks; S0 routes
  ideas/             ← S1 design proposals; S0 triages into directives
  audits/            ← S2 review/audit reports; S0 triages into fixes
  prompts/ S1..S6    ← copy-paste bootstrap prompt for each session
```
