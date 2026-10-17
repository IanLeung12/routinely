"""Synthetic demo residents for the dashboard (SPEC section 8). Offline, no DB yet.

5-6 residents built from the synthetic generators, one per pattern: most normal,
one with a sudden spike (the demo resident "Mrs. K"), one with a slow drift, one
with evening-only worsening (sundowning), one with motor slowing after a sedating
medication change. Each resident's sessions are scored and checked against their
own baseline with the same pure functions the pipeline uses for a live session.

A live session that has been played this run is one of those sessions. Whatever
`routine_watch.session_log` has recorded for a resident is merged in as their newest
sessions, so the session a teammate just made tea for spikes their sparkline and, if
it is the second qualifying one inside the window, flags a change for review on the
next `/residents` and `/alerts` (SPEC section 10, step 4).
"""

from collections import Counter
from datetime import UTC, datetime

from . import session_log
from .change_detection import Baseline, build_baseline, flag_change
from .scoring import session_score
from .synth.care_records import generate_care_records
from .synth.history import generate_history

#: The fixed "today" the synthetic generators build history up to.
DEMO_NOW = datetime(2026, 1, 1, tzinfo=UTC)

DEMO_DAYS = 14

#: Whose session the live demo is: a teammate makes tea on stage as Mrs. K (SPEC
#: sections 8 and 10), so this is the resident `routine_watch.live` records against
#: when nobody says otherwise.
DEMO_RESIDENT = "mrs-k"

#: Seeds are pinned so each resident lands on its intended status (SPEC section 8:
#: most normal, one spike, one drift) rather than drifting with the RNG.
_RESIDENTS: tuple[dict[str, str | int], ...] = (
    {"id": "mrs-k", "name": "Mrs. K", "room": "204", "scenario": "spike", "seed": 1},
    {"id": "mr-chen", "name": "Mr. Chen", "room": "211", "scenario": "drift", "seed": 0},
    {"id": "mrs-ahmed", "name": "Mrs. Ahmed", "room": "108", "scenario": "normal", "seed": 0},
    {"id": "mr-silva", "name": "Mr. Silva", "room": "117", "scenario": "normal", "seed": 2},
    {"id": "mr-nguyen", "name": "Mr. Nguyen", "room": "126", "scenario": "evening", "seed": 0},
    {"id": "mrs-patel", "name": "Mrs. Patel", "room": "132", "scenario": "motor", "seed": 0},
)


def _status(latest_score: float, baseline: Baseline, flagged: bool) -> str:
    if flagged:
        return "flagged"
    if latest_score > baseline.threshold:
        return "watch"
    return "normal"


def _score(session: dict) -> float:
    """One session's score, whether it was generated or just played live."""
    return session_score(session["errors"], session["self_corrected"], session["assisted"])


def _live_sessions(resident_id: str) -> list[dict]:
    """This run's recorded live sessions for one resident, written the way the
    synthetic generator writes a session, so everything downstream - scoring, the
    baseline comparison, the alert's evidence - reads both the same way."""
    sessions = []
    for session in session_log.sessions_for(resident_id):
        errors = session_log.errors_for(session.session_id)
        counts = Counter(str(error.type) for error in errors if not error.self_corrected)
        ended_at = session.ended_at or session.started_at
        sessions.append(
            {
                "resident_id": resident_id,
                "session_id": session.session_id,
                "ts": session.started_at.isoformat(),
                "task": session.task_id,
                "errors": dict(counts),
                "self_corrected": sum(1 for error in errors if error.self_corrected),
                "duration_s": round((ended_at - session.started_at).total_seconds(), 1),
                "assisted": session.assisted,
            }
        )
    return sessions


def demo_residents() -> list[dict]:
    """Build the demo residents end to end: deterministic, no network, no DB."""
    residents = []
    for config in _RESIDENTS:
        history = generate_history(
            config["id"], days=DEMO_DAYS, seed=config["seed"], scenario=config["scenario"]
        )
        care_records = generate_care_records(
            config["id"], days=DEMO_DAYS, seed=config["seed"], scenario=config["scenario"]
        )
        # The baseline is what this resident is normally like, so it is built from the
        # history they came in with and a live session is measured against it, the way
        # `replay.change_flag` measures a replayed one. Folding live sessions into it
        # would let two bad sessions raise the bar they are being judged by until the
        # change they are hides itself.
        baseline = build_baseline([_score(session) for session in history])
        sessions = sorted(history + _live_sessions(config["id"]), key=lambda s: s["ts"])
        scores = [_score(session) for session in sessions]
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
