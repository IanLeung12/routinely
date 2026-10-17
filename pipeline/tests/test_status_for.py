"""Raw flag thresholds preserve each demo resident's own status."""

import pytest

from routine_watch.demo import DEMO_RESIDENT, demo_residents, status_for


def test_raw_threshold_preserves_demo_status() -> None:
    for resident in demo_residents():
        assert status_for(resident, resident["baseline"]["threshold"]) == resident["status"], (
            resident["id"]
        )


def test_raw_threshold_preserves_status_after_live_tea(mrs_k_flagged) -> None:
    residents = demo_residents()
    assert next(r for r in residents if r["id"] == DEMO_RESIDENT)["status"] == "flagged"
    for resident in residents:
        assert status_for(resident, resident["baseline"]["threshold"]) == resident["status"], (
            resident["id"]
        )


@pytest.mark.parametrize("live_tea", [False, True], ids=["seeded", "live-tea"])
def test_high_threshold_never_flags(live_tea, request) -> None:
    if live_tea:
        request.getfixturevalue("mrs_k_flagged")
    for resident in demo_residents():
        assert status_for(resident, 1e9) != "flagged", resident["id"]
