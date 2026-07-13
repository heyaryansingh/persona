# S2 finding — RED test `test_a2_token_breaking_packages_present` is STALE (do NOT revert code)

**When:** 2026-07-13 · caught by R2.STANDING (suite went 147-green → **1 failed, 179 passed**).
**Severity:** MED (suite not commit-clean) + **⚠️ TRAP: the naive fix re-introduces PQ-REG-1 (fatal PDF-compile break).**

## Symptom
`tests/test_deliv_document_quality.py::test_a2_token_breaking_packages_present` fails **deterministically** (alone: 1 failed/6 passed; the earlier `test_latex_unicode` report was a red herring). Assertion:
```
assert "\\usepackage{microtype}" in tex      # test_deliv_document_quality.py:32
```

## Root cause — STALE TEST, correct code
`persona/deliverables/document.py:33` emits `\usepackage[expansion=false]{microtype}`. The test asserts the **bare** `\usepackage{microtype}` as an exact substring — which `[expansion=false]` no longer contains. The other two A2 assertions (`[hyphens]{url}`, `\sloppy`+`\emergencystretch`) both pass (document.py:27, :38).

**This is my prior PQ-REG-1, re-surfacing:** bare `\usepackage{microtype}` broke **all** PDF compiles (font-expansion needs Type1 metrics; the bitmap-font sandbox → fatal). S0 fixed it to `[expansion=false]` (S2-verified: compiled a 24 KB PDF). The code fix is CORRECT and load-bearing.

## ⚠️ Do NOT "fix" the code
Reverting `document.py` to bare `\usepackage{microtype}` to make the test green **re-breaks every PDF compile** (PQ-REG-1). The test is wrong, not the code.

## Fix (test-only, one line) — owner imp4/Lane-3 (deliverables, PARKED)
Update the assertion to match the PQ-REG-1-safe form:
```
assert "microtype}" in tex                              # or:
assert "\\usepackage[expansion=false]{microtype}" in tex
```
`test_deliv_document_quality.py` is untracked (new). Both it and `document.py`/`paper.py` are uncommitted. **The suite is not green until this test is corrected — block the deliverables commit on it.**

## Route
imp4/Lane-3 owns `deliverables/*` + is PARKED → S0 please route (or assign whoever authored `test_deliv_document_quality.py`). Filed `requests/S2--to--S0--redtest-a2-microtype.md`.
