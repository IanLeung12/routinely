"""Shared API state (SPEC MVP 7, Nice to have 8): no FastAPI app import here.

`api.py`, `api_residents.py` and `api_alerts.py` all need the nurse feedback
store and the helpers that fold it into a resident's status. Kept here, not on
`api.py`, so a router reaches this directly at module load time instead of
reaching back into the module that imports it from inside every handler (a
circular import hidden there).

A reset (`/demo/reset`, and every test fixture that wants a clean store)
calls `reset()`, which mutates `_feedback_store` in place. Nothing here
rebinds the module global itself: a caller that imported `_feedback_store`
directly (as every route here does) would otherwise keep pointing at the
old, un-reset store.
"""

from .alerts import top_pattern_for
from .demo import demo_residents, status_for
from .feedback import FeedbackStore

#: What the unit-overview list shows, vs. the fuller resident-detail payload.
_SUMMARY_FIELDS = ("id", "name", "room", "status", "top_pattern", "scores")

#: In-memory only (SPEC MVP 7): no DB, so feedback resets when the API restarts.
_feedback_store = FeedbackStore()


def reset() -> None:
    """Forget every logged nurse feedback answer (SPEC MVP 7 and 8), in place."""
    _feedback_store.reset()


def _tuned(resident: dict) -> dict:
    """`resident`, with its status (and `top_pattern`) recomputed against this
    resident's feedback-tuned threshold (SPEC MVP 7) instead of the raw baseline
    one, so `/residents` and `/alerts` agree with `/handoff` and the alert payload
    once a nurse's feedback moves the bar a session is judged against.
    """
    threshold = _feedback_store.threshold(resident["id"], base=resident["baseline"]["threshold"])
    status = status_for(resident, threshold)
    top_pattern = _top_pattern(resident) if status != "normal" else None
    return {**resident, "status": status, "top_pattern": top_pattern}


def _top_pattern(resident: dict) -> dict | None:
    """This resident's overview pattern chip, ranked by her own nurses' answers.

    `demo.py` ranks the patterns with no weights, so once a nurse has answered "what
    was it?" the raw field and this resident's alert can name different patterns for
    the same change (SPEC Nice to have 8). With answers logged, rank it the way her
    alert does (`alerts.top_pattern_for`); with none the two already agree, so the raw
    field stands and `/residents` does no extra work for a unit nobody has answered
    about yet.
    """
    if not _feedback_store.pattern_weights(resident["id"]):
        return resident["top_pattern"]
    return top_pattern_for(resident, _feedback_store)


def _flagged_residents() -> list[dict]:
    """Residents still flagged once their nurse-feedback-tuned threshold applies:
    what `/alerts` builds alerts from, so feedback that tunes an alert away takes it
    off the list rather than leaving it to show against a threshold it no longer
    clears. Only ever a subset of the raw-flagged residents, so this never asks
    `build_alerts` to build an alert for a resident whose raw threshold it never
    qualified against.
    """
    return [
        resident
        for resident in demo_residents()
        if resident["status"] == "flagged" and _tuned(resident)["status"] == "flagged"
    ]
