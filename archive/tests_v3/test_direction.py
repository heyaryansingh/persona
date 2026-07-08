"""T0.1: effect-direction is real — opposing findings contradict, not merge.
Run: python tests/test_direction.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from persona.store import BeliefStore                     # noqa: E402
from persona.membrane import Membrane                     # noqa: E402
from persona.swarm.reader import effect_sign, build_candidate, claim_key  # noqa: E402
from persona.ingest.base import Document                  # noqa: E402
from persona.swarm.reader import HeuristicExtractor       # noqa: E402


def test_effect_sign_directions():
    assert effect_sign("increases") == +1.0 and effect_sign("causes") == +1.0
    assert effect_sign("decreases") == -1.0 and effect_sign("inhibits") == -1.0
    assert effect_sign("no_effect") == -1.0


def test_same_pair_opposite_sign_same_key():
    up = build_candidate("microglia", "neuroinflammation", "increases", "J", "d1")
    down = build_candidate("microglia", "neuroinflammation", "decreases", "J", "d2")
    assert up.claim_key == down.claim_key            # same node
    assert up.direction == +1.0 and down.direction == -1.0   # opposite signs


def test_opposing_findings_fire_contradiction():
    s = BeliefStore()
    m = Membrane(s)
    for g in ("A", "B"):
        m.submit(build_candidate("microglia", "neuroinflammation", "increases", f"J{g}", f"J{g}:d"))
    for g in ("C", "D"):
        m.submit(build_candidate("microglia", "neuroinflammation", "decreases", f"J{g}", f"J{g}:d"))
    rep = m.harvest()
    assert rep.contradictions, "opposing directions must contradict, not merge as agreement"
    s.close()


def test_heuristic_and_shared_builder_agree_on_sign():
    """The offline heuristic and the shared builder must map 'decreases' to the SAME sign
    (fixes the v2 heuristic(-1)-vs-Claude(+1) split)."""
    doc = Document("d", "t", "Microglia decreases neuroinflammation in this model.",
                   source="t", group="J")
    cands = HeuristicExtractor().extract(doc)
    assert cands and cands[0].direction == -1.0    # 'decreases' -> down, same as build_candidate


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for t in tests:
        t()
        print(f"PASS {t.__name__}")
    print(f"\n{len(tests)} direction tests passed.")
