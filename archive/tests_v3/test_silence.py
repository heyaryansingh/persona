"""Silence/dark-literature detector tests (assert-based, stdlib only).
Run: python tests/test_silence.py
"""
import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from persona.engine.silence import (  # noqa: E402
    entity_year_counts,
    abandonment_score,
    detect_abandoned,
)

ABANDONED = {2015: 8, 2016: 10, 2017: 9, 2018: 2, 2019: 1, 2020: 0}
RISING = {2018: 5, 2019: 7, 2020: 9}


def test_abandonment_score_high_for_dropped_target():
    assert abandonment_score(ABANDONED) > 0.6


def test_abandonment_score_low_for_rising_target():
    assert abandonment_score(RISING) < 0.3


def test_abandonment_score_needs_min_peak_and_active_years():
    assert abandonment_score({2020: 1}) == 0.0          # < 2 active years
    assert abandonment_score({2018: 1, 2019: 0, 2020: 0}) == 0.0  # peak < 2


def test_entity_year_counts_builds_from_docs():
    docs = [
        SimpleNamespace(year=2015, title="GeneX in disease", text=""),
        SimpleNamespace(year=2015, title="unrelated", text="mentions GeneX again"),
        SimpleNamespace(year=2020, title="", text="GeneY rising study"),
        SimpleNamespace(year=None, title="GeneX no year", text=""),  # skipped
    ]
    counts = entity_year_counts(docs, ["GeneX", "GeneY"])
    assert counts["GeneX"] == {2015: 2}
    assert counts["GeneY"] == {2020: 1}


def test_detect_abandoned_picks_abandoned_not_rising():
    series = {"GeneX": ABANDONED, "GeneY": RISING}
    result = detect_abandoned(series)
    entities = [r["entity"] for r in result]
    assert entities == ["GeneX"]
    assert result[0]["peak_year"] == 2016
    assert result[0]["peak"] == 10


def test_detect_abandoned_respects_min_peak():
    series = {"tiny": {2015: 1, 2016: 1, 2019: 0}}
    assert detect_abandoned(series, min_peak=3) == []


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for t in tests:
        t()
        print(f"PASS {t.__name__}")
    print(f"\n{len(tests)} silence tests passed.")
