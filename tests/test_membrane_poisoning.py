"""Collected oracle: the membrane's anchor write-policy resists correlated poisoning.

This wires `experiments/exp_poisoning.py` (the poisoning-protection oracle CLAUDE.md 4
refers to) into the pytest suite so `poisoning_signals` + anchor retention have a real
regression test. Behavior is exercised against a live FalkorDB (real graph, not mocked);
the test skips cleanly when no graph DB is reachable so CI without one stays green.
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
def test_anchor_retained_and_poison_detected_under_correlated_attack():
    # exp_poisoning.main() asserts the anchored belief is RETAINED (sign/confidence pinned)
    # and the low-independence high-volume attack is DETECTED by poisoning_signals.
    _load("exp_poisoning").main()
