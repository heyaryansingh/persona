"""S2 paper-quality fixes on the generation side (persona/deliverables/paper.py).

Deterministic, offline — exercises the pure post-processing helpers directly, no network/model:
  A5  status vocabulary renders as a styled badge, never a raw **[OPEN]** literal
  A6  citations renumber contiguously 1..k; every inline [n] resolves; no gaps
  B1  deliverable filename is word-boundary readable, carries an ISO date, no 'latex-document-' prefix
"""
import re

from persona.deliverables.paper import (
    _badge, _deliverable_name, _fix_references, _slug, _style_status,
)


# --- A5: status badges -----------------------------------------------------------------------------

def test_no_raw_status_literal_survives():
    md = ("## Main result\n"
          "- The bound is tight **[PROVED HERE]**\n"
          "- Checked on 10^6 samples **[VERIFIED NUMERICALLY]**\n"
          "- General case unresolved **[OPEN]**\n")
    out = _style_status(md)
    # no bare **[A-Z]+** (single- or multi-word) literal remains
    assert not re.search(r"\*\*\[[A-Z][A-Z /]*\]\*\*", out), out
    # each status now renders as a styled small-caps badge
    for label in ("proved here", "verified numerically", "open"):
        assert r"\textsc{%s}" % label in out
    # defined once = a single legend line explaining the key
    assert out.count("*Status key:*") == 1


def test_unknown_status_token_gets_neutral_badge():
    out = _style_status("## Main result\n- odd claim **[CONJECTURED]**\n")
    assert r"\colorbox{gray!25}{\textsc{conjectured}}" in out
    assert "**[CONJECTURED]**" not in out


def test_style_status_noop_without_tags():
    md = "## Results\nJust prose with a cite [1].\n"
    assert _style_status(md) == md   # no badges injected when there's nothing to style


def test_badge_survives_markdown_to_latex_and_compiles_in_text_mode():
    # badge is inline math wrapping \text so md_to_latex keeps it verbatim; \colorbox runs in text mode
    b = _badge("OPEN")
    assert b.startswith("$") and b.endswith("$")
    assert r"\text{\colorbox{red!20}{\textsc{open}}}" in b


# --- A6: contiguous citations ----------------------------------------------------------------------

def _ref_nums(md):
    refs = md.split("## References", 1)[1]
    return [int(n) for n in re.findall(r"^\s*(\d+)\.\s", refs, re.M)]


def test_citations_renumber_contiguously():
    sources = [f"Source {i}" for i in range(1, 8)]   # 7 sources exist
    # body cites only 5, 2, 7 (out of order, sparse) — classic gappy case
    md = "## Results\nFoo [5], bar [2], and baz [7]; again [5].\n"
    out = _fix_references(md, sources)
    nums = _ref_nums(out)
    assert nums == [1, 2, 3], nums                    # exactly 1..k, no gaps
    # first-appearance order: 5->1, 2->2, 7->3
    assert re.findall(r"\[(\d+)\]", out.split("## References")[0]) == ["1", "2", "3", "1"]
    # every inline [n] resolves to a listed reference, and the mapped source text is right
    body, refs = out.split("## References")
    inline = {int(n) for n in re.findall(r"\[(\d+)\]", body)}
    listed = set(_ref_nums(out))
    assert inline <= listed
    assert "1. Source 5" in refs and "2. Source 2" in refs and "3. Source 7" in refs


def test_dangling_citation_dropped():
    md = "## Results\nreal [1], dangling [9].\n"
    out = _fix_references(md, ["Only source"])
    assert _ref_nums(out) == [1]
    assert re.findall(r"\[(\d+)\]", out.split("## References")[0]) == ["1"]   # [9] removed


def test_no_valid_cites_drops_all():
    out = _fix_references("## Results\nnothing cited here.\n", ["A", "B"])
    assert "## References" not in out
    assert "[" not in out


# --- B1: readable filenames ------------------------------------------------------------------------

def test_deliverable_name_is_readable_with_iso_date():
    name = _deliverable_name("The Erdos-Straus conjecture on 4/n for large n and its consequences")
    assert name.endswith(".pdf")
    assert "latex-document-" not in name
    assert re.search(r"-\d{4}-\d{2}-\d{2}\.pdf$", name), name        # carries an ISO date
    stem = name[:-4]
    for seg in stem.split("-"):
        assert not (seg.isalpha() and len(seg) > 40), seg           # no run-on alpha blob (B1 lint)


def test_slug_never_cuts_mid_word():
    long_title = "quantum error correction thresholds for surface codes under biased noise channels"
    s = _slug(long_title)
    assert len(s) <= 60
    # truncation lands on a word boundary: the slug is a prefix of the full hyphenated title's words
    full_words = re.sub(r"[^a-z0-9]+", "-", long_title.lower()).split("-")
    assert s.split("-") == full_words[:len(s.split("-"))]           # no partial trailing word
