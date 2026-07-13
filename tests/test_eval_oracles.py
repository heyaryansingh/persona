"""FC-7 contract test — persona.eval.run_oracle (Lane 4 / S3, Milestone-0 stub)."""
import pytest

from persona.eval import run_oracle, KNOWN_ORACLES


@pytest.mark.parametrize("name", KNOWN_ORACLES)
def test_run_oracle_contract(name):
    r = run_oracle(name, n=0, seed=0)
    assert {"metric", "score", "n", "per_item"} <= set(r), r   # FC-7 minimum; extras (sourcing_status) allowed
    assert isinstance(r["metric"], str)
    assert isinstance(r["score"], float)
    assert isinstance(r["n"], int)
    assert isinstance(r["per_item"], list)


def test_run_oracle_unknown_raises():
    with pytest.raises(ValueError):
        run_oracle("definitely-not-an-oracle")
