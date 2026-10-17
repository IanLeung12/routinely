"""Unit tests for `routine_watch.session_log` (T326)."""

from datetime import UTC, datetime

import pytest

from routine_watch import session_log
from routine_watch.contracts import ErrorType, EvidenceKind, EvidenceRef, Session, TaskError


@pytest.fixture(autouse=True)
def _reset():
    session_log.reset()
    yield
    session_log.reset()


def _session(session_id: str, resident_id: str, started_at: datetime) -> Session:
    return Session(
        session_id=session_id,
        resident_id=resident_id,
        task_id="make_tea",
        started_at=started_at,
    )


def _error(error_id: str, session_id: str) -> TaskError:
    return TaskError(
        error_id=error_id,
        session_id=session_id,
        type=ErrorType.OMISSION,
        t_start=0.0,
        t_end=1.0,
        evidence=[EvidenceRef(kind=EvidenceKind.STEP_EVENT, t_start=0.0, t_end=1.0)],
    )


def test_record_then_sessions_for_returns_oldest_first():
    early = _session("s1", "mrs-k", datetime(2026, 1, 1, tzinfo=UTC))
    late = _session("s2", "mrs-k", datetime(2026, 1, 2, tzinfo=UTC))

    session_log.record("mrs-k", late)
    session_log.record("mrs-k", early)

    assert [s.session_id for s in session_log.sessions_for("mrs-k")] == ["s1", "s2"]


def test_errors_for_session_id():
    session = _session("s1", "mrs-k", datetime(2026, 1, 1, tzinfo=UTC))
    errors = [_error("e1", "s1"), _error("e2", "s1")]

    session_log.record("mrs-k", session, errors)

    assert [e.error_id for e in session_log.errors_for("s1")] == ["e1", "e2"]


def test_unknown_resident_gives_empty_list():
    assert session_log.sessions_for("nobody") == []


def test_unknown_session_gives_empty_list():
    assert session_log.errors_for("nope") == []


def test_two_residents_stay_separate():
    session_log.record("mrs-k", _session("s1", "mrs-k", datetime(2026, 1, 1, tzinfo=UTC)))
    session_log.record("mr-b", _session("s2", "mr-b", datetime(2026, 1, 1, tzinfo=UTC)))

    assert [s.session_id for s in session_log.sessions_for("mrs-k")] == ["s1"]
    assert [s.session_id for s in session_log.sessions_for("mr-b")] == ["s2"]


def test_reset_clears_everything():
    session = _session("s1", "mrs-k", datetime(2026, 1, 1, tzinfo=UTC))
    session_log.record("mrs-k", session, [_error("e1", "s1")])

    session_log.reset()

    assert session_log.sessions_for("mrs-k") == []
    assert session_log.errors_for("s1") == []
