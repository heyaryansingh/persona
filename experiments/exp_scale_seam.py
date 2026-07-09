"""exp_scale_seam (v4 P8) — the horizontal scale-out invariant: many worker PROCESSES can share
one durable queue with no double-work.

The queue's lease is a single transactional UPDATE ... RETURNING, so N independent processes
draining the same SQLite file each get disjoint tasks. This is the whole cloud-seam claim: to
scale out on one machine, add worker processes (`python -m persona --worker`); to span machines,
swap SQLite for Postgres behind the same TaskQueue interface — nothing else changes.

Test: preload 300 tasks, spawn 4 processes that lease+complete until empty, assert every task was
leased EXACTLY once (disjoint) and all 300 completed. Run: python experiments/exp_scale_seam.py
"""
import os
import subprocess
import sys
import tempfile
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

_WORKER = r"""
import os, sys, json
sys.path.insert(0, r"{root}")
from persona.daemon.queue import TaskQueue
q = TaskQueue()
leased = []
while True:
    t = q.lease()
    if t is None:
        break
    leased.append(t.id)
    q.complete(t.id, "ok")
open(os.environ["OUT"], "w").write(json.dumps(leased))
"""


def main():
    root = str(Path(__file__).resolve().parent.parent)
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as d:   # win: sqlite handle lingers
        env_ws = str(Path(d) / "ws")
        os.environ["PERSONA_WORKSPACE"] = env_ws
        # reimport config/queue against this workspace
        import importlib
        import persona.config as cfg
        importlib.reload(cfg)
        from persona.daemon import queue as qmod
        importlib.reload(qmod)
        q = qmod.TaskQueue()
        N = 300
        for i in range(N):
            q.enqueue("noop", f"task-{i}")
        print(f"enqueued {N} tasks; launching 4 worker processes …")

        wscript = Path(d) / "w.py"
        wscript.write_text(_WORKER.format(root=root), encoding="utf-8")
        procs = []
        for k in range(4):
            e = dict(os.environ)
            e["OUT"] = str(Path(d) / f"out{k}.json")
            e["PERSONA_WORKSPACE"] = env_ws
            procs.append(subprocess.Popen([sys.executable, str(wscript)], env=e))
        for p in procs:
            p.wait()

        import json
        all_leased = []
        per = []
        for k in range(4):
            got = json.loads((Path(d) / f"out{k}.json").read_text(encoding="utf-8"))
            per.append(len(got))
            all_leased += got
        counts = Counter(all_leased)
        dupes = [tid for tid, c in counts.items() if c > 1]
        print(f"per-process leased: {per} (total {len(all_leased)})")
        print(f"distinct tasks leased: {len(counts)} / {N}")
        print(f"double-leased tasks: {len(dupes)}")
        ok = len(all_leased) == N and len(counts) == N and not dupes
        print(f"\nVERDICT: {'PASS' if ok else 'FAIL'} — {N} tasks drained by 4 processes, "
              f"each leased exactly once (no double-work)")
        assert ok


if __name__ == "__main__":
    main()
