import copy

from routine_watch.alerts import top_pattern_for
from routine_watch.demo import demo_residents


def test_top_pattern_for_matches_demo_top_pattern() -> None:
    for resident in demo_residents():
        if resident["top_pattern"] is None:
            continue
        result = top_pattern_for(resident)
        assert result["pattern_id"] == resident["top_pattern"]["pattern_id"]


def test_top_pattern_for_returns_expected_keys() -> None:
    for resident in demo_residents():
        if resident["top_pattern"] is None:
            continue
        result = top_pattern_for(resident)
        assert set(result) == {"pattern_id", "name", "urgency"}
        assert isinstance(result["urgency"], str)


def test_top_pattern_for_returns_none_below_threshold() -> None:
    resident = copy.deepcopy(demo_residents()[0])
    for session in resident["sessions"]:
        session["errors"] = {}
    resident["care_records"] = []

    assert top_pattern_for(resident) is None
