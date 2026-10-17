"""The live path and offline replay must find the same errors and flag (SPEC §10's
fallback vs `scripts/e2e.sh`).

Two things turn a scenario recording into an outcome: `routine_watch.replay`, which
`scripts/e2e.sh` checks in CI, and `routine_watch.live.session_messages`, which the
demo plays when the camera or Wi-Fi gives out. Nothing asserted the two agree, so a
change to one could leave the demo showing different errors from what CI tested. This
plays every playable scenario through `session_messages` at a very high speed and
compares the errors and the flag it sends against the same `expected.yaml` the
offline replay is checked against.

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

#: These scenarios' `expected.yaml` has a `sequence` error: a step done before a
#: dependency it depends on, with that dependency done later. Read in one shot
#: (`replay.py`, and live's own classification right before `session_end`), the
#: dependency's later event is already in the timeline, so it is never reported
#: missing - only the sequence error is. Read step by step as a live session plays
#: (`errors.classify_errors(..., ended=False)`), the dependency has not happened yet
#: at the moment it is checked, so live also reports it as a transient `omission`
#: before the later event turns it into a `sequence` error. `live.py` documents this
#: as deliberate ("errors accumulate; the task map heals"), but it means the demo's
#: error list is not the one `expected.yaml` (and CI) checked for these three. Real
#: mismatch, not a test bug: flagged here for the orchestrator to file, not fixed here.
_SEQUENCE_HEALS_FROM_A_TRANSIENT_OMISSION = frozenset(
    {
        "tea_sequence_error",
        "tea_self_corrected",
        "meds_pill_before_water",
        "meds_self_corrected",
    }
)


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
    if name in _SEQUENCE_HEALS_FROM_A_TRANSIENT_OMISSION:
        pytest.xfail(
            reason="live reports a sequence error's dependency missing before the "
            "later event heals it; expected.yaml only has the healed state (T162)"
        )

    expected = load_scenario(scenario_path(name)).expected
    errors, end = asyncio.run(_play(name))

    want = Counter((str(error.type), error.step) for error in expected.errors)
    got = Counter((str(error.type), error.step_id) for error in errors)
    assert got == want
    assert end["flag"] == expected.flag
