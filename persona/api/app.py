"""FastAPI app (v5 P3) — multi-persona: a gallery of fully-isolated researcher minds.

Every persona has its own workspace, graph, events, budget, and daemon. Endpoints are routed by
persona_id and set the current-persona context so the shared code (log/get_kg/budget/selfmind)
resolves to the right mind. `GET /` serves the gallery UI.

Run: python -m persona   (or: uvicorn persona.api.app:app --port 8137)
"""
from __future__ import annotations

import asyncio
import json
import mimetypes
import re
from pathlib import Path

from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, FileResponse

from .. import config, context, selfmind
from ..manager import manager

app = FastAPI(title="Persona v5", version="5.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
_STATIC = Path(__file__).resolve().parent / "static"


@app.on_event("startup")
async def _startup():
    asyncio.create_task(_supervisor())    # start/resume seeded personas' daemons in the loop


async def _supervisor():
    """Ensure every SEEDED persona has a running daemon (resume on boot + start newly-seeded)."""
    while True:
        try:
            for p in manager().list():
                if p.is_seeded() and not p.is_halted():   # HALTED personas stay down until resumed
                    manager().start(p)      # no-op if already running
        except Exception:
            pass
        await asyncio.sleep(3)


@app.on_event("shutdown")
async def _shutdown():
    manager().stop_all()


def _p(pid: str):
    p = manager().get(pid)
    if p is None:
        raise HTTPException(status_code=404, detail=f"no persona {pid!r}")
    return p


# --------------------------------------------------------------- gallery
@app.get("/api/personas")
def personas():
    return {"personas": [p.to_card() for p in manager().list()]}


@app.post("/api/personas")
def create_persona(payload: dict):
    interests = payload.get("interests") or []
    if isinstance(interests, str):
        interests = [s.strip() for s in interests.split(",") if s.strip()]
    p = manager().create(payload["name"], interests=interests,
                         budget_usd=payload.get("budget_usd"))
    # create() already seeds when interests are given; the startup _supervisor() loop starts the
    # daemon from WITHIN the event loop. Don't call manager().start() here — this is a sync request
    # thread with no running loop, so asyncio.create_task() would raise (a 500 with no UI feedback).
    return p.to_card()


@app.post("/api/persona/{pid}/seed")
def seed(pid: str, payload: dict):
    interests = payload.get("interests") or []
    if isinstance(interests, str):
        interests = [s.strip() for s in interests.split(",") if s.strip()]
    fresh = manager().seed(pid, interests)
    with context.use(_p(pid)):
        from ..events import log
        log().emit("seed", f"{'born' if fresh else 're-seeded'}: {', '.join(interests)}", actor="human")
    return {"applied": True, "fresh_birth": fresh}


@app.post("/api/persona/{pid}/reset")
def reset(pid: str):
    with context.use(_p(pid)):
        selfmind.reset()
    return {"reset": True}


# --------------------------------------------------------------- control plane (v6 P0)
@app.post("/api/persona/{pid}/pause")
def pause(pid: str):
    p = _p(pid)
    p.set_run_state("PAUSED")
    with context.use(p):
        from ..events import log
        log().emit("control", "paused by human — no new work or spend until resumed", actor="human")
    return {"run_state": "PAUSED"}


@app.post("/api/persona/{pid}/resume")
def resume(pid: str):
    p = _p(pid)
    p.set_run_state("RUNNING")   # the startup supervisor restarts a halted daemon within ~3s
    with context.use(p):
        from ..events import log
        log().emit("control", "resumed by human", actor="human")
    return {"run_state": "RUNNING"}


@app.post("/api/persona/{pid}/halt")
def halt(pid: str):
    p = _p(pid)
    p.set_run_state("HALTED")
    manager().stop(pid)          # stop the daemon; supervisor won't restart while HALTED
    with context.use(p):
        from ..events import log
        log().emit("control", "halted by human — daemon stopped", actor="human")
    return {"run_state": "HALTED"}


@app.get("/api/persona/{pid}/spend")
def spend(pid: str):
    p = _p(pid)
    b = p.budget
    with context.use(p):
        from ..events import log
        recent = [e for e in log().since(max(0, log().latest_id() - 400))
                  if e.get("type") == "cost"][-12:]
    return {"spent_today": round(b.spent_today(), 4), "cap_usd": round(p.cap_usd, 2),
            "remaining": round(b.remaining(), 4), "run_state": p.run_state(),
            "recent_costs": [{"task": e["data"].get("task_type"), "usd": e["data"].get("cost"),
                              "at": e["ts"]} for e in recent]}


@app.post("/api/persona/{pid}/budget")
def set_budget(pid: str, payload: dict):
    p = _p(pid)
    p.set_cap(float(payload["cap_usd"]))
    return {"cap_usd": round(p.cap_usd, 2), "remaining": round(p.budget.remaining(), 4)}


@app.post("/api/persona/{pid}/delete")
def delete(pid: str, payload: dict = None):
    return {"deleted": manager().delete(pid, wipe=(payload or {}).get("wipe", False))}


# --------------------------------------------------------------- per-persona views
@app.get("/api/persona/{pid}/status")
def status(pid: str):
    p = _p(pid)
    d = manager()._daemons.get(pid)
    with context.use(p):
        from ..events import log
        return {**p.to_card(), "workers": (d.n_workers if d else 0),
                "queue": (d.queue.counts() if d else {}), "latest_event": log().latest_id(),
                "have_key": config.have_key()}


@app.get("/api/persona/{pid}/swarm")
def swarm(pid: str):
    """Live swarm snapshot for the real-time view: worker count, what each active (leased) task is
    doing with a human target, recent completions, queued steps, and run-state — the truth behind the
    animation (all real tasks; nothing padded). `investigation_id` on a task groups it into a team."""
    p = _p(pid)
    d = manager()._daemons.get(pid)
    with context.use(p):
        q = d.queue if d else p.queue()
        snap = q.active()
        counts = snap.get("counts", {})
        snap["in_flight"] = counts.get("pending", 0) + counts.get("leased", 0)  # honest fleet size
        snap["live_cap"] = config.LIVE_CONCURRENCY
    snap["workers"] = d.n_workers if d else 0
    snap["run_state"] = p.to_card().get("run_state")
    return snap


@app.get("/api/persona/{pid}/investigations")
def investigations(pid: str):
    """The persona's research programs (the master lines of thought): each open question as a
    persistent multistep investigation with per-step progress. Documents live under investigations/."""
    p = _p(pid)
    d = manager()._daemons.get(pid)
    with context.use(p):
        from ..research.investigation import Investigation
        q = d.queue if d else p.queue()
        out = []
        for inv in sorted(Investigation.list_all(), key=lambda i: i.meta.get("updated", ""), reverse=True):
            qsteps = {s["step_idx"]: s for s in q.investigation_steps(inv.id)}
            steps = [{"role": s["role"], "type": s["type"],
                      "status": qsteps.get(s["idx"], {}).get("status", s.get("status", "pending"))}
                     for s in inv.meta.get("steps", [])]
            done = sum(1 for s in steps if s["status"] == "done")
            out.append({"slug": inv.slug, "question": inv.question,
                        "specialization": inv.meta.get("specialization", ""),
                        "status": inv.meta.get("status", "open"), "updated": inv.meta.get("updated"),
                        "steps": steps, "done": done, "total": len(steps),
                        "report": (inv.meta.get("findings") or {}).get("report")})
    return {"investigations": out, "n": len(out)}


@app.get("/api/persona/{pid}/now")
def now(pid: str):
    """The master line of thought as data: the persona's specializations, active investigations with
    live progress, recently produced reports, and open questions — powers the UI's 'current work'."""
    p = _p(pid)
    d = manager()._daemons.get(pid)
    with context.use(p):
        from ..research.investigation import Investigation
        q = d.queue if d else p.queue()
        invs = Investigation.list_all()
        active = []
        for i in invs:
            if i.meta.get("status") != "running":
                continue
            steps = {s["step_idx"]: s for s in q.investigation_steps(i.id)}
            nd = sum(1 for s in steps.values() if s["status"] == "done")
            active.append({"slug": i.slug, "question": i.question, "done": nd,
                           "total": len(i.meta.get("steps", []))})
        recent = [{"slug": i.slug, "question": i.question,
                   "report": (i.meta.get("findings") or {}).get("report")}
                  for i in sorted([x for x in invs if x.meta.get("status") == "done"],
                                  key=lambda x: x.meta.get("updated", ""), reverse=True)[:6]]
        return {"specializations": [n for n, _ in sorted(selfmind.interests(), key=lambda x: -x[1])[:5]],
                "open_questions": selfmind.open_questions()[:10], "active": active, "recent": recent}


@app.get("/api/persona/{pid}/folder/bundle")
def folder_bundle(pid: str, path: str):
    """Export any folder the persona built as a .zip (a real research directory you can take away)."""
    import io
    import zipfile
    from fastapi.responses import StreamingResponse
    p = _p(pid)
    with context.use(p):
        base = p.paths.safe(path)
        if not base.is_dir():
            return {"ok": False, "reason": "not-a-folder"}
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
            for f in base.rglob("*"):
                if f.is_file() and ".persona" not in f.parts:
                    z.write(f, f.relative_to(base))
        buf.seek(0)
        name = (base.name or "folder") + ".zip"
    return StreamingResponse(buf, media_type="application/zip",
                             headers={"Content-Disposition": f'attachment; filename="{name}"'})


@app.get("/api/persona/{pid}/events")
def events(pid: str, after: int = 0, limit: int = 500):
    with context.use(_p(pid)):
        from ..events import log
        return {"events": log().since(after, limit), "latest": log().latest_id()}


@app.get("/api/persona/{pid}/self")
def get_self(pid: str):
    with context.use(_p(pid)):
        return {"seeded": selfmind.is_seeded(), "interests": selfmind.interests(),
                "open_questions": selfmind.open_questions(), "files": selfmind.read_self()}


@app.get("/api/persona/{pid}/verified")
def verified_ledger(pid: str):
    """The verification ledger — what the mind has actually PROVEN/TESTED (not just read), with the
    method (lean/sympy/analyst) and whether the revisit loop has re-confirmed or refuted it."""
    with context.use(_p(pid)):
        from ..memory import verified as vled
        return {"entries": vled.entries(), "summary": vled.summary()}


@app.get("/api/persona/{pid}/knowledge")
def knowledge_tree(pid: str):
    """The layered knowledge ladder: L1 topics known → L2 summaries → L3 in-depth → L4 sources."""
    with context.use(_p(pid)):
        from ..agents import knowledge
        return knowledge.tree()


@app.post("/api/persona/{pid}/run_code")
def run_code(pid: str, payload: dict):
    """Code editor: run Python in the offline sandbox (torch/numpy/scipy/sklearn/matplotlib/pandas/
    sympy preinstalled, network-denied, resource-capped) and return stdout/stderr + any figures it
    wrote. Optionally save the edited code back to a workspace file first."""
    p = _p(pid)
    code = payload.get("code", "")
    if not code.strip():
        return {"ok": False, "reason": "empty"}
    with context.use(p):
        from ..tools import sandbox
        if not sandbox.image_ready():
            return {"ok": False, "reason": "sandbox-image-missing"}
        path = (payload.get("path") or "").strip()
        if path:                                  # persist the edit to the workspace
            try:
                dst = p.paths.safe(path)
                dst.parent.mkdir(parents=True, exist_ok=True)
                dst.write_text(code, encoding="utf-8")
            except Exception:
                pass
        workdir = p.paths.workspace / "code" / "run"
        workdir.mkdir(parents=True, exist_ok=True)
        for old in workdir.rglob("*.png"):        # clear prior figures so we only report new ones
            try:
                old.unlink()
            except Exception:
                pass
        r = sandbox.run_python(code, workdir, timeout=90)
        figs = [str(f.relative_to(p.paths.workspace)).replace("\\", "/") for f in sorted(workdir.rglob("*.png"))]
    return {"ok": r.get("exit_code") == 0, "stdout": (r.get("stdout") or "")[-8000:],
            "stderr": (r.get("stderr") or "")[-4000:], "exit_code": r.get("exit_code"),
            "timeout": r.get("timeout"), "figures": figs[:6]}


@app.post("/api/persona/{pid}/audit")
def audit_paper(pid: str, payload: dict):
    """Robustness audit of a PAST paper: deterministic statistical forensics (statcheck/GRIM/GRIMMER/
    power/p-curve, run in code) + literature stance + a grounded, calibrated replication-likelihood.
    Target by source `slug`, by a `query` (best-matching read paper), or by raw `text`."""
    p = _p(pid)
    slug = (payload.get("slug") or "").strip() or None
    text = payload.get("text") or ""
    title = payload.get("title") or ""
    q = (payload.get("query") or payload.get("q") or "").strip()
    if not slug and not text.strip() and q:
        # resolve a query to the best-matching read paper by its stored title
        import json as _json
        ql = q.lower()
        best = None
        for mf in p.paths.sources_dir.glob("*/meta.json"):
            try:
                m = _json.loads(mf.read_text(encoding="utf-8", errors="replace"))
            except Exception:
                continue
            t = (m.get("title") or "").lower()
            score = sum(1 for w in ql.split() if len(w) > 3 and w in t)
            if score and (best is None or score > best[0]):
                best = (score, mf.parent.name, m.get("title"))
        if best:
            slug, title = best[1], best[2]
    if not slug and not text.strip():
        return {"ok": False, "reason": "empty"}
    with context.use(p):
        from ..agents import audit
        return audit.audit(slug=slug, text=text, title=title)


@app.post("/api/persona/{pid}/report")
def region_report(pid: str, payload: dict):
    """Idea-genealogy: a grounded, CITED report for a selected region (a query or an explicit entity
    set) with an optional follow-up focus. Every statement traces to a source paper + year + DOI."""
    p = _p(pid)
    q = (payload.get("query") or payload.get("q") or payload.get("text") or "").strip()
    ents = payload.get("entities") or None
    msg = (payload.get("message") or "").strip()
    if not q and not ents:
        return {"ok": False, "reason": "empty"}
    with context.use(p):
        from ..agents import report
        return report.generate(q or (ents[0] if ents else ""), entities=ents, message=msg)


@app.post("/api/persona/{pid}/verify")
@app.post("/api/persona/{pid}/prove")
def verify_claim(pid: str, payload: dict):
    """Ask the persona to formally PROVE a claim (Harmonic Aristotle, Lean 4). Async — proving takes
    minutes; the kernel-verified result lands in the verification ledger (Studio → Signals). Falls back
    to the sympy machine-check path (a `prove` investigation step) when no Aristotle key is configured."""
    p = _p(pid)
    d = manager()._daemons.get(pid)
    stmt = (payload.get("statement") or payload.get("claim") or payload.get("question")
            or payload.get("text") or "").strip()
    if not stmt:
        return {"ok": False, "reason": "empty"}
    if d is None:
        return {"ok": False, "reason": "daemon not running (seed/resume the persona)"}
    with context.use(p):
        from ..tools import aristotle
        from ..events import log
        log().emit("say", f"[verify] {stmt}", actor="human")
        if aristotle.available():
            tid = d.queue.enqueue("formal_verify", priority=1, params={"statement": stmt})
            return {"ok": True, "mode": "formal", "task": tid,
                    "message": "submitted a formal Lean 4 proof to Aristotle — it lands in Signals when verified"}
        # no key: run the sympy machine-check via a prove task
        tid = d.queue.enqueue("prove", priority=1, params={"question": stmt})
        return {"ok": True, "mode": "sympy", "task": tid,
                "message": "machine-checking with sympy — result lands in Signals"}


@app.get("/api/persona/{pid}/sessions")
def research_sessions(pid: str, limit: int = 100, offset: int = 0):
    from ..sessions import list_sessions
    p = _p(pid)
    sessions = list_sessions(p.paths.runs_dir)
    summaries = [{key: session.get(key) for key in (
        "session_id", "question", "title", "model", "status", "started_at", "finished_at",
        "duration_ms", "cost_usd", "verification")}
        | {"artifact_count": len(session.get("artifacts", [])),
           "conclusion_count": len(session.get("conclusions", [])),
           "required_claim_count": len(session.get("required_claim_ids", []))}
        for session in sessions]
    start, size = max(0, offset), max(1, min(limit, 500))
    return {"sessions": summaries[start:start + size], "total": len(summaries),
            "offset": start, "limit": size}


@app.get("/api/persona/{pid}/sessions/{session_id}")
def research_session(pid: str, session_id: str, limit: int = 500):
    from ..sessions import read_session
    data = read_session(_p(pid).paths.runs_dir, session_id)
    if data is None:
        raise HTTPException(status_code=404, detail="session not found")
    events = data["events"]
    return {"session": data["session"], "event_count": len(events),
            "events": events[-max(1, min(limit, 2000)):],
            "read_errors": data.get("read_errors", [])}


@app.get("/api/persona/{pid}/sessions/{session_id}/verify")
def verify_research_session(pid: str, session_id: str):
    from ..sessions import verify_session
    result = verify_session(_p(pid).paths.runs_dir, session_id)
    if result.get("errors") == ["session-not-found"]:
        raise HTTPException(status_code=404, detail="session not found")
    return result


@app.get("/api/persona/{pid}/sessions/{session_id}/artifact/{sha256}")
def research_session_artifact(pid: str, session_id: str, sha256: str, download: bool = False):
    import re
    from ..sessions import read_session
    p = _p(pid)
    data = read_session(p.paths.runs_dir, session_id)
    if data is None or not re.fullmatch(r"[0-9a-f]{64}", sha256):
        raise HTTPException(status_code=404, detail="artifact not found")
    artifact = next((a for a in data["session"].get("artifacts", [])
                     if a.get("sha256") == sha256), None)
    if artifact is None:
        raise HTTPException(status_code=404, detail="artifact not found")
    root = (p.paths.runs_dir / session_id).resolve()
    path = (root / artifact["path"]).resolve()
    if root not in path.parents or not path.exists():
        raise HTTPException(status_code=404, detail="artifact not found")
    return FileResponse(path, media_type=artifact.get("media_type"),
                        filename=artifact.get("name") if download else None)


@app.get("/api/persona/{pid}/kg")
def kg(pid: str):
    p = _p(pid)
    with context.use(p):
        from ..memory.membrane import get_kg
        g = get_kg()
        if g is None:
            return {"available": False}
        beliefs = []
        for belief in g.beliefs(min_independent=1):
            state = ("anchored" if belief.get("anchored") else
                     "tested" if belief.get("provenance") == "TESTED" else
                     "corroborated" if belief.get("independent_sources", 0) >= 2 else "observed")
            beliefs.append({**belief, "epistemic_state": state})
        conflicts = g.candidate_conflicts()
        return {"available": True, "stats": g.stats(), "beliefs": beliefs,
                "candidate_conflicts": conflicts, "contradictions": conflicts,
                "graph": g.graph_snapshot()}


# --------------------------------------------------------------- navigable graph (v6 P3)
@app.get("/api/persona/{pid}/graph/overview")
def graph_overview(pid: str, limit: int = 60):
    with context.use(_p(pid)):
        from ..memory.membrane import get_kg
        g = get_kg()
        return g.overview(limit) if g else {"nodes": [], "edges": []}


@app.get("/api/persona/{pid}/graph/neighbors")
def graph_neighbors(pid: str, node: str, limit: int = 40):
    with context.use(_p(pid)):
        from ..memory.membrane import get_kg
        g = get_kg()
        return g.neighbors(node, limit) if g else {"nodes": [], "edges": []}


@app.get("/api/persona/{pid}/graph/node")
def graph_node(pid: str, node: str):
    with context.use(_p(pid)):
        from ..memory.membrane import get_kg
        g = get_kg()
        return g.node(node) if g else {}


@app.get("/api/persona/{pid}/graph/search")
def graph_search(pid: str, q: str):
    with context.use(_p(pid)):
        from ..memory.membrane import get_kg
        g = get_kg()
        return {"results": g.search(q) if g else []}


@app.get("/api/persona/{pid}/provenance/{claim_id}")
def provenance(pid: str, claim_id: str):
    """The defensible chain: belief → claim → every supporting source + verbatim quote + DOI/URL."""
    with context.use(_p(pid)):
        from ..memory.membrane import get_kg
        g = get_kg()
        return g.provenance(claim_id) if g else {}


@app.get("/api/persona/{pid}/history/{claim_id}")
def history(pid: str, claim_id: str):
    p = _p(pid)
    return {"series": p.history.series(claim_id)}


@app.get("/api/persona/{pid}/inbox")
def inbox(pid: str):
    p = _p(pid)
    with context.use(p):
        from ..conflict_reviews import conflict_id, summarize_conflict_reviews
        from ..memory.membrane import get_kg
        g = get_kg()
        items = g.candidate_conflicts(limit=50) if g else []
        summaries = summarize_conflict_reviews(p.paths.ops_dir)
        for item in items:
            cid = conflict_id(item["pos_claim"], item["neg_claim"])
            item.update({"conflict_id": cid, "review_summary": summaries.get(cid, {
                "review_count": 0, "latest": None})})
        return {"available": g is not None, "items": items}


def _candidate_match(g, pos_claim: str, neg_claim: str):
    return next((item for item in (g.candidate_conflicts(100) if g else [])
                 if item["pos_claim"] == pos_claim and item["neg_claim"] == neg_claim), None)


@app.get("/api/persona/{pid}/inbox/dossier")
def conflict_dossier(pid: str, pos_claim: str, neg_claim: str):
    """Exact evidence and an honest review contract; reading this never mutates a belief."""
    p = _p(pid)
    with context.use(p):
        from ..conflict_reviews import (conflict_id, read_conflict_reviews,
                                        summarize_conflict_reviews)
        from ..memory.membrane import get_kg
        g = get_kg()
        match = _candidate_match(g, pos_claim, neg_claim)
        if match is None:
            raise HTTPException(status_code=404, detail="candidate conflict not found")
        cid = conflict_id(pos_claim, neg_claim)
        reviews = [review for review in read_conflict_reviews(p.paths.ops_dir)
                   if review["conflict_id"] == cid]
        summaries = summarize_conflict_reviews(p.paths.ops_dir)
        return {
            "conflict_id": cid,
            "subject": match["subject"],
            "object": match["object"],
            "status": "candidate_conflict",
            "scientific_verdict": "unverified",
            "belief_mutated": False,
            "why_raised": {
                "trigger": "same canonical subject/object pair with opposite stored effect signs",
                "what_it_does_not_mean": "This sign collision is not evidence of a true scientific contradiction.",
            },
            "positive": g.provenance(pos_claim),
            "negative": g.provenance(neg_claim),
            "missing_context_fields": ["population or species", "tissue or cell type",
                                       "disease stage", "perturbation and comparator",
                                       "dose and timepoint", "outcome definition", "study design"],
            "next_checks": [
                "Confirm that each stored quote is verbatim and that its relation/sign matches the source sentence.",
                "Extract and compare population, tissue, disease stage, perturbation, dose, timepoint, and outcome.",
                "Check whether the sources are independent, reuse a cohort, or have corrections/retractions.",
                "Only if direction still differs under matched qualifiers, design the cheapest discriminating analysis or experiment.",
            ],
            "review_options": ["extraction_error", "true_refutation", "context_divergence",
                               "insufficient_evidence"],
            "review_summary": summaries.get(cid, {"review_count": 0, "latest": None}),
            "reviews": reviews[-10:],
        }


@app.post("/api/persona/{pid}/inbox/review")
def conflict_review(pid: str, payload: dict):
    """Append a scoped human label. Reviews train/evaluate typing later; they never anchor now."""
    p = _p(pid)
    pos, neg = str(payload.get("pos_claim", "")), str(payload.get("neg_claim", ""))
    with context.use(p):
        from ..conflict_reviews import LedgerIntegrityError, append_conflict_review
        from ..events import log
        from ..memory.membrane import get_kg
        match = _candidate_match(get_kg(), pos, neg)
        if match is None:
            raise HTTPException(status_code=404, detail="candidate conflict not found")
        try:
            record = append_conflict_review(
                p.paths.ops_dir,
                pos_claim_id=pos,
                neg_claim_id=neg,
                verdict=payload.get("verdict"),
                rationale=payload.get("rationale"),
                confidence=payload.get("confidence"),
                qualifier=payload.get("qualifier", ""),
                next_check=payload.get("next_check", ""),
            )
        except LedgerIntegrityError as exc:
            raise HTTPException(status_code=500, detail=f"review ledger integrity failure: {exc}") from exc
        except (TypeError, ValueError) as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        log().emit("control", f"human review recorded for {match['subject']} → {match['object']}: "
                   f"{record['verdict']} (belief unchanged)", actor="human")
        return {"ok": True, "review": record, "belief_mutated": False}


@app.post("/api/persona/{pid}/inbox/resolve")
def inbox_resolve(pid: str, payload: dict):
    return {"ok": False, "reason": "contradiction-typing-not-validated",
            "message": "Review is recorded append-only, but candidate conflicts cannot anchor beliefs until RQ-E02 passes its precision gate."}


@app.post("/api/persona/{pid}/inbox/investigate")
def inbox_investigate(pid: str, payload: dict):
    """Run a bounded session with the exact two candidate claims pinned into its evidence packet."""
    p = _p(pid)
    pos, neg = payload.get("pos_claim"), payload.get("neg_claim")
    with context.use(p):
        from ..memory.membrane import get_kg
        g = get_kg()
        match = _candidate_match(g, pos, neg)
    if match is None:
        return {"ok": False, "reason": "candidate-not-found"}
    daemon = manager()._daemons.get(pid)
    if daemon is None:
        return {"ok": False, "reason": "daemon-not-running"}
    question = (payload.get("question") or
                f"Do the opposite stored signs for {match['subject']} → {match['object']} represent "
                "a true refutation, context divergence, or extraction error?")
    task = daemon.queue.enqueue("investigate", priority=2, params={"question": question,
                                "evidence_claim_ids": [pos, neg]})
    return {"ok": True, "task": task, "evidence_claim_ids": [pos, neg]}


@app.get("/api/persona/{pid}/synthesis")
def synthesis(pid: str):
    """The persona's cited synthesis notes — what it has UNDERSTOOD per subtopic."""
    p = _p(pid)
    nd = p.paths.notes_dir
    notes = []
    if nd.exists():
        for f in sorted(nd.glob("*.md"), key=lambda x: -x.stat().st_mtime):
            first = f.read_text(encoding="utf-8").splitlines()
            title = next((l[2:] for l in first if l.startswith("# ")), f.stem)
            notes.append({"slug": f.stem, "title": title})
    return {"notes": notes}


@app.post("/api/persona/{pid}/deliver")
def deliver(pid: str, payload: dict):
    """Ask a persona to produce a deliverable now: a cited review or a LaTeX->PDF paper on a topic."""
    p = _p(pid)
    d = manager()._daemons.get(pid)
    kind = payload.get("kind", "review")
    topic = payload.get("topic", "")
    if d is None:
        return {"ok": False, "reason": "daemon not running (seed the persona first)"}
    tid = d.queue.enqueue("paper" if kind == "paper" else "review", priority=0,
                          params={"topic": topic})
    return {"ok": True, "queued": kind, "task": tid}


# --------------------------------------------------------------- knowledge transfer (v6 P5)
@app.get("/api/persona/{pid}/topic/digest")
def topic_digest_read(pid: str, q: str):
    """Read the evidence bundle for a topic without invoking a model or spending budget."""
    p = _p(pid)
    with context.use(p):
        from ..memory.membrane import get_kg
        from ..agents.knowledge import topic_digest as _td
        return _td(q, get_kg(), p.history)


@app.post("/api/persona/{pid}/topic/digest")
def topic_digest_generate(pid: str, payload: dict):
    """Explicitly spend budget to generate a cited briefing from the topic evidence bundle."""
    q = payload.get("q")
    if not isinstance(q, str) or not q.strip() or len(q) > 500:
        return {"ok": False, "reason": "invalid-topic"}
    p = _p(pid)
    with context.use(p):
        from ..memory.membrane import get_kg
        from ..agents.knowledge import topic_digest as _td
        return _td(q.strip(), get_kg(), p.history, generate=True)


@app.get("/api/persona/{pid}/topic/evolution")
def topic_evolution(pid: str, q: str):
    """How belief/consensus on a topic moved over time (per-claim confidence + support series)."""
    p = _p(pid)
    with context.use(p):
        from ..memory.membrane import get_kg
        g = get_kg()
        if g is None:
            return {"series": []}
        ents = [n["label"] for n in g.search(q, 25) if n["type"] == "entity"]
        claims = g.claims_about(ents, 12) if ents else []
        out = []
        for c in claims:
            s = p.history.series(c["claim_id"])
            if len(s) >= 2:
                out.append({"claim_id": c["claim_id"],
                            "text": f"{c['subject']} [{c['effect_sign']}] {c['object']}", "series": s})
        return {"topic": q, "series": out}


@app.get("/api/persona/{pid}/graph/subgraph")
def graph_subgraph(pid: str, q: str):
    with context.use(_p(pid)):
        from ..memory.membrane import get_kg
        g = get_kg()
        if g is None:
            return {"nodes": [], "edges": []}
        ents = [n["label"] for n in g.search(q, 40) if n["type"] == "entity"]
        return g.subgraph(ents)


@app.post("/api/persona/{pid}/science")
def science_ep(pid: str, payload: dict):
    """Query a scientific database directly (Open Targets / UniProt / NCBI-GEO / PubChem / trials)."""
    _p(pid)
    from ..tools import science
    return science.call(payload.get("api", ""), payload.get("params", {}) or {})


@app.post("/api/persona/{pid}/goal")
@app.post("/api/persona/{pid}/investigate")
def goal(pid: str, payload: dict):
    """Directed mode: hand the persona a real question. It opens a persistent multistep INVESTIGATION
    — a team of agents (gather → harvest → synthesize → analyze → prove → write → critique → finalize)
    tracked as a folder of documents — as high-priority work, without rewriting its durable self."""
    p = _p(pid)
    d = manager()._daemons.get(pid)
    g = (payload.get("goal") or payload.get("question") or payload.get("text") or "").strip()
    if not g:
        return {"ok": False, "reason": "empty"}
    if d is None:
        return {"ok": False, "reason": "daemon not running (seed/resume the persona)"}
    with context.use(p):
        from ..events import log
        from ..research.investigation import Investigation
        log().emit("say", f"[investigate] {g}", actor="human")
        inv = Investigation.create(g, specialization="human-requested")
        inv.launch(d.queue)
    return {"ok": True, "slug": inv.slug, "steps": len(inv.meta.get("steps", [])), "question": g}


@app.post("/api/persona/{pid}/mywork")
async def mywork(pid: str, file: UploadFile = File(...), kind: str = "draft"):
    """Upload YOUR paper/draft/notes -> the persona extracts your claims and cross-checks each against
    everything it has read (what supports it, what contradicts it, with quotes+DOIs)."""
    p = _p(pid)
    up = p.paths.uploads_dir
    up.mkdir(parents=True, exist_ok=True)
    name = "".join(c for c in (file.filename or "doc") if c.isalnum() or c in "._- ")[:120] or "doc"
    (up / name).write_bytes(await file.read())
    with context.use(p):
        from ..memory.membrane import get_kg
        from ..agents.mywork import ingest
        return ingest(f"uploads/{name}", kind, get_kg())


@app.post("/api/persona/{pid}/ask")
def ask(pid: str, payload: dict):
    """Ask the persona's knowledge graph a question in plain English — answered with citations."""
    p = _p(pid)
    q = (payload.get("q") or payload.get("question") or "").strip()
    if not q:
        return {"ok": False, "reason": "empty"}
    with context.use(p):
        from ..memory.membrane import get_kg
        from ..agents.knowledge import ask_graph
        return ask_graph(q, get_kg())


# --------------------------------------------------------------- builders + free mind (v6 P4)
@app.post("/api/persona/{pid}/build")
def build_ep(pid: str, payload: dict):
    """Ask the persona to build a real artifact now: a diagram, generative art, an interactive page,
    or a small code tool — grounded in its knowledge, browsable in files/deliverables when done."""
    p = _p(pid)
    d = manager()._daemons.get(pid)
    kind = (payload.get("kind") or "diagram").strip()
    topic = (payload.get("topic") or "").strip()
    if not topic:
        return {"ok": False, "reason": "empty topic"}
    if kind not in ("diagram", "art", "page", "code"):
        return {"ok": False, "reason": f"unknown kind {kind}"}
    if d is None:
        return {"ok": False, "reason": "daemon not running (seed/resume the persona)"}
    tid = d.queue.enqueue("build", priority=3, params={"kind": kind, "topic": topic})
    return {"ok": True, "queued": kind, "task": tid}


@app.post("/api/persona/{pid}/freemove")
def freemove_ep(pid: str):
    """Let the persona choose its own next move (the free mind), one step, budget-gated."""
    d = manager()._daemons.get(pid)
    if d is None:
        return {"ok": False, "reason": "daemon not running (seed/resume the persona)"}
    tid = d.queue.enqueue("free_move", priority=2)
    return {"ok": True, "task": tid}


@app.get("/api/persona/{pid}/fieldmap")
def fieldmap(pid: str):
    """A navigable map through the field: subtopics → beliefs → contradictions → open-questions → papers."""
    p = _p(pid)
    with context.use(p):
        from ..memory.membrane import get_kg
        from ..synthesis import fieldmap as fm
        g = get_kg()
        if g is None:
            return {"n_subtopics": 0, "subtopics": []}
        return fm.build(g, p.paths.notes_dir)


@app.get("/api/persona/{pid}/note/{slug}")
def note(pid: str, slug: str):
    if "/" in slug or "\\" in slug:
        raise HTTPException(400, "bad slug")
    f = _p(pid).paths.notes_dir / f"{slug}.md"
    if not f.exists():
        raise HTTPException(404, "not found")
    return {"slug": slug, "content": f.read_text(encoding="utf-8")}


# --------------------------------------------------------------- conversation / steer (v6 P2)
@app.post("/api/persona/{pid}/say")
def say(pid: str, payload: dict):
    """Talk to the persona while it works. It replies (grounded in its self+graph), remembers a
    standing directive if you steer it, and starts reading any topics you point it at — without
    stopping. Runs synchronously so it replies immediately in any run-state."""
    p = _p(pid)
    text = (payload.get("text") or "").strip()
    if not text:
        return {"ok": False, "reason": "empty"}
    with context.use(p):
        from ..events import log
        from ..memory.membrane import get_kg
        from ..agents.converse import converse
        log().emit("say", text, actor="human")
        res = converse(text, get_kg())
    if res.get("ok") and res.get("focus_now"):     # act on steering: priority reads, but keep working
        q = p.queue()
        for topic in res["focus_now"]:
            q.enqueue("scout", priority=1, params={"interest": topic})
    return res


# --------------------------------------------------------------- paper-centric idea graph
@app.get("/api/persona/{pid}/paper/{slug}")
def paper_dossier(pid: str, slug: str):
    """A read paper as an idea node: its metadata, abstract, main points (extracted claims), and the
    supports/contradictions those claims participate in across the rest of the literature (with DOIs).
    Read-only; never mutates a belief."""
    p = _p(pid)
    try:
        sdir = p.paths.safe(f"sources/{slug}")
    except ValueError:
        raise HTTPException(400, "bad slug")
    meta_f = sdir / "meta.json"
    if not meta_f.is_file():
        raise HTTPException(404, "paper not found")
    try:
        meta = json.loads(meta_f.read_text(encoding="utf-8"))
    except Exception:
        meta = {}
    abstract = ""
    if (sdir / "clean.md").is_file():
        abstract = (sdir / "clean.md").read_text(encoding="utf-8", errors="replace")[:6000]
    claims = []
    if (sdir / "claims.jsonl").is_file():
        for line in (sdir / "claims.jsonl").read_text(encoding="utf-8", errors="replace").splitlines():
            try:
                claims.append(json.loads(line))
            except Exception:
                pass
    own = {c.get("claim_id") for c in claims}
    supports, contradictions, seen_s, seen_c = [], [], set(), set()
    with context.use(p):
        from ..memory.membrane import get_kg
        g = get_kg()
        if g is not None:
            for c in claims:
                try:
                    cc = g.crosscheck(c.get("subject", ""), c.get("object", ""), c.get("effect_sign", "na"))
                except Exception:
                    continue
                about = f"{c.get('subject','')} → {c.get('object','')}"
                for s in cc.get("support", []):
                    cid = s.get("claim_id")
                    if cid and cid not in own and cid not in seen_s:
                        seen_s.add(cid); supports.append({**s, "about": about})
                for s in cc.get("contradict", []):
                    cid = s.get("claim_id")
                    if cid and cid not in seen_c:
                        seen_c.add(cid); contradictions.append({**s, "about": about})
    main_points = [{"claim_id": c.get("claim_id"),
                    "text": f"{c.get('subject','')} [{c.get('effect_sign','na')}] {c.get('object','')}",
                    "quote": c.get("quote", ""), "confidence": c.get("confidence")} for c in claims]
    return {"ok": True, "slug": slug, "title": meta.get("title"), "doi": meta.get("doi"),
            "year": meta.get("year"), "authors": meta.get("authors", []),
            "affiliations": meta.get("affiliations", []), "url": meta.get("url"),
            "venue": meta.get("venue"), "abstract": abstract, "main_points": main_points,
            "supports": supports[:30], "contradictions": contradictions[:30]}


# --------------------------------------------------------------- file & artifact browser (v6 P1)
_TEXT_EXT = {".py", ".md", ".txt", ".json", ".jsonl", ".csv", ".tsv", ".tex", ".log", ".yaml",
             ".yml", ".toml", ".ini", ".cfg", ".ipynb", ".r", ".sh", ".js", ".ts", ".html", ".css"}


@app.get("/api/persona/{pid}/files")
def files(pid: str):
    """The persona's workspace as a jailed recursive tree (dirs + files, sizes) — so every
    experiment, script, figure, dataset, and compiled deliverable it made is browsable. Investigation
    folders are labelled with their question; over-large dirs (e.g. 600+ sources) are capped per
    directory so the document folders are never starved by the raw read-paper pile."""
    import json as _json
    p = _p(pid)
    root = p.paths.workspace.resolve()
    budget = [6000]
    PER_DIR = 300                       # cap children per directory; surface the remainder as a count
    # document-first ordering: the folders a scientist reads come first; raw sources last
    ORDER = {"investigations": 0, "deliverables": 1, "notes": 2, "drafts": 3, "self": 4,
             "projects": 5, "datasets": 6, "runs": 7, "uploads": 8, "sources": 9}

    def _label(e):
        if e.parent.name == "investigations":            # annotate an investigation folder
            try:
                m = _json.loads((e / "investigation.json").read_text(encoding="utf-8"))
                st = m.get("status", "")
                return f"{m.get('question', '')[:80]}" + (f" · {st}" if st else "")
            except Exception:
                return None
        return None

    def walk(d, depth):
        out = []
        try:
            entries = list(d.iterdir())
        except Exception:
            return out
        if depth == 0:
            entries.sort(key=lambda x: (ORDER.get(x.name, 50), x.name.lower()))
        else:
            entries.sort(key=lambda x: (x.is_file(), x.name.lower()))
        shown = 0
        for e in entries:
            if e.name.startswith(".") or budget[0] <= 0:
                continue
            if shown >= PER_DIR:
                out.append({"name": f"… {len(entries) - shown} more", "type": "more",
                            "count": len(entries) - shown})
                break
            shown += 1
            budget[0] -= 1
            rel = str(e.relative_to(root)).replace("\\", "/")
            if e.is_dir():
                node = {"name": e.name, "path": rel, "type": "dir",
                        "children": walk(e, depth + 1) if depth < 7 else []}
                lab = _label(e)
                if lab:
                    node["label"] = lab
                out.append(node)
            else:
                try:
                    sz = e.stat().st_size
                except Exception:
                    sz = 0
                out.append({"name": e.name, "path": rel, "type": "file",
                            "ext": e.suffix.lower().lstrip("."), "size": sz})
        return out

    return {"root": p.name, "tree": walk(root, 0)}


@app.get("/api/persona/{pid}/file")
def get_file(pid: str, path: str):
    """Serve ONE workspace file inline with the right media type — PDF, code, image, CSV, md.
    Path-jailed to the persona workspace (traversal/symlink escape -> 400)."""
    p = _p(pid)
    try:
        target = p.paths.safe(path)
    except ValueError:
        raise HTTPException(400, "bad path")
    if not target.exists() or not target.is_file():
        raise HTTPException(404, "not found")
    mt = mimetypes.guess_type(str(target))[0]
    if target.suffix.lower() in _TEXT_EXT:      # show code/notes in-browser, don't force download
        mt = "text/plain; charset=utf-8"
    return FileResponse(str(target), media_type=(mt or "application/octet-stream"))  # inline (no filename)


# --------------------------------------------------------- LaTeX: editable / recompilable deliverables
def _iso():
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _find_deliverable_project(p, deliverable: str):
    """Map a deliverable PDF name back to its project dir + receipt via each project's compile.json."""
    pj = p.paths.projects_dir
    if not pj.exists():
        return None
    for cj in pj.glob("*/*/compile.json"):
        try:
            rec = json.loads(cj.read_text(encoding="utf-8"))
        except Exception:
            continue
        if (rec.get("deliverable") or {}).get("path") == deliverable:
            return cj.parent, rec
    return None


@app.get("/api/persona/{pid}/deliverable/source")
def deliverable_source(pid: str, deliverable: str):
    """Fetch the editable LaTeX source (+ figure list + compile receipt) behind a compiled paper PDF."""
    p = _p(pid)
    found = _find_deliverable_project(p, deliverable)
    if found is None:
        raise HTTPException(404, "no editable source for this deliverable")
    proj, rec = found
    tex = proj / "main.tex"
    if not tex.is_file():
        raise HTTPException(404, "source missing")
    figs = sorted({f.name for f in proj.glob("*.png")} | {f.name for f in proj.glob("results/*.png")})
    ws = p.paths.workspace
    return {"ok": True,
            "rel_tex": str(tex.relative_to(ws)).replace("\\", "/"),
            "rel_pdf": str((proj / "main.pdf").relative_to(ws)).replace("\\", "/"),
            "tex": tex.read_text(encoding="utf-8", errors="replace"),
            "figures": figs, "deliverable": deliverable, "compile": rec}


@app.post("/api/persona/{pid}/recompile")
def recompile(pid: str, payload: dict):
    """Deterministically (re)compile edited or brand-new LaTeX — NO model call. Reuses the offline,
    read-only sandbox compiler; on success copies a hash-versioned PDF to deliverables/ for export."""
    import shutil
    import uuid as _uuid
    from ..tools import sandbox
    p = _p(pid)
    src = str(payload.get("source_tex") or "")
    if not src.strip():
        raise HTTPException(422, "empty source")
    if len(src) > 400_000:
        raise HTTPException(413, "source too large")
    if not sandbox.image_ready():
        return {"ok": False, "reason": "sandbox-image-missing"}
    if payload.get("new"):
        slug = "".join(c for c in str(payload.get("slug") or "document").lower()
                       if c.isalnum() or c == "-").strip("-")[:50] or "document"
        proj = p.paths.projects_dir / f"latex-{slug}" / _uuid.uuid4().hex[:8]
        proj.mkdir(parents=True, exist_ok=True)
    else:
        try:
            tex_path = p.paths.safe(str(payload.get("rel_tex") or ""))
        except ValueError:
            raise HTTPException(400, "bad path")
        if tex_path.name != "main.tex" or "projects" not in tex_path.parts:
            raise HTTPException(400, "recompile targets a project main.tex")
        proj = tex_path.parent
        proj.mkdir(parents=True, exist_ok=True)
    (proj / "main.tex").write_text(src, encoding="utf-8")
    r = sandbox.compile_latex(proj, "main.tex")
    if not r["ok"]:
        return {"ok": False, "log": r.get("log", ""), "exit_code": r.get("exit_code")}
    p.paths.deliverables_dir.mkdir(parents=True, exist_ok=True)
    dst = p.paths.deliverables_dir / f"{proj.parent.name}-{r['source_sha256'][:10]}.pdf"
    shutil.copy2(proj / "main.pdf", dst)
    rec = {"topic": proj.parent.name, "recompiled_at": _iso(), "ok": True,
           "source_sha256": r["source_sha256"], "pdf_sha256": r["pdf_sha256"],
           "sandbox_image_digest": r.get("image_digest"),
           "deliverable": {"path": dst.name, "bytes": dst.stat().st_size, "pdf_sha256": r["pdf_sha256"]}}
    (proj / "compile.json").write_text(json.dumps(rec, indent=2), encoding="utf-8")
    with context.use(p):
        from ..events import log
        log().emit("artifact", f"recompiled a document → {dst.name}", actor="human", file=dst.name)
    return {"ok": True, "deliverable": dst.name,
            "rel_pdf": str((proj / "main.pdf").relative_to(p.paths.workspace)).replace("\\", "/"),
            "pdf_sha256": r["pdf_sha256"], "source_sha256": r["source_sha256"]}


@app.get("/api/persona/{pid}/deliverable/bundle")
def deliverable_bundle(pid: str, deliverable: str):
    """Export tex + figures + pdf as a single zip for collaboration."""
    import io
    import zipfile
    p = _p(pid)
    found = _find_deliverable_project(p, deliverable)
    if found is None:
        raise HTTPException(404, "no source for this deliverable")
    proj, _rec = found
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for f in proj.glob("*"):
            if f.is_file() and f.suffix.lower() in (".tex", ".pdf", ".png", ".json", ".bib"):
                z.write(f, f.name)
        for f in proj.glob("results/*.png"):
            z.write(f, f"figures/{f.name}")
    buf.seek(0)
    stem = deliverable.rsplit(".", 1)[0]
    return StreamingResponse(buf, media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{stem}.zip"'})


# --------------------------------------------------------- documents (md|tex -> real compiled PDF)
def _doc_compile(p, source: str, fmt: str, slug: str, title: str, *, extra_dir: Path = None) -> dict:
    """Compile a document source to a hash-addressed PDF (cached), copy to deliverables/. LLM-free."""
    import hashlib
    import shutil
    from ..deliverables import document
    from ..tools import sandbox
    if not sandbox.image_ready():
        return {"ok": False, "reason": "sandbox-image-missing"}
    h = hashlib.sha256((fmt + "\x00" + title + "\x00" + source).encode("utf-8")).hexdigest()[:12]
    project = p.paths.projects_dir / f"doc-{document.slug_for(slug)}" / h
    pdf = project / "main.pdf"
    if not pdf.is_file():                       # cache: identical source+title+fmt -> same PDF
        if extra_dir and extra_dir.is_dir():    # bring along sibling figures (name.png)
            project.mkdir(parents=True, exist_ok=True)
            for f in extra_dir.glob("*.png"):
                shutil.copy2(f, project / f.name)
            for f in extra_dir.glob("results/*.png"):
                shutil.copy2(f, project / f.name)
        r = document.compile_source(source, fmt, project, title=title)
        if not r["ok"]:
            return {"ok": False, "log": r.get("log", ""), "exit_code": r.get("exit_code")}
        p.paths.deliverables_dir.mkdir(parents=True, exist_ok=True)
        dst = p.paths.deliverables_dir / f"{project.parent.name}-{r['source_sha256'][:10]}.pdf"
        shutil.copy2(pdf, dst)
        (project / "compile.json").write_text(json.dumps(
            {"topic": project.parent.name, "at": _iso(), "ok": True, "format": fmt,
             "source_sha256": r["source_sha256"], "pdf_sha256": r["pdf_sha256"],
             "deliverable": {"path": dst.name, "bytes": dst.stat().st_size, "pdf_sha256": r["pdf_sha256"]}},
            indent=2), encoding="utf-8")
    rel = lambda x: str(x.relative_to(p.paths.workspace)).replace("\\", "/")
    return {"ok": True, "rel_pdf": rel(pdf), "rel_tex": rel(project / "main.tex")}


@app.post("/api/persona/{pid}/document/compile")
def document_compile(pid: str, payload: dict):
    """Compile a markdown or LaTeX source to a real PDF (previewable + downloadable). No model call."""
    p = _p(pid)
    source = str(payload.get("source") or "")
    if not source.strip():
        raise HTTPException(422, "empty source")
    if len(source) > 500_000:
        raise HTTPException(413, "source too large")
    fmt = "tex" if str(payload.get("format")) == "tex" else "md"
    title = str(payload.get("title") or "Document")[:160]
    slug = str(payload.get("slug") or title)
    with context.use(p):
        return _doc_compile(p, source, fmt, slug, title)


@app.get("/api/persona/{pid}/document")
def document_view(pid: str, path: str):
    """Return a note/draft/report as a document: its source + a compiled PDF (cached). md or tex."""
    p = _p(pid)
    try:
        target = p.paths.safe(path)
    except ValueError:
        raise HTTPException(400, "bad path")
    if not target.is_file():
        raise HTTPException(404, "not found")
    ext = target.suffix.lower()
    fmt = "tex" if ext == ".tex" else "md" if ext in (".md", ".txt") else None
    if fmt is None:
        raise HTTPException(400, "not a document")
    source = target.read_text(encoding="utf-8", errors="replace")
    m = re.search(r"^#\s+(.+)$", source, re.M)
    title = (m.group(1).strip() if m else target.stem.replace("-", " "))[:160]
    with context.use(p):
        r = _doc_compile(p, source, fmt, target.stem, title, extra_dir=target.parent)
    r.update({"source": source, "format": fmt, "title": title, "path": path})
    return r


@app.post("/api/persona/{pid}/upload")
async def upload(pid: str, file: UploadFile = File(...)):
    """Upload a file into the persona's workspace (uploads/). P5 reads these into the 'my work' corpus."""
    p = _p(pid)
    up = p.paths.uploads_dir
    up.mkdir(parents=True, exist_ok=True)
    name = "".join(c for c in (file.filename or "upload.bin") if c.isalnum() or c in "._- ")[:120]
    dest = up / (name or "upload.bin")
    data = await file.read()
    dest.write_bytes(data)
    return {"ok": True, "path": f"uploads/{dest.name}", "bytes": len(data)}


@app.get("/api/persona/{pid}/workspace")
def workspace(pid: str):
    p = _p(pid)
    pa = p.paths
    drafts = sorted(x.name for x in pa.drafts_dir.glob("*.md")) if pa.drafts_dir.exists() else []
    deliv = sorted(x.name for x in pa.deliverables_dir.glob("*")) if pa.deliverables_dir.exists() else []
    projects = sorted(x.name for x in pa.projects_dir.glob("*") if x.is_dir()) if pa.projects_dir.exists() else []
    n_sources = len(list(pa.sources_dir.glob("*/meta.json"))) if pa.sources_dir.exists() else 0
    with context.use(p):
        return {"self": selfmind.read_self(), "drafts": drafts, "deliverables": deliv,
                "projects": projects, "n_sources": n_sources}


@app.get("/api/persona/{pid}/draft/{name}")
def draft(pid: str, name: str):
    if "/" in name or "\\" in name or not name.endswith(".md"):
        raise HTTPException(400, "bad name")
    p = _p(pid)
    f = p.paths.drafts_dir / name
    if not f.exists():
        f = p.paths.deliverables_dir / name
    if not f.exists():
        raise HTTPException(404, "not found")
    return {"name": name, "content": f.read_text(encoding="utf-8")}


@app.post("/api/persona/{pid}/read_url")
def read_url(pid: str, payload: dict):
    p = _p(pid)
    d = manager()._daemons.get(pid)
    if d is None:
        return {"ok": False, "reason": "daemon not running"}
    tid = d.queue.enqueue("read_url", priority=2,
                          params={"url": payload["url"], "interest": payload.get("interest", "web")})
    return {"ok": True, "task": tid}


@app.get("/api/persona/{pid}/stream")
async def stream(pid: str):
    p = _p(pid)

    async def gen():
        with context.use(p):
            from ..events import log
            seen = max(0, log().latest_id() - 80)
            while True:
                evs = log().since(seen)
                if evs:
                    for e in evs:
                        yield f"data: {json.dumps(e)}\n\n"
                    seen = evs[-1]["id"]
                else:
                    yield ": keepalive\n\n"
                await asyncio.sleep(0.4)
    return StreamingResponse(gen(), media_type="text/event-stream")


@app.get("/")
def root():
    idx = _STATIC / "index.html"
    return FileResponse(str(idx)) if idx.exists() else {"service": "Persona v5", "hint": "UI missing"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8137)
