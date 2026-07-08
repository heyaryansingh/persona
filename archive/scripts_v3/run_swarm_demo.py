"""Live demo of the REAL parallel Claude swarm (v2, P2): reads real abstracts in parallel,
streams swarm events, commits real structured beliefs. Run: python scripts/run_swarm_demo.py [N]
"""
import asyncio
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

from persona.researcher import Researcher
from persona.ingest import EuropePMCAdapter
from persona.ingest.base import DiskCache


def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 4
    r = Researcher(root="runs/swarm_demo", name="Ada",
                   adapter=EuropePMCAdapter(cache=DiskCache("tests/fixtures/ingest")))
    events = []
    try:
        summary = asyncio.run(r.aread(
            queries=["neuroinflammation AND alzheimer AND microglia"], limit=n,
            on_event=events.append))
        print(f"=== real swarm: {n} docs in parallel ===")
        print("event types:", dict(Counter(e["type"] for e in events)))
        for e in events:
            if e["type"] == "read" and e.get("ok"):
                print(f"  read [{e['group']}] {e.get('title','')[:50]} → {e['n_claims']} claims")
        print(f"\nsummary: read={summary['read']} committed={summary['committed']} "
              f"held={summary['held']} contradictions={summary['contradictions']} "
              f"${summary['spent_usd']:.3f} errors={summary['errors']}")
        print("\ncore beliefs (real structured claims):")
        for c in r.me.store.core_claims()[:8]:
            print(f"  p={c.calibrated_p:.2f} src={r.me.store.independent_source_count(c.claim_id)} "
                  f":: {c.statement[:70]}")
    finally:
        r.close()


if __name__ == "__main__":
    main()
