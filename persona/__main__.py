"""Entry point: `python -m persona` starts the always-on daemon + live-thought UI.

Optional: `python -m persona --seed "topic a, topic b"` seeds the blank slate before starting.
"""
from __future__ import annotations

import argparse
import sys

import uvicorn

from . import config, selfmind

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass


def main() -> None:
    ap = argparse.ArgumentParser(prog="persona")
    ap.add_argument("--seed", default=None, help="comma-separated seed interests (blank-slate spawn)")
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=8137)
    args = ap.parse_args()

    config.ensure_workspace()
    if args.seed:
        interests = [s.strip() for s in args.seed.split(",") if s.strip()]
        if selfmind.seed(interests):
            print(f"seeded blank slate with: {', '.join(interests)}")
        else:
            print("already seeded; leaving the existing self intact")

    print(f"Persona v4 -> http://{args.host}:{args.port}  (workspace: {config.WORKSPACE})")
    uvicorn.run("persona.api.app:app", host=args.host, port=args.port)


if __name__ == "__main__":
    main()
