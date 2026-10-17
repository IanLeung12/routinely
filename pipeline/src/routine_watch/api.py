"""FastAPI backend (SPEC section 16, decisions B and C).

Takes events, sessions and downsampled skeletons from the pipeline, serves the nurse
dashboard, and carries the live view and alerts over one WebSocket.

/health, the demo /residents routes, the /alerts routes and the live WebSocket exist
so far; later tasks add the event and session routes backed by a real database.
"""

import os
from datetime import UTC, datetime
from typing import Annotated

from fastapi import FastAPI, HTTPException, Query, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, field_validator

from . import __version__, session_log
from .alerts import build_alerts
from .contracts import Alert, AlertFeedback, FeedbackVerdict
from .demo import DEMO_NOW, demo_residents, status_for
from .drift import daily_scores, drift
from .evidence import EvidenceError, normal_replay_frames, replay_frames
from .feedback import FeedbackStore
from .handoff import DEFAULT_WINDOW_H, build_handoff
from .live import SCENARIO_NOT_FOUND, as_json, scenario_path, session_messages
from .patterns_library import BY_ID as PATTERNS_BY_ID
from .replay import ReplayError

app = FastAPI(title="Routine Watch API", version=__version__)

#: The dashboard's origin(s), so the browser's CORS check lets fetch() through
#: (SPEC section 16): comma-separated, defaults to the dev dashboard's origin.
_CORS_ORIGINS = [
    origin.strip()
    for origin in os.environ.get("CORS_ORIGINS", "http://localhost:5173").split(",")
    if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_CORS_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)

#: What the unit-overview list shows, vs. the fuller resident-detail payload.
_SUMMARY_FIELDS = ("id", "name", "room", "status", "top_pattern", "scores")

#: In-memory only (SPEC MVP 7): no DB, so feedback resets when the API restarts.
_feedback_store = FeedbackStore()

#: The MVP has no nurse logins yet; every one-tap feedback is logged under this name.
_FEEDBACK_BY = "nurse"

#: A nurse who saw a cause the pattern library has no pattern for answers with this.
OTHER_CAUSE = "other"

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


def _tuned(resident: dict) -> dict:
    """`resident`, with its status (and `top_pattern`) recomputed against this
    resident's feedback-tuned threshold (SPEC MVP 7) instead of the raw baseline
    one, so `/residents` and `/alerts` agree with `/handoff` and the alert payload
    once a nurse's feedback moves the bar a session is judged against.
    """
    threshold = _feedback_store.threshold(resident["id"], base=resident["baseline"]["threshold"])
    status = status_for(resident, threshold)
    top_pattern = resident["top_pattern"] if status != "normal" else None
    return {**resident, "status": status, "top_pattern": top_pattern}


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


def _alerts_by_id() -> dict[str, Alert]:
    """Every raw-flagged resident's alert, keyed by id.

    Looks up by the raw flag rather than `_flagged_residents()`'s feedback-tuned
    subset, so an alert a nurse has just tuned away with a "false alarm" (SPEC MVP 7)
    still resolves here: `GET /alerts/{id}` and a second feedback POST (the "what was
    it?" cause) must keep working on it even after `/alerts` stops listing it.
    """
    residents = [resident for resident in demo_residents() if resident["status"] == "flagged"]
    return {
        alert.alert_id: alert
        for alert in build_alerts(residents, feedback=_feedback_store)
    }


def _alert_payload(alert: Alert) -> dict:
    """The alert as JSON, with its feedback and feedback-tuned threshold applied."""
    payload = alert.model_dump(mode="json")
    feedback = _feedback_store.get(alert.alert_id)
    payload["feedback"] = feedback.model_dump(mode="json") if feedback else None
    payload["baseline"]["threshold"] = _feedback_store.threshold(
        alert.resident_id, base=alert.baseline.threshold
    )
    return payload


@app.get("/health")
def health() -> dict[str, str]:
    """Liveness probe, used by the dashboard, scripts/e2e.sh and the tester."""
    return {"status": "ok", "version": __version__}


def _demo_reset_enabled() -> bool:
    """Whether `/demo/reset` is reachable: offline demo/dev stacks only (SPEC §10, §13)."""
    return os.environ.get("OFFLINE_MODE", "").lower() == "true" or os.environ.get(
        "DEMO_RESET"
    ) == "1"


@app.post("/demo/reset")
def demo_reset() -> dict[str, bool]:
    """Put the demo back to its seeded history (SPEC §10, §13).

    Forgets every live session recorded against a demo resident and every logged
    nurse feedback, so a rehearsal's flag doesn't linger into the next run. Only
    reachable with `OFFLINE_MODE=true` or `DEMO_RESET=1`, so it can't wipe a real
    deployment's state; 404 otherwise, as if the route didn't exist.
    """
    if not _demo_reset_enabled():
        raise HTTPException(status_code=404, detail="not found")
    session_log.reset()
    _feedback_store.reset()
    return {"ok": True}


@app.get("/residents")
def list_residents() -> list[dict]:
    """Unit overview (SPEC section 9): status chip and sparkline per resident."""
    return [
        {field: resident[field] for field in _SUMMARY_FIELDS}
        for resident in (_tuned(resident) for resident in demo_residents())
    ]


def _resident_or_404(resident_id: str) -> dict:
    """The demo resident with this id, or a 404 (SPEC section 9)."""
    for resident in demo_residents():
        if resident["id"] == resident_id:
            return resident
    raise HTTPException(status_code=404, detail="resident not found")


@app.get("/residents/{resident_id}")
def get_resident(resident_id: str) -> dict:
    """Resident detail (SPEC section 9): sessions, care records and baseline."""
    return _tuned(_resident_or_404(resident_id))


@app.get("/residents/{resident_id}/drift")
def resident_drift(resident_id: str) -> dict:
    """Daily score trend (SPEC section 8): backs the drift card with one point per day."""
    resident = _resident_or_404(resident_id)
    result = drift(daily_scores(resident["scores"]))
    return {
        "resident_id": resident_id,
        "slope_per_day": result.slope_per_day,
        "days": result.days,
        "trending": result.trending,
    }


@app.get("/alerts")
def list_alerts() -> list[dict]:
    """Every current alert (SPEC section 5, MVP 5): one per still-flagged resident."""
    return [
        _alert_payload(alert)
        for alert in build_alerts(_flagged_residents(), feedback=_feedback_store)
    ]


@app.get("/alerts/{alert_id}")
def get_alert(alert_id: str) -> dict:
    """One alert's full evidence: errors, baseline comparison and suggested checks."""
    alerts = _alerts_by_id()
    if alert_id not in alerts:
        raise HTTPException(status_code=404, detail="alert not found")
    return _alert_payload(alerts[alert_id])


@app.post("/alerts/{alert_id}/feedback")
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
    alert = alerts[alert_id]
    feedback = AlertFeedback(
        verdict=body.verdict,
        by=_FEEDBACK_BY,
        at=datetime.now(UTC),
        note=body.note,
        cause=body.cause,
    )
    _feedback_store.record(
        alert_id,
        alert.resident_id,
        feedback,
        cause=feedback.cause,
        top_pattern=alert.patterns[0].pattern_id if alert.patterns else None,
    )
    return _alert_payload(alert)


@app.get("/handoff")
def shift_handoff(hours: Annotated[int, Query(ge=1, le=168)] = DEFAULT_WINDOW_H) -> dict:
    """Shift handoff (SPEC section 9): who changed in the `hours` before now.

    One row per resident - sessions flagged for review, alerts nobody has reviewed yet
    and whether their score is trending up - plus a plain-language summary of the whole
    window (`routine_watch.handoff`). The window ends at the demo's clock, which is also
    what a live session is recorded against, so a session played on stage is inside it.
    """
    return build_handoff(DEMO_NOW, hours, feedback=_feedback_store)


@app.get("/sessions/{session_id}/replay")
def session_replay(
    session_id: str,
    t_start: Annotated[float, Query(ge=0.0)],
    t_end: Annotated[float, Query(ge=0.0)],
    fps: Annotated[float, Query(gt=0)] = 10.0,
) -> dict:
    """Skeleton-frame evidence for one window of one session (SPEC section 8)."""
    try:
        frames = replay_frames(session_id, t_start, t_end, fps=fps)
    except EvidenceError:
        raise HTTPException(status_code=404, detail="session not found") from None
    return {
        "session_id": session_id,
        "frames": [frame.model_dump(mode="json") for frame in frames],
    }


@app.get("/residents/{resident_id}/normal_replay")
def resident_normal_replay(
    resident_id: str,
    t_start: Annotated[float, Query(ge=0.0)],
    t_end: Annotated[float, Query(ge=0.0)],
) -> dict:
    """A normal session's skeleton frames, for the evidence view's ghost layer."""
    try:
        frames = normal_replay_frames(resident_id, t_start, t_end)
    except EvidenceError:
        raise HTTPException(status_code=404, detail="resident not found") from None
    return {
        "resident_id": resident_id,
        "frames": [frame.model_dump(mode="json") for frame in frames],
    }


@app.websocket("/ws/live")
async def live_session(
    websocket: WebSocket,
    scenario: str = "",
    speed: Annotated[float, Query(gt=0)] = 1.0,
) -> None:
    """The live view and its alerts, on one socket (SPEC section 16, decision B).

    Plays the recorded scenario named by `?scenario=` through the pipeline in real
    time, `?speed=` times as fast: frames, steps, the task map, errors as they are
    classified, then the session's score and flag (`routine_watch.live`). That is also
    the demo's fallback for a camera that fails (SPEC section 10), and the camera
    plugs into the same generator later.

    An unknown scenario closes with 4404, and the socket closes normally when the
    session ends.
    """
    await websocket.accept()
    try:
        async for message in session_messages(scenario_path(scenario), speed=speed):
            await websocket.send_json(as_json(message))
    except ReplayError:
        await websocket.close(code=SCENARIO_NOT_FOUND)
        return
    except WebSocketDisconnect:  # the dashboard closed the tab mid-session
        return
    await websocket.close()
