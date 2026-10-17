"""Bounds on `GET /handoff?hours=` (T268): the route declares `Query(ge=1, le=168)`
but nothing exercised the edges of that range."""

import pytest
from fastapi.testclient import TestClient

from routine_watch.api import app


@pytest.mark.parametrize("hours", [1, 168])
def test_route_accepts_the_edges_of_its_window(hours: int) -> None:
    with TestClient(app) as client:
        response = client.get("/handoff", params={"hours": hours})

    assert response.status_code == 200
    body = response.json()
    assert body["window_hours"] == hours
    assert "diagnos" not in body["summary"].lower()


@pytest.mark.parametrize("hours", [0, 169])
def test_route_rejects_just_outside_its_window(hours: int) -> None:
    with TestClient(app) as client:
        response = client.get("/handoff", params={"hours": hours})

    assert response.status_code == 422
