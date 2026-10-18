"""FastAPI backend (SPEC section 16, decisions B and C).

Takes events, sessions and downsampled skeletons from the pipeline, serves the nurse
dashboard, and carries the live view and alerts over one WebSocket.

/health, the demo /residents routes, the /alerts routes, the /routines builder, the
safety check-ins and the live WebSocket exist so far; later tasks add the event and
session routes backed by a real database.

The app's lifespan owns one background task: the safety check-in countdown
(`api_checkin.tick_forever`, SPEC §18). It is the server, not a screen, that counts
down to an alarm, so it has to keep counting with nobody connected.
"""

import asyncio
import contextlib
import os
from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from . import __version__, api_checkin, session_log
from .api_alerts import KNOWN_CAUSES, OTHER_CAUSE, AlertFeedbackIn  # noqa: F401 (re-export)
from .api_alerts import router as _alerts_router
from .api_checkin import router as _checkin_router
from .api_live import router as _live_router
from .api_residents import router as _residents_router
from .api_routines import router as _routines_router
from .api_state import _feedback_store
from .checkin import get_checkin_store
from .demo import DEMO_NOW
from .evidence import reset_demo_replays
from .handoff import DEFAULT_WINDOW_H, build_handoff
from .monitoring import get_monitoring_store


@contextlib.asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    """Run the safety check-in countdown for as long as the app is up (SPEC §18).

    One asyncio task, ticking once a second: it is what fires a check-in's alarm when
    the person does not answer and passes it down their supporter list when nobody
    acknowledges, whether or not any screen is still connected (Project KAZE's
    connectivity failure). It is stopped and awaited on shutdown, so a test client
    leaves nothing running behind it.
    """
    ticker = asyncio.create_task(api_checkin.tick_forever())
    try:
        yield
    finally:
        ticker.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await ticker


app = FastAPI(title="Routinely API", version=__version__, lifespan=lifespan)
app.include_router(_live_router)
app.include_router(_alerts_router)
app.include_router(_residents_router)
app.include_router(_routines_router)
app.include_router(_checkin_router)

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

    Forgets every live session recorded against a demo resident, every logged nurse
    feedback, every kept replay and every safety check-in (SPEC §18), so a rehearsal's
    flag - or the skeleton of the attempt behind it (SPEC section 17) - doesn't linger
    into the next run. Only
    reachable with `OFFLINE_MODE=true` or `DEMO_RESET=1`, so it can't wipe a real
    deployment's state; 404 otherwise, as if the route didn't exist.
    """
    if not _demo_reset_enabled():
        raise HTTPException(status_code=404, detail="not found")
    session_log.reset()
    _feedback_store.reset()
    get_monitoring_store().reset()
    reset_demo_replays()
    get_checkin_store().reset()
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
