"""Synthetic tea-making session history generator for demo residents."""

import random
from datetime import UTC, datetime, timedelta

from routine_watch.errors import ERROR_TYPES

SCENARIOS = ("normal", "spike", "drift", "motor", "evening")

#: Sessions in the last this many days count toward the evening-only worsening
#: pattern (SPEC §7.5: sundowning).
EVENING_RECENT_DAYS = 7

#: Days before the end of the window that the sedating medication starts in the
#: "motor" scenario (SPEC §7.5: motor slowing after a medication change).
MOTOR_MED_START_DAYS_BEFORE_END = 5


def generate_history(
    resident_id: str, days: int = 14, seed: int = 0, scenario: str = "normal"
) -> list[dict]:
    if scenario not in SCENARIOS:
        raise ValueError(f"unknown scenario: {scenario}")

    rng = random.Random(seed)
    end = datetime(2026, 1, 1, tzinfo=UTC)
    start = end - timedelta(days=days)

    sessions: list[dict] = []
    for day in range(days):
        day_start = start + timedelta(days=day)
        n_sessions = 2 if scenario == "evening" else rng.choice([1, 2])
        days_before_end = days - day - 1
        for hour in (8, 18)[:n_sessions]:
            ts = day_start + timedelta(hours=hour, minutes=rng.randint(0, 30))
            hours_until_end = (end - ts).total_seconds() / 3600
            errors, self_corrected = _session_errors(
                rng, scenario, day, days, hours_until_end, days_before_end, hour
            )
            sessions.append(
                {
                    "resident_id": resident_id,
                    "ts": ts.isoformat(),
                    "task": "tea",
                    "errors": errors,
                    "self_corrected": self_corrected,
                    "duration_s": _session_duration(rng, scenario, days_before_end),
                    "assisted": False,
                }
            )

    sessions.sort(key=lambda s: s["ts"])
    return sessions


def _session_duration(rng: random.Random, scenario: str, days_before_end: int) -> float:
    base = rng.uniform(150.0, 200.0)
    if scenario == "motor" and days_before_end <= MOTOR_MED_START_DAYS_BEFORE_END:
        base *= rng.uniform(1.4, 1.6)
    return round(base, 1)


def _session_errors(
    rng: random.Random,
    scenario: str,
    day: int,
    days: int,
    hours_until_end: float,
    days_before_end: int,
    hour: int = 8,
) -> tuple[dict[str, int], int]:
    if scenario == "evening":
        if days_before_end < EVENING_RECENT_DAYS and hour >= 16:
            errors = {}
            error_types = list(("sequence", "omission", "hesitation"))
            for _ in range(rng.randint(1, 3)):
                et = rng.choice(error_types)
                errors[et] = errors.get(et, 0) + 1
            return errors, 0
        errors = {}
        self_corrected = 0
        if rng.random() < 0.2:
            if rng.random() < 0.5:
                errors["hesitation"] = 1
            else:
                self_corrected = 1
        return errors, self_corrected

    if scenario == "normal":
        errors: dict[str, int] = {}
        self_corrected = 0
        if rng.random() < 0.2:
            if rng.random() < 0.5:
                errors["hesitation"] = 1
            else:
                self_corrected = 1
        return errors, self_corrected

    if scenario == "spike":
        if hours_until_end <= 36:
            return {"omission": 1, "perseveration": 1}, 0
        errors = {}
        self_corrected = 0
        if rng.random() < 0.2:
            errors["hesitation"] = 1
        return errors, self_corrected

    if scenario == "motor":
        # Before the sedating med starts: normal-like, occasional slip.
        if days_before_end > MOTOR_MED_START_DAYS_BEFORE_END:
            errors = {}
            self_corrected = 0
            if rng.random() < 0.2:
                if rng.random() < 0.5:
                    errors["hesitation"] = 1
                else:
                    self_corrected = 1
            return errors, self_corrected
        # After the sedating med starts: slower and more hesitant, but the
        # resident still gets the sequence right (SPEC §7.5: few sequencing
        # errors is what tells this apart from delirium).
        errors = {}
        self_corrected = 0
        if rng.random() < 0.6:
            errors["hesitation"] = 1
        elif rng.random() < 0.1:
            self_corrected = 1
        return errors, self_corrected

    # drift: total errors per session trend upward across the whole window,
    # at most one error per session in the first 3 days.
    progress = day / max(days - 1, 1)
    if day < 3:
        count = 1 if rng.random() < 0.3 else 0
    else:
        count = round(progress * 3) + (1 if rng.random() < 0.5 else 0)
        count = max(count, 1)
    errors = {}
    error_types = list(ERROR_TYPES)
    for _ in range(count):
        et = rng.choice(error_types)
        errors[et] = errors.get(et, 0) + 1
    return errors, 0
