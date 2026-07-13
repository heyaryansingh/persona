"""S2 paper-quality fixes for deliverables/document.py — all offline, no sandbox/model calls.

Asserts the EMITTED LaTeX (via render_latex/md_to_latex, no compile) carries the four legibility fixes:
A1 code blocks use `listings`, A2 microtype + url token-breaking, A3 large figures embed full text-width,
A4 the layout field honours `two` (twocolumn).
"""
from persona.deliverables import document


def test_a1_code_fences_render_as_listings_with_language():
    body = document.md_to_latex("```python\nprint('hello world '*20)\nx = 1\n```\n")
    assert "\\begin{lstlisting}" in body and "\\end{lstlisting}" in body
    assert "language=Python" in body
    assert "verbatim" not in body            # old overflowing path is gone


def test_a1_unknown_language_falls_back_to_plain_listing():
    # an unknown language must NOT emit language=... (undefined listings language aborts pdflatex)
    body = document.md_to_latex("```zzznotalang\nfoo\n```\n")
    assert "\\begin{lstlisting}\n" in body and "language=" not in body


def test_a1_preamble_loads_listings_and_lstset():
    tex = document.render_latex("hello", "md")
    assert "\\usepackage{listings}" in tex
    assert "\\usepackage{xcolor}" in tex or "xcolor}" in tex  # xcolor present (listings colours)
    assert "\\lstset{" in tex and "breaklines=true" in tex


def test_a2_token_breaking_packages_present():
    tex = document.render_latex("a long_snake_case_identifier_that_would_overflow", "md")
    # expansion=false is load-bearing: bare \usepackage{microtype} breaks all PDF compiles in the
    # bitmap-font sandbox (PQ-REG-1). Assert the safe form so a revert fails this test.
    assert "\\usepackage[expansion=false]{microtype}" in tex
    assert "\\usepackage[hyphens]{url}" in tex
    assert "\\sloppy" in tex and "\\emergencystretch" in tex


def test_a3_figures_embed_full_text_width_not_fixed_085():
    body = document.md_to_latex("![a flowchart](fig.png)\n")
    assert "width=\\linewidth" in body           # full text-width path
    assert "keepaspectratio" in body             # aspect capped so tall figures don't go micro-width
    assert "0.85\\linewidth" not in body          # the old shrink-to-85% behaviour is gone


def test_a4_layout_two_yields_twocolumn_and_one_stays_single():
    two = document.render_latex("# Title\n\nbody text", "md", layout="two")
    one = document.render_latex("# Title\n\nbody text", "md", layout="one")
    assert "twocolumn" in two
    assert "twocolumn" not in one


def test_a4_choose_layout_prefers_one_for_math_heavy():
    math_md = "We study $f(x)$ where $a+b$ and $c=d$ and $e<f$ and $g>h$ over the reals."
    assert document.choose_layout(math_md) == "one"
