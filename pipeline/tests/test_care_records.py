from routine_watch.synth.care_records import generate_care_records
from routine_watch.synth.history import MOTOR_MED_START_DAYS_BEFORE_END


def test_deterministic():
    a = generate_care_records("r1", days=14, seed=0, scenario="normal")
    b = generate_care_records("r1", days=14, seed=0, scenario="normal")
    assert a == b


def test_normal_scenario():
    records = generate_care_records("r1", days=14, seed=0, scenario="normal")
    assert not [r for r in records if r["kind"] == "med_change"]
    for r in records:
        if r["kind"] == "temperature":
            assert 36.4 <= r["value"] <= 37.0
        if r["kind"] == "fluid_intake":
            assert 1200 <= r["value"] <= 1800


def test_spike_scenario():
    records = generate_care_records("r1", days=14, seed=0, scenario="spike")
    med_changes = [r for r in records if r["kind"] == "med_change"]
    assert len(med_changes) == 1

    temps = sorted((r["ts"], r["value"]) for r in records if r["kind"] == "temperature")
    last_temp = temps[-1][1]
    assert 37.8 <= last_temp <= 38.2

    fluids = sorted((r["ts"], r["value"]) for r in records if r["kind"] == "fluid_intake")
    last_fluid = fluids[-1][1]
    assert last_fluid < 1200


def test_motor_scenario():
    from datetime import datetime, timedelta

    days = 14
    records = generate_care_records("r1", days=days, seed=0, scenario="motor")
    med_changes = [r for r in records if r["kind"] == "med_change"]
    assert len(med_changes) == 1
    assert med_changes[0]["value"] == "diphenhydramine"

    end = datetime(2026, 1, 1)
    expected_day = end - timedelta(days=MOTOR_MED_START_DAYS_BEFORE_END + 1)
    med_ts = datetime.fromisoformat(med_changes[0]["ts"]).replace(tzinfo=None)
    assert med_ts.date() == expected_day.date()

    for r in records:
        if r["kind"] == "temperature":
            assert 36.4 <= r["value"] <= 37.0
        if r["kind"] == "fluid_intake":
            assert 1200 <= r["value"] <= 1800
