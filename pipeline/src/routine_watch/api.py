"""FastAPI backend (SPEC section 16, decisions B and C).

Takes events, sessions and downsampled skeletons from the pipeline, serves the nurse
dashboard, and carries the live view and alerts over one WebSocket.

/health, the demo /residents routes, the /alerts routes and the live WebSocket exist
so far; later tasks add the event and session routes backed by a real database.
"""

from collections import defaultdict
from datetime import UTC, date, datetime
from statistics import mean
from typing import Annotated

from fastapi import FastAPI, HTTPException, Query, WebSocket, WebSocketDisconnect
from pydantic import BaseModel

from . import __version__
from .alerts import build_alerts
from .contracts import Alert, AlertFeedback, FeedbackVerdict
from .demo import demo_residents
from .drift import drift
from .evidence import EvidenceError, normal_replay_frames, replay_frames
from .feedback import FeedbackStore
from .live import SCENARIO_NOT_FOUND, as_json, scenario_path, session_messages
from .replay import ReplayError

app = FastAPI(title="Routine Watch API", version=__version__)

#: What the unit-overview list shows, vs. the fuller resident-detail payload.
_SUMMARY_FIELDS = ("id", "name", "room", "status", "scores")

#: In-memory only (SPEC MVP 7): no DB, so feedback resets when the API restarts.
_feedback_store = FeedbackStore()

#: The MVP has no nurse logins yet; every one-tap feedback is logged under this name.
_FEEDBACK_BY = "nurse"


class AlertFeedbackIn(BaseModel):
    """The one-tap feedback body (SPEC section 5, MVP 7)."""

    verdict: FeedbackVerdict
    note: str | None = None


def _daily_scores(scores: list[dict]) -> list[tuple[date, float]]:
    """Mean score per calendar date, for `drift.drift` (one point per day)."""
    by_day: dict[date, list[float]] = defaultdict(list)
    for entry in scores:
        day = datetime.fromisoformat(entry["ts"]).date()
        by_day[day].append(entry["score"])
    return sorted((day, mean(values)) for day, values in by_day.items())


def _alerts_by_id() -> dict[str, Alert]:
    return {alert.alert_id: alert for alert in build_alerts(demo_residents())}


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


@app.get("/residents")
def list_residents() -> list[dict]:
    """Unit overview (SPEC section 9): status chip and sparkline per resident."""
    return [{field: resident[field] for field in _SUMMARY_FIELDS} for resident in demo_residents()]


@app.get("/residents/{resident_id}")
def get_resident(resident_id: str) -> dict:
    """Resident detail (SPEC section 9): sessions, care records and baseline."""
    for resident in demo_residents():
        if resident["id"] == resident_id:
            return resident
    raise HTTPException(status_code=404, detail="resident not found")


@app.get("/residents/{resident_id}/drift")
def resident_drift(resident_id: str) -> dict:
    """Daily score trend (SPEC section 8): backs the drift card with one point per day."""
    for resident in demo_residents():
        if resident["id"] == resident_id:
            result = drift(_daily_scores(resident["scores"]))
            return {
                "resident_id": resident_id,
                "slope_per_day": result.slope_per_day,
                "days": result.days,
                "trending": result.trending,
            }
    raise HTTPException(status_code=404, detail="resident not found")


@app.get("/alerts")
def list_alerts() -> list[dict]:
    """Every current alert (SPEC section 5, MVP 5): one per flagged resident."""
    return [_alert_payload(alert) for alert in build_alerts(demo_residents())]


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

    Re-posting the same alert replaces its verdict rather than double-counting it.
    """
    alerts = _alerts_by_id()
    if alert_id not in alerts:
        raise HTTPException(status_code=404, detail="alert not found")
    alert = alerts[alert_id]
    feedback = AlertFeedback(
        verdict=body.verdict, by=_FEEDBACK_BY, at=datetime.now(UTC), note=body.note
    )
    _feedback_store.record(alert_id, alert.resident_id, feedback)
    return _alert_payload(alert)


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
