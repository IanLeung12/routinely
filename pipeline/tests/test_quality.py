"""Session quality (SPEC section 12): thin or mostly-unclear sessions are unclear,
never scored as if they were clean."""

from __future__ import annotations

from routine_watch.contracts import ObjectLabel, StepEvent, StepSource
from routine_watch.quality import session_quality

SESSION = "session-1"


def _event(index: int, *, confidence: float = 0.9, unclear: bool = False) -> StepEvent:
    return StepEvent(
        event_id=f"{SESSION}:step@{index}",
        session_id=SESSION,
        step_id="boil",
        objects=[ObjectLabel.KETTLE],
        t_start=float(index),
        t_end=float(index) + 1.0,
        confidence=confidence,
        source=StepSource.RULE,
        unclear=unclear,
    )


def _events(n: int, *, n_unclear: int = 0) -> list[StepEvent]:
    return [_event(i, confidence=0.3, unclear=True) for i in range(n_unclear)] + [
        _event(i) for i in range(n_unclear, n)
    ]


def test_clean_session_is_ok():
    assert session_quality(_events(10)) == "ok"


def test_half_unclear_session_is_unclear():
    assert session_quality(_events(10, n_unclear=5)) == "unclear"


def test_too_few_events_is_unclear():
    assert session_quality(_events(2)) == "unclear"


def test_exactly_at_the_fraction_is_ok():
    events = _events(10, n_unclear=4)
    assert session_quality(events, unclear_fraction=0.4) == "ok"


def test_low_confidence_without_unclear_flag_still_counts():
    events = [_event(i, confidence=0.3, unclear=False) for i in range(3)] + [
        _event(i) for i in range(3, 10)
    ]
    assert session_quality(events, unclear_fraction=0.2) == "unclear"
