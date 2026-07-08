"""FastAPI app serving the Researcher's mind to the UI (the seven screens, BUILD_PLAN §6).

Run: uvicorn persona.api.app:app --port 8000   (or: python -m persona.api.app)
The UI (Vite dev server) proxies /api to here; CORS is open for localhost dev.
"""
from __future__ import annotations

import asyncio
import json
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from ..researcher import Researcher
from ..engine import ExperimentCandidate
from ..ingest import EuropePMCAdapter
from ..ingest.base import DiskCache

CACHED_QUERY = "neuroinflammation AND alzheimer AND microglia"
FIXTURES = str(Path(__file__).resolve().parent.parent.parent / "tests" / "fixtures" / "ingest")

app = FastAPI(title="Persona", version="0.0.1")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# single persistent researcher (the Self is durable on disk)
_R: Researcher | None = None


def researcher() -> Researcher:
    global _R
    if _R is None:
        _R = Researcher(root="runs/api_self", name="Ada",
                        seed_interests=["neuroinflammation", "microglia", "tau"],
                        adapter=EuropePMCAdapter(cache=DiskCache(FIXTURES)))
        if not _R.beliefs():                 # seed a few ticks so beliefs accrue history
            try:
                for _ in range(3):           # -> non-trivial trajectories on the argument screen
                    _R.tick(queries=[CACHED_QUERY])
            except Exception:
                pass
    return _R


@app.get("/api/dashboard")
def dashboard():
    return researcher().dashboard()


@app.get("/api/notebook")
def notebook(n: int = 60):
    return {"lines": researcher().notebook(n)}


@app.get("/api/beliefs")
def beliefs():
    return {"beliefs": researcher().beliefs()}


@app.get("/api/argument/{claim_id}")
def argument(claim_id: str):
    return researcher().argument_state(claim_id)


@app.get("/api/dependency")
def dependency():
    return researcher().dependency_graph()


@app.get("/api/experiments")
def experiments():
    r = researcher()
    # synthesize candidate experiments from the current beliefs (each belief = a question)
    cands = [ExperimentCandidate(exp_id=b["claim_id"], question=f"Resolve: {b['statement'][:80]}",
                                 target_claim_id=b["claim_id"],
                                 resolution_type=("existing-data" if b["independent_sources"] >= 2
                                                  else "cheap-assay"))
             for b in r.beliefs()]
    return {"queue": r.experiment_queue(cands)}


@app.get("/api/handoffs")
def handoffs():
    return {"handoffs": researcher().handoffs()}


@app.get("/api/artifacts")
def artifacts():
    return researcher().artifacts()


@app.post("/api/tick")
def tick():
    return researcher().tick(queries=[CACHED_QUERY])


@app.post("/api/selftest/{claim_key}")
def selftest(claim_key: str):
    return researcher().self_test(claim_key)


@app.post("/api/resolve")
def resolve(payload: dict):
    return researcher().resolve_handoff(payload["claim_key"], payload.get("explanation", ""),
                                        int(payload.get("truth", 1)))


@app.get("/api/stream/notebook")
async def stream_notebook():
    """SSE: emit new notebook lines as they appear (the living notebook, live)."""
    async def gen():
        seen = 0
        while True:
            lines = researcher().notebook(500)
            if len(lines) > seen:
                for ln in lines[seen:]:
                    yield f"data: {json.dumps(ln)}\n\n"
                seen = len(lines)
            await asyncio.sleep(1.0)
    return StreamingResponse(gen(), media_type="text/event-stream")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
