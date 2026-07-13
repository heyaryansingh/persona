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
    from .. import config
    from ..reading import reader, batch
    from ..budget import budget
    interest = task.params.get("interest", task.prompt)
    if not budget().can_read():
        return "bulk: reading budget reserved for outputs"
    works = await asyncio.to_thread(reader.scout, interest, config.BATCH_SWEEP)
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
    from ..budget import budget
    if not budget().can_read():
        return "scout: reading budget reserved for outputs (synthesis/papers)"
    interest = task.params.get("interest", task.prompt)
    works = await asyncio.to_thread(reader.scout, interest, 20)
    for w in works:
        queue.enqueue("observe", priority=5, params={"work": w, "interest": interest},
                      parent_id=task.parent_id)
    log().emit("spawn", f"found {len(works)} unread paper(s) on “{interest}” → queued readers",
               actor="scout", parent_id=task.parent_id, interest=interest, n=len(works))
    return f"scout: queued {len(works)} readers for {interest}"


@handler("gather")
async def _gather(task, queue) -> str:
    """An investigation's evidence step: scout the question (field + relevance gated) and read the
    top-K papers INLINE, so the evidence is on disk before the dependent harvest step runs."""
    import asyncio
    from .. import config
    from ..reading import reader
    from ..budget import budget
    interest = task.params.get("interest", task.prompt)
    if not budget().can_read():
        return "gather: reading budget reserved for outputs"
    works = await asyncio.to_thread(reader.scout, interest, config.GATHER_READS)
    read = 0
    for w in works:
        if not budget().can_read():
            break
        r = await asyncio.to_thread(reader.read_work, w, interest, parent_id=task.parent_id)
        if r.get("ok") and r.get("read", True) is not False:
            read += 1
    log().emit("spawn", f"gathered {read} on-topic paper(s) for “{interest[:60]}”", actor="gather",
               parent_id=task.parent_id, interest=interest, n=read)
    return f"gather: read {read} paper(s) for the question"


@handler("formal_verify")
async def _formal_verify(task, queue) -> str:
    """Human/team request for a FORMAL Lean 4 proof: submit to Aristotle (async, ~minutes) and track it;
    collect_proofs records the kernel-verified result to the ledger when it lands."""
    import asyncio
    from ..memory import proofs
    stmt = task.params.get("statement") or task.params.get("question") or task.prompt
    res = await asyncio.to_thread(proofs.submit_and_track, stmt)
    if res.get("ok"):
        queue.enqueue("collect_proofs", priority=9)
        return f"formal_verify: submitted to Aristotle (Lean 4, proving…) {str(res['task_id'])[:8]}"
    return f"formal_verify: {res.get('reason')}"


@handler("collect_proofs")
async def _collect_proofs(task, queue) -> str:
    """Drain pending Aristotle proofs; kernel-verified ones become lean-TESTED beliefs in the ledger.
    Re-enqueues itself (gently paced) until nothing is left proving — Lean proofs take minutes."""
    import asyncio
    from ..memory import proofs
    r = await asyncio.to_thread(proofs.poll)
    if r.get("still_pending"):
        await asyncio.sleep(25)                       # gentle pacing; proving takes minutes
        queue.enqueue("collect_proofs", priority=9)   # keep draining until done
    return f"collect_proofs: {r.get('verified', 0)} formally verified, {r.get('still_pending', 0)} still proving"


@handler("revisit")
async def _revisit(task, queue) -> str:
    """Self-correction: re-test a past verified result and update the ledger (verified/weakened/refuted)."""
    import asyncio
    from ..agents import revisit
    res = await asyncio.to_thread(revisit.revisit, parent_id=task.parent_id)
    if not res.get("ok"):
        return f"revisit: {res.get('reason')}"
    if res.get("revisited") == 0:
        return "revisit: nothing to re-verify yet"
    return f"revisit: “{res.get('statement','')[:36]}” {res.get('old')}→{res.get('new')}"


@handler("reaudit")
async def _reaudit(task, queue) -> str:
    """Living watchlist: re-audit the least-recently-checked audited paper against the current literature
    and record any movement in its replication verdict (the auditor's analogue of the revisit loop)."""
    import asyncio
    from ..agents import audit
    res = await asyncio.to_thread(audit.reaudit, parent_id=task.parent_id)
    if not res.get("ok"):
        return f"reaudit: {res.get('reason')}"
    if res.get("reaudited") == 0:
        return "reaudit: nothing on the watchlist yet"
    return f"reaudit: “{res.get('title','')[:36]}” {int((res.get('old') or 0)*100)}%→{int(res['new']*100)}% ({res['delta']:+.0%})"


@handler("critique")
async def _critique(task, queue) -> str:
    """Self-check step: review the report against the question; write critique.md; revise once if weak."""
    import asyncio
    from ..agents import critic
    q = task.params.get("question", task.params.get("topic", task.prompt))
    res = await asyncio.to_thread(critic.critique, q,
                                  investigation_id=task.params.get("investigation_id", ""),
                                  parent_id=task.parent_id)
    if not res.get("ok"):
        return f"critique: {res.get('reason')}"
    return f"critique: {res.get('verdict')}" + (" · revised the report" if res.get("revised") else "")


@handler("finalize_investigation")
async def _finalize_investigation(task, queue) -> str:
    """Close an investigation: aggregate step outcomes into findings.md and mark it done."""
    import asyncio
    from ..research.investigation import Investigation
    inv = Investigation.load(task.params.get("investigation_id") or "")
    if inv is None:
        return "finalize: no investigation"
    await asyncio.to_thread(inv.finalize, queue)
    report = (inv.meta.get("findings") or {}).get("report")
    log().emit("thought", f"closed the investigation “{inv.question[:64]}”"
               + (f" → {report}" if report else ""), actor="self", parent_id=task.parent_id)
    return f"finalize: {inv.slug} done" + (f" ({report})" if report else "")


@handler("prove")
async def _prove(task, queue) -> str:
    """Reasoning/proof step: produce a structured derivation and machine-check its steps with sympy."""
    import asyncio
    from ..agents import reason
    q = task.params.get("question", task.params.get("topic", task.prompt))
    res = await asyncio.to_thread(reason.prove, q, parent_id=task.parent_id)
    if not res.get("ok"):
        return f"prove: {res.get('reason')}"
    return f"prove: {res.get('verified')}/{res.get('checks')} steps verified" \
           + (f" → {res['doc']}" if res.get("doc") else "")


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


@handler("review")
async def _review(task, queue) -> str:
    """Write a cited literature review of a topic from the mind's synthesis notes (deliverable)."""
    import asyncio
    from ..deliverables import review
    res = await asyncio.to_thread(review.write_review, task.params.get("topic", task.prompt),
                                  parent_id=task.parent_id)
    return f"review: {res.get('file', res.get('reason'))}"


@handler("paper")
async def _paper(task, queue) -> str:
    """Write + compile a LaTeX -> PDF paper (deliverable)."""
    import asyncio
    from ..deliverables import paper
    res = await asyncio.to_thread(paper.write_paper, task.params.get("topic", task.prompt),
                                  parent_id=task.parent_id)
    return f"paper: {res.get('pdf', res.get('reason'))}"


@handler("discover")
async def _discover(task, queue) -> str:
    """See what's known, generate hypotheses, run the testable ones, flag physical ones for humans."""
    import asyncio
    from ..agents import discover
    res = await asyncio.to_thread(discover.discover, parent_id=task.parent_id)
    if not res.get("ok"):
        return f"discover: {res.get('reason')}"
    return f"discover: {res['ideas']} lead(s), {res['queued']} experiment(s), {res['escalated']} to human"


@handler("consolidate")
async def _consolidate(task, queue) -> str:
    """Sleep-time synthesis: turn accumulated claims into cited per-topic understanding (notes)."""
    import asyncio
    from ..synthesis import consolidator
    res = await asyncio.to_thread(consolidator.consolidate, 6, task.parent_id)
    if not res.get("ok"):
        return f"consolidate: {res.get('reason')}"
    return f"consolidate: {res['synthesized']} note(s) from {res['communities']} subtopic(s)"


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
    # act on the sharpest open question: do REAL work on it (analyst: data + code + report)
    from ..selfmind import open_questions
    qs = open_questions()
    if qs:
        queue.enqueue("investigate", priority=4, params={"question": qs[0]}, parent_id=task.parent_id)
    return f"deliberate: evolved self, spawned {len(res.get('new_interests', []))} interest(s), " \
           f"queued {len(res.get('priority_reads', [])[:4])} priority read(s) + 1 investigation"


@handler("investigate")
async def _investigate(task, queue) -> str:
    """The analyst does REAL work on a question: fetches data, runs code in the sandbox, writes a report."""
    import asyncio
    from ..agents import analyst
    q = task.params.get("question", task.prompt)
    log().emit("thought", f"investigating: {q[:110]}", actor="analyst", parent_id=task.parent_id)
    res = await asyncio.to_thread(analyst.investigate, q, parent_id=task.parent_id,
                                  evidence_claim_ids=task.params.get("evidence_claim_ids"))
    if not res.get("ok"):
        return f"investigate: {res.get('reason')}"
    return f"investigate: wrote “{res.get('title','')[:60]}” (code={res.get('ran_code')})"


@handler("build")
async def _build(task, queue) -> str:
    """Build a real artifact (diagram/art/page/code), grounded in the mind's knowledge + browsable."""
    import asyncio
    from ..agents import builder
    from ..memory import membrane
    kind = task.params.get("kind", "diagram")
    topic = task.params.get("topic", task.prompt)
    kg = await asyncio.to_thread(membrane.get_kg)
    if kind in ("diagram", "art"):
        res = await asyncio.to_thread(builder.build_visual, kind, topic, parent_id=task.parent_id, kg=kg)
    elif kind == "page":
        res = await asyncio.to_thread(builder.build_page, topic, parent_id=task.parent_id, kg=kg)
    elif kind == "code":
        res = await asyncio.to_thread(builder.build_code, topic, parent_id=task.parent_id, kg=kg)
    else:
        return f"build: unknown kind {kind}"
    return f"build {kind}: {res.get('artifact', res.get('reason'))}"


@handler("free_move")
async def _free_move(task, queue) -> str:
    """The FREE mind: an Opus step picks any vetted action + topic, then enqueues it (v6 P4)."""
    import asyncio
    from ..agents import freemove
    from ..memory import membrane
    kg = await asyncio.to_thread(membrane.get_kg)
    res = await asyncio.to_thread(freemove.free_move, kg, parent_id=task.parent_id)
    if not res.get("ok"):
        return f"free_move: {res.get('reason')}"
    a, topic = res["action"], res.get("topic", "")
    if a == "scout":
        queue.enqueue("scout", priority=3, params={"interest": topic}, parent_id=task.parent_id)
    elif a == "investigate":
        queue.enqueue("investigate", priority=4, params={"question": topic}, parent_id=task.parent_id)
    elif a == "review":
        queue.enqueue("review", priority=4, params={"topic": topic}, parent_id=task.parent_id)
    elif a == "paper":
        queue.enqueue("paper", priority=5, params={"topic": topic}, parent_id=task.parent_id)
    elif a == "consolidate":
        queue.enqueue("consolidate", priority=5, parent_id=task.parent_id)
    elif a in ("diagram", "art", "page", "code"):
        queue.enqueue("build", priority=4, params={"kind": a, "topic": topic}, parent_id=task.parent_id)
    return f"free_move -> {a}: {topic[:60]}"


@handler("observe")
async def _observe(task, queue) -> str:
    """Reader: fetch ONE specific paper (from the scout) and extract structured claims.
    Runs the blocking fetch+LLM off the event loop so other workers keep going."""
    import asyncio
    from ..reading import reader
    from ..budget import budget
    if not budget().can_read():
        return "observe: reading budget reserved for outputs"
    work = task.params.get("work")
    interest = task.params.get("interest", "")
    if not work:
        return "observe: no work in params"
    res = await asyncio.to_thread(reader.read_work, work, interest, parent_id=task.parent_id)
    if res.get("read"):
        return f"observe: read {res.get('slug')} ({res.get('n_claims',0)} claims)"
    return f"observe: {res.get('reason','no-read')}"
