"""Pattern ids must remain safe, unambiguous feedback causes."""

import re

from routine_watch import api
from routine_watch.patterns_library import BY_ID, LIBRARY


def test_pattern_ids_are_unique():
    pattern_ids = [pattern.pattern_id for pattern in LIBRARY]
    assert len(pattern_ids) == len(set(pattern_ids)) == len(BY_ID)


def test_pattern_ids_are_safe_feedback_causes():
    for pattern_id in BY_ID:
        assert re.fullmatch(r"[a-z][a-z0-9_]*", pattern_id), pattern_id
        assert pattern_id != api.OTHER_CAUSE


def test_known_causes_match_pattern_ids_and_other():
    assert api.OTHER_CAUSE == "other"
    assert api.KNOWN_CAUSES == set(BY_ID) | {"other"}
