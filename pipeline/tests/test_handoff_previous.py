"""Each handoff row's previous shift: `previous_flags` (T324).

A nurse coming on shift wants to know whether a resident is getting better or worse,
so every row carries last shift's flag count beside this one's. What is worth testing
is where the two windows meet: they must never share a session, or "one more than last
shift" would mean one session counted twice.

The clock here comes from the demo's own data rather than a hand-written timestamp:
the bounds are read off a real above-baseline session, so these tests still say what
they mean if the synthetic history moves.
"""

from datetime import datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from routine_watch import api_state
from routine_watch.api import app
from routine_watch.demo import DEMO_NOW, demo_residents
from routine_watch.handoff import build_handoff
from routine_watch.monitoring import get_monitoring_store

#: The demo resident whose seeded history has the sudden spike (SPEC section 10).
FLAGGED_RESIDENT = "mrs-k"

#: A demo resident whose only above-baseline sessions are days old, so a long enough
#: window has them behind it rather than inside it.
EARLIER_RESIDENT = "mr-nguyen"

#: Two days, the longest window the handoff screen offers: long enough that
#: `EARLIER_RESIDENT`'s older sessions land in the window before this one.
LONG_WINDOW_H = 48


@pytest.fixture(autouse=True)
def _nothing_reviewed():
    """A clean feedback store and every room monitored: both are global state."""
    api_state.reset()
    get_monitoring_store().reset()
    yield
    api_state.reset()
    get_monitoring_store().reset()


def resident(resident_id: str) -> dict:
    return next(r for r in demo_residents() if r["id"] == resident_id)


def row(result: dict, resident_id: str) -> dict:
    rows = [row for row in result["residents"] if row["resident_id"] == resident_id]
    assert rows, f"{resident_id} is missing from the handoff"
    return rows[0]


def above_baseline(resident_id: str) -> list[datetime]:
    """When this demo resident's above-baseline sessions ran, oldest first.

    The same comparison `build_handoff` makes - that resident's own score against
    their own threshold (SPEC section 7) - so a test can place a window edge exactly
    on a session the handoff will count.
    """
    person = resident(resident_id)
    threshold = person["baseline"]["threshold"]
    return [
        datetime.fromisoformat(point["ts"])
        for point in person["scores"]
        if point["score"] > threshold
    ]


def latest_flagged(resident_id: str) -> datetime:
    flagged = above_baseline(resident_id)
    assert flagged, f"{resident_id} has no above-baseline session to measure from"
    return flagged[-1]


def test_every_row_carries_last_shifts_count() -> None:
    rows = build_handoff(DEMO_NOW, 12)["residents"]

    assert rows, "the demo unit has residents to hand over"
    for entry in rows:
        assert entry["previous_flags"] >= 0


def test_the_previous_window_is_the_one_before_this_one() -> None:
    """`previous_flags` is counted the same way `flags` is, one window back: every
    resident's own above-baseline sessions in `[now - 2 h, now - h)`, nobody else's
    average and nobody else's bar."""
    hours = LONG_WINDOW_H
    start = DEMO_NOW - timedelta(hours=2 * hours)
    end = DEMO_NOW - timedelta(hours=hours)
    expected = {
        person["id"]: len([ts for ts in above_baseline(person["id"]) if start <= ts < end])
        for person in demo_residents()
    }

    rows = build_handoff(DEMO_NOW, hours)["residents"]

    assert {entry["resident_id"]: entry["previous_flags"] for entry in rows} == expected


def test_a_session_exactly_at_the_window_start_counts_in_this_window_only() -> None:
    """The edge the two windows share. `flags` owns it: a session at `now - hours` is
    the oldest thing this shift is answerable for, and counting it in both windows
    would make a resident look one worse than last shift for no new session."""
    session = latest_flagged(FLAGGED_RESIDENT)
    now = session + timedelta(hours=12)

    entry = row(build_handoff(now, 12), FLAGGED_RESIDENT)

    assert entry["flags"] == 1, "the session sits exactly on this window's start"
    assert entry["previous_flags"] == 0, "so last shift must not count it again"


def test_a_session_exactly_at_the_previous_window_start_counts_as_last_shift() -> None:
    """One window further on, the same session is the oldest thing the previous
    window holds: `[now - 2 h, now - h)` is closed at the bottom, so nothing falls
    between the two windows either."""
    session = latest_flagged(FLAGGED_RESIDENT)
    now = session + timedelta(hours=24)

    entry = row(build_handoff(now, 12), FLAGGED_RESIDENT)

    assert entry["flags"] == 0, "the session is behind this window now"
    assert entry["previous_flags"] == 1, "it is last shift's"


def test_a_session_just_before_the_previous_window_counts_in_neither() -> None:
    """A window back from that, the session is older than both windows and the row
    reads as a quiet shift after a quiet shift rather than a stale count."""
    session = latest_flagged(FLAGGED_RESIDENT)
    now = session + timedelta(hours=24, minutes=1)

    entry = row(build_handoff(now, 12), FLAGGED_RESIDENT)

    assert (entry["flags"], entry["previous_flags"]) == (0, 0)


def test_the_demo_window_reads_as_one_more_than_last_shift(mrs_k_flagged) -> None:
    """The demo's fourth beat (SPEC section 10): the session a teammate just made tea
    for is Mrs. K's, and the nurse coming on shift sees that this shift has flagged
    sessions the one before it did not."""
    entry = row(build_handoff(DEMO_NOW, 12), FLAGGED_RESIDENT)

    assert entry["flags"] == 2, "her seeded spike plus the live session"
    assert entry["previous_flags"] == 0, "the shift before hers was quiet"


def test_the_seeded_demo_shift_is_worse_than_the_one_before_it() -> None:
    """Without the live session, the seeded history alone: one flagged session this
    shift, none last shift."""
    entry = row(build_handoff(DEMO_NOW, 12), FLAGGED_RESIDENT)

    assert entry["flags"] == 1
    assert entry["previous_flags"] == 0


def test_a_resident_can_read_as_fewer_than_last_shift() -> None:
    """The other direction, which a bare `flags` cannot say: nothing flagged in the
    last two days, something flagged in the two before them."""
    entry = row(build_handoff(DEMO_NOW, LONG_WINDOW_H), EARLIER_RESIDENT)

    assert entry["flags"] == 0
    assert entry["previous_flags"] == 1


def test_the_route_sends_last_shifts_count_too() -> None:
    with TestClient(app) as client:
        body = client.get("/handoff", params={"hours": 12}).json()

    assert body["residents"], "every demo resident is handed over"
    assert all("previous_flags" in entry for entry in body["residents"])
    assert row(body, FLAGGED_RESIDENT)["previous_flags"] == 0
    assert "diagnos" not in body["summary"].lower()
