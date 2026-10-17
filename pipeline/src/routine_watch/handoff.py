"""Nurse shift handoff: who changed in the window this nurse missed (SPEC section 9).

A nurse coming on shift does not want six resident screens, they want one: who had a
change flagged for review in the last twelve hours, which alerts nobody has reviewed
yet, and who is on a slow rise. `build_handoff` builds exactly that from the same pure
functions the dashboard already uses - offline, deterministic, no DB::

    from routine_watch.demo import DEMO_NOW
    from routine_watch.handoff import build_handoff

    build_handoff(DEMO_NOW, hours=12)
    # {"window_hours": 12,
    #  "residents": [{"resident_id": "mrs-k", "name": "Mrs. K", "flags": 1,
    #                 "pending_review": 1, "trending": False}, ...],
    #  "summary": "..."}

`now` is where the window ends and must be timezone-aware. Pass `demo.DEMO_NOW`: the
synthetic history and a live session played on stage (`routine_watch.live`) are both
anchored there, so that is the clock the demo's data lives on.

The plain-language summary comes from the `Explainer` interface, which means the
template explainer unless `LIVE_API=1` and a key are set (AGENTS.md): no paid call
from a test, from CI or from the demo's default path. Routine Watch flags a change for
review - here as everywhere, it never diagnoses anything.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, timedelta
from statistics import mean

from .alerts import build_alerts
from .contracts import Alert
from .demo import demo_residents
from .drift import drift
from .explain import Explainer
from .explain_claude import get_explainer
from .feedback import FeedbackStore

#: A nursing shift, and so the window the handoff looks back over by default.
DEFAULT_WINDOW_H = 12

#: Stand-in for the step an error happened at. The demo history carries a count of
#: errors per type per session rather than the individual step events, so the summary
#: gets the same placeholder step and spaced times `alerts.py` hands the explainer.
_UNKNOWN_STEP = "the task"

_ERROR_SPACING_S = 10.0


def _get_explainer() -> Explainer:
    """Wraps `get_explainer()` so tests can monkeypatch the explainer used here."""
    return get_explainer()


def build_handoff(
    now: datetime,
    hours: int = DEFAULT_WINDOW_H,
    *,
    feedback: FeedbackStore | None = None,
) -> dict:
    """One row per resident for the `hours` before `now`, plus a summary of the lot.

    Every resident is listed, quiet ones included with `flags: 0`, so a nurse can see
    that the unit was looked at rather than guess why someone is missing. Rows needing
    attention come first. `feedback` is the nurse feedback logged so far: it tunes each
    resident's threshold and takes reviewed alerts out of `pending_review`.
    """
    if now.tzinfo is None:
        raise ValueError("now must be timezone-aware: pass demo.DEMO_NOW")

    residents = demo_residents()
    pending = _pending_by_resident(build_alerts(residents), now, hours, feedback)

    rows = []
    flagged_sessions = []
    for resident in residents:
        threshold = _threshold(resident, feedback)
        flagged = [
            session
            for session, score in _window_sessions(resident, now, hours)
            if score > threshold
        ]
        flagged_sessions.extend(flagged)
        rows.append(
            {
                "resident_id": resident["id"],
                "name": resident["name"],
                "flags": len(flagged),
                "pending_review": pending.get(resident["id"], 0),
                "trending": _trending(resident),
            }
        )
    rows.sort(key=_review_first)

    return {
        "window_hours": hours,
        "residents": rows,
        "summary": _summary(rows, flagged_sessions, residents, hours),
    }


def _window_sessions(resident: dict, now: datetime, hours: int) -> list[tuple[dict, float]]:
    """The resident's sessions that ran inside the window, with their scores."""
    start = now - timedelta(hours=hours)
    return [
        (session, point["score"])
        for session, point in zip(resident["sessions"], resident["scores"], strict=True)
        if start <= datetime.fromisoformat(session["ts"]) <= now
    ]


def _threshold(resident: dict, feedback: FeedbackStore | None) -> float:
    """This resident's error-score threshold, tuned by their logged feedback (MVP 7)."""
    base = resident["baseline"]["threshold"]
    if feedback is None:
        return base
    return feedback.threshold(resident["id"], base=base)


def _pending_by_resident(
    alerts: list[Alert], now: datetime, hours: int, feedback: FeedbackStore | None
) -> dict[str, int]:
    """Alerts per resident raised in the window that still have no nurse verdict.

    With no feedback store nothing has been reviewed, so every alert in the window is
    still waiting for someone.
    """
    start = now - timedelta(hours=hours)
    pending: dict[str, int] = defaultdict(int)
    for alert in alerts:
        if not start <= alert.created_at <= now:
            continue
        if feedback is not None and feedback.get(alert.alert_id) is not None:
            continue
        pending[alert.resident_id] += 1
    return pending


def _trending(resident: dict) -> bool:
    """Whether this resident's daily error score is on a slow rise (`drift.drift`).

    A slow drift takes weeks to show, not one shift (SPEC section 7.5), so it is read
    over the resident's whole history and shown beside the window's flags rather than
    measured inside it: it is the thing a nurse would otherwise miss entirely.
    """
    return drift(_daily_scores(resident["scores"])).trending


def _daily_scores(scores: list[dict]) -> list[tuple[date, float]]:
    """Mean score per calendar date, the one-point-per-day shape `drift` wants.

    Same grouping as the `/residents/{id}/drift` route, kept here so the trend a nurse
    reads on the handoff is the one they read on the resident's drift card, and so this
    module stays independent of the API layer that imports it.
    """
    by_day: dict[date, list[float]] = defaultdict(list)
    for entry in scores:
        by_day[datetime.fromisoformat(entry["ts"]).date()].append(entry["score"])
    return sorted((day, mean(values)) for day, values in by_day.items())


def _review_first(row: dict) -> tuple[int, int, bool, str]:
    """Sort key: most flags first, then unreviewed alerts, then a rising trend, then
    name, so two quiet residents always come out in the same order."""
    return (-row["flags"], -row["pending_review"], not row["trending"], row["name"])


def _summary(
    rows: list[dict], flagged_sessions: list[dict], residents: list[dict], hours: int
) -> str:
    """The handoff's plain-language line, written by the `Explainer` (fake by default).

    It is given only what the pipeline found. The errors are the ones in the most
    recent flagged session - the session a nurse would open first, and the one the
    explainer's sentence is about - while the context lines carry the window's own
    totals, resident by resident.
    """
    errors = _explainer_errors(_latest(flagged_sessions))
    baseline = {
        "observed": len(errors),
        "baseline_mean": round(_unit_error_rate(residents), 2),
        "baseline_days": _history_days(residents),
    }
    return _get_explainer().summarise(errors, baseline, _context(rows, hours))


def _latest(sessions: list[dict]) -> dict | None:
    """The most recent of the window's flagged sessions, or None if none was flagged."""
    if not sessions:
        return None
    return max(sessions, key=lambda session: datetime.fromisoformat(session["ts"]))


def _explainer_errors(session: dict | None) -> list[dict]:
    """One entry per error in that session, in the `Explainer` interface's shape."""
    if session is None:
        return []
    errors = []
    t = 0.0
    for error_type, count in sorted(session["errors"].items()):
        for _ in range(count):
            errors.append({"type": error_type, "step_id": _UNKNOWN_STEP, "t_start": t})
            t += _ERROR_SPACING_S
    return errors


def _unit_error_rate(residents: list[dict]) -> float:
    """What a session on this unit normally costs: mean errors per session, all history."""
    counts = [
        sum(session["errors"].values())
        for resident in residents
        for session in resident["sessions"]
    ]
    return sum(counts) / len(counts) if counts else 0.0


def _history_days(residents: list[dict]) -> int:
    """How many calendar days of history that unit average is drawn from."""
    return len(
        {
            datetime.fromisoformat(session["ts"]).date()
            for resident in residents
            for session in resident["sessions"]
        }
    )


def _context(rows: list[dict], hours: int) -> list[str]:
    """The window, then one line per resident worth a look, then the quiet rest.

    These lines reach the nurse as written, whichever explainer is in play, so they are
    the handoff's own facts: the window's length, who to look at and why.
    """
    review = [row for row in rows if _needs_review(row)]
    lines = [f"last {hours} h, {_count(len(rows), 'resident')}"]
    lines.extend(f"{row['name']}: " + ", ".join(_reasons(row)) for row in review)
    quiet = len(rows) - len(review)
    if quiet:
        lines.append(f"{_count(quiet, 'resident')} with no change flagged for review")
    return lines


def _reasons(row: dict) -> list[str]:
    reasons = []
    if row["flags"]:
        reasons.append(f"{_count(row['flags'], 'session')} flagged for review")
    if row["pending_review"]:
        reasons.append(f"{_count(row['pending_review'], 'alert')} pending review")
    if row["trending"]:
        reasons.append("error score trending up")
    return reasons


def _needs_review(row: dict) -> bool:
    return bool(row["flags"] or row["pending_review"] or row["trending"])


def _count(n: int, noun: str) -> str:
    return f"{n} {noun}" if n == 1 else f"{n} {noun}s"
