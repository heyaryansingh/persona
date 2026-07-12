"""Documents, not boxes — compile a markdown or LaTeX SOURCE to a real PDF a human can read.

The mind's reports/notes/reviews are authored as markdown (or LaTeX); this turns any of them into a
professional compiled PDF with real figures/math, deterministically and offline (reuses the read-only
`sandbox.compile_latex`; no pandoc in the image, so we do a pragmatic markdown->LaTeX ourselves).
Images referenced as ![alt](name.png) are included if the file sits next to the source (figures).
"""
from __future__ import annotations

import hashlib
import re
import shutil
from pathlib import Path

from ..tools import sandbox

_TEMPLATE = (
    "\\documentclass[11pt]{article}\n"
    "\\usepackage[utf8]{inputenc}\n"
    "\\usepackage[T1]{fontenc}\n"
    "\\usepackage[margin=1in]{geometry}\n"
    "\\usepackage{amsmath,amssymb,graphicx,hyperref,enumitem,xcolor}\n"
    "\\usepackage{parskip}\n"
    "\\hypersetup{colorlinks=true,linkcolor=blue,urlcolor=blue}\n"
    "\\title{%(title)s}\n\\author{Persona}\n\\date{\\today}\n"
    "\\begin{document}\n\\maketitle\n%(body)s\n\\end{document}\n"
)

# LLM markdown is full of Unicode math/Greek that pdflatex rejects — map the common ones to
# math macros (stashed as math so they survive escaping), scrub the exotic rest.
_UNI = {
    "≥": r"$\geq$", "≤": r"$\leq$", "≠": r"$\neq$", "≈": r"$\approx$", "≡": r"$\equiv$",
    "×": r"$\times$", "÷": r"$\div$", "±": r"$\pm$", "·": r"$\cdot$", "∙": r"$\cdot$",
    "→": r"$\to$", "←": r"$\leftarrow$", "↔": r"$\leftrightarrow$", "⇒": r"$\Rightarrow$",
    "⇔": r"$\Leftrightarrow$", "∈": r"$\in$", "∉": r"$\notin$", "∋": r"$\ni$", "⊂": r"$\subset$",
    "⊆": r"$\subseteq$", "⊃": r"$\supset$", "⊇": r"$\supseteq$", "∪": r"$\cup$", "∩": r"$\cap$",
    "∞": r"$\infty$", "∀": r"$\forall$", "∃": r"$\exists$", "∅": r"$\emptyset$", "∑": r"$\sum$",
    "∏": r"$\prod$", "∫": r"$\int$", "√": r"$\surd$", "∇": r"$\nabla$", "∂": r"$\partial$",
    "∝": r"$\propto$", "≪": r"$\ll$", "≫": r"$\gg$", "⌊": r"$\lfloor$", "⌋": r"$\rfloor$",
    "⌈": r"$\lceil$", "⌉": r"$\rceil$", "…": r"\ldots{}", "‰": r"\textperthousand{}",
    "ℝ": r"$\mathbb{R}$", "ℤ": r"$\mathbb{Z}$", "ℕ": r"$\mathbb{N}$", "ℚ": r"$\mathbb{Q}$",
    "ℂ": r"$\mathbb{C}$", "α": r"$\alpha$", "β": r"$\beta$", "γ": r"$\gamma$", "δ": r"$\delta$",
    "ε": r"$\varepsilon$", "ζ": r"$\zeta$", "η": r"$\eta$", "θ": r"$\theta$", "ι": r"$\iota$",
    "κ": r"$\kappa$", "λ": r"$\lambda$", "μ": r"$\mu$", "ν": r"$\nu$", "ξ": r"$\xi$", "π": r"$\pi$",
    "ρ": r"$\rho$", "σ": r"$\sigma$", "τ": r"$\tau$", "υ": r"$\upsilon$", "φ": r"$\varphi$",
    "χ": r"$\chi$", "ψ": r"$\psi$", "ω": r"$\omega$", "Γ": r"$\Gamma$", "Δ": r"$\Delta$",
    "Θ": r"$\Theta$", "Λ": r"$\Lambda$", "Π": r"$\Pi$", "Σ": r"$\Sigma$", "Φ": r"$\Phi$",
    "Ψ": r"$\Psi$", "Ω": r"$\Omega$", "°": r"$^\circ$", "²": r"$^2$", "³": r"$^3$", "½": r"$\frac12$",
    "–": "--", "—": "---", "“": "``", "”": "''", "‘": "`", "’": "'", "→": r"$\to$",
}
_UNI_RE = re.compile("|".join(re.escape(k) for k in _UNI))


def _scrub(text: str) -> str:
    """Drop combining marks (U+0300–U+036F) and exotic non-Latin codepoints (>= U+0300) that survived
    mapping, so pdflatex never dies on an undefined/combining character. Precomposed accented Latin
    (< U+0300, e.g. é ő) is kept and rendered via inputenc+fontenc."""
    return "".join(c if ord(c) < 0x0300 else " " for c in text)

_SPECIALS = [("\\", "\\textbackslash{}"), ("&", "\\&"), ("%", "\\%"), ("#", "\\#"),
             ("_", "\\_"), ("{", "\\{"), ("}", "\\}"), ("~", "\\textasciitilde{}"),
             ("^", "\\textasciicircum{}"), ("$", "\\$")]


def _esc(text: str) -> str:
    for a, b in _SPECIALS:
        text = text.replace(a, b)
    return text


def _inline(text: str) -> str:
    """Escape a prose span, then re-apply inline markdown (bold/italic/code/link/img). Math and code
    are extracted first so their contents are never escaped."""
    slots = []

    def stash(m):
        slots.append(m.group(0))
        return f"\x00{len(slots) - 1}\x00"

    # protect $...$ math and `code` before escaping
    text = re.sub(r"\$[^$]+\$", stash, text)
    text = re.sub(r"`[^`]+`", stash, text)
    # map Unicode math/Greek to LaTeX macros, stashed as math so they survive escaping
    text = _UNI_RE.sub(lambda m: (slots.append(_UNI[m.group(0)]) or f"\x00{len(slots) - 1}\x00"), text)
    # images / links captured pre-escape (their targets must not be escaped)
    imgs, links = [], []
    text = re.sub(r"!\[[^\]]*\]\(([^)]+)\)",
                  lambda m: (imgs.append(m.group(1)) or f"\x01{len(imgs) - 1}\x01"), text)
    text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)",
                  lambda m: (links.append((m.group(1), m.group(2))) or f"\x02{len(links) - 1}\x02"), text)
    text = _scrub(_esc(text))
    text = re.sub(r"\*\*([^*]+)\*\*", r"\\textbf{\1}", text)
    text = re.sub(r"\*([^*]+)\*", r"\\textit{\1}", text)
    # restore code (as \texttt, escaped), math (raw), images, links
    def unstash(m):
        raw = slots[int(m.group(1))]
        if raw.startswith("`"):
            return "\\texttt{" + _esc(raw.strip("`")) + "}"
        return raw   # math kept verbatim
    text = re.sub(r"\x00(\d+)\x00", unstash, text)
    text = re.sub(r"\x01(\d+)\x01",
                  lambda m: "\\includegraphics[width=0.85\\linewidth]{%s}" % imgs[int(m.group(1))], text)
    text = re.sub(r"\x02(\d+)\x02",
                  lambda m: "\\href{%s}{%s}" % (links[int(m.group(1))][1], _esc(links[int(m.group(1))][0])), text)
    return text


def md_to_latex(md: str, title: str = "") -> str:
    """Pragmatic markdown -> LaTeX body (headings, lists, code fences, blockquotes, images, math)."""
    lines = (md or "").replace("\r\n", "\n").split("\n")
    out, i, in_list, in_code = [], 0, None, False
    def close_list():
        nonlocal in_list
        if in_list:
            out.append("\\end{itemize}" if in_list == "ul" else "\\end{enumerate}")
            in_list = None
    while i < len(lines):
        ln = lines[i]
        if ln.strip().startswith("```"):
            if not in_code:
                close_list(); out.append("\\begin{verbatim}"); in_code = True
            else:
                out.append("\\end{verbatim}"); in_code = False
            i += 1; continue
        if in_code:
            out.append(ln); i += 1; continue
        if not ln.strip():
            close_list(); out.append(""); i += 1; continue
        h = re.match(r"^(#{1,4})\s+(.*)$", ln)
        if h:
            close_list()
            lvl = len(h.group(1)); cmd = ["section", "subsection", "subsubsection", "paragraph"][min(lvl - 1, 3)]
            out.append("\\%s*{%s}" % (cmd, _inline(h.group(2)))); i += 1; continue
        m = re.match(r"^\s*[-*+]\s+(.*)$", ln)
        if m:
            if in_list != "ul":
                close_list(); out.append("\\begin{itemize}[leftmargin=1.4em]"); in_list = "ul"
            out.append("\\item " + _inline(m.group(1))); i += 1; continue
        m = re.match(r"^\s*\d+\.\s+(.*)$", ln)
        if m:
            if in_list != "ol":
                close_list(); out.append("\\begin{enumerate}[leftmargin=1.6em]"); in_list = "ol"
            out.append("\\item " + _inline(m.group(1))); i += 1; continue
        if ln.strip().startswith(">"):
            close_list(); out.append("\\begin{quote}" + _inline(ln.strip()[1:].strip()) + "\\end{quote}"); i += 1; continue
        if re.match(r"^\s*\$\$\s*$", ln):   # display-math fence
            close_list(); block = []
            i += 1
            while i < len(lines) and not re.match(r"^\s*\$\$\s*$", lines[i]):
                block.append(lines[i]); i += 1
            out.append("\\[" + "\n".join(block) + "\\]"); i += 1; continue
        close_list(); out.append(_inline(ln)); i += 1
    close_list()
    if in_code:
        out.append("\\end{verbatim}")
    return "\n".join(out)


def compile_source(source: str, fmt: str, project: Path, *, title: str = "") -> dict:
    """Write `source` (md|tex) as main.tex in `project` and compile to PDF. Deterministic, offline."""
    project.mkdir(parents=True, exist_ok=True)
    if fmt == "tex":
        tex = source
    else:
        body = md_to_latex(source, title)
        tex = _TEMPLATE % {"title": _scrub(_esc(title or "Document")), "body": body}
    (project / "main.tex").write_text(tex, encoding="utf-8")
    r = sandbox.compile_latex(project, "main.tex")
    return r


def slug_for(text: str) -> str:
    return (re.sub(r"[^a-z0-9]+", "-", (text or "").lower()).strip("-")[:48]) or "document"
