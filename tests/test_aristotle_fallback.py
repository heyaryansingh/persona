"""Aristotle (formal Lean 4) degrades safely to sympy when no key/lib is present."""
from persona.tools import aristotle


def test_unavailable_without_key(monkeypatch):
    monkeypatch.delenv("PERSONA_ARISTOTLE_KEY", raising=False)
    assert aristotle.available() is False
    r = aristotle.prove_formal("2 + 2 = 4")
    assert r["available"] is False and r["verified"] is False
