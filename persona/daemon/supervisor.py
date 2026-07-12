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

    # When a mind runs out of easy reading it must not die — it should think, test, write, and
    # grow its own agenda. free_move lets it CHOOSE its next act; discover ideates; consolidate writes up.
    IDLE_AGENDA = ("free_move", "discover", "consolidate", "deliberate")
    # Once the reading budget is spent (READING_BUDGET_FRACTION), switch to PRODUCING outputs with the
    # reserved budget — synthesize, write reviews and compiled papers — so a mind ships, not just reads.
    OUTPUT_AGENDA = ("consolidate", "review", "paper", "free_move", "discover")

    def _top_interest(self) -> str:
        try:
            ints = selfmind.interests()
            return ints[0][0] if ints else self.persona.name
        except Exception:
            return self.persona.name

    async def _scheduler_loop(self) -> None:
        from .. import selfmind
        last_reflect = (asyncio.get_running_loop().time() if self.queue.counts()
                        else float("-inf"))
        last_self = float("-inf")
        idle_i = 0
        announced_wait = False
        while not self._stop.is_set():
            try:
                # SEEDED-GATE: do NO work until the user has given this persona its interests.
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
                counts = self.queue.counts()
                depth = counts.get("pending", 0)
                active = depth + counts.get("leased", 0)   # queued OR currently running
                can_spend = self.persona.budget.can_spend()
                can_read = self.persona.budget.can_read()   # False once the reading reserve is spent
                enqueued = False
                # 0. DRIVE INVESTIGATIONS — the master line of thought. Every open question inside a
                #    specialization becomes a persistent multistep PROGRAM worked by a team of agents
                #    (gather → harvest → synthesize → analyze → write → finalize), chained by the
                #    queue's dependency engine. This is the primary work; reading below just feeds it.
                if can_spend:
                    try:
                        from ..research.investigation import Investigation
                        from ..agents import director
                        active_invs = [i for i in Investigation.list_all()
                                       if i.meta.get("status") == "running"]
                        if len(active_invs) < config.MAX_ACTIVE_INVESTIGATIONS:
                            # the Director assigns a NON-OVERLAPPING problem (dedup vs active/done/verified)
                            q = director.assign_question(selfmind.open_questions(), self._top_interest())
                            if q:
                                inv = Investigation.create(q, specialization=self._top_interest())
                                inv.launch(self.queue)
                                log().emit("thought", f"opened an investigation: “{q[:70]}” — a "
                                           f"{len(inv.meta['steps'])}-agent team is on it", actor="self")
                                enqueued = True
                    except Exception as e:
                        log().emit("error", f"investigation driver: {str(e)[:150]}", actor="scheduler")
                # 1. keep the reading fresh — ONLY while within the reading budget (the rest is
                #    reserved for producing outputs, so a mind never spends its whole day reading).
                if can_read and _should_reflect(depth, now, last_reflect):
                    self.queue.enqueue("reflect", priority=1)
                    last_reflect = now; enqueued = True
                    log().emit("schedule", f"queue low ({depth} < {config.QUEUE_MIN_DEPTH}); "
                               "starting a research pulse", actor="scheduler", depth=depth)
                # 2. periodic reflective cognition + SHIP THE FIRST PAPER once enough is synthesized.
                if now - last_self >= config.SELF_INTERVAL_S:
                    self.queue.enqueue("consolidate", priority=2)
                    self.queue.enqueue("deliberate", priority=3)
                    self.queue.enqueue("discover", priority=4)
                    try:
                        notes = sum(1 for _ in self.persona.paths.notes_dir.glob("*.md"))
                        has_paper = any(self.persona.paths.deliverables_dir.glob("paper-*.pdf"))
                    except Exception:
                        notes, has_paper = 0, True
                    if notes >= 4 and not has_paper and can_spend:
                        self.queue.enqueue("paper", priority=0, params={"topic": self._top_interest()})
                        log().emit("schedule", "enough synthesis — writing a compiled paper",
                                   actor="scheduler")
                    # SELF-CORRECTION: re-test a past proven result against what it knows now.
                    try:
                        from ..memory import verified as vled
                        if any(e.get("status") in ("verified", "weakened") for e in vled.entries()) and can_spend:
                            self.queue.enqueue("revisit", priority=3)
                    except Exception:
                        pass
                    # FORMAL PROOFS: drain any pending Aristotle Lean 4 proofs (free to poll; no $ gate).
                    try:
                        from ..memory import proofs
                        if proofs.pending():
                            self.queue.enqueue("collect_proofs", priority=8)
                    except Exception:
                        pass
                    last_self = now; enqueued = True
                # 3. NEVER IDLE: keep ideating/testing/writing. Once the reading reserve is spent,
                #    switch to PRODUCING outputs (reviews/papers) with the reserved budget.
                if not enqueued and active == 0 and can_spend:
                    agenda = self.IDLE_AGENDA if can_read else self.OUTPUT_AGENDA
                    act = agenda[idle_i % len(agenda)]; idle_i += 1
                    params = {"topic": self._top_interest()} if act in ("paper", "review") else {}
                    self.queue.enqueue(act, priority=(0 if act in ("paper", "review") else 3),
                                       params=params)
                    log().emit("schedule",
                               f"{'producing outputs' if not can_read else 'keeping research alive'} "
                               f"— a {act} pulse", actor="scheduler")
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
