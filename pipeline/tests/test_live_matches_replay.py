"""The live path and offline replay must find the same errors (SPEC §10's fallback vs
`scripts/e2e.sh`).

Two things turn a scenario recording into an outcome: `routine_watch.replay`, which
`scripts/e2e.sh` checks in CI, and `routine_watch.live.session_messages`, which the
demo plays when the camera or Wi-Fi gives out. Nothing asserted the two agree, so a
change to one could leave the demo showing different errors from what CI tested. This
plays every playable scenario through `session_messages` at a very high speed and
compares the errors it ends on against the same `expected.yaml` the offline replay is
checked against.

Not the flag: `session_end`'s is the resident's reading, over their own history with
this session now in it, rather than this recording's verdict against the scenario's
(T236, `live.py`, "the `flag` is the resident's"). The recording's own flag is
`expected.yaml`'s and is checked where it is read, in `test_replay.py` and
`scripts/e2e.sh`; that the live screen and the dashboard agree about the resident's is
`test_live.py`'s `test_session_end_says_what_the_dashboard_says`.

What a live session *ends on* is `session_end`'s `errors`, not the `error` messages it
streamed: a step done before a dependency reports the dependency missing at the time
it is checked and reports itself as a sequence error once that dependency lands, so
the stream holds both readings while the finished session's classification holds only
the second (`live.py`, "the end is the finished session's"). The stream is still
checked here, as the superset it is meant to be.

The autouse `_empty_log` fixture (`conftest.py`) keeps this from recording live
sessions against the demo resident across tests.
"""

from __future__ import annotations

import asyncio
from collections import Counter
from typing import Any

import pytest

from routine_watch.contracts import TaskError
from routine_watch.live import scenario_path, session_messages
from routine_watch.replay import load_scenario, scenario_dirs

#: A session played this much faster than recorded finishes instantly.
FAST = 1000.0


def _scenario_names() -> list[str]:
    return [path.name for path in scenario_dirs()]


async def _play(name: str) -> tuple[list[TaskError], dict[str, Any]]:
    """Play one scenario live; return every error it sent and its `session_end`."""
    errors: list[TaskError] = []
    end: dict[str, Any] | None = None
    async for message in session_messages(scenario_path(name), speed=FAST):
        if message["type"] == "error":
            errors.append(message["error"])
        elif message["type"] == "session_end":
            end = message
    assert end is not None, f"{name}: session never ended"
    return errors, end


@pytest.mark.parametrize("name", _scenario_names())
def test_live_matches_replay(name: str) -> None:
    expected = load_scenario(scenario_path(name)).expected
    streamed, end = asyncio.run(_play(name))

    want = Counter((str(error.type), error.step) for error in expected.errors)
    got = Counter((str(error.type), error.step_id) for error in end["errors"])
    assert got == want
    # The stream is every reading the session went through, so it holds the errors it
    # ended on and whatever healed on the way, never less.
    assert {error.error_id for error in streamed} >= {error.error_id for error in end["errors"]}
