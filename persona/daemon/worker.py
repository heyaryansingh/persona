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
    # a background bulk sweep (Batch API, ~50% cost, thousands/day) on the top interest
    top = sorted(ints, key=lambda x: -x[1])[:1]
    if top:
        queue.enqueue("bulk", priority=7, params={"interest": top[0][0]}, parent_id=ev)
    queue.enqueue("collect_batches", priority=9, parent_id=ev)   # drain finished batches
    queue.enqueue("harvest", priority=8, parent_id=ev)           # digest AFTER reads drain
    return f"reflect: scouting {spawned} interest(s)"


@handler("bulk")
async def _bulk(task, queue) -> str:
    """Background bulk sweep: scout a batch of papers and submit them to the Batch API."""
    import asyncio
    from ..reading import reader, batch
    from ..budget import budget
    interest = task.params.get("interest", task.prompt)
    if not budget().can_spend():
        return "bulk: budget reached"
    works = await asyncio.to_thread(reader.scout, interest, 25)
    if not works:
        return "bulk: nothing new"
    res = await asyncio.to_thread(batch.submit, works, interest)
    return f"bulk: submitted {res.get('n',0)} to batch {str(res.get('batch_id',''))[:12]}"


@handler("collect_batches")
async def _collect_batches(task, queue) -> str:
    import asyncio
    from ..reading import batch
    res = await asyncio.to_thread(batch.collect_pending)
    return f"collect_batches: checked {res.get('checked',0)}, collected {res.get('collected',0)}"


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


@handler("read_url")
async def _read_url(task, queue) -> str:
    """Read an arbitrary web/online source (any URL)."""
    import asyncio
    from ..reading import reader
    url = task.params.get("url", task.prompt)
    res = await asyncio.to_thread(reader.read_url, url, task.params.get("interest", "web"),
                                  parent_id=task.parent_id)
    return f"read_url: {res.get('slug', res.get('reason', res.get('error','?')))}"


@handler("harvest")
async def _harvest(task, queue) -> str:
    """Digest new reads: claims.jsonl -> membrane -> temporal KG (beliefs + contradictions)."""
    import asyncio
    from ..memory import membrane
    res = await asyncio.to_thread(membrane.harvest, 2, task.parent_id)
    if not res.get("ok"):
        return f"harvest: {res.get('reason')}"
    return f"harvest: +{res['ingested']} sources, {res['beliefs']} beliefs, {res['new_contradictions']} new contradiction(s)"


@handler("deliberate")
async def _deliberate(task, queue) -> str:
    """The reflecting self (Opus): reads what it's learned and EVOLVES — reweights + spawns new
    interests, forms questions, then scouts its own priority reads. This is autonomy."""
    import asyncio
    from ..agents import deliberate as dlb
    from ..memory import membrane
    kg = await asyncio.to_thread(membrane.get_kg)
    res = await asyncio.to_thread(dlb.deliberate, kg, parent_id=task.parent_id)
    if not res.get("ok"):
        return f"deliberate: {res.get('reason')}"
    for topic in res.get("priority_reads", [])[:4]:
        queue.enqueue("scout", priority=2, params={"interest": topic}, parent_id=task.parent_id)
    return f"deliberate: evolved self, spawned {len(res.get('new_interests', []))} interest(s), " \
           f"queued {len(res.get('priority_reads', [])[:4])} priority read(s)"


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
