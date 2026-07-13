"""F3.9 — GEO/dataset resolution (offline, deterministic). Verifies geo_lookup/geo_search parse a
local GEO SOFT cache and degrade to found:false (with a network seam) when nothing is cached. No
network is touched; the cache dir is redirected at import time via PERSONA_GEO_CACHE."""
import importlib
import os

import pytest


# A minimal but real GEO SOFT snippet: one series, two samples, one platform. This is the shape a
# live GEO fetch would drop into the cache, so parsing it here validates the offline half end-to-end.
_SOFT = """^SERIES = GSE12345
!Series_title = Cortical neurons under hypoxia
!Series_platform_id = GPL570
!Series_sample_id = GSM111
!Series_sample_id = GSM222
^PLATFORM = GPL570
!Platform_geo_accession = GPL570
"""


@pytest.fixture()
def science(tmp_path, monkeypatch):
    """Point science.GEO_CACHE_DIR at a tmp cache holding one series, then reload the module so the
    module-level GEO_CACHE_DIR picks up the env var."""
    cache = tmp_path / "geo"
    cache.mkdir()
    (cache / "GSE12345.soft").write_text(_SOFT, encoding="utf-8")
    monkeypatch.setenv("PERSONA_GEO_CACHE", str(cache))
    import persona.tools.science as sci
    importlib.reload(sci)
    yield sci
    monkeypatch.delenv("PERSONA_GEO_CACHE", raising=False)
    importlib.reload(sci)  # restore default cache dir for other tests


def test_lookup_hit_parses_soft(science):
    r = science.geo_lookup("GSE12345")
    assert r == {"gse_id": "GSE12345", "title": "Cortical neurons under hypoxia",
                 "platform": "GPL570", "n_samples": 2, "found": True,
                 "source": "cache:GSE12345.soft"}


def test_lookup_normalizes_id(science):
    # lowercase + whitespace must still resolve — deterministic normalization, not a guess.
    assert science.geo_lookup("  gse12345 ")["found"] is True


def test_lookup_miss_has_network_seam(science):
    r = science.geo_lookup("GSE99999")
    assert r["found"] is False and r["source"] == "not_cached" and r["n_samples"] == 0


def test_lookup_invalid_id(science):
    assert science.geo_lookup("not-an-accession")["source"] == "invalid_id"


def test_search_by_title_and_platform(science):
    assert [h["gse_id"] for h in science.geo_search("hypoxia")] == ["GSE12345"]
    assert science.geo_search("GPL570", field="platform")[0]["gse_id"] == "GSE12345"
    # field restriction excludes non-matching fields
    assert science.geo_search("hypoxia", field="platform") == []


def test_search_empty_query_and_no_match(science):
    assert science.geo_search("") == []
    assert science.geo_search("nonexistent-term") == []


def test_missing_cache_dir_is_offline_safe(monkeypatch, tmp_path):
    monkeypatch.setenv("PERSONA_GEO_CACHE", str(tmp_path / "absent"))
    import persona.tools.science as sci
    importlib.reload(sci)
    try:
        assert sci.geo_lookup("GSE12345")["found"] is False
        assert sci.geo_search("anything") == []
    finally:
        monkeypatch.delenv("PERSONA_GEO_CACHE", raising=False)
        importlib.reload(sci)


def test_dispatch_via_call(science):
    hit = science.call("geo_lookup", {"gse_id": "GSE12345"})
    assert hit["ok"] is True and hit["found"] is True and hit["n_samples"] == 2
    srch = science.call("geo_search", {"query": "hypoxia"})
    assert srch["ok"] is True and srch["hits"][0]["gse_id"] == "GSE12345"
