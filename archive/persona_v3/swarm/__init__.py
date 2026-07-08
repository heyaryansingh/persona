"""The swarm — bounded, disposable, READ-ONLY agents (BUILD_PLAN 5.1).

They read and emit *candidate* observations; they never write to the self. Only the
membrane commits (harvest-then-commit). Reasoning/synthesis stays single-agent elsewhere
(planning/LITERATURE.md §B: fan-out is for reading only).
"""
from .reader import Candidate, HeuristicExtractor, Extractor

__all__ = ["Candidate", "HeuristicExtractor", "Extractor"]
