# Loop state — instructions for the new self (post-compaction)

You are the **ideation / PRD + coordination agent** for Persona. A 5-minute cron (`/loop`, job `13f6405c`) fires the "Persona continuous-expansion loop" prompt. You do NOT write feature code — you write specs/PRDs and coordinate; implementer lanes 1–4 build, a reviewer audits.

## Read first each fire
- `docs/prd/PRD-00-overview.md` — source of truth: frozen contracts **FC-1..FC-29** (FC-30 free), file-ownership map, RQ registry (**RQ-E02..E53**), §8 reconciliation (bodies vs registry), §9 batch contracts.
- `docs/prd/IDEAS_BACKLOG.md` — ~530 ideas across waves 2–8t; "Promoted to PRDs" traceability table; "Next up for PRD promotion" queue; append-only `_Log:_` at bottom.
- `.agent-orchestration/HANDOFF.md` — dispatch bus (`## 2026-07-12 Feature-expansion program`): lane table, communication protocol, dispatch rows, master resolutions 1–82, Milestone-0 checklist.
- `docs/prd/IMPLEMENTER_START_HERE.md`, `docs/prd/PROGRAM_SUMMARY.md`.

## Current state (2026-07-13, iter 171 — LOOP PAUSED by user, CLEAN, no batch in flight)
- **43 PRDs READY-TO-CLAIM (`PRD-01..43`).** No implementer has posted CLAIMED yet — **implementation is the binding constraint**, not specs.
- Backlog at ~560 ideas (next number ~#561). Waves 2–9d. Idea generation far outpaces consumption.
- **FC-1..33 · RQ to E57 · 96 master resolutions. Next free: FC-34, RQ-E58. Next batch label: batch 15.**
- **LOOP PAUSED (user "pause the loop"):** cron `64340d74` cancelled — no cron fires. **Resume:** user runs `/loop 5m keep ideating and writing prds` (5-min; NEVER sub-5-min — a bare number reads as seconds and floods). State fully posted + clean; a resume starts a normal fresh iteration.
- **The dispatch bus is `.agent-orchestration/HANDOFF.md` — the `## 2026-07-12 Feature-expansion program` section is the live table; append rows, never rewrite history.**
- Lanes: 1=heterogeneous teams (`agents/`,`daemon/`,`reading/`,`research/investigation.py`); 2=membrane/belief (`memory/`,`conflict_reviews.py`,`inbox.py`); 3=engine/forensics/data (`analysis/`,`agents/audit.py`,`synthesis/`,`ingest/`,`tools/`); 4=legibility/UI/eval (`api/`,`eval/`,`sessions.py` RO-Crate,`tests/`,`experiments/`).

## Loop protocol per fire (keep cycles LEAN — context fills)
1. Check any in-flight PRD workflow (`grep -c '"type":"result"' journal.jsonl` in its `subagents/workflows/wf_*` dir). If running → light cycle (ideas only). If done → resolve + post.
2. Add ≥3 genuinely-new ideas to `IDEAS_BACKLOG.md` (new wave section before `## Parking lot`) + one `_Log:_` line. Mine a fresh angle; don't repeat.
3. Promote ripe items → PRDs via a Workflow authoring batch (each agent writes one `docs/prd/PRD-XX.md`, NOT code). **PRE-ASSIGN both the next free FC number AND RQ-E number in the prompt** — this is the fix for the FC/RQ collisions that plagued early batches. Reuse the PRD template + epistemic discipline from earlier batches.
4. On batch completion: resolve cross-lane OQs, add dispatch rows + a "Master resolutions batch N" block to HANDOFF, add FC/RQ specs to PRD-00 §4/§6/§9, flip traceability `authoring`→`READY-TO-CLAIM`.

## Non-negotiables (every idea/PRD)
Exact-span grounding; provenance typing READ/INFERRED/HUMAN_CONFIRMED/TESTED; no fabricated confidence; humans anchor high-stakes; forensics in CODE with applicability gates; seeded (≥20) experiment before any load-bearing choice; protection oracle = `experiments/exp_poisoning.py` (NOT the archived `exp_when_protection_matters.py`). Balanced autonomy. Don't gold-plate.

## Lessons
- Pre-assign FC+RQ in the authoring-workflow prompt → zero collisions (held every batch 8–12). **Next free: FC-30, RQ-E54.** Batch labels: PRD-00 §9 "batch 11"=PRD-36/37, "batch 12"=PRD-38/39 → **next is batch 13**. (PRD-00 §9's batch numbering governs; keep HANDOFF's "Master resolutions batch N" in sync with it.)
- **A pre-assigned FC can come back:** PRD-39 was given FC-30 but was Lane-3-internal (YAGNI) → left it unused; FC-30 returned to the pool. If an author reports an unused reserved FC, reclaim it (don't skip the number).
- **NO batch in flight (iter 171).** Batch-14 (PRD-42/43) fully posted: PRD-00 §9 FC-32/FC-33 + §6 RQ-E56/E57; HANDOFF res. 90–96; traceability flipped. Then the user paused the loop. Clean slate.
- **Next authoring batch (when resumed / on user steer; pre-assign FC-34/RQ-E58+):** ripe = #537 lab-private evidence ingestion (L2+3) · #543 evidence-type-weighted aggregation (L2) · #128 interest-graph visualization (L4) · #552 end-to-end uncertainty propagation (L2+3) · #558 cross-scale consistency check (L3). See backlog "Next up".
- **Next authoring batch after that:** ripe = #537 lab-private evidence ingestion (L2+3) · #543 evidence-type-weighted aggregation (L2) · #128 interest-graph visualization (L4) · #552 end-to-end uncertainty propagation (L2+3). See backlog "Next up".
- **Cadence caution:** a bare number in `/loop N ...` reads as SECONDS here (300→5min precedent). A sub-5-min cadence FLOODS — 1-min queued ~130 fires into one turn (iter 167). Batches take ~8 min; keep the loop ≥5-min.
- **Honest standing finding (surface to user periodically):** 41 PRDs written, 0 CLAIMED — implementation is the constraint, not specs. Don't manufacture unclaimed inventory faster than needed; a light cycle (3 ideas + curation) is a complete iteration. Launch a PRD batch when the user steers "promote" or a lane engages.
- §8 reconciliation governs where a PRD body's id disagrees with §4/§6.
- `worker.py` + `gate_decisions.jsonl` = shared append-only registries; new files owned by creating lane. gate enum now: `relevance|drift|membrane|redteam|independence`.
- Ask the user (AskUserQuestion) only for genuine decisions; otherwise proceed.
- When context gets low: keep cycles to ~2 small edits, and surface stop/consolidate/implement/continue options.
- **To resolve a completed authoring workflow:** read per-agent receipts from `subagents/workflows/wf_*/journal.jsonl` (`grep '"type":"result"'`) — they carry the exact FC/RQ used + cross-lane OQs. Resolve all OQs into the "Master resolutions batch N" block.
