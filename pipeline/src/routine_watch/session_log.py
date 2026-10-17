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
    session_log.reset()                            # back to the seeded demo

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

from .contracts import Session, TaskError

STAGE = "session_log"

#: Sessions by resident, and each session's errors by session id. Two dictionaries
#: rather than one record so that both reads stay the store's: `sessions_for` is the
#: resident's history, `errors_for` is one session's evidence.
_sessions: dict[str, dict[str, Session]] = {}
_errors: dict[str, list[TaskError]] = {}


def record(resident_id: str, session: Session, errors: Iterable[TaskError] = ()) -> None:
    """Record one finished session, and the errors found in it, against a resident.

    `resident_id` is who the session belongs to and wins over the one the session
    carries, because a live session learns its resident from whoever started it rather
    than from the recording it was played out of.

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


def reset() -> None:
    """Forget every recorded session: the demo is back to its seeded history."""
    _sessions.clear()
    _errors.clear()
