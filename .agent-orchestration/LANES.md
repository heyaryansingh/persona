# LANES — file ownership (PRD-aligned · labels fixed 2026-07-13)

> **6 agents:** `idea`, `review`, `imp1`, `imp2`, `imp3`, `imp4`. **Four implementers = imp1–imp4. No "agent 5".**
> Authoritative = the PRD (`docs/prd/PRD-00…04`) + **FC-1…FC-7**. You edit ONLY files your lane OWNS.
> Cross-lane need → a `requests/` note routed by the coordinator, never a direct edit.
> `index_v6_backup.html` = **USER-OWNED, never touch.**

## Roles (old S-number in parens, retired)
`idea` (S1) · `review` (S2) · `imp1` (S3) · `imp2` (S4) · `imp3` (S5) · `imp4` (S6).

## Ownership (`*` = new file)

### imp1 — LANE 4 · Legibility & benchmarks  ·  Fable · high
OWN: `persona/api/app.py` (sole writer), `persona/api/static/index.html` + `static/{css,js}/**` (sole writer), `persona/sessions.py` (RO-Crate add only), `persona/eval/**`, `experiments/**` (new), `tests/**` (new for this lane). Owns the H1/M1 `app.py` security fix.
PROVIDES **FC-7**. CONSUMES FC-2..FC-6.

### imp2 — LANE 1 · Heterogeneous agent teams  ·  Sonnet · high
OWN: `persona/agents/{verifier*, debate*, analyst, critic, revisit, director, discover, deliberate}`, `persona/research/investigation.py`, `persona/daemon/{supervisor, queue}`, `persona/reading/{extract, reader}`.
**+ ABSORBS from dark Lane 2:** `persona/conflict_reviews.py`, `persona/inbox.py*` (**FC-2**), conflict-typing.
PROVIDES **FC-1, FC-2**. CONSUMES FC-3, FC-5.

### imp4 — LANE 3 · Intellectual engine, forensics & data acting-loop  ·  Sonnet · high
OWN: `persona/analysis/{forensics, dependency*, trajectory*, value_queue*, darklit*}`, `persona/agents/audit.py`, `persona/synthesis/{fieldmap, synthesizer, consolidator}`, `persona/ingest/{sources, retraction*}`, `persona/tools/{science, datasets, sandbox}`.
**+ ABSORBS from dark Lane 2:** `persona/memory/{kg, membrane, calibrate*, coherence, history, vectors, watchlist}` (**FC-3, FC-5**).
PROVIDES **FC-3, FC-4, FC-5, FC-6**. CONSUMES FC-2.
⚠️ **`memory/*` FROZEN to the coordinator until the Lane-2 Milestone-0 workflow lands its stubs** (posted on the board); then imp4 owns + extends.

### imp3 — LANE 2 · Membrane (DARK all session → REDISTRIBUTED above)
Status: no code produced. Its FC-2/FC-3/FC-5 work is redistributed to imp2 (conflict/inbox) + imp4 (belief-store) and the coordinator's M0 workflow. **If this terminal revives, it reclaims Lane 2 via the board** and imp2/imp4 hand back.

### idea (S1) — Ideation / PRD  ·  Fable · xhigh
OWN: `docs/prd/**`, `ideas/**`, `status/idea`. Specs + PRDs only, no product code.

### review (S2) — Reviewer  ·  Opus · xhigh
OWN: `audits/**`, `status/review`, `tests/test_audit_*`. Failing regression tests only; never edits product code.

### coordinator — shared infra + arbitration + Lane-2 M0
OWN: `persona/config.py`, `paths.py`, `budget.py`, `requirements.txt`, `pyproject.toml`, `pytest.ini`, root docs, all `.agent-orchestration/` except each session's own `status/`+`ideas/`+`audits/`. Temporarily drives Lane-2 Milestone-0 (memory/conflict/inbox stubs) until imp2/imp4 take over.

## Boundary rule
Two lanes touch a seam → decouple with an **FC**, not shared editing. No lane changes an FC unilaterally — post a CONTRACT CHANGE PROPOSAL; coordinator + consumers ack. Commit lane-scoped (`git add <paths>`, never `-A`), only on human authorization.
