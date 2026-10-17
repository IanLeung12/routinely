"""Alert routes and nurse feedback (SPEC section 5, MVP 5, 7 and 8).

Split out of `api.py`: `GET /alerts`, `GET /alerts/{alert_id}` and
`POST /alerts/{alert_id}/feedback` share these helpers, kept together here.
The feedback store and the feedback-tuned flagged-residents list stay module
state on `api.py` (tests reset `api._feedback_store` directly), so every
lookup here goes back through `. import api` rather than caching either at
import time, or a test's reset would be invisible to these routes.
"""

from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, field_validator

from .alerts import build_alerts
from .contracts import Alert, AlertFeedback, FeedbackVerdict
from .demo import demo_residents
from .patterns_library import BY_ID as PATTERNS_BY_ID

router = APIRouter()

#: A nurse who saw a cause the pattern library has no pattern for answers with this.
OTHER_CAUSE = "other"

#: The MVP has no nurse logins yet; every one-tap feedback is logged under this name.
_FEEDBACK_BY = "nurse"

#: Every answer "what was it?" accepts (SPEC section 5, MVP 8): one of the library's
#: patterns, or "other". Anything else is a typo or a stale client, so it is a 422
#: rather than a cause nobody can count later.
KNOWN_CAUSES = frozenset(PATTERNS_BY_ID) | {OTHER_CAUSE}


class AlertFeedbackIn(BaseModel):
    """The one-tap feedback body (SPEC section 5, MVP 7), plus "what was it?" (MVP 8)."""

    verdict: FeedbackVerdict
    note: str | None = None
    cause: str | None = Field(
        default=None,
        description='The answer to "what was it?": a pattern_id, "other", or null for '
        "no answer.",
    )

    @field_validator("cause")
    @classmethod
    def _known_cause(cls, value: str | None) -> str | None:
        if value is not None and value not in KNOWN_CAUSES:
            raise ValueError(
                f"unknown cause {value!r}: expected a pattern_id from the library "
                f'or "{OTHER_CAUSE}"'
            )
        return value


def _alerts_by_id() -> dict[str, Alert]:
    """Every raw-flagged resident's alert, keyed by id.

    Looks up by the raw flag rather than `api._flagged_residents()`'s feedback-tuned
    subset, so an alert a nurse has just tuned away with a "false alarm" (SPEC MVP 7)
    still resolves here: `GET /alerts/{id}` and a second feedback POST (the "what was
    it?" cause) must keep working on it even after `/alerts` stops listing it.
    """
    from . import api

    residents = [resident for resident in demo_residents() if resident["status"] == "flagged"]
    return {
        alert.alert_id: alert
        for alert in build_alerts(residents, feedback=api._feedback_store)
    }


def _alert_payload(alert: Alert) -> dict:
    """The alert as JSON, with its feedback and feedback-tuned threshold applied."""
    from . import api

    payload = alert.model_dump(mode="json")
    feedback = api._feedback_store.get(alert.alert_id)
    payload["feedback"] = feedback.model_dump(mode="json") if feedback else None
    payload["baseline"]["threshold"] = api._feedback_store.threshold(
        alert.resident_id, base=alert.baseline.threshold
    )
    return payload


@router.get("/alerts")
def list_alerts() -> list[dict]:
    """Every current alert (SPEC section 5, MVP 5): one per still-flagged resident."""
    from . import api

    return [
        _alert_payload(alert)
        for alert in build_alerts(api._flagged_residents(), feedback=api._feedback_store)
    ]


@router.get("/alerts/{alert_id}")
def get_alert(alert_id: str) -> dict:
    """One alert's full evidence: errors, baseline comparison and suggested checks."""
    alerts = _alerts_by_id()
    if alert_id not in alerts:
        raise HTTPException(status_code=404, detail="alert not found")
    return _alert_payload(alerts[alert_id])


@router.post("/alerts/{alert_id}/feedback")
def post_alert_feedback(alert_id: str, body: AlertFeedbackIn) -> dict:
    """One-tap nurse feedback (SPEC section 5, MVP 7): tunes this resident's threshold.

    An optional `cause` is the answer to "what was it?" (MVP 8): the pattern the change
    turned out to be, or "other". It is logged against the resident and re-weights her
    pattern ranking on later alerts (Nice to have 8), together with the pattern this
    alert led with, which is what a "false alarm" is a false alarm on.

    Re-posting the same alert replaces its verdict and its cause rather than
    double-counting them.
    """
    from . import api

    alerts = _alerts_by_id()
    if alert_id not in alerts:
        raise HTTPException(status_code=404, detail="alert not found")
    alert = alerts[alert_id]
    feedback = AlertFeedback(
        verdict=body.verdict,
        by=_FEEDBACK_BY,
        at=datetime.now(UTC),
        note=body.note,
        cause=body.cause,
    )
    api._feedback_store.record(
        alert_id,
        alert.resident_id,
        feedback,
        cause=feedback.cause,
        top_pattern=alert.patterns[0].pattern_id if alert.patterns else None,
    )
    return _alert_payload(alert)
