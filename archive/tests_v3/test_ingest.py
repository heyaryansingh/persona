"""Ingestion tests — live-first, offline-reproducible via a committed fixture cache.
Run: python tests/test_ingest.py
"""
import sys
import urllib.error
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from persona.ingest import EuropePMCAdapter  # noqa: E402
from persona.ingest.base import DiskCache      # noqa: E402

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "ingest"
SEED_QUERY = "neuroinflammation AND alzheimer AND microglia"


def test_europepmc_search_live_or_fixture():
    cache = DiskCache(root=str(FIXTURES))
    pmc = EuropePMCAdapter(cache=cache)
    try:
        docs = pmc.search(SEED_QUERY, limit=8)
        mode = "LIVE (now cached)"
    except (urllib.error.URLError, TimeoutError) as e:
        cached = cache.get("europepmc", SEED_QUERY, "8")
        if cached is None:
            print(f"SKIP test_europepmc_search: no network and no fixture ({e})")
            return
        docs = pmc.search(SEED_QUERY, limit=8)
        mode = "OFFLINE fixture"
    assert len(docs) >= 1, "expected >=1 document"
    d = docs[0]
    assert d.title and d.source == "europepmc" and d.doc_id
    assert any(x.text for x in docs), "expected at least one abstract"
    # second call must be served from cache (no network)
    again = pmc.search(SEED_QUERY, limit=8)
    assert [x.doc_id for x in again] == [x.doc_id for x in docs]
    print(f"PASS test_europepmc_search [{mode}]: {len(docs)} docs; top = {d.title[:70]!r}")


if __name__ == "__main__":
    test_europepmc_search_live_or_fixture()
    print("\ningest tests passed.")
