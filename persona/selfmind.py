"""The durable SELF (v4) — the small, legible, git-diffable mind on disk.

Blank-slate by default: `seed(interests)` writes the initial self ONLY if the workspace has
never been seeded (it never overwrites an evolved self — that was a v3 bug). Everything here is
plain markdown so a human can read the mind and `git diff` shows it change over time. The
reflection loop (later phase) rewrites these files; P0 just seeds + reads them.
"""
from __future__ import annotations

import re
from datetime import datetime, timezone

from . import config


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def is_seeded() -> bool:
    return (config.SELF_DIR / "interests.md").exists()


def seed(interests: list[str], name: str = "Persona") -> bool:
    """Born blank: lay down the initial self from seed interests. No-op if already seeded.
    Returns True if it seeded, False if a self already existed."""
    config.ensure_workspace()
    if is_seeded():
        return False
    (config.SELF_DIR / "identity.md").write_text(
        f"# identity\n\nname: {name}\nborn: {_now()}\n\n"
        f"I am a synthetic researcher, spawned as a blank slate. I was given a few starting "
        f"interests; everything else I will learn, decide, and become on my own.\n",
        encoding="utf-8")
    (config.SELF_DIR / "interests.md").write_text(
        "# interests\n\n_seed interests (weight 1.0). These evolve as I read._\n\n"
        + "".join(f"- {i.strip()} :: 1.0\n" for i in interests if i.strip()),
        encoding="utf-8")
    (config.SELF_DIR / "open_questions.md").write_text(
        "# open questions\n\n_what I most want to find out. Drives what I read next._\n\n"
        + "".join(f"- What is currently known about {i.strip()}?\n" for i in interests if i.strip()),
        encoding="utf-8")
    for f, header in (("beliefs.md", "# beliefs\n\n_high-confidence claims, projected from my "
                       "knowledge graph. Empty until I've read and converged evidence._\n"),
                      ("strategies.md", "# strategies\n\n_reading/analysis strategies that have "
                       "worked for me. Empty until I've learned some._\n"),
                      ("taste.md", "# taste\n\n_what I find surprising or worth my attention._\n")):
        (config.SELF_DIR / f).write_text(header, encoding="utf-8")
    (config.SELF_DIR / "CHANGELOG.md").write_text(
        f"# changelog\n\n- {_now()} — born; seeded interests: "
        f"{', '.join(i.strip() for i in interests if i.strip())}\n", encoding="utf-8")
    return True


def interests() -> list[tuple[str, float]]:
    """Parse (name, weight) from interests.md."""
    p = config.SELF_DIR / "interests.md"
    if not p.exists():
        return []
    out = []
    for line in p.read_text(encoding="utf-8").splitlines():
        m = re.match(r"\s*-\s*(.+?)\s*::\s*([0-9.]+)\s*$", line)
        if m:
            out.append((m.group(1).strip(), float(m.group(2))))
        elif line.strip().startswith("- ") and "::" not in line:
            out.append((line.strip()[2:].strip(), 1.0))
    return out


def open_questions() -> list[str]:
    p = config.SELF_DIR / "open_questions.md"
    if not p.exists():
        return []
    return [ln.strip()[2:].strip() for ln in p.read_text(encoding="utf-8").splitlines()
            if ln.strip().startswith("- ")]


def read_self() -> dict:
    """The self as a dict of {filename: text} — fed (excerpted) into agent prompts."""
    out = {}
    for f in config.SELF_FILES:
        p = config.SELF_DIR / f
        out[f] = p.read_text(encoding="utf-8") if p.exists() else ""
    return out


def append_changelog(line: str) -> None:
    p = config.SELF_DIR / "CHANGELOG.md"
    prev = p.read_text(encoding="utf-8") if p.exists() else "# changelog\n"
    p.write_text(prev.rstrip() + f"\n- {_now()} — {line}\n", encoding="utf-8")
