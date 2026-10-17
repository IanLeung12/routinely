"""Session quality: tell an unclear session from a scoreable one (SPEC section 12).

Pose and detection are less reliable with walkers, wheelchairs or bad lighting
(SPEC section 12). A session where too much of the capture is unclear must not
be scored as if it were clean - that would push a resident toward a flag on
nothing but bad lighting. `session_quality` is the rule that catches those
sessions before scoring sees them.
"""

from collections.abc import Sequence

from .contracts import Quality, StepEvent
from .recogniser import MIN_STEP_CONFIDENCE

#: Re-exported from `routine_watch.contracts`, where it is a field of the live
#: socket's `session_end` (`LiveSessionEnd.quality`): the stages read it from here,
#: beside the rule that decides it.
__all__ = ["Quality", "session_quality"]


def session_quality(
    events: Sequence[StepEvent],
    *,
    unclear_fraction: float = 0.4,
    min_events: int = 3,
) -> Quality:
    """`"unclear"` when `events` is too thin or too much of it is unclear or
    below `MIN_STEP_CONFIDENCE`, `"ok"` otherwise."""
    if len(events) < min_events:
        return "unclear"

    unclear = sum(1 for event in events if event.unclear or event.confidence < MIN_STEP_CONFIDENCE)
    if unclear > unclear_fraction * len(events):
        return "unclear"

    return "ok"
