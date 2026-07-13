"""Dual-signal atomic admission gate (PRD F2.1) — the 'discipline of believing'.

Pure/offline (no FalkorDB, no model): admit_candidate takes a candidate + a KG, and admits
ONLY when BOTH an exact-span entailment AND independent KG support agree. Everything else
abstains to a human (one signal) or rejects (no signal). The poisoning case is the point:
cheap evidence (a valid span backed only by echo — many copies, one lab) can NOT commit.
"""
from persona.memory import membrane


class FakeKG:
    """crosscheck returns same-sign support items with the given per-item lab counts
    (labs = independent_source_count). Echo/poisoning = a high count list of 1s."""
    def __init__(self, support_labs):
        self._labs = support_labs

    def crosscheck(self, subject, obj, effect_sign):
        return {"support": [{"labs": n} for n in self._labs], "contradict": []}


# subject+object both appear verbatim in the span -> nli_span passes (offline stub).
_GROUNDED = {"subject": "microglia", "object": "synapse loss", "effect_sign": "+",
             "quote": "we observed that microglia drive synapse loss in the hippocampus"}
# no span text at all -> nli_span fails.
_UNGROUNDED = {"subject": "microglia", "object": "synapse loss", "effect_sign": "+"}


def test_both_signals_commit():
    out = membrane.admit_candidate(_GROUNDED, kg=FakeKG([2, 3]))
    assert out["admit"] is True
    assert out["route"] == "commit"
    assert out["signals"] == {"nli_span": True, "kg_support": True}


def test_span_only_abstains_to_human():
    out = membrane.admit_candidate(_GROUNDED, kg=FakeKG([1]))  # only 1 lab -> no KG support
    assert out["admit"] is False
    assert out["route"] == "human"
    assert out["signals"] == {"nli_span": True, "kg_support": False}


def test_kg_only_abstains_to_human():
    out = membrane.admit_candidate(_UNGROUNDED, kg=FakeKG([2, 4]))
    assert out["admit"] is False
    assert out["route"] == "human"
    assert out["signals"] == {"nli_span": False, "kg_support": True}


def test_no_signal_rejects():
    out = membrane.admit_candidate(_UNGROUNDED, kg=FakeKG([]))
    assert out["admit"] is False
    assert out["route"] == "reject"
    assert out["signals"] == {"nli_span": False, "kg_support": False}


def test_poisoning_cheap_evidence_alone_does_not_admit():
    # Correlated poisoning: a real, locatable span (nli_span passes) but the KG "support" is
    # pure echo — 40 copies from a SINGLE lab. Independence-by-lab means kg_support stays False,
    # so the gate abstains to a human and NEVER commits. Cheap volume can't buy belief.
    poison_kg = FakeKG([1] * 40)  # 40 supporting claims, all one lab
    out = membrane.admit_candidate(_GROUNDED, kg=poison_kg)
    assert out["admit"] is False
    assert out["route"] != "commit"
    assert out["signals"]["kg_support"] is False


def test_never_returns_anchor_side_effect():
    # The gate only routes; it must not expose/trigger anchoring. A KG with no anchor method
    # still works (proves admit_candidate never calls one).
    class NoAnchorKG(FakeKG):
        def anchor(self, *a, **k):
            raise AssertionError("admit_candidate must never anchor")

    out = membrane.admit_candidate(_GROUNDED, kg=NoAnchorKG([2, 2]))
    assert out["route"] == "commit" and out["admit"] is True
