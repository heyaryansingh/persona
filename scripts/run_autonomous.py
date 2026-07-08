"""Always-on autonomous researcher (v2, P9): loops read → reflect → act → follow-curiosity
cycles with REAL Claude reading and self-testing. Run: python scripts/run_autonomous.py [cycles]
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
    cycles = int(sys.argv[1]) if len(sys.argv) > 1 else 2
    r = Researcher(root="runs/autonomous", name="Ada",
                   adapter=EuropePMCAdapter(cache=DiskCache("tests/fixtures/ingest")))
    try:
        for c in range(cycles):
            s = await r.autonomous_cycle(limit=6)
            st = s.get("self_test") or {}
            print(f"cycle {c+1}: read {s['read']} → committed {s['committed']}, held {s['held']}, "
                  f"{s['contradictions']} contradiction(s); acted_on={s['acted_on']} "
                  f"self-test={st.get('outcome','-')}; ${s['spent_usd']:.3f}")
        print("\n--- living notebook (tail) ---")
        for ln in r.notebook(16):
            print(ln)
        print(f"\nbeliefs: {len(r.me.store.core_claims())} | open handoffs: {len(r.inbox.open_items())}")
    finally:
        r.close()


if __name__ == "__main__":
    asyncio.run(main())
