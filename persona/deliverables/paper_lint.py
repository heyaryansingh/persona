"""Pre-ship paper lint (S2 item D) — a deterministic, offline gate the compile path runs before it
declares a PDF done. No network, no model: pure string forensics over the compiled artifacts.

The checks encode the formatting regressions we actually shipped (overflowing code/headings, leaked
status literals, broken/non-contiguous citations, Unix-epoch '1970'/'(0)' years, unreadable
filenames). `paper.py` can call `lint_paper(...)` after `compile_source` and refuse to copy a PDF
into deliverables/ if `ok` is False.

    from .paper_lint import lint_paper
    verdict = lint_paper({"tex": (project/"main.tex").read_text(encoding="utf-8"),
                          "markdown": md, "filename": dst.name, "sources": sources})
    if not verdict["ok"]:
        ...  # log verdict["violations"], keep the note, do NOT ship the PDF

Input (`lint_paper`): either a LaTeX/Markdown source `str`, or a dict with any of:
  tex|latex|source | markdown|md   the compiled .tex and/or the .md source (both linted if given)
  filename|pdf                     the shipped PDF filename (for B1)
  sources|source_cards             the numbered reference/source strings (A7 scans these too)
  font_ok (bool)                   best-effort A3 signal, if the caller knows it
  provenance_present (bool)        best-effort A8 signal, if the caller knows it
"""
from __future__ import annotations

import re

# --- calibration knobs (monospace/heading widths depend on the 11pt article template) -------------
# ponytail: char thresholds, not pt measurement — tune if the geometry/font in document.py changes.
VERBATIM_COL_MAX = 80      # cmtt at 11pt, 6.5in textwidth wraps ~72 cols; 80 flags only real overflow
HEADING_TOKEN_MAX = 42     # a single unbroken token this long in a big heading font overflows the line
FILENAME_TOKEN_MAX = 40    # an alpha run this long in the filename means no readable word boundaries

# single-word ALL-CAPS status tags that are LEGITIMATE (see paper.py _SYSTEM). Everything else in the
# `**[XXX]**` / `\textbf{[XXX]}` shape (classically `[CITED]`) is a leaked literal the prompt forbids.
_ALLOWED_STATUS = {"OPEN"}
_REF_HEADING = re.compile(r"(?:^#{1,3}\s*references\b|\\(?:sub)?section\*?\{\s*references\s*\})", re.I | re.M)


def _norm(meta):
    """Normalize str-or-dict input into (parts, filename, cards, font_ok, prov). `parts` is the list of
    source texts to lint (tex and/or md); both are linted when both are supplied."""
    if isinstance(meta, str):
        return [meta], "", [], None, None
    if not isinstance(meta, dict):
        return [str(meta or "")], "", [], None, None
    parts = [meta[k] for k in ("tex", "latex", "source", "markdown", "md") if meta.get(k)]
    filename = meta.get("filename") or meta.get("pdf") or ""
    cards = meta.get("sources") or meta.get("source_cards") or []
    return parts, filename, list(cards), meta.get("font_ok"), meta.get("provenance_present")


def _split_body_refs(text):
    """(body, refs) split at the References heading; body holds the inline [n] cites, refs the list."""
    m = _REF_HEADING.search(text)
    return (text[:m.start()], text[m.start():]) if m else (text, "")


def _verbatim_blocks(text):
    """Lines inside code that pdflatex will NOT wrap: ```fences``` (md) and \\begin{verbatim} (tex)."""
    out = []
    for m in re.finditer(r"```[^\n]*\n(.*?)```", text, re.S):
        out += m.group(1).splitlines()
    for m in re.finditer(r"\\begin\{verbatim\}(.*?)\\end\{verbatim\}", text, re.S):
        out += m.group(1).splitlines()
    return out


def _check_one(text, v):
    body, refs = _split_body_refs(text)

    # A1 — code lines overflow text width (verbatim/monospace never wraps, so a long one runs off-page)
    for ln in _verbatim_blocks(text):
        if len(ln.rstrip()) > VERBATIM_COL_MAX:
            v.append(("A1", f"code line overflows (>{VERBATIM_COL_MAX} cols): {ln.strip()[:60]!r}"))
            break

    # A2 — a heading has a single unbroken token too long for the (large) heading font
    for h in re.finditer(r"(?:^#{1,4}\s+(.*)$|\\(?:sub)*section\*?\{([^}]*)\}|\\paragraph\*?\{([^}]*)\})",
                         text, re.M):
        head = next(g for g in h.groups() if g is not None)
        for tok in head.split():
            if len(tok) > HEADING_TOKEN_MAX:
                v.append(("A2", f"heading token overflows (>{HEADING_TOKEN_MAX} chars): {tok[:50]!r}"))
                break
        else:
            continue
        break

    # A5 — raw `**[XXX]**` / `\textbf{[XXX]}` status literal (single ALL-CAPS word, e.g. [CITED]) in body
    for m in re.finditer(r"\*\*\[([A-Z]+)\]\*\*|\\textbf\{\[([A-Z]+)\]\}", body):
        tag = m.group(1) or m.group(2)
        if tag not in _ALLOWED_STATUS:
            v.append(("A5", f"raw status literal in body: [{tag}]"))
            break

    # A6 — citations contiguous + every inline [n] resolves to a listed reference
    inline = sorted({int(n) for n in re.findall(r"\[(\d+)\]", body)})
    ref_nums = [int(n) for n in re.findall(r"^\s*(\d+)[.)]\s", refs, re.M)]
    n_items = len(ref_nums) or len(re.findall(r"\\item\b", refs))   # tex enumerate has no explicit nums
    if inline:
        if ref_nums and ref_nums != list(range(1, len(ref_nums) + 1)):
            v.append(("A6", f"reference numbers not contiguous: {ref_nums}"))
        if n_items == 0:
            v.append(("A6", "inline citations present but no reference list found"))
        else:
            dangling = [n for n in inline if n < 1 or n > n_items]
            if dangling:
                v.append(("A6", f"inline citation(s) with no reference: {dangling} (refs=1..{n_items})"))

    # A7 — Unix-epoch leak: '1970' or a '(0)' year in the shipped body/source-cards
    if re.search(r"\b1970\b", text):
        v.append(("A7", "epoch year '1970' present"))
    if re.search(r"\(\s*0\s*\)", text):
        v.append(("A7", "'(0)' year present"))


def lint_paper(latex_or_pdf_meta) -> dict:
    """Return {ok: bool, violations: [{code, msg}]}. Deterministic; no network/model."""
    parts, filename, cards, font_ok, prov = _norm(latex_or_pdf_meta)
    v: list = []
    seen = set()
    for text in parts:
        got: list = []
        _check_one(text or "", got)
        for code, msg in got:                      # dedupe identical (code,msg) across tex+md
            if (code, msg) not in seen:
                seen.add((code, msg))
                v.append((code, msg))

    # A7 also scans the raw source-cards (their author/year strings are where epoch dates leak in)
    for c in cards:
        s = str(c)
        if re.search(r"\b1970\b", s) and ("A7", "epoch year '1970' in source-card") not in [(a, b) for a, b in v]:
            v.append(("A7", f"epoch year '1970' in source-card: {s[:60]!r}"))
        if re.search(r"\(\s*0\s*\)", s):
            v.append(("A7", f"'(0)' year in source-card: {s[:60]!r}"))

    # B1 — filename is word-boundary readable (hyphen-separated words, no run-on alpha blob)
    if filename:
        stem = re.sub(r"\.(pdf|tex|md)$", "", filename, flags=re.I)
        for seg in stem.split("-"):
            if seg.isalpha() and len(seg) > FILENAME_TOKEN_MAX:
                v.append(("B1", f"filename not word-boundary readable: run-on segment {seg[:50]!r}"))
                break
        else:
            if "-" not in stem and len(stem) > 20:
                v.append(("B1", f"filename has no word boundaries: {stem[:50]!r}"))

    # A3 (font) — best-effort. TODO: inspect embedded fonts from the real PDF (needs pdffonts / a PDF
    # parser we don't run at lint time). For now only fail on an explicit caller signal.
    if font_ok is False:
        v.append(("A3", "font check failed (caller-reported)"))

    # A8 (provenance-present) — best-effort. TODO: verify each shipped claim carries a provenance tag
    # once the compiled output exposes it; here we only trust an explicit caller signal.
    if prov is False:
        v.append(("A8", "provenance not present (caller-reported)"))

    return {"ok": not v, "violations": [{"code": c, "msg": m} for c, m in v]}


def demo():
    clean = {
        "markdown": (
            "# A Clean Paper on Tau Aggregation\n\n"
            "## Abstract\nWe establish a bound [1] and verify it [2].\n\n"
            "## Results\nThe rate scales linearly [1].\n\n"
            "```\nshort = compute(x)\n```\n\n"
            "## References\n\n1. Smith et al. — Nature (doi:10.1/a)\n2. Doe et al. — PNAS (doi:10.2/b)\n"
        ),
        "filename": "paper-tau-aggregation-a1b2c3d4e5.pdf",
        "sources": ["Smith et al. — Nature (doi:10.1/a)", "Doe et al. — PNAS (doi:10.2/b)"],
    }
    r = lint_paper(clean)
    assert r["ok"], r

    dirty = {
        "markdown": (
            "# " + "x" * 50 + "\n\n"                      # A2: run-on heading token
            "## Results\nA claim **[CITED]** here [5].\n\n"  # A5 + A6 (only 2 refs) ; A7 below
            "Published in 1970. See year (0).\n\n"          # A7
            "```\n" + "y" * 100 + "\n```\n\n"               # A1: overflowing code line
            "## References\n\n1. A — v (doi:1)\n3. B — v (doi:2)\n"  # A6: non-contiguous 1,3
        ),
        "filename": "paper-" + "a" * 60 + "-deadbeef00.pdf",  # B1: run-on segment
    }
    r = lint_paper(dirty)
    codes = {x["code"] for x in r["violations"]}
    assert not r["ok"], r
    for expected in ("A1", "A2", "A5", "A6", "A7", "B1"):
        assert expected in codes, f"{expected} did not fire: {codes}"
    print("paper_lint demo ok:", codes)


if __name__ == "__main__":
    demo()
