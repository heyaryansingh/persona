"""Editable-LaTeX recompile is byte-deterministic and rejects broken input.

The `/recompile` endpoint wraps `sandbox.compile_latex` (offline, read-only Docker, no model
call). This exercises that primitive directly — the same guarantee the endpoint relies on — so a
user editing and recompiling a paper gets reproducible PDFs. Skips cleanly without the sandbox image.
"""
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest

from persona.tools import sandbox

_GOOD = (r"\documentclass{article}\usepackage{amsmath}\title{T}\author{P}"
         r"\begin{document}\maketitle\section{S}Hello $E=mc^2$.\end{document}")
_BAD = r"\documentclass{article}\begin{document}\unknownmacro no end"


@pytest.mark.skipif(not sandbox.image_ready(), reason="persona-sandbox image not available")
def test_recompile_is_byte_deterministic():
    hashes = []
    for _ in range(2):
        with TemporaryDirectory() as td:
            (Path(td) / "main.tex").write_text(_GOOD, encoding="utf-8")
            r = sandbox.compile_latex(Path(td), "main.tex")
            assert r["ok"], r.get("log", "")[-400:]
            assert r["pdf_sha256"]
            hashes.append(r["pdf_sha256"])
    assert hashes[0] == hashes[1], "identical source+environment must produce identical PDF bytes"


@pytest.mark.skipif(not sandbox.image_ready(), reason="persona-sandbox image not available")
def test_broken_latex_fails_without_stale_pdf():
    with TemporaryDirectory() as td:
        (Path(td) / "main.tex").write_text(_BAD, encoding="utf-8")
        r = sandbox.compile_latex(Path(td), "main.tex")
        assert r["ok"] is False
        assert not (Path(td) / "main.pdf").exists(), "a failed build must not leave a PDF"
