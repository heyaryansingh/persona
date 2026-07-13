"""A8 + D — the grounded 'Provenance & Process' section and the pre-ship lint gate.

Offline, $0, deterministic. Proves:
  1. `_provenance_section` renders a grounded section from fixture run-data — every number carries its
     grounding key, computation hashes appear, and re-render is byte-identical (no wall-clock / model).
  2. Missing data degrades honestly to "not recorded for this run", never a fabricated 0.
  3. The section it ships is itself lint-clean (round-trip through the gate).
  4. D — a lint-failing document is BLOCKED by the ship-gate predicate; a clean one is not.
"""
import re

from persona.deliverables.paper import _provenance_section, _ship_blocked
from persona.deliverables.paper_lint import lint_paper


_FIXTURE = {
    "funnel": {"read": 42, "claims_extracted": 130, "admitted": 118, "rejected": 12,
               "reject_reasons": {"quote-not-verbatim": 9, "low-confidence": 3}},
    "pipeline": [{"stage": "Reader swarm", "count": 42, "source": "sources/*/meta.json"},
                 {"stage": "Consolidation", "count": 6, "source": "notes/*.md"},
                 {"stage": "Writer", "count": 1, "source": "this manuscript"}],
    "sources": {"admitted": 8, "quarantined": 3},
    "computations": [{"what": "Figure 1 (sandbox matplotlib)",
                      "source_sha256": "a1b2c3d4e5f6a7b8c9d0", "ok": True}],
    "robustness": {"band": "plausible", "likelihood": "58%", "interval": "41–72%",
                   "failing": ["no-independent-replication"], "source": "robustness audit"},
}


def test_provenance_section_grounded_and_deterministic():
    sec = _provenance_section(_FIXTURE)
    assert "## Provenance & Process" in sec
    # every headline number is present AND carries a grounding key on its line
    for num, key in (("42", "sources/*/meta.json"), ("118", "sources/*/claims.jsonl"),
                     ("12", "sources/*/claims_rejected.jsonl"), ("8", "## References")):
        line = next((l for l in sec.splitlines() if re.search(rf"\b{num}\b", l) and "**" in l), None)
        assert line and key in line, f"{num} not grounded by {key}: {line!r}"
    assert "quote-not-verbatim (9)" in sec          # reject-reason breakdown, sorted+deterministic
    assert "sha256:a1b2c3d4e5f6" in sec             # computation content hash (truncated)
    assert "plausible" in sec and "58%" in sec       # robustness verdict
    # re-render is byte-identical (no wall-clock, no model call in the render path)
    assert _provenance_section(_FIXTURE) == sec
    # the section it ships must itself pass the deterministic lint (no A1/A5/A6/A7 self-trips)
    assert lint_paper({"markdown": "# t\n\n## Results\nBody [1].\n\n## References\n\n1. X (doi:1)\n"
                       + "\n\n" + sec})["ok"], "provenance section must not trip its own lint"


def test_missing_data_is_honest_never_zero():
    sec = _provenance_section({})                    # no logged data at all
    assert sec.count("not recorded for this run") >= 4   # funnel/pipeline/sources/computations/robustness
    # honesty: a missing datum is NEVER rendered as a fabricated bold 0
    assert "**0**" not in sec
    # a partial run degrades per-section: funnel present, robustness absent
    partial = _provenance_section({"funnel": {"read": 5}})
    assert "**5**" in partial and "sources/*/meta.json" in partial
    assert "not recorded for this run" in partial.split("### Robustness")[1]


def test_lint_gate_blocks_failing_doc():
    # a doc with an epoch-1970 leak and non-contiguous references fails the deterministic audit
    dirty = {"markdown": ("# A Paper\n\n## Results\nA claim [5], published in 1970.\n\n"
                          "## References\n\n1. A — v (doi:1)\n3. B — v (doi:2)\n")}
    verdict = lint_paper(dirty)
    assert not verdict["ok"], "dirty doc should fail lint"
    assert _ship_blocked(verdict) is True, "a lint-failing doc MUST be blocked from shipping"

    clean = {"markdown": ("# A Clean Paper\n\n## Results\nA bound holds [1] and is verified [2].\n\n"
                          "## References\n\n1. A — v (doi:1)\n2. B — v (doi:2)\n"),
             "filename": "paper-clean-2026-07-13.pdf"}
    ok = lint_paper(clean)
    assert ok["ok"], ok
    assert _ship_blocked(ok) is False, "a clean doc must ship"


if __name__ == "__main__":
    test_provenance_section_grounded_and_deterministic()
    test_missing_data_is_honest_never_zero()
    test_lint_gate_blocks_failing_doc()
    print("ok")
