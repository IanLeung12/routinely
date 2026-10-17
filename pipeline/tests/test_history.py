import pytest

from routine_watch.synth.history import generate_history


def test_deterministic_for_seed():
    a = generate_history("r1", seed=42)
    b = generate_history("r1", seed=42)
    assert a == b


def test_unknown_scenario_raises():
    with pytest.raises(ValueError):
        generate_history("r1", scenario="bogus")


def test_sorted_by_time():
    sessions = generate_history("r1", seed=1)
    assert [s["ts"] for s in sessions] == sorted(s["ts"] for s in sessions)


def test_normal_mostly_zero_errors():
    sessions = generate_history("r1", days=14, seed=1, scenario="normal")
    with_issue = [s for s in sessions if s["errors"] or s["self_corrected"]]
    assert len(with_issue) / len(sessions) <= 0.3
    for s in sessions:
        assert sum(s["errors"].values()) <= 1
        assert s["self_corrected"] <= 1


def test_spike_last_36h_has_omission_and_perseveration():
    sessions = generate_history("r1", days=14, seed=2, scenario="spike")
    from datetime import UTC, datetime, timedelta

    end = datetime(2026, 1, 1, tzinfo=UTC)
    early = [s for s in sessions if end - datetime.fromisoformat(s["ts"]) > timedelta(hours=36)]
    late = [s for s in sessions if end - datetime.fromisoformat(s["ts"]) <= timedelta(hours=36)]
    assert late
    for s in late:
        assert s["errors"].get("omission") == 1
        assert s["errors"].get("perseveration") == 1
    for s in early:
        assert "omission" not in s["errors"]
        assert "perseveration" not in s["errors"]


def test_drift_trends_upward_and_capped_early():
    sessions = generate_history("r1", days=14, seed=3, scenario="drift")
    from datetime import datetime

    start = min(datetime.fromisoformat(s["ts"]) for s in sessions)
    early = [s for s in sessions if (datetime.fromisoformat(s["ts"]) - start).days < 3]
    late = [s for s in sessions if (datetime.fromisoformat(s["ts"]) - start).days >= 3]
    for s in early:
        assert sum(s["errors"].values()) <= 1

    early_avg = sum(sum(s["errors"].values()) for s in early) / len(early)
    late_avg = sum(sum(s["errors"].values()) for s in late) / len(late)
    assert late_avg > early_avg
