"""Tests for the pre-ship paper lint (persona/deliverables/paper_lint.py)."""
from persona.deliverables.paper_lint import lint_paper


CLEAN = {
    "markdown": (
        "# A Clean Paper on Tau Aggregation\n\n"
        "## Abstract\nWe establish a bound [1] and verify it numerically [2].\n\n"
        "## Main result\n- The rate scales linearly **[OPEN]**\n\n"   # OPEN is a legit single-word tag
        "## Results\nThe rate scales linearly [1] as shown [2].\n\n"
        "```\nshort = compute(x)\n```\n\n"
        "## References\n\n"
        "1. Smith et al. — Nature (doi:10.1/a)\n"
        "2. Doe et al. — PNAS (doi:10.2/b)\n"
    ),
    "filename": "paper-tau-aggregation-a1b2c3d4e5.pdf",
    "sources": ["Smith et al. — Nature (doi:10.1/a)", "Doe et al. — PNAS (doi:10.2/b)"],
}


def test_clean_paper_passes():
    r = lint_paper(CLEAN)
    assert r["ok"] is True, r
    assert r["violations"] == []


def test_legit_open_tag_is_allowed():
    # `**[OPEN]**` must NOT trip A5 even though it matches the `**[A-Z]+**` shape.
    r = lint_paper({"markdown": "## Main result\n- conjecture **[OPEN]**\n"})
    assert not any(x["code"] == "A5" for x in r["violations"]), r


def test_str_input_accepted():
    assert lint_paper("# Title\n\nJust prose, no cites.\n")["ok"] is True


def _codes(meta):
    return {x["code"] for x in lint_paper(meta)["violations"]}


def test_dirty_paper_fires_every_code():
    dirty = {
        "markdown": (
            "# " + "x" * 50 + "\n\n"                          # A2: run-on heading token
            "## Results\nA claim **[CITED]** here, and see [5].\n\n"  # A5 + A6 (only 2 refs)
            "This work was published in 1970 (0).\n\n"        # A7: '1970' and '(0)'
            "```\n" + "y" * 100 + "\n```\n\n"                 # A1: overflowing code line
            "## References\n\n"
            "1. A — v (doi:1)\n"
            "3. B — v (doi:2)\n"                              # A6: non-contiguous (1,3)
        ),
        "filename": "paper-" + "a" * 60 + "-deadbeef00.pdf",  # B1: run-on alpha segment
    }
    codes = _codes(dirty)
    assert lint_paper(dirty)["ok"] is False
    for expected in ("A1", "A2", "A5", "A6", "A7", "B1"):
        assert expected in codes, f"{expected} did not fire; got {codes}"


def test_a1_verbatim_only():
    r = lint_paper("```\n" + "z" * 90 + "\n```\n")
    assert {x["code"] for x in r["violations"]} == {"A1"}


def test_a6_dangling_citation():
    md = "## Results\nsee [3]\n\n## References\n\n1. A (doi:1)\n2. B (doi:2)\n"
    assert "A6" in {x["code"] for x in lint_paper({"markdown": md})["violations"]}


def test_a6_contiguous_and_resolved_passes():
    md = "## Results\nsee [1] and [2]\n\n## References\n\n1. A (doi:1)\n2. B (doi:2)\n"
    assert not any(x["code"] == "A6" for x in lint_paper({"markdown": md})["violations"])


def test_a7_scans_source_cards():
    r = lint_paper({"markdown": "# T\n\nbody\n", "sources": ["Ghost et al. — J (1970)"]})
    assert "A7" in {x["code"] for x in r["violations"]}


def test_tex_input_and_textbf_status_literal():
    tex = (r"\section*{Results}" + "\n" + r"A claim \textbf{[CITED]} here." + "\n")
    assert "A5" in {x["code"] for x in lint_paper({"tex": tex})["violations"]}


def test_best_effort_signals():
    r = lint_paper({"markdown": "# T\n\nbody\n", "font_ok": False, "provenance_present": False})
    codes = {x["code"] for x in r["violations"]}
    assert "A3" in codes and "A8" in codes
