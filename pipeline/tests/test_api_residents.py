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
        assert set(resident) == {"id", "name", "room", "status", "top_pattern", "scores"}
        assert resident["scores"]
        for point in resident["scores"]:
            assert set(point) == {"ts", "score"}

    by_id = {resident["id"]: resident for resident in body}
    assert by_id[MRS_K]["status"] == "watch"
    assert by_id[MRS_K]["name"] == "Mrs. K"


def test_flagged_and_watch_residents_show_their_top_pattern() -> None:
    """SPEC §9 screen 1 and demo step 6: each flagged or watch row names the pattern
    the change is consistent with; normal residents show nothing (no clear pattern)."""
    by_id = {resident["id"]: resident for resident in demo_residents()}

    sudden = by_id[MRS_K]["top_pattern"]
    assert sudden is not None
    assert sudden["pattern_id"] == "sudden_change"
    assert set(sudden) == {"pattern_id", "name", "urgency"}

    drift_resident = next(r for r in by_id.values() if r["status"] == "watch" and r["id"] != MRS_K)
    assert drift_resident["top_pattern"]["pattern_id"] == "slow_drift"

    normal_residents = [r for r in by_id.values() if r["status"] == "normal"]
    assert normal_residents
    assert all(r["top_pattern"] is None for r in normal_residents)


def test_mrs_k_flagged_still_shows_sudden_change(mrs_k_flagged) -> None:
    """A live session that flags Mrs. K keeps her top pattern, not just her watch
    status (SPEC section 10 beats 2-5)."""
    by_id = {resident["id"]: resident for resident in demo_residents()}
    assert by_id[MRS_K]["status"] == "flagged"
    assert by_id[MRS_K]["top_pattern"]["pattern_id"] == "sudden_change"


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


def test_resident_scoped_routes_404_for_unknown_id() -> None:
    """``_resident_or_404`` backs every resident-scoped route the same way."""
    with TestClient(app) as client:
        responses = [
            client.get("/residents/does-not-exist"),
            client.get("/residents/does-not-exist/drift"),
            client.get(
                "/residents/does-not-exist/normal_replay",
                params={"t_start": 0.0, "t_end": 1.0},
            ),
        ]

    for response in responses:
        assert response.status_code == 404
        assert response.json() == {"detail": "resident not found"}


def test_no_resident_is_flagged_by_default() -> None:
    """A live session is what flags mrs-k (SPEC section 10 beats 2-4, T124)."""
    statuses = [resident["status"] for resident in demo_residents()]
    assert statuses.count("flagged") == 0
