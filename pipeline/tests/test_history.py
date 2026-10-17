import pytest

from routine_watch.synth.history import MOTOR_MED_START_DAYS_BEFORE_END, generate_history


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


def test_all_scenarios_have_duration():
    from routine_watch.synth.history import SCENARIOS

    for scenario in SCENARIOS:
        sessions = generate_history("r1", days=14, seed=4, scenario=scenario)
        for s in sessions:
            assert s["duration_s"] > 0


def test_motor_duration_rises_after_med_start_and_sequencing_stays_rare():
    from datetime import UTC, datetime, timedelta

    sessions = generate_history("r1", days=14, seed=5, scenario="motor")
    end = datetime(2026, 1, 1, tzinfo=UTC)
    med_start = end - timedelta(days=MOTOR_MED_START_DAYS_BEFORE_END + 1)
    before = [s for s in sessions if datetime.fromisoformat(s["ts"]) < med_start]
    after = [s for s in sessions if datetime.fromisoformat(s["ts"]) >= med_start]
    assert before and after

    before_avg = sum(s["duration_s"] for s in before) / len(before)
    after_avg = sum(s["duration_s"] for s in after) / len(after)
    assert after_avg >= 1.4 * before_avg

    for s in after:
        assert s["errors"].get("omission", 0) == 0
        assert s["errors"].get("sequence", 0) == 0


def test_motor_sequencing_no_more_common_than_normal():
    motor = generate_history("r1", days=14, seed=6, scenario="motor")
    normal = generate_history("r1", days=14, seed=6, scenario="normal")

    def seq_omission_rate(sessions):
        total = sum(
            s["errors"].get("omission", 0) + s["errors"].get("sequence", 0) for s in sessions
        )
        return total / len(sessions)

    assert seq_omission_rate(motor) <= seq_omission_rate(normal)
    with_hesitation = [s for s in motor if "hesitation" in s["errors"]]
    assert with_hesitation


def test_evening_deterministic_for_seed():
    a = generate_history("r1", seed=7, scenario="evening")
    b = generate_history("r1", seed=7, scenario="evening")
    assert a == b


def test_evening_worsens_only_in_recent_evenings():
    from datetime import UTC, datetime, timedelta

    sessions = generate_history("r1", days=14, seed=7, scenario="evening")
    end = datetime(2026, 1, 1, tzinfo=UTC)
    recent = [s for s in sessions if end - datetime.fromisoformat(s["ts"]) <= timedelta(days=7)]

    recent_mornings = [
        s for s in recent if datetime.fromisoformat(s["ts"]).hour < 16
    ]
    recent_evenings = [
        s for s in recent if datetime.fromisoformat(s["ts"]).hour >= 16
    ]
    assert recent_mornings and recent_evenings

    morning_avg = sum(sum(s["errors"].values()) for s in recent_mornings) / len(recent_mornings)
    evening_avg = sum(sum(s["errors"].values()) for s in recent_evenings) / len(recent_evenings)
    assert evening_avg >= 3 * max(morning_avg, 0.01)

    for s in recent_evenings:
        assert 1 <= sum(s["errors"].values()) <= 3

    for day in range(14 - 7, 14):
        day_start = end - timedelta(days=14) + timedelta(days=day)
        day_sessions = [
            s
            for s in sessions
            if day_start <= datetime.fromisoformat(s["ts"]) < day_start + timedelta(days=1)
        ]
        hours = [datetime.fromisoformat(s["ts"]).hour for s in day_sessions]
        assert any(h < 16 for h in hours)
        assert any(h >= 16 for h in hours)
