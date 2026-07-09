"""Central config + paths (v4). Loads .env; defines the on-disk workspace layout.

The workspace IS the mind: a git-versioned directory the agent reads and grows. Everything
durable lives under WORKSPACE; operational state (queue, events) under WORKSPACE/.persona.
"""
from __future__ import annotations

import os
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parent.parent / ".env")
except Exception:
    pass

ROOT = Path(__file__).resolve().parent.parent
WORKSPACE = Path(os.environ.get("PERSONA_WORKSPACE", ROOT / "persona-workspace"))
KG_NAME = os.environ.get("PERSONA_KG_NAME", "persona")     # default persona's FalkorDB graph
PERSONAS_ROOT = Path(os.environ.get("PERSONA_PERSONAS_ROOT", ROOT / "personas"))  # multi-persona home

# workspace subdirs (the on-disk mind — see the v4 plan §"Memory / folder system")
SELF_DIR = WORKSPACE / "self"
NOTES_DIR = WORKSPACE / "notes"
SOURCES_DIR = WORKSPACE / "sources"
DATASETS_DIR = WORKSPACE / "datasets"
PROJECTS_DIR = WORKSPACE / "projects"
DRAFTS_DIR = WORKSPACE / "drafts"
RUNS_DIR = WORKSPACE / "runs"
OPS_DIR = WORKSPACE / ".persona"

QUEUE_DB = OPS_DIR / "queue.db"
EVENTS_DB = OPS_DIR / "events.db"

SELF_FILES = ("identity.md", "interests.md", "beliefs.md", "strategies.md",
              "taste.md", "open_questions.md", "directives.md", "CHANGELOG.md")

# models (verified at call time — never assume availability)
MODEL_READER = os.environ.get("PERSONA_READER_MODEL", "claude-haiku-4-5")
MODEL_WORKER = os.environ.get("PERSONA_WORKER_MODEL", "claude-sonnet-5")
MODEL_SELF = os.environ.get("PERSONA_SELF_MODEL", "claude-opus-4-8")

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")
NCBI_API_KEY = os.environ.get("NCBI_API_KEY")
OPENALEX_API_KEY = os.environ.get("OPENALEX_API_KEY")            # 10x daily budget (OpenAlex moved to a $-budget model, 2025)
# A REAL contact email is what puts us in Crossref's "polite pool" (they email before blocking, not
# silently 403) and identifies us to OpenAlex. One canonical value, used for both the mailto param
# and the HTTP User-Agent. Override with OPENALEX_MAILTO or CONTACT_EMAIL in .env.
CONTACT_EMAIL = os.environ.get("CONTACT_EMAIL") or os.environ.get("OPENALEX_MAILTO", "aryanrheasingh@gmail.com")
OPENALEX_MAILTO = CONTACT_EMAIL
# Dev safety valve: multiply every per-host min-interval to crawl extra-gently while iterating
# (set PERSONA_INGEST_GENTLE=3 during heavy dev). 1.0 = the verified polite defaults.
INGEST_INTERVAL_MULT = float(os.environ.get("PERSONA_INGEST_GENTLE", "1.0"))
# HTTP cache lifetime: identical searches/PDFs within this window are served from disk (no network,
# no budget spend). Long is good for dev — bump it while iterating so restarts never refetch.
HTTP_CACHE_TTL_DAYS = float(os.environ.get("PERSONA_HTTP_CACHE_TTL_DAYS", "7"))

# daemon knobs
N_WORKERS = int(os.environ.get("PERSONA_WORKERS", "6"))
QUEUE_MIN_DEPTH = int(os.environ.get("PERSONA_QUEUE_MIN_DEPTH", "4"))   # scheduler tops up below this
SCHEDULER_INTERVAL_S = float(os.environ.get("PERSONA_SCHEDULER_INTERVAL", "5"))
SELF_INTERVAL_S = float(os.environ.get("PERSONA_SELF_INTERVAL", "240"))   # reflecting-self cadence
DAILY_BUDGET_USD = float(os.environ.get("PERSONA_DAILY_BUDGET_USD", "15"))
LEASE_SECONDS = int(os.environ.get("PERSONA_LEASE_SECONDS", "300"))


def have_key() -> bool:
    return bool(ANTHROPIC_API_KEY)


def ensure_workspace() -> None:
    """Create the workspace skeleton if absent (blank slate). Idempotent."""
    for d in (SELF_DIR, NOTES_DIR, SOURCES_DIR, DATASETS_DIR, PROJECTS_DIR, DRAFTS_DIR,
              RUNS_DIR, OPS_DIR):
        d.mkdir(parents=True, exist_ok=True)
