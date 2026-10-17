from datetime import datetime, timedelta

import pytest

from routine_watch.change_detection import build_baseline, flag_change

NOW = datetime(2026, 1, 1, 12, 0, 0)


def test_build_baseline_requires_three_scores():
    with pytest.raises(ValueError):
        build_baseline([1.0, 2.0])


def test_build_baseline_all_zero_uses_min_std_floor():
    baseline = build_baseline([0.0, 0.0, 0.0])
    assert baseline.mean == 0.0
    assert baseline.std == 0.0
    assert baseline.threshold == 1.0


def test_one_bad_session_never_flags():
    baseline = build_baseline([1.0, 1.0, 1.0])
    sessions = [(NOW - timedelta(hours=1), 10.0)]
    assert flag_change(sessions, baseline, NOW) is False


def test_two_bad_sessions_30h_apart_flag():
    baseline = build_baseline([1.0, 1.0, 1.0])
    sessions = [
        (NOW - timedelta(hours=40), 10.0),
        (NOW - timedelta(hours=10), 10.0),
    ]
    assert flag_change(sessions, baseline, NOW) is True


def test_two_bad_sessions_60h_apart_do_not_flag():
    baseline = build_baseline([1.0, 1.0, 1.0])
    sessions = [
        (NOW - timedelta(hours=60), 10.0),
        (NOW - timedelta(hours=5), 10.0),
    ]
    assert flag_change(sessions, baseline, NOW) is False


def test_sessions_at_or_below_threshold_never_count():
    baseline = build_baseline([1.0, 1.0, 1.0])
    sessions = [
        (NOW - timedelta(hours=1), baseline.threshold),
        (NOW - timedelta(hours=2), baseline.threshold - 0.1),
    ]
    assert flag_change(sessions, baseline, NOW) is False
