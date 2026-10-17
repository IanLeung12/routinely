"""FastAPI backend (SPEC section 16, decisions B and C).

Takes events, sessions and downsampled skeletons from the pipeline, serves the nurse
dashboard, and carries the live view and alerts over one WebSocket.

/health, the demo /residents routes, the /alerts routes and the live WebSocket exist
so far; later tasks add the event and session routes backed by a real database.
"""

import os
from typing import Annotated

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from . import __version__, session_log
from .alerts import top_pattern_for
from .api_alerts import KNOWN_CAUSES, OTHER_CAUSE, AlertFeedbackIn  # noqa: F401 (re-export)
from .api_alerts import router as _alerts_router
from .api_live import router as _live_router
from .api_residents import router as _residents_router
from .demo import DEMO_NOW, demo_residents, status_for
from .feedback import FeedbackStore
from .handoff import DEFAULT_WINDOW_H, build_handoff
from .monitoring import get_monitoring_store

app = FastAPI(title="Routine Watch API", version=__version__)
app.include_router(_live_router)
app.include_router(_alerts_router)
app.include_router(_residents_router)

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
    get_monitoring_store().reset()
    return {"ok": True}


@app.get("/handoff")
def shift_handoff(hours: Annotated[int, Query(ge=1, le=168)] = DEFAULT_WINDOW_H) -> dict:
    """Shift handoff (SPEC section 9): who changed in the `hours` before now.

    One row per resident - sessions flagged for review, alerts nobody has reviewed yet
    and whether their score is trending up - plus a plain-language summary of the whole
    window (`routine_watch.handoff`). The window ends at the demo's clock, which is also
    what a live session is recorded against, so a session played on stage is inside it.
    """
    return build_handoff(DEMO_NOW, hours, feedback=_feedback_store)
