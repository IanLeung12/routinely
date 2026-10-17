from routine_watch.hesitation import hesitations


def test_no_history_for_step_never_flagged():
    history = {}
    durations = {"brush_teeth": 1000.0}
    assert hesitations(durations, history) == []


def test_empty_input_returns_empty_list():
    assert hesitations({}, {}) == []


def test_just_below_threshold_not_flagged():
    history = {"brush_teeth": [10.0, 10.0, 10.0]}
    durations = {"brush_teeth": 12.49}
    assert hesitations(durations, history) == []


def test_just_above_threshold_flagged():
    history = {"brush_teeth": [10.0, 10.0, 10.0]}
    durations = {"brush_teeth": 12.51}
    assert hesitations(durations, history) == ["brush_teeth"]


def test_zero_length_durations_history_not_flagged():
    history = {"brush_teeth": [0.0, 0.0, 0.0]}
    durations = {"brush_teeth": 0.0}
    assert hesitations(durations, history) == []


def test_history_for_one_step_does_not_affect_another():
    history = {"a": [10.0, 10.0, 10.0, 10.0, 10.0, 10.0, 10.0, 10.0, 100.0]}
    durations = {"b": 1000.0}
    assert hesitations(durations, history) == []
