"""Personal baseline and change-flag detection (SPEC sections 6.3 and 7).

One baseline per resident per task - error score, step durations, gaps between steps -
and a detector that compares each new session against it.

Two or more sessions above that resident's own threshold within 24-48 h flag a change
for a nurse to review. A single bad session never alerts, and a sustained upward trend
over weeks is reported as a trend rather than as an alert.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta

STAGE = "change_detection"

#: Hesitation threshold, in standard deviations above this resident's own average.
HESITATION_SIGMA = 2.5

#: Sessions above threshold needed inside the window before a change is flagged.
FLAG_MIN_SESSIONS = 2


@dataclass(frozen=True)
class Baseline:
    mean: float
    std: float
    threshold: float


def build_baseline(scores: list[float], k: float = 2.0, min_std: float = 0.5) -> Baseline:
    if len(scores) < 3:
        raise ValueError("need at least 3 scores to build a baseline")
    mean = sum(scores) / len(scores)
    variance = sum((s - mean) ** 2 for s in scores) / len(scores)
    std = variance**0.5
    threshold = mean + k * max(std, min_std)
    return Baseline(mean=mean, std=std, threshold=threshold)


def flag_change(
    sessions: list[tuple[datetime, float]],
    baseline: Baseline,
    now: datetime,
    window_h: float = 48.0,
    min_sessions: int = FLAG_MIN_SESSIONS,
) -> bool:
    window_start = now - timedelta(hours=window_h)
    count = sum(
        1
        for ts, score in sessions
        if window_start <= ts <= now and score > baseline.threshold
    )
    return count >= min_sessions
