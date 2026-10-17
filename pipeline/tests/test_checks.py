from datetime import UTC, datetime

from routine_watch.checks import suggest_checks
from routine_watch.synth.care_records import generate_care_records


def test_spike_scenario_suggests_all_checks():
    records = generate_care_records("r1", scenario="spike")
    now = datetime(2026, 1, 1, tzinfo=UTC)

    result = suggest_checks(records, now)

    assert result == ["infection_or_uti", "hydration", "medication_review", "cam_screen"]


def test_normal_scenario_suggests_only_cam_screen():
    records = generate_care_records("r1", scenario="normal")
    now = datetime(2026, 1, 1, tzinfo=UTC)

    result = suggest_checks(records, now)

    assert result == ["cam_screen"]


def test_old_records_are_ignored():
    records = generate_care_records("r1", scenario="spike")
    far_future = datetime(2026, 2, 1, tzinfo=UTC)

    result = suggest_checks(records, far_future, lookback_h=72.0)

    assert result == ["cam_screen"]
