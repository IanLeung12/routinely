from routine_watch.contracts import PatternUrgency
from routine_watch.demo import demo_residents
from routine_watch.patterns_library import BY_ID


def test_demo_top_pattern_is_only_set_for_non_normal_residents():
    residents = demo_residents()
    normal = [resident for resident in residents if resident["status"] == "normal"]
    non_normal = [resident for resident in residents if resident["status"] != "normal"]

    assert normal
    assert non_normal
    for resident in normal:
        assert resident["top_pattern"] is None, resident["id"]

    valid_urgencies = {urgency.value for urgency in PatternUrgency}
    for resident in non_normal:
        assert resident["status"] in {"watch", "flagged"}
        pattern = resident["top_pattern"]
        if pattern is None:
            continue
        assert isinstance(pattern, dict), resident["id"]
        assert set(pattern) == {"pattern_id", "name", "urgency"}, resident["id"]
        assert pattern["pattern_id"] in BY_ID, resident["id"]
        assert pattern["urgency"] in valid_urgencies, resident["id"]

    mrs_k = next(resident for resident in residents if resident["id"] == "mrs-k")
    assert mrs_k["top_pattern"] is not None
