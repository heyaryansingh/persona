"""F3.5: dead_science (dark-literature meter). Dict-backed fake KG duck-types the one KG surface
dead_science reads (`_q(...).result_set`), so it runs with NO FalkorDB and is a faithful oracle.
`now` is injected so dormancy is deterministic.
"""
from datetime import datetime, timezone

from persona.analysis.darklit import dead_science, MIN_SUPPORT, DORMANT_DAYS

NOW = datetime(2026, 1, 1, tzinfo=timezone.utc)


class _Res:
    def __init__(self, rows):
        self.result_set = rows


class FakeKG:
    """rows: [claim_id, ingest_time, provenance, anchored, support_count]. Applies the same
    support/topic/valid_to filter the real Cypher does, so the test exercises real filtering."""
    def __init__(self, rows):
        self._rows = rows

    def _q(self, cypher, params):
        k = params["k"]
        t = params.get("t")
        out = []
        for cid, ingest, prov, anchored, support, subj, obj in self._rows:
            if support < k:
                continue
            if t and t not in subj.lower() and t not in obj.lower():
                continue
            out.append([cid, ingest, prov, anchored, support])
        return _Res(out)


def _iso(days_before):
    return (NOW.replace(hour=0) - __import__("datetime").timedelta(days=days_before)).isoformat()


def _row(cid, days_ago, support=5, prov="READ", anchored=False, subj="drugX", obj="outcomeY"):
    return [cid, _iso(days_ago), prov, anchored, support, subj, obj]


def test_no_kg_returns_empty():
    assert dead_science("anything", kg=None) == []
    assert dead_science("anything", kg=False) == []


def test_dormant_high_support_surfaced_active_and_thin_excluded():
    rows = [
        _row("clm_dark", days_ago=DORMANT_DAYS + 100, support=8),        # dark: old + supported
        _row("clm_fresh", days_ago=10, support=8),                       # active -> excluded
        _row("clm_thin", days_ago=DORMANT_DAYS + 100, support=MIN_SUPPORT - 1),  # low support
        _row("clm_offtopic", days_ago=DORMANT_DAYS + 100, support=8,
             subj="aspirin", obj="headache"),                            # off-topic -> filtered
        _row("clm_notime", days_ago=0, support=8),                       # will null the timestamp
    ]
    rows[-1][1] = None  # missing ingest_time -> skipped, never raises
    res = dead_science("drugx", kg=FakeKG(rows), now=NOW)
    assert [d["claim_id"] for d in res] == ["clm_dark"]
    assert res[0]["dormant_days"] == DORMANT_DAYS + 100
    assert res[0]["revived"] is False


def test_revived_flag_and_dormant_ordering():
    rows = [
        _row("clm_a", days_ago=DORMANT_DAYS + 5, support=5),
        _row("clm_b", days_ago=DORMANT_DAYS + 900, support=5, prov="TESTED"),   # revived by test
        _row("clm_c", days_ago=DORMANT_DAYS + 900, support=5, anchored=True),   # revived by anchor
        _row("clm_h", days_ago=DORMANT_DAYS + 900, support=5, prov="HUMAN_CONFIRMED"),
    ]
    res = dead_science(None, kg=FakeKG(rows), now=NOW)  # topic=None -> whole KG
    # most-dormant first; the three 900-day claims tie and break by claim_id, then clm_a last.
    assert [d["claim_id"] for d in res] == ["clm_b", "clm_c", "clm_h", "clm_a"]
    revived = {d["claim_id"]: d["revived"] for d in res}
    assert revived == {"clm_b": True, "clm_c": True, "clm_h": True, "clm_a": False}


if __name__ == "__main__":
    test_no_kg_returns_empty()
    test_dormant_high_support_surfaced_active_and_thin_excluded()
    test_revived_flag_and_dormant_ordering()
    print("ok")
