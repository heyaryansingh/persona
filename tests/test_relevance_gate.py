"""The objective-relevance gate must drop off-topic scouted papers and keep on-topic ones.

Real behavioral test against the shipped bge-small embedder + shipped tau (0.70), validated in
experiments/exp_rq_e14_relevance_gate.py (0.939 balanced accuracy on 646 real Erdos titles).
"""
from persona.reading import reader
from persona import config


class _W:
    def __init__(self, title):
        self.title = title


def test_relevance_gate_keeps_on_topic_drops_off_topic(monkeypatch):
    # a focused number-theory objective
    monkeypatch.setattr(reader, "_objective_anchor", lambda: [
        "Erdos-Straus conjecture on 4/n unit fractions",
        "Egyptian fractions and unit-fraction representations",
        "Diophantine equations and analytic number theory",
    ])
    reader._ANCHOR_CACHE["key"] = None  # bust the anchor cache so the monkeypatched anchor is used

    works = [
        _W("On the Erdős–Straus conjecture and three-term unit fractions"),   # on-topic
        _W("Aberrant gene activation in synovial sarcoma relies on SSX specificity"),  # off-topic
        _W("Egyptian fraction expansions of 4/n for primes ≡ 1 (mod 4)"),     # on-topic
        _W("Higuchi fractal dimension in EEG aging studies"),                 # off-topic
    ]
    kept, dropped = reader._relevance_filter(works, config.RELEVANCE_TAU)
    kept_titles = [w.title for w in kept]

    assert any("Straus" in t for t in kept_titles), "on-topic Erdős–Straus paper must be kept"
    assert not any("sarcoma" in t for t in kept_titles), "biomedical paper must be dropped"
    assert not any("EEG" in t for t in kept_titles), "EEG paper must be dropped"
    assert dropped >= 2


def test_relevance_gate_fails_open_with_no_anchor(monkeypatch):
    # a blank-slate persona (no interests yet) must never have its reading blocked
    monkeypatch.setattr(reader, "_objective_anchor", lambda: [])
    works = [_W("anything at all"), _W("something else")]
    kept, dropped = reader._relevance_filter(works, config.RELEVANCE_TAU)
    assert len(kept) == 2 and dropped == 0
