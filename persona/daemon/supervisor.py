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


def _should_reflect(depth: int, now: float, last_reflect: float) -> bool:
    return depth < config.QUEUE_MIN_DEPTH and now - last_reflect >= config.SCOUT_INTERVAL_S


class Daemon:
    def __init__(self, n_workers: int = None, queue: TaskQueue = None, scheduler: bool = True,
                 persona=None):
        from ..context import get_persona
        self.persona = persona or get_persona()          # every daemon runs FOR one persona (v5)
        self.n_workers = n_workers or config.N_WORKERS
        self.queue = queue or self.persona.queue()
        self.scheduler = scheduler          # False -> worker-only process (horizontal scale-out)
        self._stop = asyncio.Event()
        self.started_at = None
        self._tasks: list[asyncio.Task] = []

    async def _worker_loop(self, wid: int) -> None:
        while not self._stop.is_set():
            if self.persona.is_paused():         # PAUSE: lease nothing new; in-flight tasks drain
                await asyncio.sleep(0.4)
                continue
            task = self.queue.lease()
            if task is None:
                await asyncio.sleep(0.5)          # queue empty; scheduler will feed it
                continue
            log().emit("lease", f"worker-{wid} picked up task#{task.id} ({task.type})",
                       actor=f"worker-{wid}", parent_id=task.parent_id, task_id=task.id)
            before = self.persona.budget.spent_today()
            try:
                ref = await worker.dispatch(task, self.queue)
                self.queue.complete(task.id, ref)
                cost = self.persona.budget.spent_today() - before
                if cost > 1e-6:                  # per-task cost attribution (the value/$ denominator)
                    log().emit("cost", f"task#{task.id} ({task.type}) cost ${cost:.4f}",
                               actor=f"worker-{wid}", task_id=task.id, cost=round(cost, 5),
                               task_type=task.type)
            except Exception as e:                # never let one task kill a worker
                status = self.queue.fail(task.id)
                log().emit("error", f"task#{task.id} ({task.type}) failed: {str(e)[:200]} [{status}]",
                           actor=f"worker-{wid}", task_id=task.id)

    async def _scheduler_loop(self) -> None:
        from .. import selfmind
        self_every = max(1, int(config.SELF_INTERVAL_S / config.SCHEDULER_INTERVAL_S))
        tick = 0
        # A new mind pulses immediately. A restarted mind waits for the cooldown instead of
        # multiplying work across every persona whenever the API process is inspected/restarted.
        last_reflect = (asyncio.get_running_loop().time() if self.queue.counts()
                        else float("-inf"))
        announced_wait = False
        while not self._stop.is_set():
            try:
                # SEEDED-GATE: do NO work until the user has given this persona its interests.
                # (Fixes "it runs before I set it / with vanilla interests".)
                if not selfmind.is_seeded():
                    if not announced_wait:
                        log().emit("thought", "blank slate — waiting for a human to seed my "
                                   "interests before I start.", actor="self")
                        announced_wait = True
                    await asyncio.sleep(config.SCHEDULER_INTERVAL_S)
                    continue
                if self.persona.is_paused():             # PAUSE: generate no new work, no spend
                    await asyncio.sleep(config.SCHEDULER_INTERVAL_S)
                    continue
                now = asyncio.get_running_loop().time()
                tick += 1
                depth = self.queue.depth()
                if _should_reflect(depth, now, last_reflect):
                    self.queue.enqueue("reflect", priority=0)
                    last_reflect = now
                    log().emit("schedule",
                               f"queue low ({depth} < {config.QUEUE_MIN_DEPTH}); starting a "
                               f"cooldown-gated research pulse",
                               actor="scheduler", depth=depth)
                if tick % self_every == 0:
                    # slower cadence: consolidate → evolve the self → discover leads & act on them
                    self.queue.enqueue("consolidate", priority=6)
                    self.queue.enqueue("deliberate", priority=1)
                    self.queue.enqueue("discover", priority=6)
            except Exception as e:
                log().emit("error", f"scheduler: {str(e)[:200]}", actor="scheduler")
            await asyncio.sleep(config.SCHEDULER_INTERVAL_S)

    async def run(self) -> None:
        # bind THIS persona into the context so every worker/scheduler task + to_thread inherits it
        from ..context import set_persona
        set_persona(self.persona)
        self.persona.paths.ensure()
        self.started_at = asyncio.get_event_loop().time()
        recovered = self.queue.reset_expired_leases()
        log().emit("boot",
                   f"daemon up for “{self.persona.name}” — {self.n_workers} workers"
                   + (f", recovered {recovered} in-flight task(s)" if recovered else ""),
                   actor="daemon", seeded=selfmind.is_seeded())
        self._tasks = [asyncio.create_task(self._scheduler_loop())] if self.scheduler else []
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
