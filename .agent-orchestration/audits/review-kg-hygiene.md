# S2 REVIEW — kg write-boundary hygiene (A10 confidence + A7 year), 2026-07-13

Requested by `S0--to--review--verify-kg-hygiene.md` (workflow `wy0yffols`). This fixes my **L3-CONF**
(unclamped confidence at the belief-store write) + **A7** (year=0→1970). Independent gate.

## Verdict: PASS (belief-integrity fix is correct). One minor follow-up (unclamped EDGE confidence).

- **#1 `_clean_confidence` → PASS (probed directly).** 1.7→1.0, −0.2→0.0, 0.6→0.6, 0.0→0.0, 1.0→1.0;
  **NaN→ValueError, inf→ValueError, 'abc'→ValueError, None→ValueError.** Fail-loud at the write boundary —
  exactly the fix I recommended (CLAUDE.md: validate at boundaries; no silent wrong number in the belief-state).
- **#2 write-boundary coverage → PASS.** `add_claim` cleans `conf` at the param (kg.py:122), so BOTH
  `c.confidence=$conf` (l.158) and `r.conf=$conf` (l.164) get the cleaned value, and `mconf=avg(r.conf)`
  (the anchored-else branch) is therefore also bounded. Every `add_claim` caller is covered, not just the
  extract path. The reading/batch → sources → membrane.harvest path also routes through `add_claim`.
- **#3 `_clean_year` → PASS (probed).** 2020→2020, 0→None, 999→None, 3001→None, None→None, 'x'→None. Missing
  year is None, never 0 (which rendered 1970). Wired into `upsert_source`.
- **#4 no anchor/overwrite/provenance regression → PASS.** `test_membrane_poisoning` +
  `test_integrity_boundaries` still green (22 tests incl. `test_data_kg_write_hygiene`). The anchor
  write-policy I verified in oldcode-review is intact.

## Findings
- **#5 (LOW) — one OTHER unclamped confidence write path remains:** `add_dependency_edge` (kg.py:364)
  writes edge `"conf": float(confidence)` **unclamped**. This is the dependency-EDGE weight (used by
  dependency.py load_bearing/fragile), not the belief-store claim confidence — lower stakes — but S0 asked to
  confirm no other unclamped path, and this one is. **Fix:** `_clean_confidence(confidence)` there too, for
  consistency. → S5.
- **A7 read-side still open (→ S3):** the write-boundary fix stops NEW year=0 data, but the **timeline
  scrubber** (`index.html:1452 gxScrub / 1571 evScrub`) still renders `new Date(0/NaN).toISOString()` =
  "1970-01-01" when a graph's min/max timestamps are absent. Guard that `new Date` (show "live"/"—"). Plus a
  one-time cleanup of existing sources with `year=0` in seeded personas.

**kg-hygiene M0 verdict: PASS.** My L3-CONF + A7-write findings resolved at the boundary.

---

## Resolution — finding #5 CLOSED (review loop, 2026-07-13 later fire)

Finding #5 (unclamped EDGE confidence, previously routed to S5) is now **fixed in code** by the review
loop rather than left as a plan — S5 is parked and this is a 1-line root-cause hardening reusing the
same-file helper, no live Lane-2 session to collide with, file clean at HEAD.

- **`kg.py:364`** `"conf": float(confidence)` → `"conf": _clean_confidence(confidence)` (+ docstring note).
  Re-confirmed dormant before touching: `add_dependency_edge` has **no live writer** (the only ref is a
  comment at `analysis/dependency.py:47`) and **no consumer reads edge confidence** (`value_queue.py:67-68`
  + `analysis/dependency.py:37-40` use only `src`/`dst`). So this was never an active A10 recurrence — but it
  was the last confidence write to the belief store bypassing the guard, and CLAUDE.md §4 wants it fail-loud
  before a producer (I1.3 calibrated-p load_bearing is the natural one) lands.
- **`tests/test_data_kg_write_hygiene.py`** +3 tests (dep-edge clamp 1.7/−0.2/0.6 + NaN→ValueError).

**Evidence:** hygiene **12 passed** (was 8); `-k "poison or integrity or membrane"` **21 passed** (no
anchoring/provenance regression); `-k "dependency or value_queue"` **16 passed**; `compileall` OK.
**Committed** lane-scoped on `build/persona-v5` (`git add persona/memory/kg.py tests/test_data_kg_write_hygiene.py`).
**Now zero unclamped confidence writes to the belief store.**
