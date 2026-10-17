"""Shared fixtures across the test suite."""

import asyncio

import pytest

from routine_watch import session_log
from routine_watch.demo import DEMO_RESIDENT
from routine_watch.live import scenario_path, session_messages

#: The demo's bad session: skip the teabag, pour twice (SPEC section 10 beat 4).
MRS_K_LIVE_SCENARIO = "tea_skip_teabag_pour_twice"

#: Fast enough that a recorded session plays out inside a test.
_FAST = 1000.0


@pytest.fixture(autouse=True)
def _empty_log():
    """Every test starts and ends with the seeded demo and nothing recorded."""
    session_log.reset()
    yield
    session_log.reset()


@pytest.fixture
def mrs_k_flagged(_empty_log):
    """Play mrs-k's live session (SPEC section 10 beats 2-4) so tests that need a
    flagged demo resident with an alert don't have to know how she got there: the
    seeded history alone only leaves her on watch (T124)."""

    async def play() -> None:
        messages = session_messages(
            scenario_path(MRS_K_LIVE_SCENARIO), speed=_FAST, resident_id=DEMO_RESIDENT
        )
        async for _ in messages:
            pass

    asyncio.run(play())
    yield
