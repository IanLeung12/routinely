"""Synthetic care-record generator for demo residents."""

import random
from datetime import UTC, datetime, timedelta

from routine_watch.synth.history import MOTOR_MED_START_DAYS_BEFORE_END


def generate_care_records(
    resident_id: str, days: int = 14, seed: int = 0, scenario: str = "normal"
) -> list[dict]:
    rng = random.Random(seed)
    records: list[dict] = []
    end = datetime(2026, 1, 1, tzinfo=UTC)
    start = end - timedelta(days=days)

    for day in range(days):
        day_start = start + timedelta(days=day)
        days_before_end = days - day - 1

        if scenario == "spike":
            if days_before_end == 2:
                records.append(
                    {
                        "resident_id": resident_id,
                        "ts": (day_start + timedelta(hours=9)).isoformat(),
                        "kind": "med_change",
                        "value": "amoxicillin",
                        "note": "new antibiotic started",
                    }
                )
            if days_before_end == 0:
                temp = round(rng.uniform(37.8, 38.2), 1)
                fluid = rng.randint(600, 1000)
            else:
                temp = round(rng.uniform(36.4, 37.0), 1)
                fluid = rng.randint(1200, 1800)
        elif scenario == "motor":
            if days_before_end == MOTOR_MED_START_DAYS_BEFORE_END:
                records.append(
                    {
                        "resident_id": resident_id,
                        "ts": (day_start + timedelta(hours=9)).isoformat(),
                        "kind": "med_change",
                        "value": "diphenhydramine",
                        "note": "new sedating medication started",
                    }
                )
            temp = round(rng.uniform(36.4, 37.0), 1)
            fluid = rng.randint(1200, 1800)
        else:
            temp = round(rng.uniform(36.4, 37.0), 1)
            fluid = rng.randint(1200, 1800)

        records.append(
            {
                "resident_id": resident_id,
                "ts": (day_start + timedelta(hours=8)).isoformat(),
                "kind": "temperature",
                "value": temp,
                "note": "",
            }
        )
        records.append(
            {
                "resident_id": resident_id,
                "ts": (day_start + timedelta(hours=20)).isoformat(),
                "kind": "fluid_intake",
                "value": fluid,
                "note": "",
            }
        )

    return records
