"""FastAPI app serving the Researcher's mind to the UI (the seven screens, BUILD_PLAN §6).

Run: uvicorn persona.api.app:app --port 8000   (or: python -m persona.api.app)

v3 Tier 3 (make it a service):
- Live Europe PMC by default; PERSONA_OFFLINE=1 uses test fixtures (explicit opt-in).
- Shared-token auth on mutating endpoints (PERSONA_API_TOKEN; unset -> open for local dev).
- State lives on app.state (a PersonaService), not module globals.
- Real always-on daemon: a startup background task ticks autonomous_cycle on a cadence; its
  running state is persisted (a flag file) so it resumes across restarts.
- Lean in-house observability: per-run traces (tokens/cost/escalations) at /api/traces.
- Swarm Control Room works offline (heuristic extractor) when no API key is present.
"""
from __future__ import annotations

import asyncio
import json
import os
import time
from collections import deque
from pathlib import Path

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles

from .. import config
from ..researcher import Researcher
from ..engine import ExperimentCandidate
from ..ingest import EuropePMCAdapter
from ..ingest.base import DiskCache

_ROOT = Path(__file__).resolve().parent.parent.parent
FIXTURES = str(_ROOT / "tests" / "fixtures" / "ingest")


def _flag(name: str) -> bool:
    return os.environ.get(name, "").strip().lower() in ("1", "true", "yes", "on")


OFFLINE = _flag("PERSONA_OFFLINE")
API_TOKEN = os.environ.get("PERSONA_API_TOKEN") or None       # None -> open (local dev)
AUTONOMOUS = _flag("PERSONA_AUTONOMOUS")
TICK_SECONDS = float(os.environ.get("PERSONA_TICK_SECONDS", "900"))
SEED_INTERESTS = [s.strip() for s in os.environ.get(
    "PERSONA_SEED_INTERESTS", "neuroinflammation,microglia,tau").split(",") if s.strip()]


class PersonaService:
    """All mutable state for one running Persona — off module globals so it's testable and
    could be instantiated per-tenant later."""

    def __init__(self):
        cache = DiskCache(FIXTURES) if OFFLINE else DiskCache(str(_ROOT / ".cache" / "api"))
        self.r = Researcher(root="runs/api_self", name="Ada", seed_interests=SEED_INTERESTS,
                            adapter=EuropePMCAdapter(cache=cache))
        self.events: deque = deque(maxlen=3000)       # live swarm control-room events
        self.traces: deque = deque(maxlen=500)        # observability: per-run token/cost traces
        self.swarm_running = False
        self.daemon_running = False
        self.daemon_task = None
        self._daemon_flag = Path(self.r.me.root) / "daemon.on"
        self._trace_log = Path(self.r.me.root) / "traces.jsonl"
        self._seed_if_empty()

    def _seed_if_empty(self):
        if not self.r.beliefs():
            try:
                for _ in range(3):            # agenda-driven ticks (no hardcoded query) so the
                    self.r.tick()             # trajectory screen has real history to show
            except Exception:
                pass

    def trace(self, kind: str, data: dict):
        rec = {"ts": time.time(), "kind": kind, **data}
        self.traces.append(rec)
        try:
            with self._trace_log.open("a", encoding="utf-8") as f:
                f.write(json.dumps(rec) + "\n")
        except Exception:
            pass

    async def run_swarm(self, limit: int) -> dict:
        if self.swarm_running:
            return {"status": "already running"}
        self.swarm_running = True
        self.events.append({"type": "run_start", "t": time.time()})
        offline = not config.have_key()      # aread auto-degrades to the heuristic reader offline
        try:
            summary = await self.r.aread(
                limit=limit, on_event=lambda e: self.events.append({**e, "t": time.time()}))
            payload = {k: summary[k] for k in ("read", "committed", "held", "contradictions",
                                               "spent_usd") if k in summary}
            self.events.append({"type": "run_done", "t": time.time(), **payload})
            self.trace("swarm", {"limit": limit, "offline": offline, **payload,
                                 "spent_today_usd": summary.get("spent_today_usd"),
                                 "escalations": summary.get("escalations")})
            return {"status": "ok", **payload}
        except Exception as e:
            self.events.append({"type": "run_error", "t": time.time(), "error": str(e)[:200]})
            return {"status": "error", "error": str(e)[:200]}
        finally:
            self.swarm_running = False

    async def daemon_loop(self):
        while self.daemon_running:
            try:
                summary = await self.r.autonomous_cycle(
                    on_event=lambda e: self.events.append({**e, "t": time.time()}))
                self.trace("cycle", {k: summary.get(k) for k in
                                     ("read", "committed", "contradictions", "acted_on")})
            except Exception as e:
                self.trace("cycle_error", {"error": str(e)[:200]})
            await asyncio.sleep(TICK_SECONDS)

    def start_daemon(self) -> bool:
        if self.daemon_running:
            return False
        self.daemon_running = True
        self._daemon_flag.write_text("on", encoding="utf-8")
        self.daemon_task = asyncio.create_task(self.daemon_loop())
        return True

    def stop_daemon(self) -> bool:
        was = self.daemon_running
        self.daemon_running = False
        try:
            self._daemon_flag.unlink(missing_ok=True)
        except Exception:
            pass
        return was

    def daemon_persisted_on(self) -> bool:
        return self._daemon_flag.exists()


app = FastAPI(title="Persona", version="0.0.1")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


def svc() -> PersonaService:
    if getattr(app.state, "svc", None) is None:
        app.state.svc = PersonaService()
    return app.state.svc


def require_token(x_persona_token: str | None = Header(default=None)):
    """Auth guard for mutating endpoints. Open when PERSONA_API_TOKEN is unset (local dev)."""
    if API_TOKEN and x_persona_token != API_TOKEN:
        raise HTTPException(status_code=401, detail="invalid or missing X-Persona-Token")


@app.on_event("startup")
async def _startup():
    s = svc()
    if AUTONOMOUS or s.daemon_persisted_on():      # resume a persisted always-on state
        s.start_daemon()


# --------------------------------------------------------------------- reads (GET)
@app.get("/api/dashboard")
def dashboard():
    return svc().r.dashboard()


@app.get("/api/notebook")
def notebook(n: int = 60):
    return {"lines": svc().r.notebook(n)}


@app.get("/api/beliefs")
def beliefs():
    return {"beliefs": svc().r.beliefs()}


@app.get("/api/argument/{claim_id}")
def argument(claim_id: str):
    return svc().r.argument_state(claim_id)


@app.get("/api/dependency")
def dependency():
    return svc().r.dependency_graph()


@app.get("/api/idea-graph")
def idea_graph():
    return svc().r.idea_graph()


@app.get("/api/graph-at")
def graph_at(ts: str | None = None):
    """Bi-temporal view: the belief-graph as it existed at `ts` (default: latest change-point)."""
    return svc().r.graph_as_of(ts)


@app.get("/api/experiments")
def experiments():
    r = svc().r
    cands = [ExperimentCandidate(exp_id=b["claim_id"], question=f"Resolve: {b['statement'][:80]}",
                                 target_claim_id=b["claim_id"],
                                 resolution_type=("existing-data" if b["independent_sources"] >= 2
                                                  else "cheap-assay"))
             for b in r.beliefs()]
    return {"queue": r.experiment_queue(cands)}


@app.get("/api/handoffs")
def handoffs():
    return {"handoffs": svc().r.handoffs()}


@app.get("/api/artifacts")
def artifacts():
    return svc().r.artifacts()


@app.get("/api/review")
def review():
    return {"review": svc().r.review_queue()}


@app.get("/api/traces")
def traces(n: int = 100):
    """Observability: recent per-run traces (tokens/cost/escalations, cycle outcomes)."""
    s = svc()
    return {"traces": list(s.traces)[-n:], "daemon_running": s.daemon_running}


@app.get("/api/daemon/status")
def daemon_status():
    s = svc()
    return {"running": s.daemon_running, "persisted_on": s.daemon_persisted_on(),
            "tick_seconds": TICK_SECONDS, "autonomous_env": AUTONOMOUS}


# --------------------------------------------------------------------- writes (POST, auth-gated)
@app.post("/api/tick", dependencies=[Depends(require_token)])
def tick():
    return svc().r.tick()


@app.post("/api/selftest/{claim_key}", dependencies=[Depends(require_token)])
def selftest(claim_key: str):
    return svc().r.self_test(claim_key)


@app.post("/api/selftest/{claim_key}/resolve", dependencies=[Depends(require_token)])
def selftest_resolve(claim_key: str, payload: dict):
    return svc().r.resolve_self_test(claim_key, bool(payload.get("human_ok", True)),
                                     int(payload.get("truth", 1)))


@app.post("/api/resolve", dependencies=[Depends(require_token)])
def resolve(payload: dict):
    return svc().r.resolve_handoff(payload["claim_key"], payload.get("explanation", ""),
                                   int(payload.get("truth", 1)))


@app.post("/api/swarm/run", dependencies=[Depends(require_token)])
async def swarm_run(limit: int = 10):
    """Kick off a swarm read (real Claude, or heuristic offline); events stream on /api/stream/swarm."""
    s = svc()
    if s.swarm_running:
        return {"status": "already running"}
    asyncio.create_task(s.run_swarm(limit))
    return {"status": "started", "limit": limit, "offline": not config.have_key()}


@app.post("/api/daemon/start", dependencies=[Depends(require_token)])
def daemon_start():
    return {"started": svc().start_daemon(), "tick_seconds": TICK_SECONDS}


@app.post("/api/daemon/stop", dependencies=[Depends(require_token)])
def daemon_stop():
    return {"stopped": svc().stop_daemon()}


# --------------------------------------------------------------------- streams (SSE)
@app.get("/api/stream/swarm")
async def stream_swarm():
    s = svc()

    async def gen():
        seen = 0
        while True:
            n = len(s.events)
            if n > seen:
                for e in list(s.events)[seen:]:
                    yield f"data: {json.dumps(e)}\n\n"
                seen = n
            else:
                yield ": keepalive\n\n"
            await asyncio.sleep(0.4)
    return StreamingResponse(gen(), media_type="text/event-stream")


@app.get("/api/stream/notebook")
async def stream_notebook():
    s = svc()

    async def gen():
        seen = 0
        while True:
            lines = s.r.notebook(500)
            if len(lines) > seen:
                for ln in lines[seen:]:
                    yield f"data: {json.dumps(ln)}\n\n"
                seen = len(lines)
            await asyncio.sleep(1.0)
    return StreamingResponse(gen(), media_type="text/event-stream")


# Serve the built UI at "/" so the app opens at a single URL (fixes GET / -> 404).
# Mounted LAST so /api/* routes take precedence; the mount catches everything else.
_DIST = _ROOT / "ui" / "dist"
if _DIST.exists():
    app.mount("/", StaticFiles(directory=str(_DIST), html=True), name="ui")
else:
    @app.get("/")
    def _root():
        return {"service": "Persona API",
                "hint": "UI not built. Run `cd ui && npm run build` to serve it here, "
                        "or `npm run dev` for the dev server. API is under /api/*.",
                "openapi": "/docs"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
