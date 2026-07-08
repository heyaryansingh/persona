"""T4: bi-temporal time-travel over the belief-graph. Run: python tests/test_bitemporal.py

Uses controlled history timestamps (real updates are seconds+ apart; the Windows wall-clock has
~ms resolution, so a unit test injects explicit ts to test the time-travel queries deterministically).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from persona.store import BeliefStore, Claim                            # noqa: E402
from persona.graph.bitemporal import (graph_as_of, change_points,       # noqa: E402
                                       claims_valid_at, logit_at)

T0, T1, T2 = ("2020-01-01T00:00:00+00:00", "2021-01-01T00:00:00+00:00",
              "2022-01-01T00:00:00+00:00")


def _hist(s, cid, ts, after):
    s._db.execute(
        "INSERT INTO history (claim_id, ts, cause, logit_before, logit_after, "
        "provenance_before, provenance_after) VALUES (?,?,?,?,?,?,?)",
        (cid, ts, "test", 0.0, after, "READ", "READ"))


def _store():
    s = BeliefStore()
    s.add_claim(Claim("k", "microglia increase neuroinflammation"))
    s._db.execute("UPDATE claims SET valid_from=? WHERE claim_id=?", ("2019-01-01T00:00:00+00:00", "k"))
    _hist(s, "k", T0, 2.0)      # rose in 2020
    _hist(s, "k", T1, -1.0)     # fell in 2021 (contrary evidence)
    s._db.commit()
    return s


def test_graph_reconstructs_past_logit():
    s = _store()
    cps = change_points(s)
    assert cps == [T0, T1], cps
    le = next(n["logit"] for n in graph_as_of(s, "2020-06-01T00:00:00+00:00")["nodes"] if n["id"] == "k")
    ll = next(n["logit"] for n in graph_as_of(s, "2021-06-01T00:00:00+00:00")["nodes"] if n["id"] == "k")
    assert le == 2.0 and ll == -1.0, (le, ll)
    s.close()


def test_validity_window():
    s = _store()
    s._db.execute("UPDATE claims SET valid_to=? WHERE claim_id=?", (T2, "k"))
    s._db.commit()
    assert "k" in claims_valid_at(s, T1)                 # inside [2019, 2022)
    assert "k" not in claims_valid_at(s, "2023-01-01T00:00:00+00:00")   # after valid_to
    assert "k" not in claims_valid_at(s, "2018-01-01T00:00:00+00:00")   # before valid_from
    s.close()


def test_logit_before_creation_is_zero():
    s = _store()
    assert logit_at(s, "k", "1900-01-01T00:00:00+00:00") == 0.0
    s.close()


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for t in tests:
        t()
        print(f"PASS {t.__name__}")
    print(f"\n{len(tests)} bi-temporal tests passed.")
