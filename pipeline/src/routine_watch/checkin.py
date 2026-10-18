"""Safety check-ins: ask the person, then alarm whoever can help (SPEC §18, Project KAZE).

Project KAZE asks for "help when someone can't ask for it themselves", and this is
where the rest of the pipeline hands that over. A change is flagged for review
(SPEC §7) and the person is asked to **check in**. What happens next is a countdown
the *server* owns, so it keeps running if their phone or tablet drops off the network:

    pending ──person enters the safety PIN──────────────────► ok
       │     ──person enters the duress PIN──┐
       │                                     ▼
       └──check-in window expires──────► alarm (supporter #1) ──┐
                                           │                    │
                      ack window expires   ▼                    │ a supporter taps
                                        escalated (#2, #3, …)   │ "I'm on it"
                                           │                    ▼
                                           └──────────────► acknowledged
                                                                │
                              a supporter or the person says what it was
                                                                ▼
                                                             resolved

The **duress PIN** looks exactly like the safety PIN to whoever is holding the device
(`person_view` renders the two the same, and nothing that happens afterwards changes
it) and raises the alarm anyway, marked `duress` and `silent`, so a supporter knows to
come without anything showing on the person's screen.

Everything here is pure: a transition takes a record and returns a new one, and the
clock is injected (`CheckinStore(clock=...)`), so the whole flow is testable without
waiting and a replay lands on the same timestamps anywhere. `CheckinStore` is the one
piece that keeps state: the live check-ins in memory, and each person's safety settings
in memory and as one JSON file under `SAFETY_DIR` (default `.data/safety/`). The
asyncio tick that advances the countdown, the routes and the WebSocket push live in
`routine_watch.api_checkin`.

Nothing here is a real call, a real SMS or a real address (SPEC §18): an alarm is a
payload the dashboard shows, and a person's location is a string they chose to share.

**PINs.** Only ever kept as a salted PBKDF2-SHA256 hash with its salt, and never
returned by a route, written to an event log or passed to `logging`. A 4-12 character
PIN is guessable by anyone who can POST at it, so a real deployment needs rate
limiting and an account behind it; the demo has neither and says so (SPEC §18).
"""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import os
import secrets
from collections.abc import Callable, Iterator
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from functools import lru_cache
from pathlib import Path
from typing import Any, Literal
from urllib.parse import quote

from pydantic import BaseModel, ConfigDict, Field

logger = logging.getLogger(__name__)

#: What the person's own screen asks (SPEC §12 wording: plain, never alarming).
PERSON_ASK = "Can you check in?"

#: What a supporter is asked when the alarm reaches them (SPEC §18).
SUPPORTER_ASK = "Is everyone okay?"

#: How long the person has to check in, and how long one supporter has to say "I'm on
#: it" before the next one is alarmed. The demo people are seeded with the short pair
#: so a check-in plays out on stage inside the three minutes of SPEC §10.
DEFAULT_CHECKIN_WINDOW_S = 120.0
DEFAULT_ACK_WINDOW_S = 120.0
DEMO_CHECKIN_WINDOW_S = 20.0
DEMO_ACK_WINDOW_S = 15.0

#: A window somebody can set: long enough to read the question, short enough that an
#: alarm still means something today.
MIN_WINDOW_S = 5.0
MAX_WINDOW_S = 3600.0

PIN_MIN_LEN = 4
PIN_MAX_LEN = 12

#: PBKDF2 rounds. Enough that a stolen `.data/safety/*.json` is not a plaintext PIN
#: list, few enough that a check-in on a laptop answers immediately.
PIN_ITERATIONS = 100_000

#: Where each person's safety settings are kept unless `SAFETY_DIR` says otherwise.
DEFAULT_SAFETY_DIR = Path(".data/safety")

#: The demo's PINs, so whoever runs the demo can type them (SPEC §18). Not secrets:
#: they are seeded, documented and overwritable with `PUT /people/{id}/safety`.
DEMO_SAFETY_PIN = "1234"
DEMO_DURESS_PIN = "9111"


class CheckinState(StrEnum):
    """Where a check-in is. `ok` and `resolved` are the two ends of it."""

    PENDING = "pending"
    OK = "ok"
    ALARM = "alarm"
    ESCALATED = "escalated"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"


#: Nothing more will happen to a check-in in one of these.
CLOSED_STATES = frozenset({CheckinState.OK, CheckinState.RESOLVED})

#: States in which somebody is still being waited for.
OPEN_STATES = frozenset(CheckinState) - CLOSED_STATES


class ResolveReason(StrEnum):
    """Why a check-in is over, in the words whoever closed it chose (SPEC §18)."""

    FALSE_ALARM = "false_alarm"
    HELPED = "helped"
    OTHER = "other"


#: Which PIN was entered. Both answer the person identically; only the second one
#: raises the alarm.
PinKind = Literal["safety", "duress"]

#: What the demo can simulate about the person's device (SPEC §18, KAZE's
#: "connectivity failure"): the countdown is the server's either way.
SimulatedEvent = Literal["disconnect", "reconnect"]

#: Who an event in the log is by: the person, this server's own countdown, or the id
#: of the supporter who tapped something.
ACTOR_PERSON = "person"
ACTOR_SERVER = "server"

#: A clock, injected so a test (and a replay) can decide what "now" is.
Clock = Callable[[], datetime]


class CheckinError(Exception):
    """Something the caller asked of a check-in that it cannot do. `status` is the
    HTTP status `api_checkin` answers with, so the rules live here with the machine
    rather than being restated per route."""

    status = 409


class UnknownCheckin(CheckinError):
    status = 404


class UnknownPerson(CheckinError):
    status = 404


class UnknownSupporter(CheckinError):
    status = 404


class WrongPin(CheckinError):
    """A PIN that is neither the safety nor the duress one. The countdown carries on."""

    status = 401


class NotWaiting(CheckinError):
    """The check-in is past the point this call would have made a difference."""

    status = 409


class HashedPin(BaseModel):
    """A PIN as it is kept: salt, PBKDF2-SHA256 hash and the rounds used. Never
    returned by a route (`settings_payload` leaves it out) and never logged."""

    model_config = ConfigDict(extra="forbid")

    salt: str
    hash: str
    iterations: int = PIN_ITERATIONS


class Sharing(BaseModel):
    """What one supporter may see of one person (SPEC §18): the person decides, and a
    payload carries only what is switched on here.

    * `location` - the simulated room or address the person shared.
    * `alert_details` - the alert behind the check-in, so they can open the evidence.
    * `replay` - the person's kept skeleton replays (SPEC §17).
    """

    model_config = ConfigDict(extra="forbid")

    location: bool = False
    alert_details: bool = False
    replay: bool = False


class Supporter(BaseModel):
    """One person on a person's ordered list of supporters: the first one alarmed is
    the first one here (SPEC §17's links, as this backend's copy of them)."""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1, max_length=60)
    name: str = Field(min_length=1, max_length=80)
    #: How they know the person: `family`, `carer`, `nurse` or `other` (SPEC §17).
    relationship: str = "other"
    share: Sharing = Sharing()


class SafetySettings(BaseModel):
    """One person's check-in settings. The PINs are hashes; everything else is shown."""

    model_config = ConfigDict(extra="forbid")

    person_id: str
    name: str = ""
    checkin_window_s: float = DEFAULT_CHECKIN_WINDOW_S
    ack_window_s: float = DEFAULT_ACK_WINDOW_S
    supporters: tuple[Supporter, ...] = ()
    #: A simulated room or address, in the person's own words. Never a real address
    #: and never a device location: a string they typed (SPEC §18).
    location: str = ""
    safety_pin: HashedPin | None = None
    duress_pin: HashedPin | None = None

    def supporter(self, supporter_id: str) -> Supporter | None:
        return next((one for one in self.supporters if one.id == supporter_id), None)


class CheckinEvent(BaseModel):
    """One transition, as it is appended to the check-in's log: when, who by, and
    what it moved to. Never a PIN - the kind of PIN entered at most."""

    model_config = ConfigDict(extra="forbid")

    at: datetime
    event: str
    actor: str
    state: CheckinState
    detail: str | None = None


class Checkin(BaseModel):
    """One check-in, from the question to whoever closed it.

    Immutable by convention: every transition in this module returns a new record, so
    a caller can keep the one it was given (the WebSocket push does) and the store is
    the only thing that decides which is current.
    """

    model_config = ConfigDict(extra="forbid")

    checkin_id: str
    person_id: str
    #: The alert that asked for this check-in, or None when somebody started it by
    #: hand for the demo. One check-in per alert (`CheckinStore.start`).
    alert_id: str | None = None
    state: CheckinState = CheckinState.PENDING
    started_at: datetime
    #: When the state this check-in is in runs out, or None when nothing is counting.
    deadline: datetime | None = None
    #: The person entered their duress PIN. Their own screen never says so.
    duress: bool = False
    #: Nothing about this alarm may show on the person's device.
    silent: bool = False
    #: Whether the person's device is reachable. It makes no difference to the
    #: countdown; it is what a supporter is told about why nobody answered.
    device_online: bool = True
    #: The supporter being waited for right now, if any.
    supporter: str | None = None
    #: Every supporter alarmed so far, first one first.
    notified: tuple[str, ...] = ()
    acknowledged_by: str | None = None
    resolved_by: str | None = None
    resolved_reason: ResolveReason | None = None
    events: tuple[CheckinEvent, ...] = ()


def hash_pin(pin: str, *, salt: str | None = None, iterations: int = PIN_ITERATIONS) -> HashedPin:
    """`pin` as a salted PBKDF2-SHA256 hash. The plaintext is not kept anywhere."""
    salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", pin.encode("utf-8"), bytes.fromhex(salt), iterations)
    return HashedPin(salt=salt, hash=digest.hex(), iterations=iterations)


def _pin_matches(pin: str, stored: HashedPin | None) -> bool:
    """Whether `pin` is the PIN behind `stored`, compared in constant time."""
    if stored is None:
        return False
    candidate = hash_pin(pin, salt=stored.salt, iterations=stored.iterations)
    return hmac.compare_digest(candidate.hash, stored.hash)


def pin_kind(settings: SafetySettings, pin: str) -> PinKind | None:
    """Which of the person's two PINs `pin` is, or None.

    Both are always hashed and compared, so answering takes the same work either way
    and the result is the only difference between them.
    """
    is_safety = _pin_matches(pin, settings.safety_pin)
    is_duress = _pin_matches(pin, settings.duress_pin)
    if is_safety:
        return "safety"
    return "duress" if is_duress else None


def _logged(
    record: Checkin,
    event: str,
    actor: str,
    *,
    at: datetime,
    state: CheckinState,
    detail: str | None = None,
) -> tuple[CheckinEvent, ...]:
    """`record`'s event log with this transition appended."""
    return (
        *record.events,
        CheckinEvent(at=at, event=event, actor=actor, state=state, detail=detail),
    )


def start(
    settings: SafetySettings,
    now: datetime,
    *,
    checkin_id: str,
    alert_id: str | None = None,
) -> Checkin:
    """A check-in the person has `settings.checkin_window_s` to answer."""
    deadline = now + timedelta(seconds=settings.checkin_window_s)
    record = Checkin(
        checkin_id=checkin_id,
        person_id=settings.person_id,
        alert_id=alert_id,
        state=CheckinState.PENDING,
        started_at=now,
        deadline=deadline,
    )
    return record.model_copy(
        update={
            "events": _logged(
                record,
                "started",
                ACTOR_SERVER,
                at=now,
                state=CheckinState.PENDING,
                detail=alert_id,
            )
        }
    )


def respond(
    record: Checkin, settings: SafetySettings, kind: PinKind, now: datetime
) -> Checkin:
    """The person's answer: the safety PIN cancels it, the duress PIN alarms silently.

    Only a `pending` check-in can be answered this way. Once the alarm is out, taking
    it back is a supporter's or the person's `resolve`, with a reason, rather than a
    PIN somebody could be made to enter.
    """
    if record.state is not CheckinState.PENDING:
        raise NotWaiting("this check-in is not waiting for an answer any more")
    if kind == "safety":
        return record.model_copy(
            update={
                "state": CheckinState.OK,
                "deadline": None,
                "supporter": None,
                "events": _logged(
                    record, "checked_in", ACTOR_PERSON, at=now, state=CheckinState.OK
                ),
            }
        )
    alarmed = record.model_copy(update={"duress": True, "silent": True})
    return _raise_alarm(alarmed, settings, now, event="duress", actor=ACTOR_PERSON)


def is_due(record: Checkin, now: datetime) -> bool:
    """Whether `record`'s countdown has run out and nobody has answered it."""
    return record.deadline is not None and now >= record.deadline


def advance(record: Checkin, settings: SafetySettings, now: datetime) -> Checkin:
    """`record` with every deadline that has passed by `now` applied, in order.

    This is what the server's tick calls once a second, and what every route calls
    before it answers, so a check-in reads the same whether anything has been ticking
    or the clock simply jumped: the question expiring raises the alarm, and each ack
    window expiring passes it down the supporter list.

    Each step is stamped with the deadline it missed rather than with `now`, so one
    tick a second and one clock jump of ten minutes leave exactly the same record.
    """
    guard = len(settings.supporters) + 2
    while is_due(record, now) and guard > 0:
        record = _fire(record, settings)
        guard -= 1
    return record


def _fire(record: Checkin, settings: SafetySettings) -> Checkin:
    """One expired deadline applied: the question becomes an alarm, an unanswered
    alarm moves down the list."""
    at = record.deadline
    if at is None:  # only `is_due` gets here, so this cannot happen; belt and braces
        return record
    if record.state is CheckinState.PENDING:
        return _raise_alarm(record, settings, at, event="alarmed", actor=ACTOR_SERVER)
    return _escalate(record, settings, at)


def _raise_alarm(
    record: Checkin, settings: SafetySettings, at: datetime, *, event: str, actor: str
) -> Checkin:
    """Alarm the first supporter on the list, and start their ack window.

    A person with nobody linked (SPEC §17: self-monitoring is a supported state) still
    reaches `alarm`: there is simply nobody to pass it to, so the alarm stays theirs
    and the log says why.
    """
    first = settings.supporters[0] if settings.supporters else None
    detail = "duress" if event == "duress" else None
    if first is None:
        return record.model_copy(
            update={
                "state": CheckinState.ALARM,
                "deadline": None,
                "supporter": None,
                "events": _logged(
                    record,
                    event,
                    actor,
                    at=at,
                    state=CheckinState.ALARM,
                    detail="nobody linked" if detail is None else f"{detail}, nobody linked",
                ),
            }
        )
    return record.model_copy(
        update={
            "state": CheckinState.ALARM,
            "deadline": at + timedelta(seconds=settings.ack_window_s),
            "supporter": first.id,
            "notified": (first.id,),
            "events": _logged(
                record, event, actor, at=at, state=CheckinState.ALARM, detail=detail or first.id
            ),
        }
    )


def _escalate(record: Checkin, settings: SafetySettings, at: datetime) -> Checkin:
    """Nobody said "I'm on it" in time: alarm the next supporter down the list."""
    nxt = _next_supporter(record, settings)
    if nxt is None:
        return record.model_copy(
            update={
                "deadline": None,
                "events": _logged(
                    record,
                    "escalation_exhausted",
                    ACTOR_SERVER,
                    at=at,
                    state=record.state,
                    detail="nobody left to alarm",
                ),
            }
        )
    return record.model_copy(
        update={
            "state": CheckinState.ESCALATED,
            "deadline": at + timedelta(seconds=settings.ack_window_s),
            "supporter": nxt.id,
            "notified": (*record.notified, nxt.id),
            "events": _logged(
                record,
                "escalated",
                ACTOR_SERVER,
                at=at,
                state=CheckinState.ESCALATED,
                detail=nxt.id,
            ),
        }
    )


def _next_supporter(record: Checkin, settings: SafetySettings) -> Supporter | None:
    """The first supporter on the list who has not been alarmed yet."""
    return next((one for one in settings.supporters if one.id not in record.notified), None)


def acknowledge(
    record: Checkin, settings: SafetySettings, supporter_id: str, now: datetime
) -> Checkin:
    """A supporter tapped "I'm on it": the escalation stops with them.

    Any supporter on the person's list may take it, not only the one being waited for:
    somebody who heard about it from the one ahead of them is exactly what the list is
    for, and leaving them unable to answer would escalate past a supporter already on
    their way.
    """
    if settings.supporter(supporter_id) is None:
        raise UnknownSupporter("this supporter is not on that person's list")
    if record.state not in {CheckinState.ALARM, CheckinState.ESCALATED}:
        raise NotWaiting("this check-in is not waiting to be acknowledged")
    return record.model_copy(
        update={
            "state": CheckinState.ACKNOWLEDGED,
            "deadline": None,
            "supporter": supporter_id,
            "acknowledged_by": supporter_id,
            "events": _logged(
                record,
                "acknowledged",
                supporter_id,
                at=now,
                state=CheckinState.ACKNOWLEDGED,
            ),
        }
    )


def resolve(
    record: Checkin,
    settings: SafetySettings,
    by: str,
    reason: ResolveReason,
    now: datetime,
) -> Checkin:
    """A supporter or the person closes it, saying what it was.

    `by` is `"person"` or a supporter's id. A check-in that is already closed stays
    closed: the first answer stands, and a second one is somebody's stale screen.
    """
    if by != ACTOR_PERSON and settings.supporter(by) is None:
        raise UnknownSupporter("this supporter is not on that person's list")
    if record.state in CLOSED_STATES:
        raise NotWaiting("this check-in is already closed")
    return record.model_copy(
        update={
            "state": CheckinState.RESOLVED,
            "deadline": None,
            "resolved_by": by,
            "resolved_reason": reason,
            "events": _logged(
                record,
                "resolved",
                by,
                at=now,
                state=CheckinState.RESOLVED,
                detail=reason.value,
            ),
        }
    )


def set_device_online(record: Checkin, online: bool, now: datetime) -> Checkin:
    """Mark the person's device reachable or gone (SPEC §18, KAZE connectivity).

    Deliberately leaves `deadline` alone: the countdown is the server's, so a device
    that drops off after a check-in started still runs out of time and still alarms.
    """
    return record.model_copy(
        update={
            "device_online": online,
            "events": _logged(
                record,
                "reconnected" if online else "disconnected",
                ACTOR_PERSON,
                at=now,
                state=record.state,
            ),
        }
    )


def seconds_left(record: Checkin, now: datetime) -> float | None:
    """How long whoever is being waited for has, or None when nothing is counting."""
    if record.deadline is None:
        return None
    return max(0.0, round((record.deadline - now).total_seconds(), 3))


def _as_checked_in(record: Checkin) -> Checkin:
    """A duress check-in as the person's own screen sees it: the record a safety PIN
    would have left, with nothing that happened afterwards showing through.

    This is the whole duress promise (SPEC §18). Anyone looking over the person's
    shoulder - including whoever made them enter it - sees a check-in they cancelled.
    """
    return record.model_copy(
        update={
            "state": CheckinState.OK,
            "deadline": None,
            "duress": False,
            "silent": False,
            "supporter": None,
            "notified": (),
            "acknowledged_by": None,
            "resolved_by": None,
            "resolved_reason": None,
            "events": (),
        }
    )


def person_view(record: Checkin, now: datetime) -> dict[str, Any]:
    """What the person's own device may see: the question and their own countdown.

    No supporter is named and no event log is carried, so this payload is the same
    for a check-in cancelled with the safety PIN and one answered with the duress PIN
    (`_as_checked_in`) - byte for byte, which is what makes the duress PIN usable.
    """
    shown = _as_checked_in(record) if record.duress else record
    return {
        "checkin_id": shown.checkin_id,
        "person_id": shown.person_id,
        "state": shown.state.value,
        "ask": PERSON_ASK,
        "started_at": _iso(shown.started_at),
        "deadline": _iso(shown.deadline),
        "seconds_left": seconds_left(shown, now),
        "device_online": shown.device_online,
        "resolved_reason": shown.resolved_reason.value if shown.resolved_reason else None,
    }


def person_sees_open(record: Checkin) -> bool:
    """Whether the person's own screen should still be showing this check-in. A duress
    check-in reads as cancelled here too, for the same reason `person_view` does."""
    shown = _as_checked_in(record) if record.duress else record
    return shown.state in OPEN_STATES


def supporter_view(
    record: Checkin, settings: SafetySettings, supporter_id: str, now: datetime
) -> dict[str, Any]:
    """The alarm as one supporter may see it, and nothing else (SPEC §18).

    Everything the person switched off for this supporter is **absent**, not blanked:
    a supporter without `location` has no `location` key, one without `alert_details`
    gets no `alert_id` and no event log (so they cannot open the evidence), and one
    without `replay` is given no link to the person's replays (SPEC §17).

    A duress alarm says so here - that is the point of it - together with `silent`, so
    a supporter's screen knows to answer without anything going back to the person.
    """
    share = supporter.share if (supporter := settings.supporter(supporter_id)) else Sharing()
    view: dict[str, Any] = {
        "checkin_id": record.checkin_id,
        "person_id": record.person_id,
        "person_name": settings.name or record.person_id,
        "state": record.state.value,
        "ask": SUPPORTER_ASK,
        "duress": record.duress,
        "silent": record.silent,
        "started_at": _iso(record.started_at),
        "deadline": _iso(record.deadline),
        "seconds_left": seconds_left(record, now),
        "for_supporter": supporter_id,
        "supporter": record.supporter,
        "notified": list(record.notified),
        "acknowledged_by": record.acknowledged_by,
        "resolved_by": record.resolved_by,
        "resolved_reason": record.resolved_reason.value if record.resolved_reason else None,
        "device_online": record.device_online,
    }
    if share.location:
        view["location"] = settings.location
        view["location_simulated"] = True
    if share.alert_details:
        view["alert_id"] = record.alert_id
        view["events"] = [event.model_dump(mode="json") for event in record.events]
    if share.replay:
        view["replays_url"] = f"/people/{record.person_id}/replays"
    return view


def settings_payload(settings: SafetySettings) -> dict[str, Any]:
    """One person's settings as a route answers them: the PINs as "set or not", never
    as a hash, a salt or a length."""
    return {
        "person_id": settings.person_id,
        "name": settings.name,
        "checkin_window_s": settings.checkin_window_s,
        "ack_window_s": settings.ack_window_s,
        "location": settings.location,
        "location_simulated": True,
        "supporters": [one.model_dump(mode="json") for one in settings.supporters],
        "safety_pin_set": settings.safety_pin is not None,
        "duress_pin_set": settings.duress_pin is not None,
    }


def _iso(when: datetime | None) -> str | None:
    """A timestamp the way every other payload in this repo spells it: ISO 8601 with
    `Z` for UTC, like `model_dump(mode="json")`, so one payload is not two formats."""
    if when is None:
        return None
    return when.isoformat().replace("+00:00", "Z")


#: The demo's people, their supporters and what each supporter may see (SPEC §17's
#: links, which live in the frontend for now, mirrored here so the backend has an
#: ordered list to escalate down). The on-call care line is last everywhere and is
#: told the least: it hears the alarm and nothing about the person's routine, which is
#: what per-supporter sharing is for.
_CARE_LINE = Supporter(
    id="care-line",
    name="Care line (on call)",
    relationship="carer",
    share=Sharing(location=False, alert_details=False, replay=False),
)

DEMO_PEOPLE: tuple[dict[str, Any], ...] = (
    {
        "person_id": "mrs-k",
        "name": "Mrs. K",
        "location": "Room 204, care home",
        "supporters": (
            Supporter(
                id="nurse-ana",
                name="Nurse Ana",
                relationship="nurse",
                share=Sharing(location=True, alert_details=True, replay=True),
            ),
            _CARE_LINE,
        ),
    },
    {
        "person_id": "mr-d",
        "name": "Mr. D",
        "location": "14 Rowan Avenue, flat 2",
        "supporters": (
            Supporter(
                id="lena",
                name="Lena",
                relationship="family",
                share=Sharing(location=True, alert_details=True, replay=False),
            ),
            _CARE_LINE,
        ),
    },
    {
        "person_id": "sam",
        "name": "Sam",
        "location": "Home",
        "supporters": (),
    },
)


@lru_cache(maxsize=1)
def _demo_pins() -> tuple[HashedPin, HashedPin]:
    """The demo's two PINs, hashed once for this process.

    `demo_settings()` runs for every new store and every `/demo/reset`, and PBKDF2 is
    deliberately slow, so re-hashing the same two seeded PINs each time is the one
    cost worth not paying. The demo people share a salt as a result - fine for a PIN
    that is written down in SPEC §18, and never how a real one would be kept.
    """
    return hash_pin(DEMO_SAFETY_PIN), hash_pin(DEMO_DURESS_PIN)


def demo_settings() -> dict[str, SafetySettings]:
    """The seeded settings every demo person starts with: the demo's short windows
    (SPEC §10's three minutes) and the demo PINs, hashed like any other."""
    safety, duress = _demo_pins()
    return {
        person["person_id"]: SafetySettings(
            person_id=person["person_id"],
            name=person["name"],
            checkin_window_s=DEMO_CHECKIN_WINDOW_S,
            ack_window_s=DEMO_ACK_WINDOW_S,
            supporters=person["supporters"],
            location=person["location"],
            safety_pin=safety,
            duress_pin=duress,
        )
        for person in DEMO_PEOPLE
    }


def safety_dir() -> Path:
    """Where safety settings are kept: `SAFETY_DIR`, or `DEFAULT_SAFETY_DIR`."""
    return Path(os.environ.get("SAFETY_DIR", "").strip() or DEFAULT_SAFETY_DIR)


class CheckinStore:
    """The check-ins this process is running, and each person's safety settings.

    The only stateful thing here, and the only thing that reads a clock: every rule it
    applies is one of the pure functions above. `clock` is injected so a test owns
    time; settings are seeded from `demo_settings()` and overlaid with one JSON file
    per person under `directory` (written only when somebody changes them, so a plain
    demo run touches no disk).

    Every method that changes something **advances the countdown first**, so a route
    answers the same whether the server's tick has been running or the clock simply
    jumped (and so a check-in started before the API fell over does not come back
    frozen at `pending`).
    """

    def __init__(self, clock: Clock | None = None, directory: Path | str | None = None):
        self._clock: Clock = clock or _utc_now
        self.directory = Path(directory) if directory is not None else safety_dir()
        self._settings = demo_settings()
        self._checkins: dict[str, Checkin] = {}
        self._by_alert: dict[str, str] = {}
        self._loaded = False

    # -- time ------------------------------------------------------------------

    def now(self) -> datetime:
        """This store's idea of now, always timezone-aware UTC."""
        when = self._clock()
        return when if when.tzinfo is not None else when.replace(tzinfo=UTC)

    def use_clock(self, clock: Clock) -> None:
        """Point this store at another clock. The seam a fake clock comes in through."""
        self._clock = clock

    # -- settings --------------------------------------------------------------

    def people(self) -> list[str]:
        """Every person this backend has safety settings for."""
        self._load()
        return sorted(self._settings)

    def settings_of(self, person_id: str) -> SafetySettings:
        """`person_id`'s settings, or `UnknownPerson` for somebody nobody linked."""
        self._load()
        settings = self._settings.get(person_id)
        if settings is None:
            raise UnknownPerson(f"no safety settings for {person_id!r}")
        return settings

    def update_settings(self, person_id: str, changes: dict[str, Any]) -> SafetySettings:
        """Change `person_id`'s settings and keep them. PINs arrive as plaintext in
        `safety_pin`/`duress_pin` and are hashed here; nothing else ever sees them."""
        settings = self.settings_of(person_id)
        update = {key: value for key, value in changes.items() if key not in _PIN_FIELDS}
        for field, pin in ((field, changes.get(field)) for field in _PIN_FIELDS):
            if pin is not None:
                update[field] = hash_pin(pin)
        updated = settings.model_copy(update=update)
        self._settings[person_id] = updated
        self._write(updated)
        return updated

    # -- check-ins -------------------------------------------------------------

    def start(self, person_id: str, *, alert_id: str | None = None) -> Checkin:
        """Ask `person_id` to check in, and start their countdown.

        Idempotent per alert: an `alert_id` that has already asked gives back the
        check-in it asked with, however that one ended, so a flag read again - every
        `session_end`, every dashboard poll - never asks the same person twice.
        """
        settings = self.settings_of(person_id)
        if alert_id is not None and (known := self._by_alert.get(alert_id)):
            return self._current(known)
        now = self.now()
        record = start(settings, now, checkin_id=self._new_id(person_id, now), alert_id=alert_id)
        self._checkins[record.checkin_id] = record
        if alert_id is not None:
            self._by_alert[alert_id] = record.checkin_id
        logger.info("check-in %s started for %s (alert %s)", record.checkin_id, person_id, alert_id)
        return record

    def get(self, checkin_id: str) -> Checkin:
        """One check-in, countdown applied. `UnknownCheckin` if there is no such id."""
        if checkin_id not in self._checkins:
            raise UnknownCheckin("no such check-in")
        return self._current(checkin_id)

    def checkin_for_alert(self, alert_id: str) -> Checkin | None:
        """The check-in `alert_id` already asked with, or None if it never has. What
        makes the alert hook idempotent (`api_checkin.start_for_alert`)."""
        checkin_id = self._by_alert.get(alert_id)
        return None if checkin_id is None else self._current(checkin_id)

    def active(self, person_id: str | None = None) -> list[Checkin]:
        """Every check-in still waiting for somebody, oldest first, countdown applied."""
        records = [self._current(key) for key in list(self._checkins)]
        return [
            record
            for record in sorted(records, key=lambda one: one.started_at)
            if record.state in OPEN_STATES and (person_id is None or record.person_id == person_id)
        ]

    def respond(self, checkin_id: str, pin: str) -> tuple[Checkin, PinKind]:
        """The person's answer. A wrong PIN raises `WrongPin` and changes nothing, so
        whoever is counting carries on counting."""
        record = self.get(checkin_id)
        settings = self.settings_of(record.person_id)
        kind = pin_kind(settings, pin)
        if kind is None:
            raise WrongPin("that is not the check-in PIN")
        return self._put(respond(record, settings, kind, self.now())), kind

    def acknowledge(self, checkin_id: str, supporter_id: str) -> Checkin:
        """A supporter taking it: "I'm on it"."""
        record = self.get(checkin_id)
        settings = self.settings_of(record.person_id)
        return self._put(acknowledge(record, settings, supporter_id, self.now()))

    def resolve(self, checkin_id: str, by: str, reason: ResolveReason) -> Checkin:
        """A supporter or the person closing it, with a reason."""
        record = self.get(checkin_id)
        settings = self.settings_of(record.person_id)
        return self._put(resolve(record, settings, by, reason, self.now()))

    def simulate(self, checkin_id: str, event: SimulatedEvent) -> Checkin:
        """Mark the person's device gone or back (SPEC §18). The countdown is this
        server's, so it carries on either way."""
        record = self.get(checkin_id)
        return self._put(set_device_online(record, event == "reconnect", self.now()))

    def tick(self) -> list[Checkin]:
        """Advance every open check-in to this store's clock.

        Answers with the records that **changed**, which is what the WebSocket push
        goes out for: a tick that finds nothing due says nothing to anybody.
        """
        changed = []
        for checkin_id, before in list(self._checkins.items()):
            after = self._current(checkin_id)
            if after != before:
                changed.append(after)
        return changed

    def reset(self) -> None:
        """Forget every check-in and every settings change: back to the seeded demo
        people, with the files this store wrote removed (`/demo/reset`)."""
        self._checkins.clear()
        self._by_alert.clear()
        self._settings = demo_settings()
        self._loaded = True
        if self.directory.is_dir():
            for path in sorted(self.directory.glob("*.json")):
                path.unlink()

    # -- internals -------------------------------------------------------------

    def _current(self, checkin_id: str) -> Checkin:
        """`checkin_id` with its countdown applied and the result kept."""
        record = self._checkins[checkin_id]
        if record.state in CLOSED_STATES:
            return record
        return self._put(advance(record, self.settings_of(record.person_id), self.now()))

    def _put(self, record: Checkin) -> Checkin:
        self._checkins[record.checkin_id] = record
        return record

    def _new_id(self, person_id: str, now: datetime) -> str:
        """A readable, deterministic id: the person and the second it started, so the
        demo can read one out loud. A second check-in inside the same second gets a
        counter rather than overwriting the first."""
        stem = f"checkin-{person_id}-{now.strftime('%Y%m%dT%H%M%SZ')}"
        if stem not in self._checkins:
            return stem
        return next(
            candidate
            for number in range(2, 1000)
            if (candidate := f"{stem}-{number}") not in self._checkins
        )

    def _path(self, person_id: str) -> Path:
        """One person's file. The id reaches this from a URL, so it is
        percent-encoded into one flat name: nothing it can contain escapes
        `directory`."""
        return self.directory / (quote(person_id, safe="") + ".json")

    def _write(self, settings: SafetySettings) -> None:
        """One person's settings as JSON, written whole and moved into place so a
        half-written file is never read back. Hashes, never PINs."""
        try:
            self.directory.mkdir(parents=True, exist_ok=True)
            path = self._path(settings.person_id)
            partial = path.with_suffix(".part")
            partial.write_text(
                json.dumps(settings.model_dump(mode="json"), indent=2), encoding="utf-8"
            )
            partial.replace(path)
        except OSError as exc:  # a read-only or full .data/: the change still stands here
            logger.warning("safety settings for %s not written: %s", settings.person_id, exc)

    def _load(self) -> None:
        """Overlay the kept files on the seeded people, once, on first use."""
        if self._loaded:
            return
        self._loaded = True
        for settings in self._read_all():
            self._settings[settings.person_id] = settings

    def _read_all(self) -> Iterator[SafetySettings]:
        if not self.directory.is_dir():
            return
        for path in sorted(self.directory.glob("*.json")):
            try:
                settings = SafetySettings.model_validate_json(path.read_text(encoding="utf-8"))
            except (OSError, ValueError) as exc:
                # Not settings, or half of them, or an older shape: skip the file
                # rather than start the API with nobody's settings at all.
                logger.warning("ignoring %s: %s", path.name, exc)
                continue
            yield settings


#: Which settings fields arrive as a plaintext PIN and are hashed before they are kept.
_PIN_FIELDS = ("safety_pin", "duress_pin")


def _utc_now() -> datetime:
    return datetime.now(UTC)


_store: CheckinStore | None = None


def get_checkin_store() -> CheckinStore:
    """The one `CheckinStore` this process uses, built on first use so `SAFETY_DIR` is
    read then rather than at import time."""
    global _store
    if _store is None:
        _store = CheckinStore()
    return _store


def use_checkin_store(store: CheckinStore | None) -> None:
    """Point this process at `store` (or, with None, at one built fresh on the next
    call). The seam tests use."""
    global _store
    _store = store
