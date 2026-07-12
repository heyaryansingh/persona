"""Collected oracle: two personas spawned in one process share ZERO mutable state.

Wires `experiments/exp_multipersona_isolation.py` into pytest so the core multi-persona
generality claim (disjoint graphs, events, budgets, workspaces, selves; registry persists)
has a real regression test. Exercised against a live FalkorDB; skips without one.
"""
import importlib.util
import os
import socket
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent


def _falkor_up() -> bool:
    host = os.environ.get("PERSONA_FALKOR_HOST", "127.0.0.1")
    port = int(os.environ.get("PERSONA_FALKOR_PORT", "6379"))
    try:
        with socket.create_connection((host, port), timeout=1.5):
            return True
    except OSError:
        return False


def _load(name: str):
    path = ROOT / "experiments" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.skipif(not _falkor_up(), reason="FalkorDB not reachable on :6379")
def test_two_personas_are_fully_isolated():
    # asserts disjoint KG/events/budget/paths/selves and registry persistence across reload.
    _load("exp_multipersona_isolation").main()
