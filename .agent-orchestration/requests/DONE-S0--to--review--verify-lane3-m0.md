# S0 → review — independently verify Lane-3 Milestone-0 (coordinator-workflow code)

Built by workflow `whpo51ml1` — same review gate before commit-ready. (Remember PQ-REG-1: a workflow's string-tests can miss real-behaviour breaks — exercise the real paths.)

**Files ($0, deterministic, read-only over the KG):**
- `persona/analysis/dependency.py` — FC-4 `dependency_graph(topic)`; consumes FC-3 `kg.dependency_edges/provenance/citation_support_ratio`; `load_bearing` = normalized downstream in-degree (PLACEHOLDER pending RQ-E06/E17); `fragile` rule = `independent_labs<2 OR (anchored AND support_ratio<0.5)`.
- `persona/analysis/value_queue.py` — FC-4 `value_queue(topic)`; VoI÷cost ranking (voi PLACEHOLDER pending RQ-E17); clamps dirty `confidence>1`.
- `persona/analysis/engine.py` — FC-4 facade re-exporting the two (added by S0 so imp1's `engine.*` routes wire through).
- `persona/ingest/retraction.py` — FC-6 `is_retracted` (OFFLINE jsonl store, no network — real Retraction-Watch is a TODO seam) + `contamination` (BFS over dependency edges).
- Tests: `tests/test_engine_fc4_{dependency,value_queue}.py`, `test_engine_fc6_retraction.py` (13 pass self-reported; value_queue also ran live vs FalkorDB = 32 rows).

**Check specifically:** (1) exact FC-4/FC-6 signatures vs PRD-00 §4; (2) **read-only** — assert no KG mutation across a full `dependency_graph`/`value_queue`/`contamination` cycle (snapshot hash unchanged); (3) load_bearing/voi are never presented as validated (CONTINUATION §10 — placeholder tags present); (4) `contamination` BFS can't infinite-loop on a dependency cycle; (5) `is_retracted` DOI/PMID normalization matches how `kg` stores sources; (6) confidence-clamp doesn't hide a real data-integrity bug (dirty `confidence>1` in the store — worth its own flag to imp4/imp2). Re-run the 13 tests + confirm suite floor. File `audits/review-lane3-m0.md`.
