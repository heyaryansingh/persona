"""Central config: loads .env, exposes API keys, model tiers, and budget (v2, P0).

Model tiers (see the Claude model list; verified at call time — never assume availability):
  READER   = Haiku 4.5   — the cheap, fast swarm reader (bulk extraction, Batch API)
  REASONER = Sonnet 5    — the single strong reasoning agent (outer loop)
  HARD     = Opus 4.8    — escalation for the hardest calls only
Reasoning stays SINGLE-agent (Persona's DPI/E12 finding); fan-out is reading only.
"""
from __future__ import annotations

import os
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parent.parent / ".env")
except Exception:
    pass  # .env optional; env vars may be set in the shell

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")
NCBI_API_KEY = os.environ.get("NCBI_API_KEY")

MODEL_READER = os.environ.get("PERSONA_READER_MODEL", "claude-haiku-4-5")
MODEL_REASONER = os.environ.get("PERSONA_REASONER_MODEL", "claude-sonnet-5")
MODEL_HARD = os.environ.get("PERSONA_HARD_MODEL", "claude-opus-4-8")

# hard daily spend ceiling (USD); the orchestrator refuses new calls past this.
DAILY_BUDGET_USD = float(os.environ.get("PERSONA_DAILY_BUDGET_USD", "15"))

# approx list prices ($/M tokens) for budgeting; refine from real usage headers.
PRICE_PER_MTOK = {
    "claude-haiku-4-5": {"in": 1.0, "out": 5.0},
    "claude-sonnet-5": {"in": 3.0, "out": 15.0},
    "claude-opus-4-8": {"in": 15.0, "out": 75.0},
}


def have_key() -> bool:
    return bool(ANTHROPIC_API_KEY)


def anthropic_client():
    """Sync client. Raises a clear error if the key is missing."""
    if not ANTHROPIC_API_KEY:
        raise RuntimeError("ANTHROPIC_API_KEY not set — put it in .env at the repo root")
    from anthropic import Anthropic
    return Anthropic(api_key=ANTHROPIC_API_KEY)


def est_cost_usd(model: str, in_tokens: int, out_tokens: int, *, cache_read: int = 0,
                 cache_write: int = 0, batch: bool = False) -> float:
    """Cost with prompt-caching + Batch adjustments (Anthropic pricing): cached-read input is
    ~0.1x, cache-write ~1.25x, and the Batch API is ~0.5x the whole call. `in_tokens` should be
    the NON-cached input; pass cache_read/cache_write separately."""
    p = PRICE_PER_MTOK.get(model, {"in": 1.0, "out": 5.0})
    cost = (in_tokens * p["in"] + out_tokens * p["out"]
            + cache_read * p["in"] * 0.1 + cache_write * p["in"] * 1.25) / 1_000_000
    return cost * (0.5 if batch else 1.0)
