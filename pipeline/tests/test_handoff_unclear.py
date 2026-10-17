"""The shift handoff says when a room's capture was too unclear to score (T355).

Since T342 an unclear live session is dropped: it is streamed and scored 0.0, and
then left out of the resident's history so bad lighting cannot flag a change for
review (SPEC section 12). That silence is what this covers - repeated bad light, a
camera knocked askew or a view blocked by a trolley produces a resident with nothing
on their row, and nobody goes to look - so `session_log` keeps a timestamp per room
for each of those sessions and every handoff row carries `unclear_sessions` for its
own window.

Timestamps and a room, never frames and never a score (SPEC section 8), and the count
is about the camera view: it says the capture could not be read, never anything about
the resident in front of it.

The recordings are `test_live_unclear`'s - the demo's bad session written at step
level, once with four of its seven steps barely seen - so what counts as unclear here
is the same thing that keeps a session out of the history there, read once.

The autouse `_empty_log` fixture (`conftest.py`) resets the process-global session log
around every test, the unclear tally included.
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timedelta
from pathlib import Path

from fastapi.testclient import TestClient
from jsonschema import Draft202012Validator
from test_live_unclear import _BARELY_SEEN as BARELY_SEEN
from test_live_unclear import QUIET_RESIDENT, play, write_scenario

from routine_watch import session_log
from routine_watch.api import app
from routine_watch.contracts import Handoff, repo_root, schema_name
from routine_watch.demo import DEMO_NOW, demo_residents
from routine_watch.handoff import build_handoff

#: A shift, the window the handoff defaults to.
SHIFT_H = 12


def row(resident_id: str, hours: int = SHIFT_H, now: datetime = DEMO_NOW) -> dict:
    """One resident's handoff row for the window of `hours` ending at `now`."""
    rows = build_handoff(now, hours)["residents"]
    return next(entry for entry in rows if entry["resident_id"] == resident_id)


def resident(resident_id: str) -> dict:
    """One seeded demo resident, live sessions and all (`routine_watch.demo`)."""
    return next(entry for entry in demo_residents() if entry["id"] == resident_id)


def play_unclear(tmp_path: Path, name: str, resident_id: str = QUIET_RESIDENT) -> None:
    """Play one session whose capture is too unclear to score, as `resident_id`."""
    play(write_scenario(tmp_path / name, name, unclear=BARELY_SEEN), resident_id)


# ------------------------------------------------ what the window could not read


def test_two_unclear_sessions_in_the_window_are_counted_on_the_row(tmp_path: Path) -> None:
    play_unclear(tmp_path, "unclear-1")
    play_unclear(tmp_path, "unclear-2")

    assert row(QUIET_RESIDENT)["unclear_sessions"] == 2


def test_counting_them_leaves_the_resident_s_history_and_flag_alone(tmp_path: Path) -> None:
    """The count is the only thing an unclear session leaves behind (T342): it is in
    no history, so it moves no score, no flag and no other number on the row."""
    before = row(QUIET_RESIDENT)
    before_status = resident(QUIET_RESIDENT)["status"]
    before_sessions = len(resident(QUIET_RESIDENT)["sessions"])

    play_unclear(tmp_path, "unclear-1")
    play_unclear(tmp_path, "unclear-2")

    assert session_log.sessions_for(QUIET_RESIDENT) == []
    assert len(resident(QUIET_RESIDENT)["sessions"]) == before_sessions
    assert resident(QUIET_RESIDENT)["status"] == before_status
    # Everything on the row but the new count reads exactly as it did.
    assert row(QUIET_RESIDENT) | {"unclear_sessions": 0} == before


def test_the_window_decides_which_unclear_sessions_count() -> None:
    """A tally with no window would grow all day and never clear. Both edges count,
    the same way `_window_sessions` reads the resident's own sessions."""
    room = resident(QUIET_RESIDENT)["room"]
    session_log.record_unclear(room, DEMO_NOW - timedelta(hours=SHIFT_H))  # this shift's edge
    session_log.record_unclear(room, DEMO_NOW - timedelta(hours=20))  # the shift before it

    assert row(QUIET_RESIDENT, hours=SHIFT_H)["unclear_sessions"] == 1
    assert row(QUIET_RESIDENT, hours=24)["unclear_sessions"] == 2


def test_the_count_belongs_to_the_room_it_was_captured_in(tmp_path: Path) -> None:
    """It is one room's camera that could not be read, so no other row says so."""
    play_unclear(tmp_path, "unclear-1")

    elsewhere = [
        entry["unclear_sessions"]
        for entry in build_handoff(DEMO_NOW, SHIFT_H)["residents"]
        if entry["resident_id"] != QUIET_RESIDENT
    ]

    assert row(QUIET_RESIDENT)["unclear_sessions"] == 1
    assert elsewhere and set(elsewhere) == {0}


def test_a_session_the_camera_read_fine_is_not_counted(tmp_path: Path) -> None:
    """The control: the same recording, clearly enough to score, is one of hers and
    leaves the camera line off her row."""
    play(write_scenario(tmp_path / "clear", "clear-1"), QUIET_RESIDENT)

    assert [session.session_id for session in session_log.sessions_for(QUIET_RESIDENT)] == [
        "clear-1"
    ]
    assert row(QUIET_RESIDENT)["unclear_sessions"] == 0


def test_a_quiet_unit_hands_over_no_camera_to_check() -> None:
    assert all(
        entry["unclear_sessions"] == 0 for entry in build_handoff(DEMO_NOW, SHIFT_H)["residents"]
    )


def test_unclear_sessions_are_not_counted_as_nothing_to_review(tmp_path: Path) -> None:
    """T355 added the count to the row; this is the summary's own copy of the same
    bug (T425) - a room the capture could not read must read as "check the camera",
    never as "quiet", or a nurse skips the exact room that needs a look."""
    before = build_handoff(DEMO_NOW, SHIFT_H)["summary"]

    play_unclear(tmp_path, "unclear-1")
    after = build_handoff(DEMO_NOW, SHIFT_H)["summary"]

    before_quiet = int(re.search(r"(\d+) residents? with nothing to review", before).group(1))
    after_match = re.search(r"(\d+) residents? with nothing to review", after)
    after_quiet = int(after_match.group(1)) if after_match else 0

    name = resident(QUIET_RESIDENT)["name"]
    assert after_quiet == before_quiet - 1
    assert f"{name}: 1 session too unclear to score, check the camera view" in after


# ---------------------------------------------------------- as the route sends it


def test_the_route_sends_the_count_and_the_schema_holds_it(tmp_path: Path) -> None:
    """The dashboard reads `/handoff` through the generated type
    (`web/src/handoff/types.ts`), so the count has to be in the schema both sides are
    held to and not only in the payload."""
    play_unclear(tmp_path, "unclear-1")
    schema_path = repo_root() / "contracts" / f"{schema_name(Handoff)}.schema.json"
    check = Draft202012Validator(json.loads(schema_path.read_text(encoding="utf-8")))

    with TestClient(app) as client:
        body = client.get("/handoff", params={"hours": SHIFT_H}).json()

    check.validate(body)
    assert all("unclear_sessions" in entry for entry in body["residents"])
    counted = {entry["resident_id"]: entry["unclear_sessions"] for entry in body["residents"]}
    assert counted[QUIET_RESIDENT] == 1
    assert sum(counted.values()) == 1
