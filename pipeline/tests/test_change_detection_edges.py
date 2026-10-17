from datetime import datetime, timedelta

import pytest

from routine_watch.change_detection import build_baseline, flag_change

NOW = datetime(2026, 1, 1, 12, 0, 0)


def test_two_bad_sessions_exactly_48h_apart_flag():
    """window_start = now - 48h is inclusive, so a session exactly 48h before now counts."""
    baseline = build_baseline([1.0, 1.0, 1.0])
    sessions = [
        (NOW - timedelta(hours=48), 10.0),
        (NOW - timedelta(hours=1), 10.0),
    ]
    assert flag_change(sessions, baseline, NOW) is True


def test_unsorted_sessions_match_sorted_result():
    baseline = build_baseline([1.0, 1.0, 1.0])
    sorted_sessions = [
        (NOW - timedelta(hours=40), 10.0),
        (NOW - timedelta(hours=20), 10.0),
        (NOW - timedelta(hours=1), 1.0),
    ]
    unsorted_sessions = [sorted_sessions[2], sorted_sessions[0], sorted_sessions[1]]
    assert flag_change(unsorted_sessions, baseline, NOW) == flag_change(
        sorted_sessions, baseline, NOW
    )


def test_fewer_than_three_history_scores_raises():
    with pytest.raises(ValueError):
        build_baseline([1.0, 2.0])


def test_score_exactly_at_threshold_never_counts():
    baseline = build_baseline([1.0, 1.0, 1.0])
    sessions = [
        (NOW - timedelta(hours=1), baseline.threshold),
        (NOW - timedelta(hours=2), baseline.threshold),
    ]
    assert flag_change(sessions, baseline, NOW) is False


def test_three_bad_sessions_within_48h_flag():
    baseline = build_baseline([1.0, 1.0, 1.0])
    sessions = [
        (NOW - timedelta(hours=40), 10.0),
        (NOW - timedelta(hours=20), 10.0),
        (NOW - timedelta(hours=1), 10.0),
    ]
    assert flag_change(sessions, baseline, NOW) is True
