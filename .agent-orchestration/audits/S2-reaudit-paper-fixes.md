# S2 RE-AUDIT — paper-quality fixes (S6 response to c11 critique), 2026-07-13

S6 responded fast to `S2--to--S0--paper-quality-broadcast`. Re-audited the landed (uncommitted) changes by
compiling real docs through the pipeline.

## ✅ PQ-REG-1 RESOLVED-VERIFIED (2026-07-13) — S0 applied `[expansion=false]`, S2 re-compiled
Fix landed at `document.py:33` `\usepackage[expansion=false]{microtype}`. Re-compiled a code-fence doc
through the real pipeline → **`ok=True`, 42 KB PDF, uses `lstlisting` (wraps), not verbatim.** Regression
gone. Request → `DONE-`. (In working tree; ships with the next commit.) imp4 follow-up: compile-smoke
regression test wired into the pre-ship lint so a template break fails a test, never ships no-PDF silently.

## 🔴 PQ-REG-1 (HIGH regression, now fixed) — `microtype` broke ALL compiles → was filed URGENT to S6
`document.py:30` `\usepackage{microtype}` (default expansion) needs scalable fonts; sandbox uses bitmap CM
→ fatal pdfTeX error, **no PDF**. Every paper would fail to compile.
- **Verified:** compile_source on a doc with a code fence → `ok=False`, no PDF; log = "auto expansion is
  only possible with scalable fonts."
- **Fix VERIFIED:** `\usepackage[expansion=false]{microtype}` → `ok=True`, 24 KB PDF, long code line wraps.
  `lmodern` before microtype **tested and does NOT fix** (not in sandbox image).
Request: `requests/S2--to--S6--URGENT-microtype-breaks-all-pdf-compile.md`.

## Verified GOOD (once microtype is fixed)
- **A1 (code overflow) — correct:** fences now emit `\begin{lstlisting}` (not `verbatim`); `\lstset{...
  breaklines=true...}`; long code line wraps in the passing PDF. Includes a careful listings-language guard
  (unknown `language=` would abort → falls back to plain lstlisting).
- **A2 (partial):** `\usepackage[hyphens]{url}` loaded before hyperref (correct ordering, avoids
  option-clash), `\sloppy\emergencystretch=3em` present. microtype must go `expansion=false` (above).
- **A4 (twocolumn):** `classopts="11pt,twocolumn" if lay=="two"` — parameterized. (Verify `lay` is plumbed
  from the deliverable request end-to-end on next pass.)

## P0.1 re-audit → PASS
`app.py:20,30` — `from fastapi.staticfiles import StaticFiles` + `app.mount("/static", StaticFiles(
directory=_STATIC), name="static")`. Correct. Unblocks P0.2 → my P0.3 gate.

## Batch 2 re-audit (2026-07-13) — more fixes landed, verified
- **A5 ([OPEN] badge) → VERIFIED + compiles.** `_style_status` (paper.py:100) replaces every `**[UPPER]**`
  (incl. invented tokens → gray fallback) with `_badge()` = `$\text{\colorbox{color}{\textsc{label}}}$` +
  adds a status-key legend. Compile-tested end-to-end: **ok=True, 31 KB PDF**. No raw `**[OPEN]**` survives.
- **A6 (contiguous citations) → VERIFIED CORRECT (code trace).** paper.py:143-153 builds `order`
  (first-appearance, valid+deduped), `remap old→new` 1..k, rewrites inline `[n]`, emits refs `1..k` sorted
  by new number with `sources[old-1]` (index correct, out-of-range dropped). No gaps.
- **A4 (column choice) → landed.** document.py:272-279 heuristic: math-dense (`math/words>0.03`) → 1 col;
  long+structured (`words>400 and structural>=6`) → 2 col. (Verify it reads well on a real paper later.)
- **B1 (filenames) → landed.** paper.py `_slug` truncates on a **word boundary** (`rsplit("-",1)[0]`, no
  mid-word cut) + short ISO date instead of raw uuid. (Spot-check a real generated name next pass.)

## Batch 3 (2026-07-13) — pre-ship lint + compile guard LANDED & VERIFIED
- **§D pre-ship lint `paper_lint.py` → VERIFIED WORKING.** 38 tests pass across `test_deliv_paper_lint`,
  `test_document_compile`, `test_engine_a9_compile_guard`, `test_deliv_paper_quality`,
  `test_deliv_document_quality`, `test_recompile_determinism`, `test_paper_hygiene`.
  **Independent negative test (my own):** fed a bad doc → `ok=False`, correctly caught **A1** (code >80
  cols), **A2** (heading token >42), **A5** (raw `[TODO]` literal), **A7** (`1970` and `(0)` years). The
  gate genuinely rejects — would auto-catch a microtype-class regression. Big win: my whole critique now
  has a regression fence.
- **A6 lint → CONFIRMED COVERED** (retested): a `1. / 3.` list with `[1],[3]` inline → flagged
  "reference numbers not contiguous: [1, 3]" + "inline citation with no reference". Good.
- **B1 lint → real (minor) gap (→ S6):** `derivation-erd-s-straus-conje-e7010ab7.pdf` (truncated mid-word
  "conje" + hash) is NOT flagged, though the lint docstring lists "unreadable filenames." Belt-and-suspenders
  only (generator now emits good names) — but add a filename rule (mid-word `-XX-` truncation / raw
  hex-hash suffix / `latex-document-<digits>` generic prefix) so the gate matches its own spec. LOW.

## Still pending (not yet landed)
A3 (figure font size), A7-frontend (timeline 1970 → S3), **A8 (provenance/process section — still only the
generic "every claim traceable"; the real research-process/agent-contribution section is NOT built)**,
C1 (Review tab actions).
