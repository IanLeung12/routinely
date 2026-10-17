from fastapi.testclient import TestClient

from routine_watch.api import app

MRS_K = "mrs-k"
MR_CHEN = "mr-chen"
MRS_AHMED = "mrs-ahmed"


def test_resident_drift_returns_expected_shape() -> None:
    with TestClient(app) as client:
        response = client.get(f"/residents/{MRS_K}/drift")

    assert response.status_code == 200
    body = response.json()
    assert set(body) == {"resident_id", "slope_per_day", "days", "trending"}
    assert body["resident_id"] == MRS_K
    assert isinstance(body["slope_per_day"], float)
    assert isinstance(body["days"], int)
    assert isinstance(body["trending"], bool)


def test_resident_drift_404s_for_unknown_id() -> None:
    with TestClient(app) as client:
        response = client.get("/residents/does-not-exist/drift")

    assert response.status_code == 404


def test_drift_resident_is_trending() -> None:
    with TestClient(app) as client:
        response = client.get(f"/residents/{MR_CHEN}/drift")

    assert response.status_code == 200
    assert response.json()["trending"] is True


def test_spike_resident_is_not_trending() -> None:
    with TestClient(app) as client:
        response = client.get(f"/residents/{MRS_K}/drift")

    assert response.status_code == 200
    assert response.json()["trending"] is False


def test_stable_resident_is_not_trending() -> None:
    with TestClient(app) as client:
        response = client.get(f"/residents/{MRS_AHMED}/drift")

    assert response.status_code == 200
    assert response.json()["trending"] is False
