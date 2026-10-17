"""Alert routes and nurse feedback (SPEC section 5, MVP 5, 7 and 8).

Split out of `api.py`: `GET /alerts`, `GET /alerts/{alert_id}` and
`POST /alerts/{alert_id}/feedback` share these helpers, kept together here.
The feedback store and the feedback-tuned flagged-residents list live on
`api_state.py`, imported here at module load time instead of reached back
into for on every call, so a reset there (`api_state.reset()`) is visible to
these routes without either module rebinding the other's state.

`errors_by_time_of_day` is filled in here too: the evening-only pattern (SPEC
section 7.5) is scored from a resident's own history rather than from the alert,
so the strip of evidence behind it is read off that same history at the route,
where the resident is at hand, instead of being stored on the alert record.
"""

from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, HTTPException
from pydantic import field_validator

from . import api_state
from .alerts import build_alerts
from .contracts import Alert, AlertFeedback, Feedback, TimeOfDay, TimeOfDayErrors
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

#: Days of the resident's own history the time-of-day strip is read over. Longer
#: than the flag window on purpose: two bad sessions cannot show "every evening",
#: so a recurring daily pattern needs a couple of weeks of her own days
#: (`pattern_features.TIME_OF_DAY_DAYS` reads the pattern itself over a shorter
#: window; this is the evidence behind it, and a nurse reads a fortnight).
TIME_OF_DAY_DAYS = 14

#: Where a day splits into the three parts a nurse reads off a shift: morning
#: before `AFTERNOON_START_HOUR`, afternoon until `EVENING_START_HOUR`, evening
#: from there on, in the hour the session's own timestamp carries (never this
#: machine's clock, so a replay buckets the same everywhere).
#: `pattern_features.EVENING_HOUR` cuts the same day in two at 16:00 for the
#: pattern's own morning-against-late-day comparison; these three are what the
#: strip shows, and no demo session starts between the two cuts.
AFTERNOON_START_HOUR = 12
EVENING_START_HOUR = 17


class AlertFeedbackIn(Feedback):
    """The feedback body as FastAPI checks it: the shared `contracts.Feedback`
    (`contracts/feedback.schema.json`, what the dashboard is written against) plus
    the one check a schema cannot make - that `cause` names a pattern the library
    really has, which is data that moves rather than shape.
    """

    @field_validator("cause")
    @classmethod
    def _known_cause(cls, value: str | None) -> str | None:
        if value is not None and value not in KNOWN_CAUSES:
            raise ValueError(
                f"unknown cause {value!r}: expected a pattern_id from the library "
                f'or "{OTHER_CAUSE}"'
            )
        return value


def _bucket_of(ts: datetime) -> TimeOfDay:
    """Which part of the day a session starting at `ts` belongs to."""
    if ts.hour < AFTERNOON_START_HOUR:
        return TimeOfDay.MORNING
    if ts.hour < EVENING_START_HOUR:
        return TimeOfDay.AFTERNOON
    return TimeOfDay.EVENING


def errors_by_time_of_day(
    sessions: list[dict], now: datetime, days: int = TIME_OF_DAY_DAYS
) -> list[TimeOfDayErrors] | None:
    """One resident's sessions and errors per part of the day, over the last `days`.

    The evidence behind an evening-only worsening (SPEC section 7.5): the pattern
    says a change is "consistent with" errors concentrated late in the day, and this
    is what lets a nurse see it. One entry per `TimeOfDay`, always in that order,
    even for a part of the day she never makes tea in - three bars with one empty is
    the shape of her day, and a bucket quietly left out would read as a zero.

    `sessions` are session records as `demo.demo_residents` serves them, so error
    counts only: self-corrected slips are already out of them, and so is a session
    somebody was assisting with, which is somebody else's hands as much as hers
    (SPEC section 7). Each session is bucketed by the hour its own timestamp
    carries, never this machine's clock, so a replay buckets the same anywhere.

    `None` when she has no sessions of her own in the window at all: there is no
    daily shape to show, so the strip is hidden rather than drawn empty.
    """
    window_start = now - timedelta(days=days)
    counted: dict[TimeOfDay, list[int]] = {bucket: [0, 0] for bucket in TimeOfDay}
    for session in sessions:
        if session.get("assisted", False):
            continue
        ts = datetime.fromisoformat(session["ts"])
        if not window_start < ts <= now:
            continue
        totals = counted[_bucket_of(ts)]
        totals[0] += 1
        totals[1] += sum(session.get("errors", {}).values())
    if not any(count for count, _ in counted.values()):
        return None
    return [
        TimeOfDayErrors(bucket=bucket, sessions=totals[0], errors=totals[1])
        for bucket, totals in counted.items()
    ]


def _alerts_by_id() -> dict[str, tuple[Alert, dict]]:
    """Every raw-flagged resident's alert and the resident it is about, keyed by id.

    Looks up by the raw flag rather than `api_state._flagged_residents()`'s
    feedback-tuned subset, so an alert a nurse has just tuned away with a "false
    alarm" (SPEC MVP 7) still resolves here: `GET /alerts/{id}` and a second
    feedback POST (the "what was it?" cause) must keep working on it even after
    `/alerts` stops listing it.

    The resident comes back with her alert because the payload needs her own
    sessions for the time-of-day strip, and `build_alerts` is given the same
    `demo_residents()` list it was built from rather than a second call to it.
    """
    residents = {
        resident["id"]: resident
        for resident in demo_residents()
        if resident["status"] == "flagged"
    }
    return {
        alert.alert_id: (alert, residents[alert.resident_id])
        for alert in build_alerts(
            list(residents.values()), feedback=api_state._feedback_store
        )
    }


def _alert_payload(alert: Alert, resident: dict) -> dict:
    """The alert as JSON: its feedback, its feedback-tuned threshold, and the
    time-of-day strip read off `resident`'s own history (SPEC section 7.5).

    The strip's window ends at the alert's own `created_at`, the clock the demo's
    history and its live session share (`demo.DEMO_NOW`), so the fortnight it shows
    is the fortnight behind the flag rather than whenever the route was called.
    """
    payload = alert.model_dump(mode="json")
    feedback = api_state._feedback_store.get(alert.alert_id)
    payload["feedback"] = feedback.model_dump(mode="json") if feedback else None
    payload["baseline"]["threshold"] = api_state._feedback_store.threshold(
        alert.resident_id, base=alert.baseline.threshold
    )
    buckets = errors_by_time_of_day(resident["sessions"], alert.created_at)
    payload["errors_by_time_of_day"] = (
        [bucket.model_dump(mode="json") for bucket in buckets] if buckets else None
    )
    return payload


@router.get("/alerts")
def list_alerts() -> list[dict]:
    """Every current alert (SPEC section 5, MVP 5): one per still-flagged resident."""
    residents = api_state._flagged_residents()
    by_id = {resident["id"]: resident for resident in residents}
    return [
        _alert_payload(alert, by_id[alert.resident_id])
        for alert in build_alerts(residents, feedback=api_state._feedback_store)
    ]


@router.get("/alerts/{alert_id}")
def get_alert(alert_id: str) -> dict:
    """One alert's full evidence: errors, baseline comparison and suggested checks."""
    alerts = _alerts_by_id()
    if alert_id not in alerts:
        raise HTTPException(status_code=404, detail="alert not found")
    return _alert_payload(*alerts[alert_id])


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
    alerts = _alerts_by_id()
    if alert_id not in alerts:
        raise HTTPException(status_code=404, detail="alert not found")
    alert, resident = alerts[alert_id]
    feedback = AlertFeedback(
        verdict=body.verdict,
        by=_FEEDBACK_BY,
        at=datetime.now(UTC),
        note=body.note,
        cause=body.cause,
    )
    api_state._feedback_store.record(
        alert_id,
        alert.resident_id,
        feedback,
        cause=feedback.cause,
        top_pattern=alert.patterns[0].pattern_id if alert.patterns else None,
    )
    return _alert_payload(alert, resident)
