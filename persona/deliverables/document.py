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

# %(classopts)s parameterizes the class options so a caller can request twocolumn (A4). url[hyphens]
# MUST load before hyperref (which pulls in url itself) or pdflatex throws an option-clash. listings +
# xcolor style code blocks with wrapping (A1); microtype + \sloppy + \emergencystretch break long
# unbreakable tokens/URLs so headings and \texttt don't run off the margin (A2). All in texlive-base,
# so the offline compile is preserved.
_TEMPLATE = (
    "\\documentclass[%(classopts)s]{article}\n"
    "\\usepackage[utf8]{inputenc}\n"
    "\\usepackage[T1]{fontenc}\n"
    "\\usepackage[margin=1in]{geometry}\n"
    "\\usepackage[hyphens]{url}\n"
    "\\usepackage{amsmath,amssymb,graphicx,hyperref,enumitem,xcolor}\n"
    "\\usepackage{listings}\n"
    # expansion=false: default font expansion needs scalable (Type1) fonts, but the offline
    # sandbox renders Computer Modern as bitmaps -> fatal pdfTeX error / no PDF. Protrusion
    # (still on) keeps the A2 margin-breaking benefit. See S2 PQ-REG-1 (2026-07-13).
    "\\usepackage[expansion=false]{microtype}\n"
    "\\usepackage{parskip}\n"
    "\\lstset{basicstyle=\\small\\ttfamily,breaklines=true,breakatwhitespace=false,"
    "columns=fullflexible,frame=single,backgroundcolor=\\color{gray!8},keepspaces=true,"
    "showstringspaces=false}\n"
    "\\sloppy\\emergencystretch=3em\n"
    "\\hypersetup{colorlinks=true,linkcolor=blue,urlcolor=blue,breaklinks=true}\n"
    "\\title{%(title)s}\n\\author{Persona}\n\\date{\\today}\n"
    "\\begin{document}\n\\maketitle\n%(body)s\n\\end{document}\n"
)

# fence language -> listings language name. Only languages listings ships a dictionary for (an unknown
# `language=` aborts the build); everything else renders as a plain lstlisting. Keys are lowercased.
_LST_LANG = {
    "python": "Python", "py": "Python", "c": "C", "cpp": "C++", "c++": "C++", "java": "Java",
    "sql": "SQL", "r": "R", "matlab": "Matlab", "fortran": "Fortran", "html": "HTML", "xml": "XML",
    "php": "PHP", "perl": "Perl", "ruby": "Ruby", "tex": "[LaTeX]TeX", "latex": "[LaTeX]TeX",
}

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
    "✓": r"\checkmark{}", "✗": r"$\times$", "⊕": r"$\oplus$", "⊗": r"$\otimes$", "⊙": r"$\odot$",
    "∓": r"$\mp$", "≅": r"$\cong$", "≜": r"$\triangleq$", "⟨": r"$\langle$", "⟩": r"$\rangle$",
    "†": r"$\dagger$", "‖": r"$\|$", "⌀": r"$\varnothing$", "★": r"$\star$", "•": r"$\bullet$",
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


def _img_size(p: Path):
    """(width, height) in px from a PNG/JPEG header, using stdlib only (no Pillow) so figure-sizing
    stays offline + deterministic. None if the file is missing or not a format we parse."""
    try:
        data = p.read_bytes()
    except OSError:
        return None
    if data[:8] == b"\x89PNG\r\n\x1a\n" and len(data) >= 24:
        import struct
        w, h = struct.unpack(">II", data[16:24])
        return (w, h)
    if data[:2] == b"\xff\xd8":  # JPEG: walk segment markers to the SOFn frame header
        i, n = 2, len(data)
        while i + 9 < n:
            if data[i] != 0xFF:
                i += 1; continue
            marker = data[i + 1]
            if 0xC0 <= marker <= 0xCF and marker not in (0xC4, 0xC8, 0xCC):
                return ((data[i + 7] << 8) | data[i + 8], (data[i + 5] << 8) | data[i + 6])
            i += 2 + ((data[i + 2] << 8) | data[i + 3])
    return None


def _img_include(path: str, assets: Path | None) -> str:
    """Embed a figure legibly (A3): full text-width by default with the aspect capped so a tall figure
    can't force a tiny width; very-wide figures rotate to landscape so their on-figure text stays big.
    Was a fixed width=0.85\\linewidth, which shrank large flowcharts' text below legibility."""
    size = _img_size(assets / path) if assets is not None else None
    if size and size[1]:
        aspect = size[0] / size[1]
        if aspect >= 2.2:  # very wide -> rotate 90deg, size to the page height (landscape) so text is readable
            return ("\\makebox[\\linewidth]{\\rotatebox{90}{"
                    "\\includegraphics[width=0.82\\textheight,keepaspectratio]{%s}}}" % path)
        if aspect <= 0.5:  # very tall -> cap the height so it doesn't blow past the page / go micro-width
            return "\\includegraphics[height=0.82\\textheight,keepaspectratio]{%s}" % path
    # default (incl. unknown size): full text-width, but cap total height so tall figures stay on-page
    return "\\includegraphics[width=\\linewidth,totalheight=0.82\\textheight,keepaspectratio]{%s}" % path


def _inline(text: str, assets: Path | None = None) -> str:
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
                  lambda m: _img_include(imgs[int(m.group(1))], assets), text)
    text = re.sub(r"\x02(\d+)\x02",
                  lambda m: "\\href{%s}{%s}" % (links[int(m.group(1))][1], _esc(links[int(m.group(1))][0])), text)
    return text


def sanitize_markdown(md: str) -> str:
    """Strip pseudo-XML tool markers the model sometimes leaks into prose (</synthesis_markdown>,
    <parameter …>, antml/tool tags) and collapse runaway blank lines — so notes read like prose."""
    md = md or ""
    md = re.sub(r"</?(?:synthesis_markdown|report_markdown|parameter|invoke|tool_use|"
                r"function_calls|antml:[A-Za-z_:]+)[^>]*>", "", md)
    md = re.sub(r'<parameter\b[^>]*>', "", md)
    # strip inline HTML tags that leak from source metadata (e.g. "<i>APOE</i>", "<tt>IdentityFinder</tt>")
    # — they render as literal junk in LaTeX and read as unprofessional. Keep prose, drop the tags.
    md = re.sub(r"</?(?:i|b|em|strong|tt|sub|sup|u|span|small|br|mml:[A-Za-z]+)\s*/?>", "", md, flags=re.I)
    md = re.sub(r"\n{4,}", "\n\n\n", md)
    return md.strip()


def md_to_latex(md: str, title: str = "", assets: Path | None = None) -> str:
    """Pragmatic markdown -> LaTeX body (headings, lists, code fences, blockquotes, images, math).
    `assets` (dir next to the source) is used to size embedded figures; None -> default full-width."""
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
                # code block via listings (wraps long lines, A1); tag language when listings knows it
                lang = _LST_LANG.get(re.sub(r"^`+", "", ln.strip()).strip().lower(), "")
                opt = "[language=%s]" % lang if lang else ""
                close_list(); out.append("\\begin{lstlisting}%s" % opt); in_code = True
            else:
                out.append("\\end{lstlisting}"); in_code = False
            i += 1; continue
        if in_code:
            out.append(ln); i += 1; continue
        if not ln.strip():
            close_list(); out.append(""); i += 1; continue
        h = re.match(r"^(#{1,4})\s+(.*)$", ln)
        if h:
            close_list()
            lvl = len(h.group(1)); cmd = ["section", "subsection", "subsubsection", "paragraph"][min(lvl - 1, 3)]
            out.append("\\%s*{%s}" % (cmd, _inline(h.group(2), assets))); i += 1; continue
        m = re.match(r"^\s*[-*+]\s+(.*)$", ln)
        if m:
            if in_list != "ul":
                close_list(); out.append("\\begin{itemize}[leftmargin=1.4em]"); in_list = "ul"
            out.append("\\item " + _inline(m.group(1), assets)); i += 1; continue
        m = re.match(r"^\s*\d+\.\s+(.*)$", ln)
        if m:
            if in_list != "ol":
                close_list(); out.append("\\begin{enumerate}[leftmargin=1.6em]"); in_list = "ol"
            out.append("\\item " + _inline(m.group(1), assets)); i += 1; continue
        if ln.strip().startswith(">"):
            close_list(); out.append("\\begin{quote}" + _inline(ln.strip()[1:].strip(), assets) + "\\end{quote}"); i += 1; continue
        if re.match(r"^\s*\$\$\s*$", ln):   # display-math fence
            close_list(); block = []
            i += 1
            while i < len(lines) and not re.match(r"^\s*\$\$\s*$", lines[i]):
                block.append(lines[i]); i += 1
            out.append("\\[" + "\n".join(block) + "\\]"); i += 1; continue
        close_list(); out.append(_inline(ln, assets)); i += 1
    close_list()
    if in_code:
        out.append("\\end{lstlisting}")
    return "\n".join(out)


def _decl_unicode() -> str:
    """Declare the Unicode math/Greek chars LLM LaTeX emits, so pdflatex accepts them anywhere."""
    out = []
    for ch, repl in _UNI.items():
        cp = ord(ch)
        if cp < 0x80:
            continue
        m = repl.strip()
        body = ("\\ensuremath{%s}" % m[1:-1]) if (m.startswith("$") and m.endswith("$")) else m
        out.append("\\DeclareUnicodeCharacter{%04X}{%s}" % (cp, body))
    return "\n".join(out)


def harden_latex(tex: str) -> str:
    """Make LLM-written LaTeX actually compile: strip combining marks, replace the model's own
    inputenc/fontenc with robust ones, and DECLARE the Unicode math chars it emits (≥, ≤, ∑, α…) so
    pdflatex never dies on 'Unicode character not set up'. Non-destructive to real math."""
    tex = "".join(c for c in (tex or "") if not (0x0300 <= ord(c) <= 0x036F))
    tex = re.sub(r"\\usepackage(?:\[[^\]]*\])?\{(?:inputenc|fontenc)\}\s*", "", tex)
    inject = ("\n\\usepackage[utf8]{inputenc}\n\\usepackage[T1]{fontenc}\n"
              "\\usepackage{amsmath,amssymb}\n" + _decl_unicode() + "\n")
    m = re.search(r"\\documentclass(?:\[[^\]]*\])?\{[^}]*\}", tex)
    return (tex[:m.end()] + inject + tex[m.end():]) if m else ("\\documentclass{article}" + inject + tex)


def choose_layout(md: str) -> str:
    """Pick 'one' vs 'two' columns from content (A4): math-heavy derivations (wide display equations,
    dense inline math) read better single-column; long, structured empirical prose goes two-column.
    Deterministic pure function of the text. Conservative -> defaults to 'one' when unsure."""
    md = md or ""
    words = max(len(md.split()), 1)
    math = (len(re.findall(r"(?<!\$)\$(?!\$)[^$\n]+\$", md))
            + 2 * len(re.findall(r"\$\$", md)) + 2 * len(re.findall(r"\\\[", md)))
    if math / words > 0.03:            # math-dense -> single column (wide equations)
        return "one"
    structural = (len(re.findall(r"(?m)^#{1,4}\s", md)) + len(re.findall(r"(?m)^\s*[-*+]\s", md))
                  + md.count("|"))
    if words > 400 and structural >= 6:  # long + structured empirical paper -> two columns
        return "two"
    return "one"


def render_latex(source: str, fmt: str = "md", *, title: str = "", layout: str = "auto",
                 assets: Path | None = None) -> str:
    """Build the full compilable .tex for `source` (md|tex). Pure/offline so the emitted LaTeX can be
    inspected without a sandbox. `layout`: 'one'|'two'|'auto' (auto -> choose_layout)."""
    if fmt == "tex":
        tex = source
    else:
        md = sanitize_markdown(source)
        lay = choose_layout(md) if layout == "auto" else layout
        classopts = "11pt,twocolumn" if lay == "two" else "11pt"
        body = md_to_latex(md, title, assets=assets)
        tex = _TEMPLATE % {"classopts": classopts, "title": _scrub(_esc(title or "Document")), "body": body}
    # FINAL GUARANTEE (no dead PDFs): any non-ASCII math glyph that survived into a code block
    # or a raw .tex source — ≡ ≈ Ω ⊕ ✓ … — is undeclared under utf8 inputenc and aborts pdflatex
    # ("not set up for use with LaTeX → no output PDF"). Prose is already mapped to ASCII macros
    # upstream; here we strip anything ≥ U+0300 across the WHOLE document. Precomposed Latin accents
    # (é ő ü, < U+0300) are preserved and rendered by inputenc+fontenc.
    return "".join(c if ord(c) < 0x0300 else " " for c in tex)


def compile_source(source: str, fmt: str, project: Path, *, title: str = "", layout: str = "auto") -> dict:
    """Write `source` (md|tex) as main.tex in `project` and compile to PDF. Deterministic, offline."""
    project.mkdir(parents=True, exist_ok=True)
    tex = render_latex(source, fmt, title=title, layout=layout, assets=project)
    (project / "main.tex").write_text(tex, encoding="utf-8")
    r = sandbox.compile_latex(project, "main.tex")
    return r


def slug_for(text: str) -> str:
    return (re.sub(r"[^a-z0-9]+", "-", (text or "").lower()).strip("-")[:48]) or "document"
