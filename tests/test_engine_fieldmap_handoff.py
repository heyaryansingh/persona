"""F3.11 — a field-map contradiction is filed as an FC-2 handoff (not only displayed), and a synthesis
revision records what changed to a .history sidecar. Both paths are deterministic and fully offline."""
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import patch

from persona import inbox
from persona.synthesis import fieldmap
from persona.synthesis.synthesizer import note_diff, record_revision


def _contra():
    return {"subject": "IL-6", "object": "tau", "pos": 3, "neg": 1,
            "pos_claim": "clm_pos", "neg_claim": "clm_neg"}


def test_contradiction_files_a_valid_handoff():
    with TemporaryDirectory() as td:
        persona = SimpleNamespace(paths=SimpleNamespace(ops_dir=Path(td)))
        with patch.object(inbox, "get_persona", return_value=persona):
            hid = fieldmap._handoff_for_contradiction(_contra())
            assert hid.startswith("ho_")                       # filed, not swallowed
            # deterministic: same contradiction -> same content-hash id
            assert fieldmap._handoff_for_contradiction(_contra()) == hid
        rec = json.loads((Path(td) / inbox.INBOX_NAME).read_text(encoding="utf-8").splitlines()[0])
        d = rec["dossier"]
        assert rec["kind"] == "field_contradiction"
        assert d["conflict_type"] == "semantic"                # opposite signs on same relation
        assert {p["claim_id"] for p in d["disagreeing"]} == {"clm_pos", "clm_neg"}
        assert d["uncertainty"] == round(2 * 1 / 4, 3)         # balance heuristic (3 vs 1)


def test_evenly_split_is_max_uncertainty():
    with TemporaryDirectory() as td:
        persona = SimpleNamespace(paths=SimpleNamespace(ops_dir=Path(td)))
        with patch.object(inbox, "get_persona", return_value=persona):
            fieldmap._handoff_for_contradiction({"subject": "A", "object": "B", "pos": 2, "neg": 2,
                                                 "pos_claim": "x", "neg_claim": "y"})
        rec = json.loads((Path(td) / inbox.INBOX_NAME).read_text(encoding="utf-8").splitlines()[0])
        assert rec["dossier"]["uncertainty"] == 1.0


def test_note_diff_is_deterministic_and_empty_on_no_change():
    old = "# T\n\nAlpha raises tau.\nGaps remain.\n"
    new = "# T\n\nAlpha lowers tau.\nGaps remain.\n"
    d1 = note_diff(old, new)
    assert d1 == note_diff(old, new)                           # deterministic
    assert "-Alpha raises tau." in d1 and "+Alpha lowers tau." in d1
    assert not d1.startswith("---")                            # file headers dropped
    assert note_diff(old, old) == ""                           # unchanged -> empty


def test_record_revision_appends_history_sidecar():
    with TemporaryDirectory() as td:
        nd = Path(td)
        old, new = "# T\n\nold body\n", "# T\n\nnew body\n"
        diff = record_revision(nd, "il6-tau", "IL-6 & tau", old, new)
        assert diff                                            # returned the change
        hist = (nd / "il6-tau.history.md").read_text(encoding="utf-8")
        assert "## revision" in hist and "```diff" in hist and "+new body" in hist
        # unchanged revision writes nothing
        assert record_revision(nd, "il6-tau", "IL-6 & tau", new, new) == ""
        assert (nd / "il6-tau.history.md").read_text(encoding="utf-8").count("## revision") == 1
