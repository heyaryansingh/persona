"""F1.9 — a refuted past result re-opens the question as fresh grounded work (self-correcting loop).

On a re-test that FLIPS a result to `refuted`, revisit routes through the FC-1 seam
(`open_from_conflict`) to launch a fresh investigation; a result that HOLDS opens nothing. The seam is
mocked here (its own behaviour is covered by test_open_from_conflict). $0 — the re-test is stubbed.
"""
import types

from persona import context
from persona.paths import Paths
from persona.agents import revisit
from persona.agents import reason as reason_mod
from persona.memory import verified as vled
from persona.research.investigation import Investigation


def _stub(tmp_path):
    p = types.SimpleNamespace()
    p.paths = Paths(tmp_path)
    p.paths.ensure()
    p.events = types.SimpleNamespace(emit=lambda *a, **k: None)   # log().emit() sink
    return p


def _patch_common(monkeypatch, prove_result):
    monkeypatch.setattr(revisit, "budget", lambda: types.SimpleNamespace(can_spend=lambda: True))
    monkeypatch.setattr(reason_mod, "prove", lambda stmt, parent_id=None: prove_result)
    calls = []

    def _fake_ofc(cls, conflict_id, evidence_claim_ids=None):
        calls.append((conflict_id, evidence_claim_ids))
        return types.SimpleNamespace(slug="inv-reopened")

    monkeypatch.setattr(Investigation, "open_from_conflict", classmethod(_fake_ofc))
    return calls


def test_refutation_opens_one_investigation(tmp_path, monkeypatch):
    p = _stub(tmp_path)
    with context.use(p):
        vled.record("X equals Y", "sympy", "verified")
        calls = _patch_common(monkeypatch, {"verified": 0, "checks": 0})   # re-proof fails → refuted
        r = revisit.revisit()
        assert r["new"] == "refuted"
        assert len(calls) == 1                                    # exactly one fresh investigation
        assert calls[0][0].startswith("revisit:")                 # routed via the FC-1 seam
        assert calls[0][1] is None                                # no fabricated evidence — re-gathers
        assert r.get("reinvestigated") == "inv-reopened"


def test_held_result_opens_nothing(tmp_path, monkeypatch):
    p = _stub(tmp_path)
    with context.use(p):
        vled.record("A implies B", "sympy", "verified")
        calls = _patch_common(monkeypatch, {"verified": 2, "checks": 2})   # re-proof holds → verified
        r = revisit.revisit()
        assert r["new"] == "verified"
        assert calls == []                                        # nothing re-opened on a hold
