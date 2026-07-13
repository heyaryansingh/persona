"""F1.7 — director/discover value-aware prioritization.

`discover` already elicits a `value` per idea from the model but used to discard it, enqueuing every
investigation at a flat priority. Now a higher-value idea gets a lower (sooner) queue priority so the
swarm works its highest-value leads first; an idea with no value keeps the base priority (unchanged).
Pure $0 — the priority mapping only.
"""
from persona.agents.discover import _value_priority


def test_high_value_gets_sooner_priority():
    assert _value_priority(10) < _value_priority(1)      # higher value → sooner (lower number)
    assert _value_priority(10) <= 1


def test_missing_value_keeps_base_priority():
    assert _value_priority(None) == 4                    # default behaviour unchanged
    assert _value_priority("not-a-number") == 4


def test_priority_is_monotonic_and_in_band():
    priorities = [_value_priority(v) for v in range(0, 11)]
    assert all(0 <= p <= 6 for p in priorities)          # stays in the queue's [0,6] band
    assert priorities[10] <= priorities[5] <= priorities[0]   # non-increasing in value
