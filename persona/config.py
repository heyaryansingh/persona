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
# Live workers: budget/rate-limits are the real governor (E07a: effective reading-team saturates
# ~14-15), so 8 approaches that ceiling with headroom without pretending to be "hundreds". The real
# thousands/day scale lever is the Batch API (reading/batch.py, 0.5x cost, non-blocking).
N_WORKERS = int(os.environ.get("PERSONA_WORKERS", "8"))
# Relevance gate: drop scouted papers whose title is off the persona's objective (max cosine to its
# top interests, bge-small). tau=0.70 validated on 646 real Erdos titles = 0.939 balanced accuracy,
# keeps 94% on-topic / drops 94% off-topic — see experiments/exp_rq_e14_relevance_gate.py.
RELEVANCE_TAU = float(os.environ.get("PERSONA_RELEVANCE_TAU", "0.70"))
RELEVANCE_GATE = os.environ.get("PERSONA_RELEVANCE_GATE", "1") not in ("0", "false", "")
# Paper compile: repair-and-retry loop feeds the pdflatex error log back to the model (LLM LaTeX
# usually needs a pass or two). Bounded by budget().can_spend() in the loop.
PAPER_COMPILE_ATTEMPTS = int(os.environ.get("PERSONA_PAPER_COMPILE_ATTEMPTS", "3"))
BATCH_SWEEP = int(os.environ.get("PERSONA_BATCH_SWEEP", "75"))   # papers per background Batch-API sweep
# Investigation engine (v7): a research program is a chain of role-steps worked by a team.
GATHER_READS = int(os.environ.get("PERSONA_GATHER_READS", "6"))   # papers read inline per gather step
MAX_ACTIVE_INVESTIGATIONS = int(os.environ.get("PERSONA_MAX_INVESTIGATIONS", "4"))  # concurrent programs
FLEET_TARGET = int(os.environ.get("PERSONA_FLEET_TARGET", "50"))  # honest target in-flight agent-tasks
LIVE_CONCURRENCY = int(os.environ.get("PERSONA_LIVE_CONCURRENCY", str(N_WORKERS)))  # paid parallelism cap
QUEUE_MIN_DEPTH = int(os.environ.get("PERSONA_QUEUE_MIN_DEPTH", "4"))   # scheduler tops up below this
SCHEDULER_INTERVAL_S = float(os.environ.get("PERSONA_SCHEDULER_INTERVAL", "5"))
SCOUT_INTERVAL_S = float(os.environ.get("PERSONA_SCOUT_INTERVAL", "900"))  # minimum between broad pulses
SELF_INTERVAL_S = float(os.environ.get("PERSONA_SELF_INTERVAL", "1800"))   # reflecting-self cadence
DAILY_BUDGET_USD = float(os.environ.get("PERSONA_DAILY_BUDGET_USD", "15"))
READING_BUDGET_FRACTION = float(os.environ.get("PERSONA_READING_FRACTION", "0.65"))  # reserve rest for outputs
LEASE_SECONDS = int(os.environ.get("PERSONA_LEASE_SECONDS", "300"))


def have_key() -> bool:
    return bool(ANTHROPIC_API_KEY)


def ensure_workspace() -> None:
    """Create the workspace skeleton if absent (blank slate). Idempotent."""
    for d in (SELF_DIR, NOTES_DIR, SOURCES_DIR, DATASETS_DIR, PROJECTS_DIR, DRAFTS_DIR,
              RUNS_DIR, OPS_DIR):
        d.mkdir(parents=True, exist_ok=True)
