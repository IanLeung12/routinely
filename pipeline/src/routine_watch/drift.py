"""Robust daily score trends flagged for review separately from sudden changes."""

from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, datetime
from itertools import combinations
from statistics import mean, median


@dataclass(frozen=True)
class Drift:
    slope_per_day: float
    days: int
    trending: bool


def daily_scores(scores: list[dict]) -> list[tuple[date, float]]:
    """Mean score per calendar date, for `drift` (one point per day)."""
    by_day: dict[date, list[float]] = defaultdict(list)
    for entry in scores:
        day = datetime.fromisoformat(entry["ts"]).date()
        by_day[day].append(entry["score"])
    return sorted((day, mean(values)) for day, values in by_day.items())


def drift(
    daily: Sequence[tuple[date, float]], min_days: int = 7, min_slope: float = 0.1
) -> Drift:
    """Estimate Theil–Sen slope using actual elapsed days between observations.

    Days counts observed dates, so gaps cannot satisfy the minimum history.
    Observations on the same date do not define a pairwise slope.
    """
    days = len({day for day, _ in daily})
    slopes = [
        (right_score - left_score) / (right_day - left_day).days
        for (left_day, left_score), (right_day, right_score) in combinations(daily, 2)
        if right_day != left_day
    ]
    if not slopes:
        return Drift(slope_per_day=0.0, days=days, trending=False)
    slope = median(slopes)
    return Drift(slope_per_day=slope, days=days, trending=days >= min_days and slope >= min_slope)
