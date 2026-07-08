"""Always-on autonomous run (BUILD_PLAN §9.2 / Step 7): tick the researcher repeatedly,
reflecting between cycles (initiative + self-spawned interests), to fill the living
notebook — evidence it is always thinking, not a one-shot query.

Run: python scripts/run_overnight.py [cycles]   (default 6)
Uses the committed fixture cache so it runs offline; each cycle reads, updates beliefs,
reflects on its agenda, and may spawn a new interest.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

from persona.researcher import Researcher
from persona.ingest import EuropePMCAdapter
from persona.ingest.base import DiskCache
from persona.loops.artifact import mini_review

CACHED_QUERY = "neuroinflammation AND alzheimer AND microglia"


def main():
    cycles = int(sys.argv[1]) if len(sys.argv) > 1 else 6
    r = Researcher(root="runs/overnight", name="Ada",
                   adapter=EuropePMCAdapter(cache=DiskCache("tests/fixtures/ingest")))
    try:
        for c in range(cycles):
            r.tick([CACHED_QUERY])
            r.reflect()
        print(f"=== always-on run: {cycles} cycles ===")
        print(f"beliefs: {len(r.me.store.core_claims())} | "
              f"open handoffs: {len(r.inbox.open_items())}\n")
        print("--- living notebook (tail) ---")
        for ln in r.notebook(24):
            print(ln)
        print("\n--- mini-review (excerpt) ---")
        ids = [c.claim_id for c in r.me.store.core_claims()]
        print("\n".join(mini_review(r.me.store, ids, "Ada: state of the field").splitlines()[:12]))
    finally:
        r.close()


if __name__ == "__main__":
    main()
