"""Serve the API + built UI offline (fixtures, no daemon) for local preview/verification.
Run: python scripts/serve_offline.py   (serves at http://127.0.0.1:8137)
"""
import os
import sys
from pathlib import Path

os.environ.setdefault("PERSONA_OFFLINE", "1")
os.environ.pop("PERSONA_AUTONOMOUS", None)
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import uvicorn  # noqa: E402

if __name__ == "__main__":
    uvicorn.run("persona.api.app:app", host="127.0.0.1", port=8137)
