import json
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from persona import inbox


def _dossier():
    return {
        "decision_requested": "Does IL-6 raise or lower tau?",
        "why_unresolvable": "two labs report opposite signs, both single-source",
        "disagreeing": [{"claim_id": "clm_a", "span": "IL-6 increases tau", "qualifiers": ["in vitro"]}],
        "conflict_type": "semantic",
        "cheapest_test": {"action": "reanalyze GEO series", "cost_tier": "low", "dataset": "GSE123"},
        "expected_updates": [{"outcome": "positive", "belief_change": "confirm + sign"}],
        "uncertainty": 0.6,
        "authority_boundary": "needs wet-lab confirmation",
    }


def test_valid_append_returns_deterministic_id():
    with TemporaryDirectory() as td:
        persona = SimpleNamespace(paths=SimpleNamespace(ops_dir=Path(td)))
        with patch.object(inbox, "get_persona", return_value=persona):
            hid = inbox.file_handoff("conflict", _dossier())
            assert hid.startswith("ho_")
            # same dossier -> same id (no wall-clock in id)
            assert inbox.file_handoff("conflict", _dossier()) == hid
        lines = (Path(td) / inbox.INBOX_NAME).read_text(encoding="utf-8").splitlines()
        assert len(lines) == 2
        rec = json.loads(lines[0])
        assert rec["handoff_id"] == hid and rec["dossier"]["conflict_type"] == "semantic"


def test_missing_key_raises():
    with TemporaryDirectory() as td:
        persona = SimpleNamespace(paths=SimpleNamespace(ops_dir=Path(td)))
        with patch.object(inbox, "get_persona", return_value=persona):
            bad = _dossier()
            del bad["cheapest_test"]
            with pytest.raises(ValueError):
                inbox.file_handoff("conflict", bad)
            bad2 = _dossier()
            bad2["conflict_type"] = "nonsense"
            with pytest.raises(ValueError):
                inbox.file_handoff("conflict", bad2)
