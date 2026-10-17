import pytest
from fastapi.testclient import TestClient

from routine_watch.api import app

UNKNOWN = "nobody"

RESIDENT_ROUTES = [
    f"/residents/{UNKNOWN}",
    f"/residents/{UNKNOWN}/drift",
    f"/residents/{UNKNOWN}/feedback",
    f"/residents/{UNKNOWN}/normal_replay?t_start=0&t_end=1",
]


@pytest.mark.parametrize("path", RESIDENT_ROUTES)
def test_unknown_resident_returns_404(path: str) -> None:
    with TestClient(app) as client:
        response = client.get(path)

    assert response.status_code == 404
    assert "detail" in response.json()
