"""The sessions this process has watched finish (SPEC section 10, step 4).

A live session is only worth running if it counts. The demo's fourth beat is Mrs. K's
sparkline spiking and her flag appearing *because of the session that just happened*,
and for that the finished session has to become one of hers. Nothing stores a session
yet - the dashboard's residents are rebuilt from synthetic history every time they are
asked for (`routine_watch.demo`) - so this is the smallest thing that makes one stick::

    from routine_watch import session_log

    session_log.record("mrs-k", session, errors)   # the live session is now hers
    session_log.sessions_for("mrs-k")              # -> [Session], oldest first
    session_log.errors_for(session.session_id)     # -> [TaskError]
    session_log.record_unclear("204", when)        # one nobody could score, by room
    session_log.unclear_in("204", start, end)      # -> how many of those, in a window
    session_log.reset()                            # back to the seeded demo

The second pair is the sessions that did **not** become anybody's. A session too
much of whose capture is unclear is left out of the resident's history on purpose
(`routine_watch.live`, SPEC section 12), which makes a camera nobody can see through
look like a quiet room; all that is kept of it is when it happened and which room's
camera could not read it, so the shift handoff can say "check the camera view"
(`routine_watch.handoff`). Timestamps and a room, never frames, never a resident,
never a score.

It is a dictionary in this process, gone when it exits: no database, no file, no
network. The shape is `routine_watch.store.Store`'s on purpose (a session and its
errors go in, a resident's sessions come out), so pointing the demo at the real store
once it is wired up is a swap rather than a rewrite.

**It is global state, so tests have to put it back.** `demo_residents()` reads this
log, which means a test that plays a live session changes what every later test sees
unless it calls `reset()` - a fixture, not a line at the end of the test that an early
`assert` can skip.
"""

from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime

from .contracts import Session, TaskError

STAGE = "session_log"

#: Sessions by resident, and each session's errors by session id. Two dictionaries
#: rather than one record so that both reads stay the store's: `sessions_for` is the
#: resident's history, `errors_for` is one session's evidence.
_sessions: dict[str, dict[str, Session]] = {}
_errors: dict[str, list[TaskError]] = {}

#: When a session was too unclear to score, by room (SPEC section 12): timestamps and
#: nothing else - no session id, no resident, no errors, no score. By room rather than
#: by resident because what it is about is that room's camera view, and because the
#: session it counts is deliberately nobody's: `record` never sees it.
_unclear: dict[str, list[datetime]] = {}


def record(resident_id: str, session: Session, errors: Iterable[TaskError] = ()) -> None:
    """Record one finished session, and the errors found in it, against a resident.

    `resident_id` is who the session belongs to and wins over the one the session
    carries, because a live session learns its resident from whoever started it rather
    than from the recording it was played out of.

    `errors` is load-bearing, not a tally: they are the evidence this session's alert
    lists (`demo._live_sessions` carries them into the resident's history and
    `alerts.task_errors` reads them), so a session recorded without them is a session
    whose alert has to invent a step and a time for each of its errors (T155).

    Recording the same `session_id` again replaces it, the way
    `store.MemoryStore.add_session` does: a session seen twice is one session, not two
    bad sessions in the window that between them would flag a change on their own.
    """
    if session.resident_id != resident_id:
        session = session.model_copy(update={"resident_id": resident_id})
    _sessions.setdefault(resident_id, {})[session.session_id] = session
    _errors[session.session_id] = list(errors)


def sessions_for(resident_id: str) -> list[Session]:
    """Every session recorded against `resident_id`, oldest first."""
    sessions = _sessions.get(resident_id, {}).values()
    return sorted(sessions, key=lambda session: session.started_at)


def errors_for(session_id: str) -> list[TaskError]:
    """Every error recorded with one session, in the order they were classified."""
    return list(_errors.get(session_id, ()))


def record_unclear(room: str, at: datetime) -> None:
    """Note that one session in `room` ended too unclear to score (SPEC section 12).

    `at` is when it ended, in the same timezone-aware clock the window reading this
    back uses, and it is all that is kept: an unclear session is left out of the
    resident's scored history entirely (`routine_watch.live`), because too little of
    its capture can be trusted to count it as one of theirs. That silence is what
    this answers - a blocked or badly lit camera produces no sessions at all, which
    reads as a quiet room - so the count belongs to the room's camera view and says
    nothing whatever about the resident in it.
    """
    _unclear.setdefault(room, []).append(at)


def unclear_in(room: str, start: datetime, end: datetime) -> int:
    """How many of `room`'s sessions were too unclear to score from `start` to `end`.

    Both ends count, the way the shift handoff's window does
    (`routine_watch.handoff`): a session that has just this moment ended unclear is
    this shift's to hand over.
    """
    return len([at for at in _unclear.get(room, ()) if start <= at <= end])


def reset() -> None:
    """Forget every recorded session, scored or unclear: the demo is back to its
    seeded history."""
    _sessions.clear()
    _errors.clear()
    _unclear.clear()
