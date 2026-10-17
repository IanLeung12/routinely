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
from .tasks import TASKS_DIR, TaskGraph, TaskGraphError, load_task

#: How far back a session still counts toward the flag (SPEC section 7).
FLAG_WINDOW_H = 48.0

#: How far back a care-record note is still worth mentioning next to the alert.
CONTEXT_LOOKBACK_H = 72.0

#: The step a placeholder error is spaced before/after, as a fraction of the
#: session's duration, so two sessions of different lengths don't land on the
#: same timestamps and read as duplicate errors in the summary.
_MIN_ERROR_SPAN_S = 5.0


def _get_explainer() -> Explainer:
    """Wraps `get_explainer()` so tests can monkeypatch the explainer used here."""
    return get_explainer()


def build_alerts(residents: list[dict]) -> list[Alert]:
    """One alert per flagged resident (SPEC section 7: a single bad session never
    alerts, so only residents `demo_residents` already flagged get one)."""
    return [_build_alert(resident) for resident in residents if resident["status"] == "flagged"]


def _qualifying_sessions(resident: dict) -> list[tuple[str, dict, float]]:
    """The sessions behind the flag: id, session dict and score, oldest first.

    A live session played twice is one session here too: `session_log.record`
    replaces a session recorded under the same `session_id` rather than adding a
    second one (SPEC section 10 step 4), so a dashboard reload that replays the same
    recording doesn't grow the alert - `resident["sessions"]` already carries only
    the one.
    """
    threshold = resident["baseline"]["threshold"]
    window_start = DEMO_NOW - timedelta(hours=FLAG_WINDOW_H)
    qualifying = []
    sessions_and_scores = zip(resident["sessions"], resident["scores"], strict=True)
    for index, (session, point) in enumerate(sessions_and_scores):
        ts = datetime.fromisoformat(session["ts"])
        if window_start <= ts <= DEMO_NOW and point["score"] > threshold:
            qualifying.append((f"{resident['id']}-{index}", session, point["score"]))
    return qualifying


def _graph_for(task: str) -> TaskGraph:
    """The task graph behind a session's `task` field.

    Synthetic history names it by the task file (``"tea"``); a session played live
    names it by the graph's own id (``"make_tea"``, from `live.py`'s `graph.id`).
    Either way, one of the files in `TASKS_DIR` is it.
    """
    try:
        return load_task(task)
    except TaskGraphError:
        for path in TASKS_DIR.glob("*.yaml"):
            graph = load_task(path.stem)
            if graph.id == task:
                return graph
        raise


def _step_candidates(graph: TaskGraph, error_type: str) -> tuple[str, ...]:
    """The steps a placeholder error of this type could plausibly be about."""
    if error_type in ("omission", "abandonment"):
        candidates = graph.required_steps
    elif error_type == "perseveration":
        candidates = tuple(step_id for step_id in graph.step_ids if graph.is_once_only(step_id))
    elif error_type == "sequence":
        candidates = tuple(step_id for step_id in graph.step_ids if graph.deps(step_id))
    else:
        candidates = graph.step_ids
    return candidates or graph.step_ids


def _task_errors(session_id: str, session: dict) -> list[TaskError]:
    """Synthetic per-instance errors from a session's error-type counts.

    The demo history only tracks how many errors of each type a session had, not the
    individual step events, so the step and the time here are plausible placeholders
    rather than anything observed: a real step of this task, spread evenly across the
    session's own duration so two different sessions don't land on the same instant
    and read as a repeated error in the summary.
    """
    graph = _graph_for(session["task"])
    duration = session.get("duration_s") or _MIN_ERROR_SPAN_S
    counts = sorted(session["errors"].items())
    total = sum(count for _, count in counts)
    span = max(duration - _MIN_ERROR_SPAN_S, _MIN_ERROR_SPAN_S)

    errors = []
    index = 0
    for error_type, count in counts:
        candidates = _step_candidates(graph, error_type)
        for i in range(count):
            t_start = round(span * (index + 1) / (total + 1), 1)
            errors.append(
                TaskError(
                    error_id=f"{session_id}:{error_type}:{i}",
                    session_id=session_id,
                    type=error_type,
                    step_id=candidates[index % len(candidates)],
                    t_start=t_start,
                    t_end=min(t_start + _MIN_ERROR_SPAN_S, duration),
                    evidence=[],
                )
            )
            index += 1
    return errors


def _distinct_clauses(errors: list[TaskError]) -> list[dict]:
    """`errors` as explainer input, minus any whose type, step and displayed
    timestamp exactly repeat an earlier one (the explainer renders all three, so a
    repeat there is a repeated clause in the summary, SPEC section 7's "no two bad
    sessions on their own" notwithstanding)."""
    seen: set[tuple[str, str | None, str]] = set()
    distinct = []
    for error in errors:
        minutes, seconds = divmod(int(error.t_start), 60)
        key = (str(error.type), error.step_id, f"{minutes}:{seconds:02d}")
        if key in seen:
            continue
        seen.add(key)
        distinct.append(
            {"type": str(error.type), "step_id": error.step_id, "t_start": error.t_start}
        )
    return distinct


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

    explainer_errors = _distinct_clauses(errors)
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
