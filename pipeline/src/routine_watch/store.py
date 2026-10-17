"""Session store: sessions, step events and task errors as time series (SPEC §6.3 and
the Tiger Data prize).

`MemoryStore` is what every test, CI and the offline/demo path use: no database
required. `TimescaleStore` talks to a real TimescaleDB (Tiger Data) instance over
psycopg 3, only when `DATABASE_URL` is set (`get_store`); psycopg itself is the
optional `db` extra and is imported lazily so importing this module never requires it.
Not wired into the API yet - that is a later task.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import datetime
from typing import Protocol, runtime_checkable

from .contracts import ErrorType, EvidenceRef, Session, StepEvent, TaskError


@runtime_checkable
class Store(Protocol):
    def add_session(self, session: Session) -> None:
        """Insert a session, or update it (e.g. `ended_at`/`score` once it finishes)."""
        ...

    def add_events(self, events: list[StepEvent]) -> None:
        """Append step events. Never updated once written."""
        ...

    def add_errors(self, errors: list[TaskError]) -> None:
        """Append task errors. Never updated once written."""
        ...

    def sessions(self, resident_id: str, task_id: str, since: datetime) -> list[Session]:
        """This resident's sessions of this task, `started_at >= since`, oldest first."""
        ...

    def errors_for(self, session_id: str) -> list[TaskError]:
        """Every error recorded against one session, in the order they happened."""
        ...


@dataclass
class MemoryStore:
    """The default store: plain dicts and lists, gone when the process exits."""

    _sessions: dict[str, Session] = field(default_factory=dict)
    _events: list[StepEvent] = field(default_factory=list)
    _errors: dict[str, list[TaskError]] = field(default_factory=dict)

    def add_session(self, session: Session) -> None:
        self._sessions[session.session_id] = session

    def add_events(self, events: list[StepEvent]) -> None:
        self._events.extend(events)

    def add_errors(self, errors: list[TaskError]) -> None:
        for error in errors:
            self._errors.setdefault(error.session_id, []).append(error)

    def sessions(self, resident_id: str, task_id: str, since: datetime) -> list[Session]:
        matches = [
            s
            for s in self._sessions.values()
            if s.resident_id == resident_id and s.task_id == task_id and s.started_at >= since
        ]
        return sorted(matches, key=lambda s: s.started_at)

    def errors_for(self, session_id: str) -> list[TaskError]:
        return list(self._errors.get(session_id, []))


class TimescaleStore:
    """The real store: TimescaleDB (Tiger Data) over psycopg 3.

    Opens one connection per call - sessions end and errors land one batch at a time,
    not in a hot loop, so pooling would be premature. `psycopg` is only imported here,
    not at module scope, so the `db` extra stays optional for anyone not using it.
    """

    def __init__(self, dsn: str) -> None:
        self._dsn = dsn

    def _connection(self):
        import psycopg

        return psycopg.connect(self._dsn)

    def add_session(self, session: Session) -> None:
        with self._connection() as conn:
            conn.execute(
                """
                INSERT INTO sessions
                    (session_id, resident_id, task_id, started_at, ended_at, assisted, score)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (session_id, started_at) DO UPDATE SET
                    ended_at = EXCLUDED.ended_at,
                    assisted = EXCLUDED.assisted,
                    score = EXCLUDED.score
                """,
                (
                    session.session_id,
                    session.resident_id,
                    session.task_id,
                    session.started_at,
                    session.ended_at,
                    session.assisted,
                    session.score,
                ),
            )

    def add_events(self, events: list[StepEvent]) -> None:
        if not events:
            return
        from psycopg.types.json import Json

        with self._connection() as conn:
            conn.executemany(
                """
                INSERT INTO step_events
                    (event_id, session_id, step_id, objects, t_start, t_end, confidence,
                     source, unclear)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                [
                    (
                        event.event_id,
                        event.session_id,
                        event.step_id,
                        Json([label.value for label in event.objects]),
                        event.t_start,
                        event.t_end,
                        event.confidence,
                        event.source.value,
                        event.unclear,
                    )
                    for event in events
                ],
            )

    def add_errors(self, errors: list[TaskError]) -> None:
        if not errors:
            return
        from psycopg.types.json import Json

        with self._connection() as conn:
            conn.executemany(
                """
                INSERT INTO task_errors
                    (error_id, session_id, type, step_id, t_start, t_end, evidence,
                     self_corrected)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """,
                [
                    (
                        error.error_id,
                        error.session_id,
                        error.type.value,
                        error.step_id,
                        error.t_start,
                        error.t_end,
                        Json([ref.model_dump(mode="json") for ref in error.evidence]),
                        error.self_corrected,
                    )
                    for error in errors
                ],
            )

    def sessions(self, resident_id: str, task_id: str, since: datetime) -> list[Session]:
        with self._connection() as conn:
            rows = conn.execute(
                """
                SELECT session_id, resident_id, task_id, started_at, ended_at, assisted, score
                FROM sessions
                WHERE resident_id = %s AND task_id = %s AND started_at >= %s
                ORDER BY started_at
                """,
                (resident_id, task_id, since),
            ).fetchall()
        return [
            Session(
                session_id=row[0],
                resident_id=row[1],
                task_id=row[2],
                started_at=row[3],
                ended_at=row[4],
                assisted=row[5],
                score=row[6],
            )
            for row in rows
        ]

    def errors_for(self, session_id: str) -> list[TaskError]:
        with self._connection() as conn:
            rows = conn.execute(
                """
                SELECT error_id, session_id, type, step_id, t_start, t_end, evidence,
                       self_corrected
                FROM task_errors
                WHERE session_id = %s
                ORDER BY t_start
                """,
                (session_id,),
            ).fetchall()
        return [
            TaskError(
                error_id=row[0],
                session_id=row[1],
                type=ErrorType(row[2]),
                step_id=row[3],
                t_start=row[4],
                t_end=row[5],
                evidence=[EvidenceRef(**ref) for ref in row[6]],
                self_corrected=row[7],
            )
            for row in rows
        ]


def get_store() -> Store:
    """The store the rest of the pipeline should use: `MemoryStore` unless
    `DATABASE_URL` is set (SPEC §6.3 - in-memory is the default so tests, CI and the
    demo need no database)."""
    dsn = os.environ.get("DATABASE_URL")
    if dsn:
        return TimescaleStore(dsn)
    return MemoryStore()
