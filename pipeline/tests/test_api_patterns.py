from fastapi.testclient import TestClient

from routine_watch.api import app
from routine_watch.patterns_library import LIBRARY


def test_list_patterns_returns_every_library_entry() -> None:
    with TestClient(app) as client:
        response = client.get("/patterns")

    assert response.status_code == 200
    body = response.json()
    assert [entry["pattern_id"] for entry in body] == [p.pattern_id for p in LIBRARY]


def test_list_patterns_entry_shape_and_wording() -> None:
    with TestClient(app) as client:
        body = client.get("/patterns").json()

    for entry in body:
        assert set(entry) == {
            "pattern_id",
            "name",
            "signals",
            "time_profile",
            "checks",
            "urgency",
            "source",
        }
        assert entry["signals"]
        assert all(isinstance(weight, (int, float)) for weight in entry["signals"].values())
        assert set(entry["time_profile"]) == {"onset_days", "tolerance_days", "note"}
        assert len(entry["time_profile"]["onset_days"]) == 2
        assert entry["checks"]
        assert all(isinstance(check, str) for check in entry["checks"])
        assert entry["urgency"] in {"routine", "next_round", "same_shift", "urgent"}
        # Never a diagnosis (SPEC §7.5): a cited rule, not a model guess.
        assert "diagnos" not in entry["name"].lower()
        assert "diagnos" not in entry["source"].lower()


def test_list_patterns_every_entry_has_a_non_empty_source() -> None:
    with TestClient(app) as client:
        body = client.get("/patterns").json()

    assert len(body) == len(LIBRARY)
    for entry in body:
        assert entry["source"].strip()


def test_list_patterns_includes_the_urgent_one_sided_pattern() -> None:
    with TestClient(app) as client:
        body = client.get("/patterns").json()

    by_id = {entry["pattern_id"]: entry for entry in body}
    assert by_id["one_sided_change"]["urgency"] == "urgent"
