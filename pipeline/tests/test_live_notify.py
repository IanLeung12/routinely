"""A push alert fires once when a live session flags a resident (SPEC Nice-to-have 3).

`routine_watch.notify` builds the notifier; this is the one call site that uses it,
so these tests play scenarios through `session_messages` with a `FakeNotifier`
injected and check what it recorded, never the network.
"""

import asyncio
from typing import Any

import pytest

from routine_watch import session_log
from routine_watch.demo import DEMO_RESIDENT
from routine_watch.live import scenario_path, session_messages
from routine_watch.notify import FakeNotifier

#: The demo's bad session (omission + perseveration: the one that flags) and the good
#: one (no errors: never flags).
BAD = "tea_skip_teabag_pour_twice"
GOOD = "tea_normal"

#: A resident the seeded demo leaves alone, so a flag that appears is this run's.
QUIET_RESIDENT = "mrs-ahmed"

#: Fast enough that a recorded session plays out inside a test.
FAST = 1000.0


@pytest.fixture(autouse=True)
def _reset_session_log() -> None:
    session_log.reset()
    yield
    session_log.reset()


def play(scenario: str, notifier: FakeNotifier, resident_id: str = DEMO_RESIDENT) -> dict[str, Any]:
    """Play one scenario as `resident_id`'s live session with `notifier` injected."""

    async def session() -> dict[str, Any]:
        messages = session_messages(
            scenario_path(scenario), speed=FAST, resident_id=resident_id, notifier=notifier
        )
        return [message async for message in messages][-1]

    end = asyncio.run(session())
    assert end["type"] == "session_end"
    return end


def test_a_session_that_flips_the_resident_to_flagged_notifies_once() -> None:
    notifier = FakeNotifier()

    play(BAD, notifier, DEMO_RESIDENT)

    assert len(notifier.sent) == 1
    alert = notifier.sent[0]
    assert alert["resident_id"] == DEMO_RESIDENT
    assert alert["alert_id"] == f"alert-{DEMO_RESIDENT}"
    assert "diagnos" not in alert["summary"].lower()


def test_playing_it_again_while_already_flagged_does_not_notify_again() -> None:
    notifier = FakeNotifier()
    play(BAD, notifier, DEMO_RESIDENT)
    assert len(notifier.sent) == 1

    play(BAD, notifier, DEMO_RESIDENT)

    assert len(notifier.sent) == 1


def test_a_clean_session_never_notifies() -> None:
    notifier = FakeNotifier()

    play(GOOD, notifier, DEMO_RESIDENT)

    assert notifier.sent == []


def test_a_single_bad_session_does_not_flag_or_notify_yet() -> None:
    """SPEC section 7: one session above the threshold is a watch, not a flag, so a
    quiet resident's first bad session stays quiet."""
    notifier = FakeNotifier()

    play(BAD, notifier, QUIET_RESIDENT)

    assert notifier.sent == []


def test_the_second_qualifying_session_is_the_one_that_notifies() -> None:
    notifier = FakeNotifier()
    play(BAD, notifier, QUIET_RESIDENT)
    assert notifier.sent == []

    play("tea_kettle_twice", notifier, QUIET_RESIDENT)

    assert len(notifier.sent) == 1
    assert notifier.sent[0]["resident_id"] == QUIET_RESIDENT


def test_no_notifier_given_defaults_to_the_fake_and_never_calls_the_network() -> None:
    """`get_notifier()` without `LIVE_API=1` is a `FakeNotifier`, so a session played
    with no `notifier` argument still never reaches the network (AGENTS.md)."""

    async def session() -> dict[str, Any]:
        messages = session_messages(scenario_path(BAD), speed=FAST)
        return [message async for message in messages][-1]

    end = asyncio.run(session())
    assert end["type"] == "session_end"
