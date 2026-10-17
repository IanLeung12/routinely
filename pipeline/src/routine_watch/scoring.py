"""Session score weights (SPEC section 7 follow-up).

Turns per-session error counts into one session score: a hand-set weighted sum.
"""

from collections.abc import Mapping

from routine_watch.errors import ERROR_TYPES

STAGE = "scoring"

WEIGHTS: dict[str, float] = {
    "omission": 3.0,
    "substitution": 3.0,
    "sequence": 2.0,
    "perseveration": 2.0,
    "abandonment": 2.0,
    "hesitation": 1.0,
}

SELF_CORRECTED_WEIGHT = 0.5

assert set(WEIGHTS) == set(ERROR_TYPES)


def session_score(
    counts: Mapping[str, int], self_corrected: int = 0, assisted: bool = False
) -> float:
    if assisted:
        return 0.0

    for error_type in counts:
        if error_type not in WEIGHTS:
            raise ValueError(f"Unknown error type: {error_type!r}")

    score = sum(WEIGHTS[error_type] * count for error_type, count in counts.items())
    score += SELF_CORRECTED_WEIGHT * self_corrected
    return score
