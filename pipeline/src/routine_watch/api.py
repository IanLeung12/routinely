"""FastAPI backend (SPEC section 16, decisions B and C).

Takes events, sessions and downsampled skeletons from the pipeline, serves the nurse
dashboard, and carries the live view and alerts over one WebSocket.

/health and the demo /residents routes exist so far; later tasks add the event,
session and alert routes backed by a real database.
"""

from fastapi import FastAPI, HTTPException

from . import __version__
from .demo import demo_residents

app = FastAPI(title="Routine Watch API", version=__version__)

#: What the unit-overview list shows, vs. the fuller resident-detail payload.
_SUMMARY_FIELDS = ("id", "name", "room", "status", "scores")


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
