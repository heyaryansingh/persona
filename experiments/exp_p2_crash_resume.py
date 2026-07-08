"""
P2 crash-resume bake-off (gates the async swarm orchestrator). Now IMPLEMENTED.

PRE-REGISTERED HYPOTHESIS
  The asyncio orchestrator + durable observation log + read-ledger gives idempotent
  crash-resume: a run killed mid-way and resumed produces BYTE-IDENTICAL beliefs to an
  uninterrupted run, with zero double-commits and zero lost docs — with no new deps.
  (Decides asyncio vs LangGraph: LangGraph is only warranted if it buys resume correctness
  the idempotent keys don't already give. Prediction: asyncio wins; this measures it.)

METRIC (>=20 seeds)
  resume_identical    : killed+resumed beliefs == uninterrupted beliefs (want 1.0)
  no_double_commit    : re-running the whole set is a no-op (want 1.0)
  parallel_speedup    : wall-clock, concurrency=20 vs sequential, over 200 simulated reads

GO: resume_identical == 1.0 AND no_double_commit == 1.0 -> ship the asyncio swarm; no
durable-execution engine warranted. Uses a FILE-backed store reopened between runs to
simulate a real process crash (in-memory state lost, disk persists). Deterministic
extractor (LLM output isn't reproducible, so idempotency is tested offline).
"""
import sys
import asyncio
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np

from persona.store import BeliefStore
from persona.membrane import Membrane
from persona.swarm.orchestrator import AsyncSwarm
from persona.swarm.reader import Candidate, claim_key
from persona.ingest.base import Document


def build_docs(seed: int):
    """36 docs: 12 relations, each asserted by 3 distinct journals -> all converge."""
    rng = np.random.default_rng(seed)
    docs, cand_map = [], {}
    for i in range(12):
        subj, obj = f"S{i}", f"O{i}"
        k = claim_key(subj, obj)
        for g in range(3):
            doc_id = f"doc_{i}_{g}"
            d = Document(doc_id, f"paper {doc_id}", f"{subj} increases {obj}",
                         source="sim", group=f"J{g}")
            docs.append(d)
            cand_map[doc_id] = [Candidate(k, f"{subj} increases {obj}", +1.0, f"J{g}",
                                          doc_id, confidence=0.7)]
    order = rng.permutation(len(docs))
    return [docs[i] for i in order], cand_map


def make_extract_fn(cand_map, latency=0.0):
    async def ex(doc):
        if latency:
            await asyncio.sleep(latency)
        return cand_map.get(doc.doc_id, [])
    return ex


def belief_sig(store) -> str:
    rows = sorted((c.claim_id, round(c.logit, 6)) for c in store.core_claims())
    return repr(rows)


def run_full(docs, cand_map, path):
    store = BeliefStore(path)
    mem = Membrane(store)
    sw = AsyncSwarm(mem, concurrency=16, extract_fn=make_extract_fn(cand_map))
    asyncio.run(sw.read_many(docs))
    sig = belief_sig(store)
    store.close()
    return sig


def run_interrupted_then_resume(docs, cand_map, path, k):
    # run 1: read the first k docs, then "crash" (close the store)
    store = BeliefStore(path)
    mem = Membrane(store)
    sw = AsyncSwarm(mem, concurrency=16, extract_fn=make_extract_fn(cand_map))
    asyncio.run(sw.read_many(docs[:k]))
    store.close()                                   # <-- crash: in-memory state lost
    # run 2: reopen from disk, resume over ALL docs (ledger skips the done ones)
    store = BeliefStore(path)
    mem = Membrane(store)
    sw = AsyncSwarm(mem, concurrency=16, extract_fn=make_extract_fn(cand_map))
    asyncio.run(sw.read_many(docs))
    sig = belief_sig(store)
    # double-run idempotency: reading everything again must not change beliefs
    asyncio.run(sw.read_many(docs))
    sig2 = belief_sig(store)
    store.close()
    return sig, sig2


def one_seed(seed: int) -> dict:
    docs, cand_map = build_docs(seed)
    rng = np.random.default_rng(seed + 99)
    k = int(rng.integers(len(docs) // 4, 3 * len(docs) // 4))   # crash somewhere in the middle
    with tempfile.TemporaryDirectory() as d:
        full = run_full(docs, cand_map, str(Path(d) / "a.db"))
        resumed, doubled = run_interrupted_then_resume(docs, cand_map, str(Path(d) / "b.db"), k)
    return {"resume_identical": 1.0 if resumed == full else 0.0,
            "no_double_commit": 1.0 if doubled == resumed else 0.0}


def measure_speedup(n=200, latency=0.05):   # ~real Claude latency is ~1-2s; 0.05 keeps it quick
    docs = [Document(f"s{i}", "t", "S increases O", source="sim", group="J0") for i in range(n)]
    cand_map = {d.doc_id: [] for d in docs}          # empty -> just measures fan-out timing
    with tempfile.TemporaryDirectory() as d:
        store = BeliefStore(str(Path(d) / "s.db")); mem = Membrane(store)
        sw = AsyncSwarm(mem, concurrency=20, extract_fn=make_extract_fn(cand_map, latency))
        t0 = time.perf_counter(); asyncio.run(sw.read_many(docs)); par = time.perf_counter() - t0
        store.close()
    seq = n * latency
    return seq / par if par > 0 else 0.0, par


if __name__ == "__main__":
    rows = [one_seed(5000 + i) for i in range(20)]
    ri = np.mean([r["resume_identical"] for r in rows])
    nd = np.mean([r["no_double_commit"] for r in rows])
    speedup, par = measure_speedup()
    print("=== P2 crash-resume bake-off | 20 seeds (file-backed store, real reopen) ===")
    print(f"  resume_identical   {ri:.3f}   (killed+resumed == uninterrupted, byte-identical)")
    print(f"  no_double_commit   {nd:.3f}   (re-running the whole set is a no-op)")
    print(f"  parallel_speedup   {speedup:.1f}x  (200 reads @20 concurrency in {par:.2f}s)")
    print(f"  new_dependencies   0   (asyncio + SQLite; no durable-execution engine)")
    ok = ri >= 0.999 and nd >= 0.999
    print("\nGO — asyncio swarm gives idempotent crash-resume; no LangGraph/Temporal needed"
          if ok else "\nNO-GO — resume not idempotent; revisit")
    import json
    Path("results").mkdir(exist_ok=True)
    json.dump({"resume_identical": ri, "no_double_commit": nd, "speedup": speedup},
              open("results/p2_crash_resume.json", "w"), indent=2)
