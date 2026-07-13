"""P0 audit fixes: citation integrity, placeholder captions, and LaTeX Unicode survival."""
import tempfile
from pathlib import Path

from persona.deliverables.paper import _fix_references, _fix_captions


def test_fix_references_drops_orphans_and_danglers():
    md = ("Body cites [1] and [2] and a dangling [25].\n\n"
          "## References\n\n[1] canned\n[2] canned\n[3] orphan canned\n")
    sources = ["Alpha (doi:10.1/a)", "Beta (doi:10.2/b)", "Gamma (doi:10.3/c)"]
    out = _fix_references(md, sources)
    assert "[25]" not in out                      # dangling citation removed
    refs = out.split("## References")[1]
    assert "10.1/a" in refs and "10.2/b" in refs   # cited refs kept, with DOIs
    assert "Gamma" not in refs                     # uncited source (3) dropped — no orphan


def test_fix_references_no_resolvable_cites_drops_all():
    out = _fix_references("Body cites [9] only.\n\n## References\n\n[1] x\n", ["only one (doi:1)"])
    assert "[9]" not in out and "## References" not in out


def test_fix_captions_replaces_placeholder():
    md = "![Figure 1. structure and objects of the problem](figure1.png)"
    out = _fix_captions(md, {1: "Real title of the figure"})
    assert "Real title of the figure" in out and "structure and objects" not in out


def test_latex_unicode_never_crashes():
    """A doc with ≡ ≈ Ω ⊕ ✓ in prose AND a code block must still compile (was 7 dead PDFs)."""
    from persona.tools import sandbox
    if not sandbox.image_ready():
        import pytest
        pytest.skip("sandbox image not built")
    from persona.deliverables.document import compile_source
    md = ("# U\n\nProse: n ≡ 2, x ≈ y, Ω, a ⊕ b, ✓.\n\n```python\n# ✓ ⊕ Ω ≡\nprint('≈✓')\n```\n\nEnd ✓.\n"
          + "padding. " * 40)
    with tempfile.TemporaryDirectory() as td:
        r = compile_source(md, "md", Path(td), title="Unicode ≡≈Ω⊕✓")
        assert r.get("ok"), (r.get("log", "") or "")[-200:]
