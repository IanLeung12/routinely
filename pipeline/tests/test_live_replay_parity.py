"""The live socket and the offline replay must read a recording the same way (SPEC §10).

A recording reaches a nurse down two paths. `routine_watch.live.session_messages` plays
it as a live session - the camera's stand-in and the demo's fallback when the camera or
the Wi-Fi gives out - and the live screen draws what that socket sends, `as_json` and
all. `routine_watch.replay.run` runs the same directory offline, and that reading is
the one `scripts/e2e.sh` and every `expected.yaml` pin in CI, and the one the alert a
nurse opens afterwards is built from. If the two drifted apart, the screen a teammate
watches on stage and the alert that session leaves behind would tell two different
stories about the same minute, and only one of them would be the one CI tested.

So this takes every single-session recording under `tests/scenarios/` and compares
everything both paths publish about the finished session: its session id, its task, the
steps in the order they were recognised, how many of those were unclear, every field of
every error it ended on, its score, and the change flag that score raises.

**Which flag.** `session_end`'s `flag` field is not the recording's verdict: it is the
resident's, read over their own history with this session now in it, because the live
screen sits beside the dashboard and a flag there means that resident's row has gone
red and "View alert" opens something (T236, `live.py`, "the `flag` is the resident's").
Comparing that field with `run()["flag"]` would be comparing two different questions -
about a third of today's recordings answer them differently, by design - so the flag is
compared like with like: the change flag the live session's own score raises over the
recording's history (`replay.change_flag`, the same call `run` makes). The field's own
reading is checked where it belongs, against `/residents` and `/alerts`, by
`test_live_flag_consistency.py` and `test_live.py`'s
`test_session_end_says_what_the_dashboard_says`.

Errors are compared as the socket sends them - `as_json` output, not the models behind
it - and on every field `replay.run` publishes, times included. `expected.yaml` records
neither an error's times nor its self-correction, so `test_live_matches_replay.py` and
`test_live.py`, which compare the two paths through the scenario file, cannot see a
drift in either.

Everything runs at `FAST`, so the whole corpus replays in seconds with no real sleeps.
The autouse `_empty_log` fixture (`conftest.py`) resets the session log around every
test, so the sessions played here are nobody's history by the time the next test runs.
"""

from __future__ import annotations

import asyncio
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

import pytest

from routine_watch.live import as_json, session_messages
from routine_watch.replay import change_flag, run
from routine_watch.scenario import Scenario, load_scenario, scenario_dirs

#: A session played this much faster than recorded finishes inside a test: `live`'s
#: clock divides every wait by it, so nothing here sleeps for real.
FAST = 1000.0

#: One error as both paths publish it: what it was, the step it was about, when it ran
#: and whether the resident put it right straight away.
Row = tuple[str, str | None, float, float, bool]


def _played(path: Path) -> list[dict[str, Any]]:
    """Every message one live session sends, as JSON: what the socket would carry."""

    async def play() -> list[dict[str, Any]]:
        return [as_json(message) async for message in session_messages(path, speed=FAST)]

    return asyncio.run(play())


def _session_ids(scenario: Scenario) -> set[str]:
    """Every session id the recording holds, at either input level."""
    frames = {frame.session_id for frame in scenario.frames}
    return frames | {event.session_id for event in scenario.events}


def _rows(errors: Iterable[Mapping[str, Any]], step: str) -> list[Row]:
    """`errors` as comparable rows, in one fixed order whichever path they came from.

    `step` is the key the step id sits under: `step_id` in a live `TaskError` message,
    `step` in a `replay.run` result. An error's id, its session id and the evidence
    behind it are the socket's alone - `run` publishes none of them - so the comparison
    is over what both paths say about an error.
    """
    rows: list[Row] = [
        (
            error["type"],
            error[step],
            error["t_start"],
            error["t_end"],
            error["self_corrected"],
        )
        for error in errors
    ]
    # A step id is null when no single step applies (`contracts.py`), so it is sorted
    # as the empty string the offline replay's own ordering gives it.
    return sorted(rows, key=lambda row: (row[0], row[1] or "", row[2], row[3], row[4]))


@pytest.mark.parametrize("path", scenario_dirs(), ids=lambda path: path.name)
def test_a_live_session_says_what_the_offline_replay_says(path: Path) -> None:
    scenario = load_scenario(path)
    session_ids = _session_ids(scenario)
    if len(session_ids) != 1:
        # Both paths read one recording as one session (`replay.session_id_of`), so a
        # recording of several has no single reading to compare. Skipped out loud.
        pytest.skip(f"{path.name}: {len(session_ids)} sessions in one recording, not one")

    messages = _played(path)
    result = run(scenario)
    start, end = messages[0], messages[-1]
    assert [start["type"], end["type"]] == ["session_start", "session_end"]

    assert start["session_id"] == result["session_id"]
    assert start["task_id"] == result["task"]
    steps = [message["event"] for message in messages if message["type"] == "step"]
    assert [event["step_id"] for event in steps] == list(result["steps"])
    assert sum(1 for event in steps if event["unclear"]) == result["unclear"]
    assert _rows(end["errors"], "step_id") == _rows(result["errors"], "step")
    assert end["score"] == result["score"]
    # The recording's flag on both sides, not the resident's: see "Which flag" above.
    assert change_flag(end["score"], scenario.expected.history)[0] == result["flag"]
