"""Synthetic demo residents for the dashboard (SPEC section 8). Offline, no DB yet.

5-6 residents built from the synthetic generators, one per pattern: most normal,
one with a sudden spike (the demo resident "Mrs. K"), one with a slow drift, one
with evening-only worsening (sundowning), one with motor slowing after a sedating
medication change. Each resident's sessions are scored and checked against their
own baseline with the same pure functions the pipeline uses for a live session.

A live session that has been played this run is one of those sessions. Whatever
`routine_watch.session_log` has recorded for a resident is merged in as their newest
sessions - its errors included, so the alert a nurse opens afterwards shows the steps
and times that session really had - so the session a teammate just made tea for spikes
their sparkline and, if it is the second qualifying one inside the window, flags a
change for review on the next `/residents` and `/alerts` (SPEC section 10, step 4).
"""

from collections import Counter
from dataclasses import replace
from datetime import UTC, datetime, timedelta

from . import session_log
from .change_detection import Baseline, build_baseline, flag_change
from .drift import daily_scores, drift
from .patterns import extract_features, score_patterns
from .scoring import session_score
from .synth.care_records import generate_care_records
from .synth.history import generate_history

#: The fixed "today" the synthetic generators build history up to.
DEMO_NOW = datetime(2026, 1, 1, tzinfo=UTC)

DEMO_DAYS = 14

#: How many of the resident's earliest days build their baseline (SPEC section 8,
#: beat 6: a baseline drawn from the resident's *whole* history rises along with a
#: slow drift and the resident never crosses their own threshold; anchoring it to
#: the earliest days instead keeps it still while a drifting resident worsens).
BASELINE_DAYS = 7

#: Whose session the live demo is: a teammate makes tea on stage as Mrs. K (SPEC
#: sections 8 and 10), so this is the resident `routine_watch.live` records against
#: when nobody says otherwise.
DEMO_RESIDENT = "mrs-k"

#: Seeds are pinned so each resident lands on its intended status (SPEC section 8:
#: most normal, one spike, one drift) rather than drifting with the RNG.
#:
#: `consent` is the opted-in record SPEC §12 requires before a room is monitored:
#: who gave it (the resident themself, or a substitute decision-maker) and on what
#: date. Dates are fixed, deterministic, and before `DEMO_NOW - DEMO_DAYS` (2025-12-18)
#: - the first day any demo resident has a session - so consent always predates the
#: history it covers.
_RESIDENTS: tuple[dict[str, str | int | dict[str, str]], ...] = (
    {
        "id": "mrs-k",
        "name": "Mrs. K",
        "room": "204",
        "scenario": "spike",
        "seed": 1,
        "consent": {"given_by": "Resident", "on": "2025-11-15"},
    },
    {
        "id": "mr-chen",
        "name": "Mr. Chen",
        "room": "211",
        "scenario": "drift",
        "seed": 0,
        "consent": {"given_by": "Resident", "on": "2025-11-20"},
    },
    {
        "id": "mrs-ahmed",
        "name": "Mrs. Ahmed",
        "room": "108",
        "scenario": "normal",
        "seed": 0,
        "consent": {
            "given_by": "Substitute decision-maker (daughter)",
            "on": "2025-11-10",
        },
    },
    {
        "id": "mr-silva",
        "name": "Mr. Silva",
        "room": "117",
        "scenario": "normal",
        "seed": 2,
        "consent": {"given_by": "Resident", "on": "2025-11-18"},
    },
    {
        "id": "mr-nguyen",
        "name": "Mr. Nguyen",
        "room": "126",
        "scenario": "evening",
        "seed": 0,
        "consent": {
            "given_by": "Substitute decision-maker (son)",
            "on": "2025-11-05",
        },
    },
    {
        "id": "mrs-patel",
        "name": "Mrs. Patel",
        "room": "132",
        "scenario": "motor",
        "seed": 0,
        "consent": {"given_by": "Resident", "on": "2025-11-22"},
    },
)


def _status(flagged: bool, watch: bool) -> str:
    if flagged:
        return "flagged"
    if watch:
        return "watch"
    return "normal"


def _trending(points: list[dict]) -> bool:
    return drift(daily_scores(points)).trending


def _worth_watching(latest: float, early_values: list[float], points: list[dict]) -> bool:
    """True once a resident's latest session breaks their own early-days bar, or
    their own history trends upward - the two patterns a slow drift and a sudden
    spike each show on a metric (SPEC §8 beat 6, §7.5)."""
    early_baseline = build_baseline(early_values)
    return latest > early_baseline.threshold or _trending(points)


def _score(session: dict) -> float:
    """One session's score, whether it was generated or just played live."""
    return session_score(session["errors"], session["self_corrected"], session["assisted"])


def _live_sessions(resident_id: str) -> list[dict]:
    """This run's recorded live sessions for one resident, written the way the
    synthetic generator writes a session, so everything downstream - scoring, the
    baseline comparison, the alert's evidence - reads both the same way.

    Plus the one thing a generated session cannot have: `error_events`, the errors
    the classifier actually found in it (`session_log.errors_for`). Synthetic history
    only knows how many errors of each type a session had, so an alert built from
    counts alone has to invent a step and a time per error; a session this process
    watched knows both, and the nurse who just watched it has to read the same ones
    back (`alerts.task_errors`, T155). JSON data like the rest of the dict, because
    `/residents/{id}` serves it as it is.
    """
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
                "error_events": [error.model_dump(mode="json") for error in errors],
                "self_corrected": sum(1 for error in errors if error.self_corrected),
                "duration_s": round((ended_at - session.started_at).total_seconds(), 1),
                "assisted": session.assisted,
            }
        )
    return sessions


def _early_history(history: list[dict]) -> list[dict]:
    """This resident's earliest `BASELINE_DAYS` of sessions: what they were like
    before whatever is being flagged now (SPEC §8 beat 6)."""
    cutoff = DEMO_NOW - timedelta(days=DEMO_DAYS - BASELINE_DAYS)
    return [
        session for session in history if datetime.fromisoformat(session["ts"]) < cutoff
    ]


def _usual(history: list[dict]) -> dict[str, float]:
    """How long a session of this resident's normally runs and how many errors it
    normally has, over the same early window the watch bar is measured against.

    The live screen reads these back as "usually ~Xs / ~N errors" when a session ends,
    so they have to mean this resident's *old* normal: averaged over the whole history
    they would include the very days being flagged and quietly excuse them (SPEC §8
    beat 6). Assisted sessions are somebody else's hands as much as theirs, so they are
    left out. Both keys are absent for a resident with no early sessions of their own -
    the screen then leaves the "usually" half out rather than showing a guess.
    """
    own = [session for session in _early_history(history) if not session["assisted"]]
    if not own:
        return {}
    return {
        "usual_duration_s": sum(s["duration_s"] for s in own) / len(own),
        "usual_errors": sum(sum(s["errors"].values()) for s in own) / len(own),
    }


def _watch(history: list[dict], sessions: list[dict], scores: list[float]) -> bool:
    score_points = [
        {"ts": session["ts"], "score": score}
        for session, score in zip(sessions, scores, strict=True)
    ]
    # A resident's own earliest sessions - not their whole history, which rises
    # right along with a slow drift and so never gets crossed - are what "worth
    # watching" measures against (SPEC §8 beat 6). Duration catches the motor
    # pattern, which barely touches error counts by design (SPEC §7.5).
    early_history = _early_history(history)
    duration_points = [
        {"ts": session["ts"], "score": session["duration_s"]} for session in sessions
    ]
    return _worth_watching(
        scores[-1], [_score(session) for session in early_history], score_points
    ) or _worth_watching(
        sessions[-1]["duration_s"],
        [session["duration_s"] for session in early_history],
        duration_points,
    )


def _top_pattern(sessions: list[dict], baseline, care_records: list[dict]) -> dict | None:
    """The best-scoring pattern this resident's change is consistent with (SPEC §7.5,
    §9 screen 1), or `None` when nothing clears the threshold - a real answer, not a
    missing one."""
    features = extract_features(sessions, baseline, care_records, now=DEMO_NOW)
    matches = score_patterns(features)
    if not matches:
        return None
    top = matches[0]
    return {"pattern_id": top.pattern_id, "name": top.name, "urgency": top.urgency.value}


def _status_from(
    history: list[dict], sessions: list[dict], scores: list[float], baseline: Baseline
) -> str:
    """The one flag rule `demo_residents` and `status_for` both apply: flag against
    `baseline`, watch against `history`'s early days (SPEC §8 beat 6, MVP 7)."""
    timestamped = [
        (datetime.fromisoformat(session["ts"]), score)
        for session, score in zip(sessions, scores, strict=True)
    ]
    flagged = flag_change(timestamped, baseline, DEMO_NOW)
    watch = _watch(history, sessions, scores)
    return _status(flagged, watch)


def baseline_of(resident: dict) -> Baseline:
    """The flag baseline inside a resident payload.

    That payload's `baseline` also carries this resident's usual duration and error
    count (`_usual`), which `change_detection.Baseline` has no field for, so it is read
    key by key rather than splatted.
    """
    payload = resident["baseline"]
    return Baseline(
        mean=payload["mean"], std=payload["std"], threshold=payload["threshold"]
    )


def status_for(resident: dict, threshold: float) -> str:
    """`resident`'s status if its flag threshold were `threshold` instead of its own
    baseline's (SPEC MVP 7): the same flag rule `demo_residents` uses, so a
    feedback-tuned threshold (`routine_watch.feedback`) reads the same status
    wherever a resident's status is shown, not just in the handoff and the alert
    payload (`routine_watch.api`).

    `_watch`'s early-days bar is unrelated to nurse feedback - only the flag
    threshold is tuned - so it is read straight from `resident`, same as always.
    """
    sessions = resident["sessions"]
    scores = [point["score"] for point in resident["scores"]]
    tuned_baseline = replace(baseline_of(resident), threshold=threshold)
    return _status_from(sessions, sessions, scores, tuned_baseline)


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
        # change they are hides itself. It stays whole-history so a sudden two-session
        # spike (mrs-k) still flags, and so the alert evidence it backs lines up with
        # the sessions that tripped `flag_change`.
        baseline = build_baseline([_score(session) for session in history])
        sessions = sorted(history + _live_sessions(config["id"]), key=lambda s: s["ts"])
        scores = [_score(session) for session in sessions]
        score_points = [
            {"ts": session["ts"], "score": score}
            for session, score in zip(sessions, scores, strict=True)
        ]
        status = _status_from(history, sessions, scores, baseline)
        top_pattern = (
            _top_pattern(sessions, baseline, care_records) if status != "normal" else None
        )

        residents.append(
            {
                "id": config["id"],
                "name": config["name"],
                "room": config["room"],
                "consent": config["consent"],
                "status": status,
                "top_pattern": top_pattern,
                "scores": score_points,
                "sessions": sessions,
                "care_records": care_records,
                "baseline": {
                    "mean": baseline.mean,
                    "std": baseline.std,
                    "threshold": baseline.threshold,
                    **_usual(history),
                },
            }
        )
    return residents
