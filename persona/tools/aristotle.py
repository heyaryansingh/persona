"""Aristotle (Harmonic) — formally-verified Lean 4 proofs (v8).

When an Aristotle API key is set (env ARISTOTLE_API_KEY, or PERSONA_ARISTOTLE_KEY) and `aristotlelib`
is installed, Persona attempts a FORMAL Lean 4 proof of a mathematical statement — checked by the Lean
kernel, the strongest possible TESTED tier (Aristotle delivered formally-verified solutions to 5/6
IMO-2025 problems). `TaskStatus.COMPLETE` means Aristotle returned a kernel-verified proof; anything
else (COMPLETE_WITH_ERRORS / FAILED / timeout) counts as not-verified and the caller degrades to the
sympy verify-refine loop. Any error is swallowed → verified=False, so `prove` never breaks.

Aristotle proving is an async agent task that can take minutes and consumes Harmonic credits, so calls
are bounded by `timeout` and gated by config.ARISTOTLE_IN_PIPELINE (off by default in the team pipeline;
the human-facing Studio "verify" and math escalations turn it on explicitly).
"""
from __future__ import annotations

import os
import time


def _key() -> str:
    return os.environ.get("ARISTOTLE_API_KEY") or os.environ.get("PERSONA_ARISTOTLE_KEY") or ""


def available() -> bool:
    """True only if a key is set AND aristotlelib imports — else `prove` uses sympy."""
    if not _key():
        return False
    try:
        import aristotlelib  # noqa: F401
        return True
    except Exception:
        return False


_PROMPT = ("Formally prove the following mathematical statement in Lean 4. State it precisely, then "
           "produce a complete, kernel-verified proof.\n\n")


def submit(statement: str) -> dict:
    """Kick off a formal Lean 4 proof (does NOT wait — proving takes minutes). Returns {available,
    task_id, error}. The result is collected later by check()/collect_proofs."""
    if not available():
        return {"available": False}
    import asyncio

    async def _run() -> dict:
        from aristotlelib import Project, set_api_key
        set_api_key(_key())
        project = await Project.create(prompt=_PROMPT + statement.strip())
        for _ in range(6):
            tasks, _pk = await project.get_tasks(limit=1)
            if tasks:
                return {"task_id": tasks[0].agent_task_id, "project_id": getattr(project, "object_id", None)}
            await asyncio.sleep(2)
        return {"error": "no task started"}

    try:
        return {"available": True, **asyncio.run(_run())}
    except Exception as e:
        return {"available": True, "error": str(e)[:200]}


def check(task_id: str) -> dict:
    """Poll a submitted proof. Returns {available, done, verified, status, proof}. `done` is True once
    the task reaches a terminal state; `verified` is True only for a kernel-verified COMPLETE."""
    if not available():
        return {"available": False, "done": False, "verified": False}
    import asyncio

    async def _run() -> dict:
        from aristotlelib import AgentTask, TaskStatus, set_api_key
        set_api_key(_key())
        task = await AgentTask.from_id(task_id)
        try:
            await task.refresh()
        except Exception:
            pass
        terminal = {TaskStatus.COMPLETE, TaskStatus.COMPLETE_WITH_ERRORS, TaskStatus.FAILED,
                    TaskStatus.CANCELED, TaskStatus.OUT_OF_BUDGET}
        return {"done": task.status in terminal, "verified": task.status == TaskStatus.COMPLETE,
                "status": str(task.status), "proof": (getattr(task, "output_summary", "") or "")}

    try:
        return {"available": True, **asyncio.run(_run())}
    except Exception as e:
        return {"available": True, "done": False, "verified": False, "error": str(e)[:200]}
