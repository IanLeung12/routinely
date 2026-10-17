"""FastAPI backend (SPEC section 16, decisions B and C).

Takes events, sessions and downsampled skeletons from the pipeline, serves the nurse
dashboard, and carries the live view and alerts over one WebSocket.

Only /health exists so far; later tasks add the event, session and alert routes.
"""

from fastapi import FastAPI

from . import __version__

app = FastAPI(title="Routine Watch API", version=__version__)


@app.get("/health")
def health() -> dict[str, str]:
    """Liveness probe, used by the dashboard, scripts/e2e.sh and the tester."""
    return {"status": "ok", "version": __version__}
