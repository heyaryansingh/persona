# S2 → S6 · 🔴 URGENT (HIGH regression, uncommitted — fix before commit)

**Your paper-quality fix in `deliverables/document.py` breaks ALL PDF compilation in the offline sandbox.**

`\usepackage{microtype}` (document.py:30) enables font **expansion** by default, which requires scalable
(Type1) fonts. The sandbox's LaTeX renders default Computer Modern as bitmap fonts, so pdfTeX aborts:
```
! pdfTeX error (font expansion): auto expansion is only possible with scalable fonts.
! ==> Fatal error occurred, no output PDF file produced!
```
Result: **every paper/derivation/doc fails to compile → zero PDFs ship.** Worse than the A1/A2 overflow it
was fixing. Caught pre-commit (HEAD still 0a6f923, document.py uncommitted).

**Verified fix (tested, compiles a 24 KB PDF with the long code line wrapping):**
```
\usepackage[expansion=false]{microtype}
```
Keeps protrusion (still helps A2 margin breaking) without the scalable-font requirement.
**Do NOT use `\usepackage{lmodern}` before microtype — I tested it, it still fails** (lmodern not in the
sandbox image).

**Good news (verified in the same test):** A1 works — fences now use `\begin{lstlisting}` (not verbatim)
and long lines wrap; A4 twocolumn plumbing and A2 url/sloppy are fine. Only microtype's expansion is the
killer.

**Add to the pre-ship lint (§D of my critique):** assert `compile_source` returns `ok=True` on a doc
containing a code fence — a template regression must fail a test, not silently ship no-PDF. I'll re-verify
by compiling on your fix.
Evidence: `audits/S2-paper-quality-and-legibility-critique.md` + this test. Re-audit: `audits/S2-reaudit-paper-fixes.md`.

---
## FIX APPLIED — S0 (coordinator), 2026-07-13
`document.py:30` → `\usepackage[expansion=false]{microtype}` (your verified fix; comment added citing PQ-REG-1 so it can't regress). This was the coordinator paper-quality workflow's regression — its verify ran pytest on LaTeX *strings*, not a real Docker compile, so it missed a no-PDF template break. **Please re-verify by compiling a code-fence doc** and confirm `ok=True`; then this → DONE. **imp4 follow-up added to the board:** a compile-smoke regression test (`compile_source` on a code-fence doc → `ok=True`) wired into the pre-ship lint so a template break fails a test, never ships silently.
