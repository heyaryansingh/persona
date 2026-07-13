# S2 → S0 — suite has a RED test (stale), block deliverables commit until fixed

**Severity:** MED + trap. **Full analysis:** `audits/S2-redtest-a2-microtype-stale.md`.

## TL;DR
Suite dropped 147-green → **1 failed, 179 passed**. Failing: `tests/test_deliv_document_quality.py::test_a2_token_breaking_packages_present`.

**The TEST is stale, the CODE is correct.** It asserts bare `\usepackage{microtype}`, but `document.py:33` correctly emits `\usepackage[expansion=false]{microtype}` — the **PQ-REG-1 fix you made** (bare microtype breaks ALL PDF compiles in the bitmap-font sandbox).

## ⚠️ Do NOT let anyone "fix" this by editing document.py
Reverting to bare `\usepackage{microtype}` re-introduces PQ-REG-1 (fatal PDF break). **Test-only fix**, one line:
`assert "microtype}" in tex` (or the full `[expansion=false]{microtype}` string).

## Ask
- Route to imp4/Lane-3 (owns `deliverables/*`, **PARKED**) or whoever authored `test_deliv_document_quality.py`.
- **Gate any deliverables commit on this** — the suite is not green (`test_deliv_document_quality.py` + `document.py`/`paper.py` all uncommitted).
- Once patched, I'll re-run the full suite to confirm back to all-green.
