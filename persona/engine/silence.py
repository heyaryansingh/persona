"""Silence / dark-literature detector (BUILD_PLAN 3.5).

Detects ABANDONMENT: a target that was hot then went quiet (not refuted,
just dropped) -- a pattern that often hides a buried negative result.

# ponytail: this SURFACES abandonment candidates only. H3.5 (that abandonment
# enriches for discoverable nulls) is NOT yet validated against real data --
# treat detect_abandoned's output as a hypothesis-ranking tool, not a fact.

stdlib + numpy only.
"""
from __future__ import annotations

import numpy as np


def entity_year_counts(docs, entities) -> dict:
    """{entity: {year: count}} counting docs whose title+text (lowercased)
    contains the entity (lowercased). Docs with year None are skipped.
    """
    counts = {e: {} for e in entities}
    for doc in docs:
        if doc.year is None:
            continue
        haystack = ((doc.title or "") + " " + (doc.text or "")).lower()
        for e in entities:
            if e.lower() in haystack:
                counts[e][doc.year] = counts[e].get(doc.year, 0) + 1
    return counts


def abandonment_score(year_counts: dict) -> float:
    """0..1, high when recent activity is much lower than the historical
    peak and enough time has passed since that peak.
    """
    active_years = [y for y, c in year_counts.items() if c > 0]
    if len(active_years) < 2:
        return 0.0
    peak_year = max(year_counts, key=year_counts.get)
    peak = year_counts[peak_year]
    if peak < 2:
        return 0.0

    latest_year = max(year_counts)
    years_since_peak = latest_year - peak_year
    if years_since_peak < 2:
        return 0.0

    recent_window = sorted(y for y in year_counts if y > peak_year)
    if not recent_window:
        return 0.0
    recent_mean = float(np.mean([year_counts[y] for y in recent_window]))

    score = 1.0 - recent_mean / peak
    return float(np.clip(score, 0.0, 1.0))


def detect_abandoned(series_by_entity: dict, min_peak: int = 3,
                      recent_window: int = 3, threshold: float = 0.6) -> list:
    """Rank entities by abandonment_score, keep those >= threshold and with
    peak >= min_peak. recent_window is accepted for API compatibility but the
    "recent" activity used by abandonment_score is everything after the
    peak year (a data-driven window, not a fixed lookback).
    """
    out = []
    for entity, year_counts in series_by_entity.items():
        if not year_counts:
            continue
        peak_year = max(year_counts, key=year_counts.get)
        peak = year_counts[peak_year]
        if peak < min_peak:
            continue
        score = abandonment_score(year_counts)
        if score < threshold:
            continue
        recent_window_years = sorted(y for y in year_counts if y > peak_year)
        recent_mean = (
            float(np.mean([year_counts[y] for y in recent_window_years]))
            if recent_window_years else 0.0
        )
        out.append({
            "entity": entity,
            "score": score,
            "peak_year": peak_year,
            "peak": peak,
            "recent_mean": recent_mean,
        })
    out.sort(key=lambda d: d["score"], reverse=True)
    return out
