"""Suggest checks for the care team to review, based on recent care-record context."""

from datetime import datetime, timedelta

CHECKS = ("infection_or_uti", "hydration", "medication_review", "cam_screen")


def suggest_checks(
    care_records: list[dict], now: datetime, lookback_h: float = 72.0
) -> list[str]:
    cutoff = now - timedelta(hours=lookback_h)
    suggested: set[str] = set()

    for record in care_records:
        ts = datetime.fromisoformat(record["ts"])
        if ts < cutoff or ts > now:
            continue

        kind = record["kind"]
        if kind == "temperature" and record["value"] >= 37.8:
            suggested.add("infection_or_uti")
        elif kind == "fluid_intake" and record["value"] < 1000:
            suggested.add("hydration")
        elif kind == "med_change":
            suggested.add("medication_review")

    suggested.add("cam_screen")
    return [check for check in CHECKS if check in suggested]
