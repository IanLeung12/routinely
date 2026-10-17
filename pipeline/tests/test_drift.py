from datetime import date, timedelta

import pytest

from routine_watch.drift import Drift, drift


def series(scores):
    return [(date(2026, 1, 1) + timedelta(days=i), score) for i, score in enumerate(scores)]


def test_flat_series_is_not_trending():
    assert drift(series([2.0] * 14)) == Drift(slope_per_day=0.0, days=14, trending=False)


def test_steady_rise_is_trending():
    result = drift(series([0.2 * i for i in range(14)]))
    assert result.slope_per_day == pytest.approx(0.2)
    assert result.days == 14
    assert result.trending


def test_single_spike_does_not_create_a_trend():
    scores = [1.0] * 14
    scores[7] = 1000.0
    assert drift(series(scores)).slope_per_day == 0
    assert not drift(series(scores)).trending


def test_five_observed_days_are_too_short():
    assert not drift(series([float(i) for i in range(5)])).trending


def test_input_order_does_not_matter():
    daily = series([0.2 * i for i in range(14)])
    assert drift(daily[::2] + daily[1::2]) == drift(daily)
    assert drift(list(reversed(daily))) == drift(daily)


@pytest.mark.parametrize("daily", [[], [(date(2026, 1, 1), 3.0)]])
def test_insufficient_points_have_zero_slope(daily):
    assert drift(daily, min_days=0, min_slope=0) == Drift(0.0, len(daily), False)


def test_elapsed_days_determine_slope_but_not_observation_count():
    daily = [(date(2026, 1, 1), 0.0), (date(2026, 1, 11), 2.0)]
    assert drift(daily) == Drift(0.2, 2, False)


def test_custom_thresholds_and_same_date_observations():
    assert drift(series([0.0, 1.0]), min_days=2, min_slope=1.0).trending
    assert not drift(series([0.0, 1.0]), min_days=2, min_slope=1.1).trending
    assert drift([(date(2026, 1, 1), 1.0)] * 7) == Drift(0.0, 1, False)
