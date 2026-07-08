"""T2.1: Batch reader request construction + prompt-cache/batch cost accounting.
Run: python tests/test_batch_and_cost.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from persona import config                                       # noqa: E402
from persona.ingest.base import Document                         # noqa: E402
from persona.swarm.batch_reader import BatchReader               # noqa: E402


def test_batch_requests_are_wellformed():
    docs = [Document(doc_id=f"MED:{i}", title=f"T{i}", text="microglia increase il-6", source="s")
            for i in range(3)]
    reqs, id_map = BatchReader().build_requests(docs)
    assert len(reqs) == 3
    assert [r["custom_id"] for r in reqs] == ["d0", "d1", "d2"]   # safe, <=64 chars
    assert id_map["d2"].doc_id == "MED:2"
    p = reqs[0]["params"]
    assert p["tool_choice"]["name"] == "record_claims"
    assert p["system"][0]["cache_control"]["type"] == "ephemeral"


def test_batch_is_half_price():
    full = config.est_cost_usd("claude-haiku-4-5", 1000, 200)
    batch = config.est_cost_usd("claude-haiku-4-5", 1000, 200, batch=True)
    assert abs(batch - full * 0.5) < 1e-9, (full, batch)


def test_cache_read_is_cheap():
    # 1000 cached-read tokens should cost ~0.1x of 1000 fresh input tokens
    fresh = config.est_cost_usd("claude-haiku-4-5", 1000, 0)
    cached = config.est_cost_usd("claude-haiku-4-5", 0, 0, cache_read=1000)
    assert abs(cached - fresh * 0.1) < 1e-9, (fresh, cached)


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for t in tests:
        t()
        print(f"PASS {t.__name__}")
    print(f"\n{len(tests)} batch/cost tests passed.")
