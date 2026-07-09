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


def reset() -> None:
    """Wipe the durable self back to blank (a truly fresh start). Does NOT touch the KG."""
    config.ensure_workspace()
    for f in config.SELF_FILES:
        p = config.SELF_DIR / f
        if p.exists():
            p.unlink()


def seed(interests: list[str], name: str = "Persona") -> bool:
    """Seed / re-seed the persona. If blank, born fresh. If already has a self, APPLY the new
    interests (never silently drop the user's input — that was the v4 bug); accumulated beliefs/
    strategies/taste are kept. Returns True if this was a fresh birth, False if a re-seed."""
    config.ensure_workspace()
    if is_seeded():
        set_interests([(i.strip(), 1.0) for i in interests if i.strip()])
        set_open_questions([f"What is currently known about {i.strip()}?"
                            for i in interests if i.strip()])
        append_changelog(f"re-seeded by human — interests set to: "
                         f"{', '.join(i.strip() for i in interests if i.strip())}")
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


def set_interests(pairs: list[tuple[str, float]]) -> None:
    """Rewrite interests.md from an evolved (name, weight) list (the self reshaping its curiosity)."""
    lines = ["# interests\n", "_evolves as I read — new curiosities appear, weights shift._\n"]
    seen = set()
    for name, weight in pairs:
        n = name.strip()
        if n and n.lower() not in seen:
            seen.add(n.lower())
            lines.append(f"- {n} :: {round(float(weight), 2)}")
    (config.SELF_DIR / "interests.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def set_open_questions(qs: list[str]) -> None:
    lines = ["# open questions\n", "_what I most want to find out. Drives what I read next._\n"]
    lines += [f"- {q.strip()}" for q in qs if q.strip()]
    (config.SELF_DIR / "open_questions.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def append_section(filename: str, note: str) -> None:
    """Append a dated note to a self file (strategies/taste/identity accrete over time)."""
    if not note or not note.strip():
        return
    p = config.SELF_DIR / filename
    prev = p.read_text(encoding="utf-8") if p.exists() else f"# {filename[:-3]}\n"
    p.write_text(prev.rstrip() + f"\n- {_now()} — {note.strip()}\n", encoding="utf-8")
