from fastapi.testclient import TestClient

from routine_watch import __version__
from routine_watch.api import app


def test_health_is_ok() -> None:
    with TestClient(app) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "version": __version__}
