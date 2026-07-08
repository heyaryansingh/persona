"""Populate a real demo state: read N live abstracts on a narrow topic so claims converge,
into runs/api_self (what the API serves). Run: python scripts/populate_demo.py [N]
"""
import asyncio
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


async def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 40
    r = Researcher(root="runs/api_self", name="Ada",
                   adapter=EuropePMCAdapter(cache=DiskCache(".cache/populate")))
    try:
        s = await r.aread(queries=["microglia AND neuroinflammation AND alzheimer"], limit=n)
        print(f"read {s['read']} → committed {s['committed']}, held {s['held']}, "
              f"{s['contradictions']} contradiction(s); ${s['spent_usd']:.3f}")
        g = r.idea_graph()
        print(f"idea graph: {len(g['nodes'])} nodes, {len(g['edges'])} edges")
        print("top beliefs (by independent sources):")
        claims = sorted(r.me.store.core_claims(),
                        key=lambda c: -r.me.store.independent_source_count(c.claim_id))
        for c in claims[:12]:
            n_src = r.me.store.independent_source_count(c.claim_id)
            print(f"  {n_src} src  p={c.calibrated_p:.2f}  :: {c.statement[:64]}")
    finally:
        r.close()


if __name__ == "__main__":
    asyncio.run(main())
