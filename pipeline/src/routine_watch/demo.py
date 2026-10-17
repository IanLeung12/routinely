"""Synthetic demo residents for the dashboard (SPEC section 8). Offline, no DB yet.

3-5 residents built from the synthetic generators: most normal, one with a sudden
spike (the demo resident "Mrs. K"), one with a slow drift. Each resident's sessions
are scored and checked against their own baseline with the same pure functions the
pipeline uses for a live session.
"""

from datetime import UTC, datetime

from .change_detection import Baseline, build_baseline, flag_change
from .scoring import session_score
from .synth.care_records import generate_care_records
from .synth.history import generate_history

#: The fixed "today" the synthetic generators build history up to.
DEMO_NOW = datetime(2026, 1, 1, tzinfo=UTC)

DEMO_DAYS = 14

#: Seeds are pinned so each resident lands on its intended status (SPEC section 8:
#: most normal, one spike, one drift) rather than drifting with the RNG.
_RESIDENTS: tuple[dict[str, str | int], ...] = (
    {"id": "mrs-k", "name": "Mrs. K", "room": "204", "scenario": "spike", "seed": 1},
    {"id": "mr-chen", "name": "Mr. Chen", "room": "211", "scenario": "drift", "seed": 0},
    {"id": "mrs-ahmed", "name": "Mrs. Ahmed", "room": "108", "scenario": "normal", "seed": 0},
    {"id": "mr-silva", "name": "Mr. Silva", "room": "117", "scenario": "normal", "seed": 2},
)


def _status(latest_score: float, baseline: Baseline, flagged: bool) -> str:
    if flagged:
        return "flagged"
    if latest_score > baseline.threshold:
        return "watch"
    return "normal"


def demo_residents() -> list[dict]:
    """Build the demo residents end to end: deterministic, no network, no DB."""
    residents = []
    for config in _RESIDENTS:
        sessions = generate_history(
            config["id"], days=DEMO_DAYS, seed=config["seed"], scenario=config["scenario"]
        )
        care_records = generate_care_records(
            config["id"], days=DEMO_DAYS, seed=config["seed"], scenario=config["scenario"]
        )
        scores = [
            session_score(session["errors"], session["self_corrected"], session["assisted"])
            for session in sessions
        ]
        baseline = build_baseline(scores)
        timestamped = [
            (datetime.fromisoformat(session["ts"]), score)
            for session, score in zip(sessions, scores, strict=True)
        ]
        flagged = flag_change(timestamped, baseline, DEMO_NOW)
        status = _status(scores[-1], baseline, flagged)

        residents.append(
            {
                "id": config["id"],
                "name": config["name"],
                "room": config["room"],
                "status": status,
                "scores": [
                    {"ts": session["ts"], "score": score}
                    for session, score in zip(sessions, scores, strict=True)
                ],
                "sessions": sessions,
                "care_records": care_records,
                "baseline": {
                    "mean": baseline.mean,
                    "std": baseline.std,
                    "threshold": baseline.threshold,
                },
            }
        )
    return residents
