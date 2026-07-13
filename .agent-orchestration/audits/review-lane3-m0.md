# S2 REVIEW — Lane-3 M0 (FC-4/FC-6), 2026-07-13

Requested by `S0--to--review--verify-lane3-m0.md` (workflow `whpo51ml1`). Exercised real paths, not just tests.

## Verdict: PASS (no blocker). 27 lane-2/3 tests green.

- **Check #2 — read-only KG → PASS.** No `MERGE/CREATE/SET/DELETE/write/add_claim/anchor` anywhere in
  `analysis/dependency.py`, `analysis/value_queue.py`, `ingest/retraction.py` (only a comment matched).
  `dependency_edges`/`provenance`/`citation_support_ratio` are pure reads. A full
  `dependency_graph`/`value_queue`/`contamination` cycle mutates nothing.
- **Check #4 — contamination BFS cycle-safe → PASS.** `retraction.py:120-123` enqueues a neighbor only
  `if nxt not in parent` (parent = visited set). A dependency cycle (a→b→a) or a self-loop can't
  infinite-loop — the node is already visited and skipped. Verified by code.
- **`is_retracted` (FC-6)** — offline jsonl store, no network; TODO seam for Retraction-Watch is honestly
  marked. (Check #5 DOI/PMID normalization vs how `kg` stores sources — deferred to next tick.)

## Cross-lane finding (→ S5, owns `memory/kg.py`)
- **L-DEP-1 (LOW-MED): `add_dependency_edge` has no self-loop guard.** `kg.py:333-334`
  `MATCH (a{src}),(b{dst}) MERGE (a)-[:DEPENDS_ON]->(b)` — if `src==dst`, a and b are the same node → a
  self-loop edge (claim depends on itself). Contained for contamination (visited guard) but **inflates
  `load_bearing` = normalized downstream in-degree** (dependency.py) with a spurious self-edge. Fix:
  `if src_claim_id == dst_claim_id: return` (or raise) at the top. See also lane-2 review check #3.

## Check #6 — confidence-clamp IS hiding a real data bug → FINDING L3-CONF (MED, root-caused) → S5
The value_queue clamp is a symptom patch. Root cause traced:
- `analysis/value_queue.py:88-90` comments *"extraction has been seen to emit confidence > 1"* and clamps
  `min(1,max(0,conf))` — so **invalid confidence>1 exists in the belief-store**.
- `reading/extract.py:130-133` DOES validate confidence ∈ [0,1] (rejects `invalid-confidence`) — but only
  on the extraction path.
- **`memory/kg.py:122 add_claim`** — the actual KG writer — stores `float(rec.get("confidence",0.6) or 0.6)`
  with **NO clamp**. Any rec reaching add_claim off the extract path writes unbounded confidence, and
  `c.confidence = avg(source confs)` (kg.py:149) can then exceed 1.
**Fix (root cause, at the write boundary — S5):** clamp/validate `conf` to [0,1] in `add_claim` (CLAUDE.md:
"validate inputs at boundaries; a silent wrong number in the belief-state is the worst bug"). value_queue's
clamp then becomes belt-and-suspenders. Also add a store-integrity check: no live claim has confidence>1.
Not a Lane-3 blocker (Lane-3 is read-only and clamps correctly) — a Lane-2/KG-writer bug.

## Check #5 — is_retracted DOI/PMID normalization → PASS
`_doi_norm` (retraction.py:26-27) `.strip().lower()` + strips `https://doi.org/`,`http://…`,`doi:` prefixes,
applied to BOTH the query DOI and each stored record's DOI before compare — so retraction matches regardless
of how `kg` stores the raw DOI (kg stores `meta.doi` unnormalized). PMID compared as `str().strip()` both
sides. Robust. (Minor: kg stores DOI raw — fine for is_retracted since it normalizes at lookup.)

## Update: L-DEP-1 (self-loop) → FIXED
`add_dependency_edge` now `if src_claim_id == dst_claim_id: return` (kg.py:332, comment credits S2 L-DEP-1).

## Deferred (need PRD-00 text)
#1 FC-4/FC-6 signatures vs PRD-00 §4 · #3 load_bearing/voi placeholder tags (spot-confirmed in docstrings).
**Lane-3 M0 verdict: PASS.** Open: L3-CONF (unclamped confidence at add_claim) → S5, does NOT block Lane-3.
