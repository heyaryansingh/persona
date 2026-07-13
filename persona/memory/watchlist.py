"""Living re-audit watchlist (v9) — the auditor's verdicts don't rot.

A robustness verdict is only true relative to what the literature said WHEN it ran. New disconfirming
work lands every week. So every audited paper joins a watchlist; the revisit loop (daemon) periodically
re-audits the least-recently-checked one and records any movement ("replication likelihood 40%→22%
after 3 new contradicting results"). This is the auditor's analogue of the verified-belief revisit
loop — the mind re-checks its own judgments, it doesn't freeze them.

Persisted as self/watchlist.jsonl (source of truth) + a human-readable self/watchlist.md.
Only re-auditable targets are tracked: a read source (`slug`, text on disk) or an uploaded file
(`upload`, file on disk) — both can be re-read and re-scored cheaply.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone

from ..context import get_persona

_BAND = {"robust": "🟢", "contested": "🟠", "fragile": "🔴"}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _dir():
    return get_persona().paths.self_dir


def _key(target: str, ref: str) -> str:
    return f"{target}:{ref}"


def entries() -> list[dict]:
    f = _dir() / "watchlist.jsonl"
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


def add(title: str, likelihood: float, band: str, *, slug: str = "", upload: str = "",
        content_hash: str = "") -> dict:
    """Register (or refresh) an audited paper on the watchlist. `slug` (a read source) or `upload`
    (a file under uploads/) makes it re-auditable. Dedups on (target, ref); resets the history head."""
    if not slug and not upload:
        return {}                                     # text-only paste: nothing to re-read later
    target, ref = ("slug", slug) if slug else ("upload", upload)
    key = _key(target, ref)
    ents = entries()
    prev = next((e for e in ents if e.get("key") == key), None)
    hist = (prev.get("history") if prev else []) or []
    hist = (hist + [{"likelihood": round(float(likelihood), 2), "band": band, "at": _now()}])[-12:]
    ents = [e for e in ents if e.get("key") != key]
    entry = {"key": key, "target": target, "ref": ref, "title": title[:160],
             "likelihood": round(float(likelihood), 2), "band": band, "content_hash": content_hash,
             "first_seen": (prev.get("first_seen") if prev else _now()), "last_audit": _now(),
             "reaudits": (prev.get("reaudits", 0) if prev else 0), "history": hist}
    ents.append(entry)
    _write(ents)
    return entry


def due(min_history: int = 1) -> dict | None:
    """The least-recently-audited watchlist item — the next one to re-check. Oldest last_audit first."""
    ents = entries()
    if not ents:
        return None
    return sorted(ents, key=lambda e: (e.get("last_audit", ""), e.get("reaudits", 0)))[0]


def record_reaudit(key: str, likelihood: float, band: str, *, support: int = 0, contradict: int = 0,
                   content_hash: str = "") -> dict | None:
    """After a re-audit: append to history, update the head, bump the counter, note any movement."""
    ents = entries()
    e = next((x for x in ents if x.get("key") == key), None)
    if e is None:
        return None
    old = e.get("likelihood")
    e["history"] = (e.get("history", []) + [{"likelihood": round(float(likelihood), 2), "band": band,
                    "at": _now(), "support": support, "contradict": contradict}])[-12:]
    e["likelihood"] = round(float(likelihood), 2)
    e["band"] = band
    e["reaudits"] = e.get("reaudits", 0) + 1
    e["last_audit"] = _now()
    if content_hash:
        e["content_hash"] = content_hash
    delta = round(e["likelihood"] - float(old), 2) if old is not None else 0.0
    e["last_delta"] = delta
    _write(ents)
    return {"key": key, "title": e["title"], "old": old, "new": e["likelihood"], "delta": delta,
            "band": band, "support": support, "contradict": contradict}


def summary() -> dict:
    ents = entries()
    from collections import Counter
    c = Counter(e.get("band", "?") for e in ents)
    return {"total": len(ents), "robust": c.get("robust", 0), "contested": c.get("contested", 0),
            "fragile": c.get("fragile", 0), "reaudited": sum(1 for e in ents if e.get("reaudits"))}


def _write(ents: list[dict]) -> None:
    d = _dir()
    d.mkdir(parents=True, exist_ok=True)
    (d / "watchlist.jsonl").write_text(
        "\n".join(json.dumps(e, ensure_ascii=False) for e in ents) + "\n", encoding="utf-8")
    s = summary()
    lines = ["# re-audit watchlist — audited papers I keep re-checking as the literature moves\n",
             f"_{s['total']} paper(s): {s['robust']} robust · {s['contested']} contested · "
             f"{s['fragile']} fragile · {s['reaudited']} re-audited · updated {_now()}_\n"]
    for e in sorted(ents, key=lambda x: x.get("last_audit", ""), reverse=True):
        d0 = e.get("last_delta")
        arrow = "" if not d0 else (f"  \n  ↳ moved {d0:+.2f} on last re-audit" if abs(d0) >= 0.01
                                   else "  \n  ↳ held on last re-audit")
        tail = (f" · re-audited {e['reaudits']}×" if e.get("reaudits") else " · not yet re-audited")
        lines.append(f"- {_BAND.get(e['band'], '·')} **{e['title']}** — {int(e['likelihood']*100)}% "
                     f"({e['band']}){tail}" + arrow)
    (d / "watchlist.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def demo():
    """Self-check runs only inside a persona context; import-safe no-op otherwise."""
    print("watchlist module OK")


if __name__ == "__main__":
    demo()
