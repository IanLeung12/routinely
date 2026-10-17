"""Alert contracts for flagged demo residents (SPEC section 5, MVP 5).

Turns a flagged resident's qualifying sessions into the evidence a nurse reviews: the
errors, the baseline comparison, a plain-language summary, the patterns the change is
consistent with and suggested checks.

    from routine_watch.demo import demo_residents
    alerts = build_alerts(demo_residents())

The one-tap nurse feedback loop (MVP 7) that tunes thresholds from these alerts lives
in `routine_watch.feedback`; the API route that wires the two together lives in
`routine_watch.api`.
"""

from __future__ import annotations

from datetime import datetime, timedelta

from .change_detection import Baseline
from .checks import suggest_checks
from .contracts import (
    Alert,
    AlertKind,
    BaselineComparison,
    BaselineMetric,
    PatternMatch,
    SuggestedCheck,
    TaskError,
)
from .demo import DEMO_DAYS, DEMO_NOW
from .explain import Explainer
from .explain_claude import get_explainer
from .patterns import extract_features, score_patterns

#: How far back a session still counts toward the flag (SPEC section 7).
FLAG_WINDOW_H = 48.0

#: How far back a care-record note is still worth mentioning next to the alert.
CONTEXT_LOOKBACK_H = 72.0

#: Stand-in for the step an error happened at, when the resident's history only
#: carries a count of errors per type rather than individual step events.
_UNKNOWN_STEP = "the task"


def _get_explainer() -> Explainer:
    """Wraps `get_explainer()` so tests can monkeypatch the explainer used here."""
    return get_explainer()


def build_alerts(residents: list[dict]) -> list[Alert]:
    """One alert per flagged resident (SPEC section 7: a single bad session never
    alerts, so only residents `demo_residents` already flagged get one)."""
    return [_build_alert(resident) for resident in residents if resident["status"] == "flagged"]


def _qualifying_sessions(resident: dict) -> list[tuple[str, dict, float]]:
    """The sessions behind the flag: id, session dict and score, oldest first."""
    threshold = resident["baseline"]["threshold"]
    window_start = DEMO_NOW - timedelta(hours=FLAG_WINDOW_H)
    qualifying = []
    sessions_and_scores = zip(resident["sessions"], resident["scores"], strict=True)
    for index, (session, point) in enumerate(sessions_and_scores):
        ts = datetime.fromisoformat(session["ts"])
        if window_start <= ts <= DEMO_NOW and point["score"] > threshold:
            qualifying.append((f"{resident['id']}-{index}", session, point["score"]))
    return qualifying


def _task_errors(session_id: str, session: dict) -> list[TaskError]:
    """Synthetic per-instance errors from a session's error-type counts.

    The demo history only tracks how many errors of each type a session had, not the
    individual step events, so the times here are spaced placeholders rather than
    anything observed.
    """
    errors = []
    t = 0.0
    for error_type, count in sorted(session["errors"].items()):
        for i in range(count):
            errors.append(
                TaskError(
                    error_id=f"{session_id}:{error_type}:{i}",
                    session_id=session_id,
                    type=error_type,
                    step_id=None,
                    t_start=t,
                    t_end=t + 5.0,
                    evidence=[],
                )
            )
            t += 10.0
    return errors


def _context(care_records: list[dict]) -> list[str]:
    """Recent care-record notes to show next to the alert (SPEC section 5, bonus 5)."""
    cutoff = DEMO_NOW - timedelta(hours=CONTEXT_LOOKBACK_H)
    return [
        record["note"]
        for record in care_records
        if record.get("note") and cutoff <= datetime.fromisoformat(record["ts"]) <= DEMO_NOW
    ]


def _normal_error_rate(resident: dict) -> float:
    """This resident's own average errors per session, over their full history."""
    counts = [sum(session["errors"].values()) for session in resident["sessions"]]
    return sum(counts) / len(counts) if counts else 0.0


def _patterns(resident: dict) -> list[PatternMatch]:
    """The patterns this resident's change is consistent with (SPEC section 7.5).

    Deterministic rules over the features the pipeline already has, ranked against the
    pattern library. An empty list is a real answer: a change with no clear pattern.
    """
    features = extract_features(
        resident["sessions"],
        Baseline(**resident["baseline"]),
        resident["care_records"],
        now=DEMO_NOW,
        window_h=FLAG_WINDOW_H,
    )
    return score_patterns(features)


def _build_alert(resident: dict) -> Alert:
    qualifying = _qualifying_sessions(resident)
    session_ids = [session_id for session_id, _, _ in qualifying]
    errors = [
        error
        for session_id, session, _ in qualifying
        for error in _task_errors(session_id, session)
    ]

    baseline = resident["baseline"]
    comparison = BaselineComparison(
        task_id=qualifying[-1][1]["task"],
        metric=BaselineMetric.ERROR_SCORE,
        observed=qualifying[-1][2],
        baseline_mean=round(baseline["mean"], 2),
        baseline_sd=round(baseline["std"], 2),
        baseline_days=DEMO_DAYS,
        threshold=baseline["threshold"],
    )

    explainer_errors = [
        {
            "type": str(error.type),
            "step_id": error.step_id or _UNKNOWN_STEP,
            "t_start": error.t_start,
        }
        for error in errors
    ]
    summary = _get_explainer().summarise(
        explainer_errors,
        {
            "observed": len(errors),
            "baseline_mean": round(_normal_error_rate(resident), 2),
            "baseline_days": DEMO_DAYS,
        },
        _context(resident["care_records"]),
    )

    return Alert(
        alert_id=f"alert-{resident['id']}",
        resident_id=resident["id"],
        created_at=DEMO_NOW,
        kind=AlertKind.CHANGE_FLAG,
        session_ids=session_ids,
        errors=errors,
        baseline=comparison,
        summary=summary,
        suggested_checks=[
            SuggestedCheck(check) for check in suggest_checks(resident["care_records"], DEMO_NOW)
        ],
        patterns=_patterns(resident),
    )
