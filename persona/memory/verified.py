"""Verification ledger (v8) — the durable record of what the mind has actually PROVEN/TESTED.

This is the headline differentiator: a persistent AI scientist that KNOWS what it has verified, not
just what it read. An entry lands here ONLY when a check actually passed — sympy assertions verified
in the sandbox, a Lean 4 proof accepted by Aristotle, or an analyst SUPPORTED conclusion. Persisted as
self/verified.jsonl (source of truth) + a human-readable self/verified.md. The revisit loop
(agents/revisit.py) re-tests these entries against evidence gathered SINCE and updates their status —
so the mind self-corrects: still-verified / weakened / refuted.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone

from ..context import get_persona

_SYM = {"verified": "✓", "weakened": "~", "refuted": "✗", "unverified": "·"}
_METHOD_LABEL = {"lean": "Lean 4 (formal)", "sympy": "sympy (machine-checked)",
                 "analyst": "computational analysis"}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _dir():
    return get_persona().paths.self_dir


def _key(statement: str, method: str) -> str:
    return hashlib.sha1(f"{statement.strip().lower()}|{method}".encode()).hexdigest()[:12]


def entries() -> list[dict]:
    f = _dir() / "verified.jsonl"
    if not f.exists():
        return []
    out = []
    for line in f.read_text(encoding="utf-8").splitlines():
        if line.strip():
            try:
                out.append(json.loads(line))
            except Exception:
                pass
    return out


def record(statement: str, method: str, status: str, *, evidence: str = "", source: str = "",
           checks: int | None = None) -> dict:
    """Append (or replace) a tested result. method: lean|sympy|analyst. status: verified|weakened|refuted.
    Dedup by (statement, method) so re-proving the same thing updates in place, not duplicates."""
    d = _dir()
    d.mkdir(parents=True, exist_ok=True)
    key = _key(statement, method)
    ents = [e for e in entries() if e.get("key") != key]
    entry = {"key": key, "statement": statement.strip()[:400], "method": method, "status": status,
             "verified": status == "verified", "evidence": (evidence or "")[:200], "source": source,
             "checks": checks, "at": _now(), "revisits": 0}
    ents.append(entry)
    _write(ents)
    return entry


def update_status(key: str, status: str, note: str = "") -> bool:
    """The revisit loop marks an entry still-verified / weakened / refuted after re-testing."""
    ents = entries()
    found = False
    for e in ents:
        if e.get("key") == key:
            e["status"] = status
            e["verified"] = status == "verified"
            e["revisits"] = e.get("revisits", 0) + 1
            e["last_revisit"] = _now()
            if note:
                e["revisit_note"] = note[:200]
            found = True
    if found:
        _write(ents)
    return found


def summary() -> dict:
    ents = entries()
    from collections import Counter
    c = Counter(e.get("status", "unverified") for e in ents)
    return {"total": len(ents), "verified": c.get("verified", 0), "weakened": c.get("weakened", 0),
            "refuted": c.get("refuted", 0),
            "revisited": sum(1 for e in ents if e.get("revisits"))}


def _write(ents: list[dict]) -> None:
    d = _dir()
    (d / "verified.jsonl").write_text(
        "\n".join(json.dumps(e, ensure_ascii=False) for e in ents) + "\n", encoding="utf-8")
    s = summary_of(ents)
    lines = ["# verified — what I have established (not just read)\n",
             f"_{s['total']} tested result(s): {s['verified']} verified · {s['weakened']} weakened · "
             f"{s['refuted']} refuted · {s['revisited']} re-tested · updated {_now()}_\n"]
    for e in sorted(ents, key=lambda x: x.get("at", ""), reverse=True):
        meth = _METHOD_LABEL.get(e.get("method"), e.get("method", "?"))
        tail = (f" · {e['checks']} checks" if e.get("checks") else "") \
            + (f" · re-tested {e['revisits']}×" if e.get("revisits") else "") \
            + (f" · {e['source']}" if e.get("source") else "")
        lines.append(f"- {_SYM.get(e['status'], '·')} **{e['statement']}**  \n"
                     f"  _{meth} · {e['status']}{tail}_"
                     + (f"  \n  ↳ {e['revisit_note']}" if e.get("revisit_note") else ""))
    (d / "verified.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def summary_of(ents: list[dict]) -> dict:
    from collections import Counter
    c = Counter(e.get("status", "unverified") for e in ents)
    return {"total": len(ents), "verified": c.get("verified", 0), "weakened": c.get("weakened", 0),
            "refuted": c.get("refuted", 0), "revisited": sum(1 for e in ents if e.get("revisits"))}
