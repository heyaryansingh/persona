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
from .context import get_persona


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def is_seeded() -> bool:
    return (get_persona().paths.self_dir / "interests.md").exists()


def reset() -> None:
    """Wipe the durable self back to blank (a truly fresh start). Does NOT touch the KG."""
    get_persona().paths.ensure()
    for f in config.SELF_FILES:
        p = get_persona().paths.self_dir / f
        if p.exists():
            p.unlink()


def seed(interests: list[str], name: str = "Persona") -> bool:
    """Seed / re-seed the persona. If blank, born fresh. If already has a self, APPLY the new
    interests (never silently drop the user's input — that was the v4 bug); accumulated beliefs/
    strategies/taste are kept. Returns True if this was a fresh birth, False if a re-seed."""
    get_persona().paths.ensure()
    if is_seeded():
        set_interests([(i.strip(), 1.0) for i in interests if i.strip()])
        set_open_questions([f"What is currently known about {i.strip()}?"
                            for i in interests if i.strip()])
        append_changelog(f"re-seeded by human — interests set to: "
                         f"{', '.join(i.strip() for i in interests if i.strip())}")
        return False
    (get_persona().paths.self_dir / "identity.md").write_text(
        f"# identity\n\nname: {name}\nborn: {_now()}\n\n"
        f"I am a synthetic researcher, spawned as a blank slate. I was given a few starting "
        f"interests; everything else I will learn, decide, and become on my own.\n",
        encoding="utf-8")
    (get_persona().paths.self_dir / "interests.md").write_text(
        "# interests\n\n_seed interests (weight 1.0). These evolve as I read._\n\n"
        + "".join(f"- {i.strip()} :: 1.0\n" for i in interests if i.strip()),
        encoding="utf-8")
    (get_persona().paths.self_dir / "open_questions.md").write_text(
        "# open questions\n\n_what I most want to find out. Drives what I read next._\n\n"
        + "".join(f"- What is currently known about {i.strip()}?\n" for i in interests if i.strip()),
        encoding="utf-8")
    for f, header in (("beliefs.md", "# beliefs\n\n_high-confidence claims, projected from my "
                       "knowledge graph. Empty until I've read and converged evidence._\n"),
                      ("strategies.md", "# strategies\n\n_reading/analysis strategies that have "
                       "worked for me. Empty until I've learned some._\n"),
                      ("taste.md", "# taste\n\n_what I find surprising or worth my attention._\n")):
        (get_persona().paths.self_dir / f).write_text(header, encoding="utf-8")
    (get_persona().paths.self_dir / "CHANGELOG.md").write_text(
        f"# changelog\n\n- {_now()} — born; seeded interests: "
        f"{', '.join(i.strip() for i in interests if i.strip())}\n", encoding="utf-8")
    return True


def interests() -> list[tuple[str, float]]:
    """Parse (name, weight) from interests.md."""
    p = get_persona().paths.self_dir / "interests.md"
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
    p = get_persona().paths.self_dir / "open_questions.md"
    if not p.exists():
        return []
    return [ln.strip()[2:].strip() for ln in p.read_text(encoding="utf-8").splitlines()
            if ln.strip().startswith("- ")]


def read_self() -> dict:
    """The self as a dict of {filename: text} — fed (excerpted) into agent prompts."""
    out = {}
    for f in config.SELF_FILES:
        p = get_persona().paths.self_dir / f
        out[f] = p.read_text(encoding="utf-8") if p.exists() else ""
    return out


def append_changelog(line: str) -> None:
    p = get_persona().paths.self_dir / "CHANGELOG.md"
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
    (get_persona().paths.self_dir / "interests.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def set_open_questions(qs: list[str]) -> None:
    lines = ["# open questions\n", "_what I most want to find out. Drives what I read next._\n"]
    lines += [f"- {q.strip()}" for q in qs if q.strip()]
    (get_persona().paths.self_dir / "open_questions.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def directives() -> str:
    """Standing instructions from the human (steering). The reflect/deliberate/discover loops read
    this each cycle, so a conversational nudge persists and shapes what the persona does next."""
    p = get_persona().paths.self_dir / "directives.md"
    return p.read_text(encoding="utf-8") if p.exists() else ""


def add_directive(note: str) -> None:
    """Append a dated standing directive from the human (v6 P2 — steer, don't block)."""
    if not note or not note.strip():
        return
    get_persona().paths.ensure()
    p = get_persona().paths.self_dir / "directives.md"
    prev = p.read_text(encoding="utf-8") if p.exists() else (
        "# directives\n\n_standing instructions from the human. I weigh these heavily but keep my "
        "own judgment and provenance._\n")
    p.write_text(prev.rstrip() + f"\n- {_now()} — {note.strip()}\n", encoding="utf-8")


def append_section(filename: str, note: str) -> None:
    """Append a dated note to a self file (strategies/taste/identity accrete over time)."""
    if not note or not note.strip():
        return
    p = get_persona().paths.self_dir / filename
    prev = p.read_text(encoding="utf-8") if p.exists() else f"# {filename[:-3]}\n"
    p.write_text(prev.rstrip() + f"\n- {_now()} — {note.strip()}\n", encoding="utf-8")
