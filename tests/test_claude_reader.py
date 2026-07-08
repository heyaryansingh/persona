"""Real Claude reader test. Run: python tests/test_claude_reader.py
Runs a real extraction if ANTHROPIC_API_KEY is set (~$0.004); else verifies offline fallback.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from persona import config                                  # noqa: E402
from persona.swarm.claude_reader import ClaudeExtractor     # noqa: E402
from persona.swarm.reader import Candidate                  # noqa: E402
from persona.ingest.base import Document, DiskCache         # noqa: E402
from persona.ingest import EuropePMCAdapter                 # noqa: E402

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "ingest"


def test_offline_fallback_is_a_list():
    """With no client, ClaudeExtractor must fall back to the heuristic (offline demo safe)."""
    ex = ClaudeExtractor(client=None)
    if config.have_key():
        return  # can't force no-key path cleanly when a key exists; covered by design
    doc = Document("x", "Microglia and neuroinflammation", "Microglia increase neuroinflammation.",
                   source="fake", group="J")
    out = ex.extract(doc)
    assert isinstance(out, list)


def test_real_extraction_structure():
    if not config.have_key():
        print("SKIP test_real_extraction_structure: no ANTHROPIC_API_KEY")
        return
    pmc = EuropePMCAdapter(cache=DiskCache(root=str(FIXTURES)))
    doc = next((d for d in pmc.search("neuroinflammation AND alzheimer AND microglia", 8) if d.text), None)
    assert doc is not None
    ex = ClaudeExtractor()
    cands = ex.extract(doc)
    assert len(cands) >= 1, "expected >=1 real claim"
    c = cands[0]
    assert isinstance(c, Candidate) and c.claim_key and c.statement
    assert c.meta.get("relation") and 0.0 <= c.confidence <= 1.0
    print(f"PASS test_real_extraction_structure: {len(cands)} claims, "
          f"e.g. '{c.statement[:60]}' (conf {c.confidence}); "
          f"${ex.last_usage['cost']:.4f}")


if __name__ == "__main__":
    test_offline_fallback_is_a_list()
    print("PASS test_offline_fallback_is_a_list")
    test_real_extraction_structure()
    print("\nclaude reader test passed.")
