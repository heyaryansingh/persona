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
        queue.enqueue("scout", prompt=name, priority=max(1, int(6 - weight * 2)),
                      params={"interest": name}, parent_id=ev)
        log().emit("spawn", f"scouting the literature on “{name}”", actor="self",
                   parent_id=ev, interest=name)
        spawned += 1
    queue.enqueue("harvest", priority=8, parent_id=ev)   # low priority: digest AFTER reads drain
    return f"reflect: scouting {spawned} interest(s)"


@handler("scout")
async def _scout(task, queue) -> str:
    """Discover many unread papers for an interest and fan out one reader per paper (volume)."""
    import asyncio
    from ..reading import reader
    interest = task.params.get("interest", task.prompt)
    works = await asyncio.to_thread(reader.scout, interest, 20)
    for w in works:
        queue.enqueue("observe", priority=5, params={"work": w, "interest": interest},
                      parent_id=task.parent_id)
    log().emit("spawn", f"found {len(works)} unread paper(s) on “{interest}” → queued readers",
               actor="scout", parent_id=task.parent_id, interest=interest, n=len(works))
    return f"scout: queued {len(works)} readers for {interest}"


@handler("harvest")
async def _harvest(task, queue) -> str:
    """Digest new reads: claims.jsonl -> membrane -> temporal KG (beliefs + contradictions)."""
    import asyncio
    from ..memory import membrane
    res = await asyncio.to_thread(membrane.harvest, 2, task.parent_id)
    if not res.get("ok"):
        return f"harvest: {res.get('reason')}"
    return f"harvest: +{res['ingested']} sources, {res['beliefs']} beliefs, {res['new_contradictions']} new contradiction(s)"


@handler("observe")
async def _observe(task, queue) -> str:
    """Reader: fetch ONE specific paper (from the scout) and extract structured claims.
    Runs the blocking fetch+LLM off the event loop so other workers keep going."""
    import asyncio
    from ..reading import reader
    work = task.params.get("work")
    interest = task.params.get("interest", "")
    if not work:
        return "observe: no work in params"
    res = await asyncio.to_thread(reader.read_work, work, interest, parent_id=task.parent_id)
    if res.get("read"):
        return f"observe: read {res.get('slug')} ({res.get('n_claims',0)} claims)"
    return f"observe: {res.get('reason','no-read')}"
