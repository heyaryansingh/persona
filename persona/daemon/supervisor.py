"""The always-on daemon (v4): a never-idle worker pool + a scheduler that keeps the queue fed.

This is what "always active, always spawning agents" actually means: N async workers drain the
queue continuously; a scheduler wakes every few seconds and, if the queue is running low, tops it
up with work generated from the self (interests, open questions, and — later — surprise). The
process never sits idle: when there's nothing to read, it reflects and generates more to read.
Crash-resume is inherited from the queue (expired leases reset on boot).
"""
from __future__ import annotations

import asyncio

from .. import config, selfmind
from ..events import log
from .queue import TaskQueue
from . import worker


class Daemon:
    def __init__(self, n_workers: int = None, queue: TaskQueue = None):
        self.n_workers = n_workers or config.N_WORKERS
        self.queue = queue or TaskQueue()
        self._stop = asyncio.Event()
        self.started_at = None
        self._tasks: list[asyncio.Task] = []

    async def _worker_loop(self, wid: int) -> None:
        while not self._stop.is_set():
            task = self.queue.lease()
            if task is None:
                await asyncio.sleep(0.5)          # queue empty; scheduler will feed it
                continue
            log().emit("lease", f"worker-{wid} picked up task#{task.id} ({task.type})",
                       actor=f"worker-{wid}", parent_id=task.parent_id, task_id=task.id)
            try:
                ref = await worker.dispatch(task, self.queue)
                self.queue.complete(task.id, ref)
            except Exception as e:                # never let one task kill a worker
                status = self.queue.fail(task.id)
                log().emit("error", f"task#{task.id} ({task.type}) failed: {str(e)[:200]} [{status}]",
                           actor=f"worker-{wid}", task_id=task.id)

    async def _scheduler_loop(self) -> None:
        # seed the very first pulse of work so the mind starts thinking immediately
        self.queue.enqueue("reflect", priority=0)
        while not self._stop.is_set():
            try:
                depth = self.queue.depth()
                if depth < config.QUEUE_MIN_DEPTH:
                    # never idle: if we're low on work, reflect (which generates readers)
                    self.queue.enqueue("reflect", priority=0)
                    log().emit("schedule",
                               f"queue low ({depth} < {config.QUEUE_MIN_DEPTH}); generating work",
                               actor="scheduler", depth=depth)
            except Exception as e:
                log().emit("error", f"scheduler: {str(e)[:200]}", actor="scheduler")
            await asyncio.sleep(config.SCHEDULER_INTERVAL_S)

    async def run(self) -> None:
        config.ensure_workspace()
        self.started_at = asyncio.get_event_loop().time()
        recovered = self.queue.reset_expired_leases()
        log().emit("boot",
                   f"daemon up — {self.n_workers} workers"
                   + (f", recovered {recovered} in-flight task(s)" if recovered else ""),
                   actor="daemon", seeded=selfmind.is_seeded())
        self._tasks = [asyncio.create_task(self._scheduler_loop())]
        self._tasks += [asyncio.create_task(self._worker_loop(i)) for i in range(self.n_workers)]
        await self._stop.wait()
        for t in self._tasks:
            t.cancel()
        await asyncio.gather(*self._tasks, return_exceptions=True)
        log().emit("shutdown", "daemon stopped", actor="daemon")

    def stop(self) -> None:
        self._stop.set()

    def status(self) -> dict:
        return {"workers": self.n_workers, "queue": self.queue.counts(),
                "depth": self.queue.depth(), "seeded": selfmind.is_seeded()}
