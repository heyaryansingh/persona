"""Task handlers (v4). P0 wires the always-on skeleton with REAL operational handlers (no faked
cognition): `reflect` reads the self + system state and enqueues follow-up work; `observe` is the
reader slot (a real full-text reader lands in P1). Each handler emits legible events so the live
stream shows the mind's actual moves. Later phases register richer handlers here.
"""
from __future__ import annotations

from .. import selfmind
from ..events import log

# registry: task.type -> async handler(task, queue) -> result_ref(str)
_HANDLERS = {}


def handler(name: str):
    def deco(fn):
        _HANDLERS[name] = fn
        return fn
    return deco


async def dispatch(task, queue) -> str:
    fn = _HANDLERS.get(task.type)
    if fn is None:
        log().emit("error", f"no handler for task type {task.type!r}", actor="worker",
                   parent_id=task.parent_id, task_id=task.id)
        return "no-handler"
    return await fn(task, queue)


@handler("reflect")
async def _reflect(task, queue) -> str:
    """The Ralph SELF task: read the durable self, decide what to look at next, enqueue readers,
    then exit (fresh context each time). P0 = operational reflection; P4 adds LLM self-rewrite."""
    ints = selfmind.interests()
    qs = selfmind.open_questions()
    ev = log().emit("thought",
                    f"reflecting — {len(ints)} interest(s), {len(qs)} open question(s); "
                    f"deciding what to read next.", actor="self")
    spawned = 0
    for name, weight in sorted(ints, key=lambda x: -x[1])[:5]:
        queue.enqueue("observe", prompt=name, priority=max(1, int(6 - weight * 2)),
                      params={"interest": name}, parent_id=ev)
        log().emit("spawn", f"queued a reader for “{name}”", actor="self",
                   parent_id=ev, interest=name)
        spawned += 1
    return f"reflect: spawned {spawned} reader task(s)"


@handler("observe")
async def _observe(task, queue) -> str:
    """Reader: fetch a real paper for this interest and extract structured claims (P1).
    Runs the blocking fetch+LLM off the event loop so other workers keep going."""
    import asyncio
    from ..reading import reader
    interest = task.params.get("interest", task.prompt)
    res = await asyncio.to_thread(reader.read_interest, interest, parent_id=task.parent_id)
    if res.get("read"):
        return f"observe: read {res.get('slug')} ({res.get('n_claims',0)} claims, ${res.get('cost',0):.4f})"
    return f"observe: {res.get('reason', res.get('error','no-read'))}"
