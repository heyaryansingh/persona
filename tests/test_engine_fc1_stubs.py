"""Lane 1 · Milestone-0 FC-1 stubs — frozen signatures + typed returns other lanes build against.

Covers: span-weighted consensus (protected dissent), investigation.open_from_conflict (loop-closing
entry), the FC-1 queue task-type constants, and the M2 re-audit budget-churn guard S4 now owns in the
daemon. All $0, no model calls.
"""
import types

from persona import context
from persona.paths import Paths
from persona.agents import consensus, verifier, debate
from persona.daemon import queue as taskqueue
from persona.daemon import supervisor
from persona.research.investigation import Investigation


def _stub_persona(tmp_path):
    p = types.SimpleNamespace()
    p.paths = Paths(tmp_path)
    p.paths.ensure()
    return p


# ---- FC-1 consensus.span_weighted_consensus ------------------------------------------------------
def test_consensus_shape_and_protected_dissent():
    out = consensus.span_weighted_consensus([
        {"claim_id": "c1", "claim": "X increases Y", "admit": True, "span": "X raised Y.", "weight": 1.0},
        {"claim_id": "c1", "claim": "X increases Y", "admit": True, "span": "Y rose.", "weight": 0.5},
        {"claim_id": "c1", "claim": "X increases Y", "admit": False, "span": "No effect.", "weight": 2.0},
    ])
    assert set(out) == {"claim", "admit_votes", "weighted_support", "dissent"}
    assert out["admit_votes"] == 2
    assert out["weighted_support"] == round(1.5 / 3.5, 4)
    assert isinstance(out["admit_votes"], int) and isinstance(out["weighted_support"], float)
    # the dissenter is PRESERVED, not averaged away
    assert out["dissent"] == [{"claim_id": "c1", "span": "No effect.", "weight": 2.0}]


def test_consensus_empty_is_typed_zero():
    assert consensus.span_weighted_consensus([]) == {
        "claim": "", "admit_votes": 0, "weighted_support": 0.0, "dissent": []}
    # malformed entries are ignored, never trusted
    assert consensus.span_weighted_consensus([None, 3, "x"])["admit_votes"] == 0


# ---- FC-1 task types ------------------------------------------------------------------------------
def test_fc1_task_type_constants():
    assert taskqueue.TASK_VERIFY == "verify"
    assert taskqueue.TASK_DEBATE == "debate"
    assert taskqueue.TASK_STALENESS == "staleness"
    assert taskqueue.FC1_TASK_TYPES == {"verify", "debate", "staleness"}


# ---- FC-1 investigation.open_from_conflict --------------------------------------------------------
def test_open_from_conflict_returns_tagged_investigation(tmp_path):
    with context.use(_stub_persona(tmp_path)):
        inv = Investigation.open_from_conflict("cflx_123", evidence_claim_ids=["clm_a", "clm_b"])
        assert isinstance(inv, Investigation)
        assert inv.meta["origin"] == {"kind": "conflict", "conflict_id": "cflx_123",
                                      "evidence_claim_ids": ["clm_a", "clm_b"]}
        assert "cflx_123" in inv.question
        assert inv.status == "open"
        assert (inv.folder / "investigation.json").exists()
        # loadable round-trip (durable), origin persisted
        again = Investigation.load(inv.slug)
        assert again is not None and again.meta["origin"]["conflict_id"] == "cflx_123"


def test_open_from_conflict_defaults_no_evidence(tmp_path):
    with context.use(_stub_persona(tmp_path)):
        inv = Investigation.open_from_conflict("cflx_x")
        assert inv.meta["origin"]["evidence_claim_ids"] == []


# ---- FC-1 verifier / debate M0 stubs (typed, $0, no model/sandbox) --------------------------------
def test_verifier_stub_is_not_applicable_and_costless():
    r = verifier.verify("clm_x", evidence_claim_ids=["clm_a"])
    assert set(r) == {"ok", "claim_id", "verdict", "check_kind", "ran_code",
                      "artifact_ids", "span", "note"}
    assert r["verdict"] == "not_applicable" and r["verdict"] in verifier.VERDICTS
    assert r["ran_code"] is False and r["artifact_ids"] == [] and r["claim_id"] == "clm_x"


def test_debate_shape_and_no_spend_without_budget():
    # two opposing stances but no budget → debate can't run → unresolved, no escalation, no spend
    r = debate.debate("X increases Y",
                      [{"span": "X raised Y.", "stance": "+"}, {"span": "no effect.", "stance": "-"}])
    assert set(r) == {"ok", "resolved", "verdict", "agreement", "rounds_used",
                      "transcript_ref", "escalate"}                    # frozen 7-key shape
    assert r["resolved"] is False and r["escalate"] is False
    assert isinstance(r["agreement"], float) and r["agreement"] == 0.0


# ---- M2 re-audit budget-churn guard (S4-owned daemon) --------------------------------------------
def test_should_reaudit_only_when_due_and_funded():
    due = types.SimpleNamespace(due=lambda: {"key": "slug:x"})
    none = types.SimpleNamespace(due=lambda: None)
    assert supervisor._should_reaudit(due, True) is True        # funded + due → re-audit
    assert supervisor._should_reaudit(none, True) is False       # funded + nothing due → no churn
    assert supervisor._should_reaudit(due, False) is False       # no budget → never
    # exception in due() must not crash the scheduler — fail closed (no spend)
    def _boom():
        raise RuntimeError("watchlist unavailable")
    assert supervisor._should_reaudit(types.SimpleNamespace(due=_boom), True) is False
