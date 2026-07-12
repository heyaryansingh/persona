"""The verified self-correcting loop: a result is TESTED only when a check passed, and the revisit
loop can downgrade it. The headline differentiator — a mind that knows what it has proven and
re-checks its own past work.
"""
import types

from persona import context
from persona.paths import Paths
from persona.memory import verified as vled


def _stub(tmp_path):
    p = types.SimpleNamespace()
    p.paths = Paths(tmp_path)
    p.paths.ensure()
    return p


def test_record_only_reflects_actual_check(tmp_path):
    with context.use(_stub(tmp_path)):
        # a fully-passing sympy proof -> verified
        vled.record("p(5n+4) ≡ 0 (mod 5)", "sympy", "verified", checks=10, source="prove")
        # a partial check -> weakened, not verified
        vled.record("some hard claim", "sympy", "weakened", checks=3, source="prove")
        ents = vled.entries()
        assert len(ents) == 2
        bykey = {e["statement"]: e for e in ents}
        assert bykey["p(5n+4) ≡ 0 (mod 5)"]["status"] == "verified"
        assert bykey["p(5n+4) ≡ 0 (mod 5)"]["verified"] is True
        assert bykey["some hard claim"]["status"] == "weakened"
        assert bykey["some hard claim"]["verified"] is False
        s = vled.summary()
        assert s["total"] == 2 and s["verified"] == 1 and s["weakened"] == 1
        # the human-readable ledger document exists and names the result
        md = (tmp_path / "self" / "verified.md").read_text(encoding="utf-8")
        assert "p(5n+4)" in md and "verified" in md


def test_dedup_replaces_same_result(tmp_path):
    with context.use(_stub(tmp_path)):
        vled.record("claim A", "sympy", "verified", checks=5)
        vled.record("claim A", "sympy", "weakened", checks=5)   # same (statement,method) -> replace
        ents = [e for e in vled.entries() if e["statement"] == "claim A"]
        assert len(ents) == 1 and ents[0]["status"] == "weakened"


def test_revisit_downgrades_on_refutation(tmp_path):
    with context.use(_stub(tmp_path)):
        e = vled.record("claim B", "sympy", "verified", checks=4)
        # the revisit loop re-tests and finds it no longer holds
        assert vled.update_status(e["key"], "refuted", "re-proved: 0/4 checks passed")
        got = [x for x in vled.entries() if x["key"] == e["key"]][0]
        assert got["status"] == "refuted" and got["revisits"] == 1 and got["verified"] is False
        assert vled.summary()["refuted"] == 1
