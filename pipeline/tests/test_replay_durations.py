"""T157: replay.py threads an optional session duration into pattern matching.

`HistorySession.duration_s` and `Expected.duration_s` let a scenario say a session
ran long or short, which is what `patterns.extract_features` needs to compute
`duration_ratio` and the `durations_up` signal that `motor_slowing` requires
(SPEC §7.5). Unset, both stay `None`, exactly as before this task.
"""

from __future__ import annotations

import pytest

from routine_watch.patterns import Features, extract_features, signals
from routine_watch.replay import HistorySession, build_baseline, top_pattern_of

#: Ten quiet history sessions, a day apart, all the same length.
HISTORY_DURATION_S = 300.0
#: Half again as long: the replayed session a scenario expects `durations_up` from.
CURRENT_DURATION_S = 450.0


def _history(duration_s: float | None) -> list[HistorySession]:
    # 72h+ ago: outside the 48h change window (`patterns.CHANGE_WINDOW_H`), so each one
    # is "baseline", not "recent" - only the replayed session falls in the recent window.
    return [
        HistorySession(hours_ago=72.0 + 24.0 * i, score=0.0, duration_s=duration_s)
        for i in range(10)
    ]


def _features_for(
    history: list[HistorySession], duration_s: float | None, monkeypatch: pytest.MonkeyPatch
) -> Features:
    """The `Features` `top_pattern_of` computes internally, without reaching inside it."""
    baseline = build_baseline([session.score_value for session in history])
    captured: dict[str, Features] = {}

    def spy(sessions, baseline_arg, care_records, now=None, **kwargs):
        features = extract_features(sessions, baseline_arg, care_records, now=now, **kwargs)
        captured["features"] = features
        return features

    monkeypatch.setattr("routine_watch.replay.extract_features", spy)
    top_pattern_of(history, baseline, [], False, duration_s=duration_s)
    return captured["features"]


def test_a_longer_session_than_usual_gives_a_duration_ratio_and_durations_up(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    features = _features_for(_history(HISTORY_DURATION_S), CURRENT_DURATION_S, monkeypatch)
    assert features.duration_ratio == pytest.approx(1.5, rel=0.05)
    assert signals(features)["durations_up"] is not None
    assert signals(features)["durations_up"] > 0.0


def test_no_durations_leaves_duration_ratio_unset(monkeypatch: pytest.MonkeyPatch) -> None:
    features = _features_for(_history(None), None, monkeypatch)
    assert features.duration_ratio is None
    assert signals(features)["durations_up"] is None
