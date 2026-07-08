"""Delegation + artifact loop tests. Run: python tests/test_loops2.py"""
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from persona.store import BeliefStore, Claim               # noqa: E402
from persona.self_state import Self                        # noqa: E402
from persona.membrane import ContradictionEvent            # noqa: E402
from persona.loops.delegation import HandoffInbox, assemble_dossier  # noqa: E402
from persona.loops.artifact import mini_review, save_mini_review, note_reversal  # noqa: E402


def test_dossier_assembly_and_resolution_anchors_belief():
    s = BeliefStore()
    s.add_claim(Claim("k", "microglia drive neuroinflammation", logit=1.0, tier="core"))
    s.add_source("k", "PMID:1", "labA")
    inbox = HandoffInbox(s)
    ev = ContradictionEvent("k", "microglia drive neuroinflammation", "context-divergence", 2, 2,
                            "both sides independently supported")
    d = inbox.add_event(ev)
    assert d.status == "open" and d.candidate_explanations and "context" in d.candidate_explanations[0]
    assert len(inbox.open_items()) == 1
    # the human makes the call -> belief becomes an anchored, durable node
    anchored = inbox.resolve("k", d.candidate_explanations[0], truth=1)
    assert anchored.anchor and anchored.provenance_state == "HUMAN_CONFIRMED"
    assert len(inbox.open_items()) == 0
    s.close()


def test_mini_review_flags_dissents():
    s = BeliefStore()
    s.add_claim(Claim("a", "well-supported claim", logit=5.0, tier="core"))
    s.add_source("a", "r1", "g1"); s.add_source("a", "r2", "g2")
    s.add_claim(Claim("b", "single-source claim", logit=2.0, tier="core"))
    s.add_source("b", "r3", "g1")     # only 1 independent group -> dissent
    md = mini_review(s, ["a", "b"], title="Neuroinflammation review")
    assert "Unresolved dissents" in md
    assert "single-source claim" in md.split("Unresolved dissents")[1]
    assert "well-supported claim" in md
    s.close()


def test_save_review_and_error_log():
    with tempfile.TemporaryDirectory() as dtmp:
        me = Self(dtmp).hydrate()
        try:
            me.add_belief(Claim("c", "a claim", logit=1.0, tier="core"))
            me.store.update_belief("c", -1.0, cause="reader")
            path = save_mini_review(me, me.store, ["c"], title="Test Review")
            assert path.exists() and "Test Review" in path.read_text(encoding="utf-8")
            note_reversal(me, me.store, "c", note="new well-powered null")
            assert "reversed belief c" in me.errors_path.read_text(encoding="utf-8")
        finally:
            me.close()


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for t in tests:
        t()
        print(f"PASS {t.__name__}")
    print(f"\n{len(tests)} delegation+artifact tests passed.")
