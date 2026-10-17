"""Session store (SPEC §6.3): `MemoryStore` is the default everywhere; `TimescaleStore`
is exercised only when a real `DATABASE_URL` is set, which CI and the tester never do
(AGENTS.md - paid/managed services only behind an interface with a fake as default)."""

from __future__ import annotations

import os
import re
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from routine_watch.contracts import (
    ErrorType,
    EvidenceKind,
    EvidenceRef,
    ObjectLabel,
    Session,
    StepEvent,
    StepSource,
    TaskError,
)
from routine_watch.store import MemoryStore, Store, TimescaleStore, get_store

SQL_PATH = Path(__file__).resolve().parents[1] / "sql" / "schema.sql"


def _session(session_id: str, *, resident_id="r1", task_id="make_tea", started_at=None) -> Session:
    return Session(
        session_id=session_id,
        resident_id=resident_id,
        task_id=task_id,
        started_at=started_at or datetime(2026, 1, 1, tzinfo=UTC),
    )


def _event(event_id: str, session_id: str) -> StepEvent:
    return StepEvent(
        event_id=event_id,
        session_id=session_id,
        step_id="boil_water",
        objects=[ObjectLabel.KETTLE],
        t_start=0.0,
        t_end=1.0,
        confidence=0.9,
        source=StepSource.RULE,
    )


def _error(error_id: str, session_id: str) -> TaskError:
    return TaskError(
        error_id=error_id,
        session_id=session_id,
        type=ErrorType.OMISSION,
        step_id="teabag_in_cup",
        t_start=10.0,
        t_end=12.0,
        evidence=[EvidenceRef(kind=EvidenceKind.STEP_EVENT, t_start=10.0, t_end=12.0)],
    )


def test_memory_store_is_the_default_store(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    assert isinstance(get_store(), MemoryStore)


def test_get_store_picks_timescale_when_database_url_is_set(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgres://user:pass@host/db")
    store = get_store()
    assert isinstance(store, TimescaleStore)


def test_memory_store_satisfies_the_store_protocol():
    store: Store = MemoryStore()
    assert isinstance(store, Store)


def test_add_session_and_query_by_resident_task_and_since():
    store = MemoryStore()
    early = _session("s1", started_at=datetime(2026, 1, 1, tzinfo=UTC))
    late = _session("s2", started_at=datetime(2026, 1, 5, tzinfo=UTC))
    other_resident = _session("s3", resident_id="r2", started_at=datetime(2026, 1, 5, tzinfo=UTC))
    other_task = _session("s4", task_id="make_coffee", started_at=datetime(2026, 1, 5, tzinfo=UTC))
    for session in (early, late, other_resident, other_task):
        store.add_session(session)

    result = store.sessions("r1", "make_tea", since=datetime(2026, 1, 1, tzinfo=UTC))
    assert [s.session_id for s in result] == ["s1", "s2"]

    result = store.sessions("r1", "make_tea", since=datetime(2026, 1, 2, tzinfo=UTC))
    assert [s.session_id for s in result] == ["s2"]


def test_add_session_twice_updates_rather_than_duplicates():
    store = MemoryStore()
    started = datetime(2026, 1, 1, tzinfo=UTC)
    store.add_session(_session("s1", started_at=started))
    ended = _session("s1", started_at=started).model_copy(
        update={"ended_at": started + timedelta(minutes=5), "score": 0.5}
    )
    store.add_session(ended)

    result = store.sessions("r1", "make_tea", since=started)
    assert len(result) == 1
    assert result[0].ended_at == started + timedelta(minutes=5)
    assert result[0].score == 0.5


def test_add_events_does_not_raise_and_accepts_empty_list():
    store = MemoryStore()
    store.add_events([])
    store.add_events([_event("e1", "s1"), _event("e2", "s1")])


def test_add_errors_and_errors_for_session():
    store = MemoryStore()
    store.add_errors([_error("err1", "s1"), _error("err2", "s1"), _error("err3", "s2")])

    result = store.errors_for("s1")
    assert [e.error_id for e in result] == ["err1", "err2"]
    assert result[0].evidence[0].kind == EvidenceKind.STEP_EVENT


def test_errors_for_unknown_session_is_empty():
    store = MemoryStore()
    assert store.errors_for("missing") == []


@pytest.mark.skipif(
    not os.environ.get("DATABASE_URL"), reason="needs a real Timescale DATABASE_URL"
)
class TestTimescaleStoreAgainstARealDatabase:
    """Only runs when a human points `DATABASE_URL` at a real Timescale instance; CI,
    tests-by-default and the tester never set it (AGENTS.md)."""

    def test_round_trips_a_session_an_event_and_an_error(self):
        store = TimescaleStore(os.environ["DATABASE_URL"])
        session = _session("ts-s1")
        store.add_session(session)
        store.add_events([_event("ts-e1", "ts-s1")])
        store.add_errors([_error("ts-err1", "ts-s1")])

        sessions = store.sessions("r1", "make_tea", since=datetime(2025, 1, 1, tzinfo=UTC))
        assert any(s.session_id == "ts-s1" for s in sessions)

        errors = store.errors_for("ts-s1")
        assert [e.error_id for e in errors] == ["ts-err1"]


def test_schema_sql_creates_the_three_tables_idempotently():
    sql = SQL_PATH.read_text(encoding="utf-8")

    for table in ("sessions", "step_events", "task_errors"):
        assert re.search(rf"CREATE TABLE IF NOT EXISTS {table}\b", sql), table
        assert f"create_hypertable('{table}'" in sql, table
    assert "if_not_exists => TRUE" in sql


def test_schema_sql_is_a_sequence_of_well_formed_statements():
    sql = SQL_PATH.read_text(encoding="utf-8")
    body = re.sub(r"--.*", "", sql)
    statements = [s.strip() for s in body.split(";") if s.strip()]

    assert statements, "schema.sql has no statements"
    allowed_starts = ("CREATE", "SELECT", "ALTER", "DROP", "COMMENT")
    for statement in statements:
        assert statement.upper().startswith(allowed_starts), statement
        assert statement.count("(") == statement.count(")"), statement
