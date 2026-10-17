from fastapi.testclient import TestClient

from routine_watch.api import app
from routine_watch.demo import demo_residents

MRS_K = "mrs-k"


def test_demo_residents_is_deterministic() -> None:
    assert demo_residents() == demo_residents()


def test_demo_residents_has_a_spike_a_drift_and_normals() -> None:
    statuses = {resident["id"]: resident["status"] for resident in demo_residents()}
    # Her seeded history leaves her on watch; a live session is what flags her
    # (SPEC section 10 beats 2-4, T124).
    assert statuses[MRS_K] == "watch"
    assert sum(1 for status in statuses.values() if status == "normal") >= 1
    assert len(statuses) >= 3


def test_list_residents_returns_summary_fields() -> None:
    with TestClient(app) as client:
        response = client.get("/residents")

    assert response.status_code == 200
    body = response.json()
    assert len(body) == len(demo_residents())
    for resident in body:
        assert set(resident) == {"id", "name", "room", "status", "scores"}
        assert resident["scores"]
        for point in resident["scores"]:
            assert set(point) == {"ts", "score"}

    by_id = {resident["id"]: resident for resident in body}
    assert by_id[MRS_K]["status"] == "watch"
    assert by_id[MRS_K]["name"] == "Mrs. K"


def test_get_resident_returns_detail() -> None:
    with TestClient(app) as client:
        response = client.get(f"/residents/{MRS_K}")

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == MRS_K
    assert body["status"] == "watch"
    assert body["sessions"]
    assert body["care_records"]
    assert set(body["baseline"]) == {"mean", "std", "threshold"}


def test_get_resident_404s_for_unknown_id() -> None:
    with TestClient(app) as client:
        response = client.get("/residents/does-not-exist")

    assert response.status_code == 404


def test_no_resident_is_flagged_by_default() -> None:
    """A live session is what flags mrs-k (SPEC section 10 beats 2-4, T124)."""
    statuses = [resident["status"] for resident in demo_residents()]
    assert statuses.count("flagged") == 0
