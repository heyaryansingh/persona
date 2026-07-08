"""Live demo of the inner loop on real Europe PMC papers.

Reads the seed program (Alzheimer's neuroinflammation), extracts candidates, runs them
through the membrane, and prints the resulting living notebook + core beliefs — the
"watch it think" slice. Uses the committed fixture cache so it runs offline too.

Run: python scripts/run_inner_loop.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # Windows console + notebook glyphs
except Exception:
    pass

from persona.self_state import Self
from persona.membrane import Membrane
from persona.swarm.reader import HeuristicExtractor
from persona.ingest import EuropePMCAdapter
from persona.ingest.base import DiskCache
from persona.loops import run_inner_loop

SEED_QUERIES = [
    "neuroinflammation AND alzheimer AND microglia",
]

def main():
    root = Path("runs/demo_self")
    me = Self(root).hydrate()
    try:
        # reuse the committed fixture cache -> reproducible offline; live if cache miss
        adapter = EuropePMCAdapter(cache=DiskCache("tests/fixtures/ingest"))
        mem = Membrane(me.store)
        summary = run_inner_loop(me, adapter, HeuristicExtractor(), mem, SEED_QUERIES, limit=8)

        print("=== inner-loop summary ===")
        print(f"docs read      : {summary.docs_read}")
        print(f"candidates     : {summary.candidates}")
        print(f"committed      : {summary.committed}")
        print(f"held           : {summary.held}")
        print(f"contradictions : {summary.contradictions}")
        print(f"strict claims  : {summary.strict}")

        print("\n=== living notebook (runs/demo_self/notebook.md) ===")
        print(me.notebook_path.read_text(encoding="utf-8").strip())

        print("\n=== core beliefs ===")
        for c in me.store.core_claims():
            n = me.store.independent_source_count(c.claim_id)
            print(f"  p={c.calibrated_p:.2f} [{c.provenance_state}] "
                  f"src={n} :: {c.statement[:80]}")
    finally:
        me.close()

if __name__ == "__main__":
    main()
