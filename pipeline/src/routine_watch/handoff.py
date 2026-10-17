"""Nurse shift handoff: who changed in the window this nurse missed (SPEC section 9).

A nurse coming on shift does not want six resident screens, they want one: who had a
change flagged for review in the last twelve hours, which alerts nobody has reviewed
yet, and who is on a slow rise. `build_handoff` builds exactly that from the same pure
functions the dashboard already uses - offline, deterministic, no DB::

    from routine_watch.demo import DEMO_NOW
    from routine_watch.handoff import build_handoff

    build_handoff(DEMO_NOW, hours=12)
    # {"window_hours": 12,
    #  "residents": [{"resident_id": "mrs-k", "name": "Mrs. K", "room": "204",
    #                 "flags": 1, "previous_flags": 0, "pending_review": 1,
    #                 "trending": False, "monitoring_paused": False,
    #                 "unclear_sessions": 0}, ...],
    #  "paused": [],
    #  "summary": "..."}

`flags` counts the resident's sessions in the window that scored above their own
baseline threshold, which is the evidence a flag rests on rather than the flag itself:
one bad session never alerts (SPEC section 7), so a resident can have a session above
baseline and no alert at all. `pending_review` counts the alerts that were raised and
that nobody has given a verdict on yet.

`previous_flags` is `flags` for the window before this one - `[now - 2 x hours,
now - hours)` - against the same resident's same bar, so a row can say whether this
shift is worse than the last one rather than only how it was. The two windows never
share a session: the current one owns its own lower edge, so a session exactly at
`now - hours` counts once, in this shift.

`unclear_sessions` is the other half of a window: the sessions in that resident's
room the capture was too unclear to score (`routine_watch.session_log`, SPEC section
12). Those never become anybody's history - too little of them can be trusted to
count toward a flag (T342) - so a camera that is blocked, knocked askew or left in
the dark produces a row with nothing on it. The count says the capture could not be
read and to go and look at the camera; it says nothing about the resident.

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
from datetime import datetime, timedelta
from typing import NamedTuple

from . import session_log
from .alerts import (
    build_alerts,
    distinct_clauses,
    normal_error_rate,
    session_id_for,
    task_errors,
)
from .contracts import Alert, TaskError
from .demo import demo_residents
from .drift import daily_scores, drift
from .explain import Explainer
from .explain_claude import get_explainer
from .feedback import FeedbackStore
from .monitoring import get_monitoring_store

#: A nursing shift, and so the window the handoff looks back over by default.
DEFAULT_WINDOW_H = 12


class _FlaggedSession(NamedTuple):
    """A session above its own resident's threshold, and whose session it is."""

    resident: dict
    session_id: str
    session: dict


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
    attention come first, each with the resident's room, so a row read aloud or pasted
    into a handoff note says which door to walk to. Each row also carries
    `previous_flags`, the same count for the shift before this one, so a nurse reads
    better or worse rather than a bare number. `feedback` is the nurse feedback
    logged so far: it tunes the threshold each session is measured against and takes
    reviewed alerts out of `pending_review`.

    Each row also carries `unclear_sessions`: how many sessions in that resident's
    room the capture was too unclear to score in the window. Those sessions are in
    nobody's history by design (SPEC section 12), so a camera that cannot see is
    invisible here without it - the count is what turns that silence into "check the
    camera view".

    A paused room produces no flags at all (SPEC section 12), which would otherwise
    read as "all quiet" for a resident nobody was watching. `paused` lists every room
    the monitoring store (`monitoring.get_monitoring_store`) currently has paused, and
    each resident row in that room gets `monitoring_paused: True` so a nurse can tell
    "nothing happened" from "nobody was looking".
    """
    if now.tzinfo is None:
        raise ValueError("now must be timezone-aware: pass demo.DEMO_NOW")

    residents = demo_residents()
    # The same store the alert screen builds with, so these are the alerts a nurse
    # opens from a handoff row (T152) rather than a second ranking of the same change.
    pending = _pending_by_resident(
        build_alerts(residents, feedback=feedback), now, hours, feedback
    )
    paused_rooms = set(get_monitoring_store().paused_rooms())

    rows = []
    flagged_sessions: list[_FlaggedSession] = []
    paused: list[dict] = []
    for resident in residents:
        threshold = _threshold(resident, feedback)
        flagged = [
            _FlaggedSession(resident, session_id, session)
            for session_id, session, score in _window_sessions(resident, now, hours)
            if score > threshold
        ]
        flagged_sessions.extend(flagged)
        room_paused = resident["room"] in paused_rooms
        if room_paused:
            paused.append(
                {
                    "room": resident["room"],
                    "resident_id": resident["id"],
                    "name": resident["name"],
                }
            )
        rows.append(
            {
                "resident_id": resident["id"],
                "name": resident["name"],
                "room": resident["room"],
                "flags": len(flagged),
                "previous_flags": _previous_flags(resident, now, hours, threshold),
                "pending_review": pending.get(resident["id"], 0),
                "unclear_sessions": _unclear_sessions(resident["room"], now, hours),
                "trending": _trending(resident),
                "monitoring_paused": room_paused,
            }
        )
    rows.sort(key=_review_first)

    return {
        "window_hours": hours,
        "residents": rows,
        "paused": paused,
        "summary": _summary(rows, flagged_sessions, hours, paused),
    }


def _window_sessions(resident: dict, now: datetime, hours: int) -> list[tuple[str, dict, float]]:
    """The resident's sessions that ran inside the window: id, session and score.

    Both edges count: a session at `now` has just finished and one at `now - hours`
    is the oldest thing this shift is answerable for.
    """
    return _sessions_between(resident, now - timedelta(hours=hours), now)


def _previous_flags(resident: dict, now: datetime, hours: int, threshold: float) -> int:
    """`flags` for the window before this one, against the same resident's same bar.

    The window the nurse going off shift had: `[now - 2 x hours, now - hours)`. Its
    upper edge is open because `_window_sessions` owns that instant, so a session
    exactly at `now - hours` is counted once, by this shift, rather than by both -
    "one more than last shift" has to mean one more session, not one re-counted.

    The bar is the current window's `threshold`, feedback and all (MVP 7): the two
    counts are only comparable if they were measured the same way.
    """
    end = now - timedelta(hours=hours)
    return len(
        [
            score
            for _, _, score in _sessions_between(
                resident, end - timedelta(hours=hours), end, include_end=False
            )
            if score > threshold
        ]
    )


def _sessions_between(
    resident: dict, start: datetime, end: datetime, *, include_end: bool = True
) -> list[tuple[str, dict, float]]:
    """The resident's sessions from `start` to `end`: id, session and score each.

    The id is `alerts.session_id_for`'s, the one that session's alert gives it, so an
    error this handoff mentions and the same error on the alert screen are one error.
    Indexes count from the resident's whole history, so an id stays the same id
    whichever window it is read in.
    """
    sessions_and_scores = zip(resident["sessions"], resident["scores"], strict=True)
    return [
        (session_id_for(resident["id"], index, session), session, point["score"])
        for index, (session, point) in enumerate(sessions_and_scores)
        if _inside(datetime.fromisoformat(session["ts"]), start, end, include_end)
    ]


def _inside(ts: datetime, start: datetime, end: datetime, include_end: bool) -> bool:
    return start <= ts <= end if include_end else start <= ts < end


def _unclear_sessions(room: str, now: datetime, hours: int) -> int:
    """Sessions in `room` the capture was too unclear to score inside the window.

    Read from `routine_watch.session_log`, where a live session that ends unclear
    leaves a timestamp and nothing else (SPEC section 12). Both edges count, the same
    window `_window_sessions` reads the resident's own sessions over, so a session
    that has just ended unclear is this shift's to hand over.

    It is the room's count, not the resident's: what could not be read is the camera
    view of that room, so every resident in it gets the same line, and the line is
    about the camera.
    """
    return session_log.unclear_in(room, now - timedelta(hours=hours), now)


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
    measured inside it: it is the thing a nurse would otherwise miss entirely. Same
    daily grouping as the resident's drift card, so both read the same trend.
    """
    return drift(daily_scores(resident["scores"])).trending


def _review_first(row: dict) -> tuple[int, int, bool, str]:
    """Sort key: most flags first, then unreviewed alerts, then a rising trend, then
    name, so two quiet residents always come out in the same order."""
    return (-row["flags"], -row["pending_review"], not row["trending"], row["name"])


def _summary(
    rows: list[dict],
    flagged_sessions: list[_FlaggedSession],
    hours: int,
    paused: list[dict] | None = None,
) -> str:
    """The handoff's plain-language line, written by the `Explainer` (fake by default).

    It is given only what the pipeline found, about one session: the most recent
    flagged one, which is the session a nurse would open first and the one the
    explainer's sentence is about. Its errors come from `alerts.task_errors`, so the
    handoff names the steps and times that session's own alert names rather than a
    second guess at them, and they are measured against that resident's own history
    and nobody else's (SPEC section 7). A quiet window has no session to compare, so
    its numbers are zeros rather than somebody else's average.

    The context lines say whose session it is, then carry the window's own totals
    resident by resident, then one line per paused room so a quiet window reads as
    "nobody was watching" rather than "all quiet" (SPEC section 12).
    """
    latest = _latest(flagged_sessions)
    if latest is None:
        errors: list[TaskError] = []
        baseline = {"observed": 0, "baseline_mean": 0.0, "baseline_days": 0}
    else:
        errors = task_errors(latest.session_id, latest.session)
        baseline = {
            "observed": len(errors),
            "baseline_mean": round(normal_error_rate(latest.resident), 2),
            "baseline_days": _history_days(latest.resident),
        }
    return _get_explainer().summarise(
        distinct_clauses(errors), baseline, _context(rows, hours, latest, paused or [])
    )


def _latest(flagged: list[_FlaggedSession]) -> _FlaggedSession | None:
    """The most recent of the window's flagged sessions, or None if none was flagged."""
    if not flagged:
        return None
    return max(flagged, key=lambda item: datetime.fromisoformat(item.session["ts"]))


def _history_days(resident: dict) -> int:
    """How many calendar days this resident's own average is drawn from."""
    return len(
        {datetime.fromisoformat(session["ts"]).date() for session in resident["sessions"]}
    )


def _context(
    rows: list[dict], hours: int, latest: _FlaggedSession | None, paused: list[dict]
) -> list[str]:
    """Whose session it is, the window, then one line per resident worth a look, then
    one line per paused room, then the quiet rest.

    These lines reach the nurse as written, whichever explainer is in play, so they are
    the handoff's own facts: whose session the sentence is about, the window's length,
    who to look at and why, and which rooms nobody was watching.
    """
    review = [row for row in rows if _needs_review(row)]
    paused_ids = {room["resident_id"] for room in paused}
    unclear = [
        row
        for row in rows
        if row["unclear_sessions"] and row["resident_id"] not in paused_ids
    ]
    lines = []
    if latest is not None:
        lines.append(f"this session is {latest.resident['name']}'s")
    lines.append(f"last {hours} h, {_count(len(rows), 'resident')}")
    lines.extend(f"{row['name']}: " + ", ".join(_reasons(row)) for row in review)
    lines.extend(_unclear_line(row) for row in unclear)
    lines.extend(_paused_line(room) for room in paused)
    unclear_ids = {row["resident_id"] for row in unclear}
    quiet = len(
        [
            row
            for row in rows
            if row not in review
            and row["resident_id"] not in paused_ids
            and row["resident_id"] not in unclear_ids
        ]
    )
    if quiet:
        lines.append(f"{_count(quiet, 'resident')} with nothing to review")
    return lines


def _paused_line(paused_room: dict) -> str:
    """One context line for a room nobody was watching (SPEC section 12).

    Wording follows SPEC section 7.5: the pipeline never diagnoses, it only says what
    it did or did not look at.
    """
    return (
        f"Room {paused_room['room']} ({paused_room['name']}) was paused, "
        "so no flags are expected from it"
    )


def _unclear_line(row: dict) -> str:
    """One context line for a resident whose room had sessions too unclear to score.

    Unclear is not a flag (SPEC section 12), so this names the camera view, never the
    resident, and never joins `_reasons`.
    """
    return (
        f"{row['name']}: {_count(row['unclear_sessions'], 'session')} too unclear to "
        "score, check the camera view"
    )


def _reasons(row: dict) -> list[str]:
    reasons = []
    if row["flags"]:
        reasons.append(f"{_count(row['flags'], 'session')} above baseline")
    if row["pending_review"]:
        reasons.append(f"{_count(row['pending_review'], 'alert')} pending review")
    if row["trending"]:
        reasons.append("error score trending up")
    return reasons


def _needs_review(row: dict) -> bool:
    return bool(row["flags"] or row["pending_review"] or row["trending"])


def _count(n: int, noun: str) -> str:
    return f"{n} {noun}" if n == 1 else f"{n} {noun}s"
