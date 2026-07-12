"""Citation hygiene: papers never ship with orphaned references (listed but nothing cites them)."""
from persona.deliverables.paper import _prune_refs


def test_keeps_only_cited_references():
    md = ("# T\n\n## Results\nWe use [1] and also [3].\n\n"
          "## References\n1. A\n2. B\n3. C\n4. D\n")
    out = _prune_refs(md)
    assert "1. A" in out and "3. C" in out
    assert "2. B" not in out and "4. D" not in out


def test_drops_orphaned_reference_block_when_nothing_cited():
    md = "# T\n\n## Results\nNo citations here at all.\n\n## References\n1. A\n2. B\n"
    out = _prune_refs(md)
    assert "## References" not in out and "1. A" not in out


def test_no_references_section_is_untouched():
    md = "# T\n\n## Results\nBody with [1].\n"
    assert _prune_refs(md) == md
