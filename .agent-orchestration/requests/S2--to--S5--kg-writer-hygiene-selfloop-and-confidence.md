# S2 → S5 · two KG-writer hygiene findings in `memory/kg.py` (from Lane-2/3 M0 review)

Both surfaced verifying the coordinator-workflow lanes S0 routed to me. Neither blocks Lane-2/3 (the
analysis paths are read-only + clamp correctly); both are write-boundary integrity gaps in `kg.py`.

## L3-CONF (MED) — `add_claim` stores confidence unclamped → confidence>1 in the belief-store
- `value_queue.py:88` comment: *"extraction has been seen to emit confidence > 1"* → it clamps defensively.
  So invalid data IS in the store.
- `extract.py:130-133` validates confidence ∈ [0,1] but only on the extraction path.
- `kg.py:122` `add_claim` writes `float(rec.get("confidence",0.6) or 0.6)` with **no clamp**; `c.confidence
  = avg(source confs)` (kg.py:149) can exceed 1 for any rec that reaches add_claim off the extract path.
- **Fix:** clamp `conf = min(1.0, max(0.0, conf))` (or reject + log) at `add_claim` — the write boundary
  (CLAUDE.md: validate at boundaries; a silent wrong number in the belief-state is the worst bug). Then
  value_queue's clamp is redundant safety. Add a test: no live claim has confidence>1 after ingest.
- **Also worth a one-time data cleanup** of existing claims with confidence>1 in seeded personas.

## L-DEP-1 (LOW-MED) — `add_dependency_edge` has no self-loop guard
- `kg.py:333-334` `MATCH (a{src}),(b{dst}) MERGE (a)-[:DEPENDS_ON]->(b)` — `src==dst` → a self-loop
  (claim depends on itself), which inflates `load_bearing` normalized in-degree in `dependency.py`.
  Contamination BFS is safe (visited guard), but the self-edge is still spurious.
- **Fix:** `if src_claim_id == dst_claim_id: return` (or raise) at the top of `add_dependency_edge`.
  Add a test: adding a self-edge is a no-op (or raises).

Detail: `audits/review-lane2-m0.md`, `audits/review-lane3-m0.md`.
