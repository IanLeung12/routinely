"""T121: a demo alert's errors name a real step with a plausible timestamp, the
summary never repeats a clause, and replaying the same live session twice doesn't
grow the alert (SPEC section 7, section 10 step 4)."""

import asyncio

import pytest

from routine_watch.alerts import _graph_for, build_alerts, task_errors
from routine_watch.demo import DEMO_RESIDENT, demo_residents
from routine_watch.live import scenario_path, session_messages
from routine_watch.tasks import TaskGraphError

MRS_K = "mrs-k"
MRS_K_LIVE_SCENARIO = "tea_skip_teabag_pour_twice"
_FAST = 1000.0

#: Both the alert-level tests need mrs-k actually flagged (T124: the seeded demo
#: alone leaves her on watch, not flagged).
pytestmark = pytest.mark.usefixtures("mrs_k_flagged")


def _play_live_session() -> None:
    async def play() -> None:
        async for _ in session_messages(
            scenario_path(MRS_K_LIVE_SCENARIO), speed=_FAST, resident_id=DEMO_RESIDENT
        ):
            pass

    asyncio.run(play())


def _mrs_k_alert():
    alerts = {alert.resident_id: alert for alert in build_alerts(demo_residents())}
    return alerts[MRS_K]


def _summary_clauses(summary: str) -> list[str]:
    """The comma-separated bracketed clauses of a `TemplateExplainer` summary."""
    inside = summary.split("(", 1)[1].rsplit(")", 1)[0]
    return [clause.strip() for clause in inside.split(", ")]


def test_demo_alert_errors_all_have_a_step_id():
    alert = _mrs_k_alert()

    assert alert.errors
    assert all(error.step_id is not None for error in alert.errors)


def test_summary_has_no_duplicate_clauses():
    alert = _mrs_k_alert()

    clauses = _summary_clauses(alert.summary)
    assert len(clauses) == len(set(clauses))


def test_live_session_played_twice_leaves_at_most_one_live_session():
    """Replaying the exact same recorded session is still one session
    (`session_log.record` replaces it by `session_id`), so the alert this resident
    already has doesn't grow just because the dashboard reloaded."""
    before = _mrs_k_alert()

    _play_live_session()
    after = _mrs_k_alert()

    assert after.session_ids == before.session_ids
    assert len(after.errors) == len(before.errors)


def test_task_errors_assigns_real_steps_from_history_only_session():
    """A synthetic history session (no `session_id`, named by the task *file*) still
    gets plausible step ids, each a real step of its task."""
    session = {
        "resident_id": "mrs-k",
        "ts": "2025-12-30T08:00:00+00:00",
        "task": "tea",
        "errors": {"omission": 2, "sequence": 1},
        "self_corrected": 0,
        "duration_s": 180.0,
        "assisted": False,
    }

    errors = task_errors("mrs-k-9", session)

    graph = _graph_for("tea")
    assert len(errors) == 3
    assert all(error.step_id in graph.step_ids for error in errors)
    assert all(0.0 <= error.t_start < session["duration_s"] for error in errors)


def test_task_errors_resolves_a_live_session_named_by_its_graph_id():
    """A live-played session names its task by the graph id (`live.py`'s
    `graph.id`, e.g. "make_tea") rather than the task file name ("tea")."""
    session = {
        "resident_id": "mrs-k",
        "session_id": "mrs-k-live-1",
        "ts": "2025-12-31T20:00:00+00:00",
        "task": "make_tea",
        "errors": {"perseveration": 1},
        "self_corrected": 0,
        "duration_s": 90.0,
        "assisted": False,
    }

    errors = task_errors("mrs-k-10", session)

    assert errors[0].step_id is not None


def test_graph_for_raises_for_an_unknown_task():
    with pytest.raises(TaskGraphError):
        _graph_for("not-a-real-task")
