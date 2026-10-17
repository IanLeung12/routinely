from routine_watch.hesitation import hesitations


def test_duration_well_above_mean_flagged():
    history = {"brush_teeth": [10.0, 10.0, 10.0, 10.0]}
    durations = {"brush_teeth": 50.0}
    assert hesitations(durations, history) == ["brush_teeth"]


def test_at_or_below_threshold_not_flagged():
    history = {"brush_teeth": [10.0, 10.0, 10.0, 10.0]}
    durations = {"brush_teeth": 11.0}
    assert hesitations(durations, history) == []


def test_too_little_history_not_flagged():
    history = {"brush_teeth": [10.0, 10.0]}
    durations = {"brush_teeth": 100.0}
    assert hesitations(durations, history) == []


def test_min_std_floor_stops_flags_on_constant_history():
    history = {"brush_teeth": [10.0, 10.0, 10.0, 10.0]}
    durations = {"brush_teeth": 10.5}
    assert hesitations(durations, history, min_std=1.0) == []


def test_output_sorted():
    history = {
        "a": [10.0, 10.0, 10.0],
        "b": [10.0, 10.0, 10.0],
    }
    durations = {"b": 50.0, "a": 50.0}
    assert hesitations(durations, history) == ["a", "b"]
