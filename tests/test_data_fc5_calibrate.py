"""FC-5 · admit_decision routing — commit / human / reject. Pure, $0, no model."""
from persona.memory.calibrate import admit_decision

_SHAPE = {"admit", "calibrated_p", "route", "reason", "bound"}


def test_commit_strong_independent_support():
    r = admit_decision({"provenance_state": "READ", "independent_source_count": 3,
                        "support_count": 5, "calibrated_p": 0.85})
    assert set(r) == _SHAPE
    assert r["route"] == "commit" and r["admit"] is True
    assert r["calibrated_p"] == 0.85 and isinstance(r["bound"], float)


def test_human_on_anchor():
    r = admit_decision({"provenance_state": "READ", "anchored": True,
                        "independent_source_count": 9, "calibrated_p": 0.99})
    assert r["route"] == "human" and r["admit"] is False


def test_human_on_high_stakes_provenance():
    r = admit_decision({"provenance_state": "HUMAN_CONFIRMED",
                        "independent_source_count": 3, "calibrated_p": 0.9})
    assert r["route"] == "human" and r["admit"] is False


def test_reject_weak():
    r = admit_decision({"provenance_state": "READ", "independent_source_count": 1,
                        "support_count": 1, "calibrated_p": 0.2})
    assert r["route"] == "reject" and r["admit"] is False


def test_reject_zero_independent_support():
    r = admit_decision({"provenance_state": "READ", "independent_source_count": 0,
                        "support_count": 0})
    assert r["route"] == "reject" and r["admit"] is False


def test_borderline_routes_to_human():
    # supported (p in [reject, commit)) but not commit-strong -> human, not auto-anything
    r = admit_decision({"provenance_state": "READ", "independent_source_count": 1,
                        "support_count": 1, "calibrated_p": 0.55})
    assert r["route"] == "human" and r["admit"] is False


def test_logit_and_support_proxy_are_deterministic():
    from_logit = admit_decision({"provenance_state": "READ",
                                 "independent_source_count": 3, "logit": 2.0})
    assert 0.0 <= from_logit["calibrated_p"] <= 1.0
    # no p/logit -> monotone support proxy still yields a float and stable route
    proxy = admit_decision({"provenance_state": "READ", "independent_source_count": 3,
                            "support_count": 4})
    assert isinstance(proxy["calibrated_p"], float)
    assert proxy == admit_decision({"provenance_state": "READ",
                                    "independent_source_count": 3, "support_count": 4})
