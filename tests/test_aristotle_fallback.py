"""Aristotle (formal Lean 4) degrades safely to sympy when no key/lib is present."""
from persona.tools import aristotle


def test_unavailable_without_key(monkeypatch):
    monkeypatch.delenv("PERSONA_ARISTOTLE_KEY", raising=False)
    monkeypatch.delenv("ARISTOTLE_API_KEY", raising=False)
    assert aristotle.available() is False
    assert aristotle.submit("2 + 2 = 4").get("available") is False
    assert aristotle.check("nope").get("available") is False
