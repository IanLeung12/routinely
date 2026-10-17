import pytest

from routine_watch.scoring import session_score


def test_empty_counts():
    assert session_score({}) == 0.0


def test_weighted_sum():
    assert session_score({"omission": 1, "perseveration": 1}) == 5.0


def test_self_corrected_adds_half():
    assert session_score({}, self_corrected=2) == 1.0


def test_assisted_is_zero():
    assert session_score({"omission": 5}, assisted=True) == 0.0


def test_unknown_error_type_raises():
    with pytest.raises(ValueError):
        session_score({"bogus": 1})
