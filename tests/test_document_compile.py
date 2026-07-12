"""Markdown -> LaTeX -> PDF: the mind's reports/notes become real compiled documents (not boxes),
robust to the Unicode math LLM markdown is full of. Deterministic; skips without the sandbox image.
"""
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest

from persona.deliverables import document
from persona.tools import sandbox

_MD = ("# Erdos-Straus reading report\n\n"
       "We verified $4/n = 1/x+1/y+1/z$ for all n ≥ 2 up to 60000 — **0 failures**.\n\n"
       "## Findings\n"
       "- Reduces to primes p ≡ 1 (mod 24)\n"
       "- Hard cases have offset ≤ 7\n\n"
       "Greek/limits: α, β, ∑, ∫, ℝ. See [Elsholtz-Tao](https://arxiv.org/abs/1107.1010).\n")


def test_md_to_latex_maps_unicode_and_structure():
    body = document.md_to_latex(_MD, "Report")
    assert "\\section*{" in body and "\\begin{itemize}" in body
    assert "\\geq" in body and "\\equiv" in body and "\\mathbb{R}" in body  # unicode mapped
    assert "≥" not in body and "ℝ" not in body                    # no raw unicode left
    assert "\\href{https://arxiv.org/abs/1107.1010}" in body


@pytest.mark.skipif(not sandbox.image_ready(), reason="persona-sandbox image not available")
def test_markdown_compiles_to_a_real_pdf_deterministically():
    hashes = []
    for _ in range(2):
        with TemporaryDirectory() as td:
            r = document.compile_source(_MD, "md", Path(td), title="Erdos-Straus report")
            assert r["ok"], r.get("log", "")[-400:]
            assert (Path(td) / "main.pdf").stat().st_size > 0
            hashes.append(r["pdf_sha256"])
    assert hashes[0] == hashes[1]
