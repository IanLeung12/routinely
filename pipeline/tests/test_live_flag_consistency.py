"""Every scenario's live `session_end` flag must agree with `/residents` and `/alerts`
(T236, T248).

`test_live.py`'s `test_session_end_says_what_the_dashboard_says` checks this for the
demo's four key beats; this guards it for every recorded scenario under
`tests/scenarios/`, the same way `test_live_matches_replay.py` extends
`test_live_session_says_what_the_replay_says` to all of them. A session whose `flag`
disagreed with the resident's row, or whose `alert_id` the dashboard's "View alert"
would 404 on, would mislead a nurse reading the live screen.

The autouse `_empty_log` fixture (`conftest.py`) resets the session log around every
test, so each scenario plays against the demo resident's seeded history alone.
"""

from __future__ import annotations

import asyncio
from typing import Any

import pytest
from fastapi.testclient import TestClient

from routine_watch.api import app
from routine_watch.demo import DEMO_RESIDENT
from routine_watch.live import scenario_path, session_messages
from routine_watch.replay import scenario_dirs

#: Fast enough that a recorded session plays out inside a test.
FAST = 1000.0


def _scenario_names() -> list[str]:
    return [path.name for path in scenario_dirs()]


async def _play(name: str) -> dict[str, Any]:
    """Play one scenario live; return its `session_end`."""
    end: dict[str, Any] | None = None
    async for message in session_messages(scenario_path(name), speed=FAST):
        if message["type"] == "session_end":
            end = message
    assert end is not None, f"{name}: session never ended"
    return end


@pytest.mark.parametrize("name", _scenario_names())
def test_session_end_flag_matches_residents_and_alerts(name: str) -> None:
    end = asyncio.run(_play(name))

    with TestClient(app) as client:
        residents = {row["id"]: row for row in client.get("/residents").json()}
        alert_id = end["alert_id"]
        alert_status = None if alert_id is None else client.get(f"/alerts/{alert_id}").status_code

    assert end["flag"] == (residents[DEMO_RESIDENT]["status"] == "flagged")
    assert alert_id is None or alert_status == 200
