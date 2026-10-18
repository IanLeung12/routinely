"""Safety check-in routes, the server's countdown and the push behind it (SPEC §18).

`routine_watch.checkin` holds the rules; this is the part with a clock, a socket and
an event loop:

* **The countdown is the server's.** `tick_forever` wakes once a second and advances
  every open check-in (`api.py` starts it with the app's lifespan), so the alarm still
  fires when the person's device drops off the network after the check-in started -
  Project KAZE's connectivity failure. Every route advances the same way before it
  answers, so a check-in reads right even if nothing has been ticking.
* **Pushes.** A state change is published to whoever is watching on `/ws/live`
  (`routine_watch.api_live`), as a `checkin` message carrying exactly what that
  audience may see: the person's own screen gets `person_view`, a supporter gets
  `supporter_view` filtered by what the person shared with *them*.
* **Routes.** `GET /checkins/active`, `POST /checkins/demo`,
  `POST /checkins/{id}/respond|ack|resolve|simulate` and
  `GET/PUT /people/{id}/safety`. They are `async def` on purpose: publishing touches
  the event loop's queues, so a route must run on the loop rather than in FastAPI's
  thread pool.

Nothing here calls, texts or pages anybody (SPEC §18): an alarm is a payload a screen
shows. PINs arrive in a request body, are hashed by `checkin.py` and appear in no
response, no event log and no log line.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Annotated, Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field, model_validator

from .checkin import (
    ACTOR_PERSON,
    MAX_WINDOW_S,
    MIN_WINDOW_S,
    PIN_MAX_LEN,
    PIN_MIN_LEN,
    Checkin,
    CheckinError,
    ResolveReason,
    SimulatedEvent,
    Supporter,
    get_checkin_store,
    person_sees_open,
    person_view,
    settings_payload,
    supporter_view,
)
from .demo import DEMO_RESIDENT

logger = logging.getLogger(__name__)

router = APIRouter()

#: How often the server's countdown wakes up. One second: the UIs show seconds, and
#: an alarm that is a second late is still the right alarm.
TICK_S = 1.0

#: How many pushes one socket can fall behind before the oldest are dropped. A screen
#: that cannot keep up with a countdown wants the latest state, not a backlog of it.
QUEUE_LIMIT = 64

#: `/ws/live` closes with this when a socket asks for check-in pushes without saying
#: whose - or says both - because a socket has one audience and guessing it wrong is
#: the one mistake this feature must not make.
CHECKIN_AUDIENCE = 4400

AUDIENCE_DETAIL = "say who is asking: ?person= or ?supporter=, not both"

PIN_DETAIL = f"a PIN is {PIN_MIN_LEN}-{PIN_MAX_LEN} characters; digits are easiest to type"

SAME_PIN_DETAIL = "the duress PIN must be different from the safety PIN"


# -- what a socket asked to see -----------------------------------------------------


@dataclass
class Subscriber:
    """One socket's check-in feed: a queue, and who it may see.

    Exactly one of `person` and `supporter` is set. A person's feed carries their own
    check-ins; a supporter's carries the ones they have actually been alarmed about,
    so being on somebody's list is not the same as watching them.
    """

    loop: asyncio.AbstractEventLoop
    queue: asyncio.Queue[dict[str, Any]] = field(default_factory=lambda: asyncio.Queue(QUEUE_LIMIT))
    person: str | None = None
    supporter: str | None = None

    async def get(self) -> dict[str, Any]:
        """The next `checkin` message for this socket, when there is one."""
        return await self.queue.get()

    def wants(self, record: Checkin) -> bool:
        if self.person is not None:
            return record.person_id == self.person
        return self.supporter is not None and self.supporter in record.notified

    def message(self, record: Checkin) -> dict[str, Any]:
        """`record` as this socket's audience may see it."""
        store = get_checkin_store()
        now = store.now()
        if self.person is not None:
            return {"type": "checkin", "checkin": person_view(record, now)}
        settings = store.settings_of(record.person_id)
        view = supporter_view(record, settings, str(self.supporter), now)
        return {"type": "checkin", "checkin": view}


#: Every socket currently watching. Small by nature: one per open screen.
_subscribers: list[Subscriber] = []


def subscribe(*, person: str | None = None, supporter: str | None = None) -> Subscriber:
    """Watch check-ins as `person` or as `supporter`. Call it from the socket's own
    coroutine: the queue belongs to the loop the socket is being served on."""
    subscriber = Subscriber(loop=asyncio.get_running_loop(), person=person, supporter=supporter)
    _subscribers.append(subscriber)
    return subscriber


def release(subscriber: Subscriber) -> None:
    """Stop watching. Safe to call twice (a socket closing twice is not an error)."""
    if subscriber in _subscribers:
        _subscribers.remove(subscriber)


def publish(records: list[Checkin]) -> None:
    """Push every one of `records` to the sockets allowed to see it.

    Delivery is handed to each socket's own loop (`call_soon_threadsafe`), so this is
    safe to call from a route, from the tick, or from a test's thread, and a socket
    whose loop has already gone takes nothing down with it.
    """
    for record in records:
        for subscriber in list(_subscribers):
            if not subscriber.wants(record):
                continue
            try:
                message = subscriber.message(record)
                subscriber.loop.call_soon_threadsafe(_deliver, subscriber, message)
            except RuntimeError:  # that socket's loop is gone; it will be released
                release(subscriber)


def _deliver(subscriber: Subscriber, message: dict[str, Any]) -> None:
    """Put `message` on the queue, dropping the oldest if the screen is behind. Runs
    on the socket's own loop, so touching the queue here is safe."""
    if subscriber.queue.full():
        try:
            subscriber.queue.get_nowait()
        except asyncio.QueueEmpty:  # drained between the check and here
            pass
    try:
        subscriber.queue.put_nowait(message)
    except asyncio.QueueFull:  # another push won the race; the newest one still lands
        logger.debug("dropped a check-in push for a socket that is behind")


async def tick_forever(interval: float = TICK_S) -> None:
    """Advance every open check-in, for as long as the app is up (SPEC §18).

    This is what makes the countdown the server's: it fires the alarm when the
    check-in window runs out and passes it down the supporter list when an ack window
    does, whether or not anybody's screen is still connected. A tick that finds
    nothing due says nothing to anybody.
    """
    while True:
        await asyncio.sleep(interval)
        try:
            publish(get_checkin_store().tick())
        except Exception:  # a bad tick must never take the API with it
            logger.exception("check-in tick failed")


def start_for_alert(alert_id: str, person_id: str) -> Checkin:
    """Ask `person_id` to check in because `alert_id` flagged a change (SPEC §18).

    Idempotent per alert: the same alert read again - and a flag is read again on
    every `session_end` and every dashboard poll - gives back the check-in it already
    asked with, and pushes nothing a second time.
    """
    store = get_checkin_store()
    existing = store.checkin_for_alert(alert_id)
    if existing is not None:
        return existing
    record = store.start(person_id, alert_id=alert_id)
    publish([record])
    return record


# -- request bodies -----------------------------------------------------------------


class RespondIn(BaseModel):
    """The person's answer. `pin` is deliberately unconstrained here: a pydantic
    complaint quotes the value it rejected, and a PIN must not come back in a 422."""

    model_config = ConfigDict(extra="forbid")

    pin: str


class AckIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    supporter: str = Field(min_length=1, max_length=60)


class ResolveIn(BaseModel):
    """Who closed it and what it was (SPEC §18): `by` is `"person"` or a supporter id."""

    model_config = ConfigDict(extra="forbid")

    by: str = Field(min_length=1, max_length=60)
    reason: ResolveReason


class SimulateIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    event: SimulatedEvent


class DemoCheckinIn(BaseModel):
    """`POST /checkins/demo`: start one by hand, for the demo."""

    model_config = ConfigDict(extra="forbid")

    person: str = DEMO_RESIDENT
    alert_id: str | None = None


class SafetyIn(BaseModel):
    """A change to one person's safety settings. Everything is optional: a body sets
    what it names and leaves the rest alone.

    The PINs are write-only and unconstrained in the model for the same reason as
    `RespondIn.pin`; their length is checked in the route, which answers without
    quoting them.
    """

    model_config = ConfigDict(extra="forbid")

    checkin_window_s: float | None = Field(default=None, ge=MIN_WINDOW_S, le=MAX_WINDOW_S)
    ack_window_s: float | None = Field(default=None, ge=MIN_WINDOW_S, le=MAX_WINDOW_S)
    location: str | None = Field(default=None, max_length=120)
    supporters: list[Supporter] | None = None
    safety_pin: str | None = None
    duress_pin: str | None = None

    @model_validator(mode="after")
    def _one_entry_per_supporter(self) -> SafetyIn:
        if self.supporters is not None:
            ids = [one.id for one in self.supporters]
            if len(set(ids)) != len(ids):
                raise ValueError("a supporter can only be on the list once")
        return self

    def changes(self) -> dict[str, Any]:
        """The fields this body actually set, as `CheckinStore.update_settings` takes
        them (`supporters` as a tuple, so the settings stay immutable)."""
        changes = self.model_dump(exclude_none=True)
        if self.supporters is not None:
            changes["supporters"] = tuple(self.supporters)
        return changes


# -- routes -------------------------------------------------------------------------


@router.get("/checkins/active")
async def list_active_checkins(
    person: Annotated[str, Query(max_length=60)] = "",
    supporter: Annotated[str, Query(max_length=60)] = "",
) -> dict:
    """Every check-in still waiting for somebody, as one audience may see it.

    `?person=` is their own screen: their question and their countdown, and a check-in
    they answered with the duress PIN is **not** in it, because on their screen that
    one is cancelled (SPEC §18). `?supporter=` is a supporter's: the check-ins that
    have actually reached them, each carrying only what that person shared with them.

    One of the two, never both and never neither: a payload that depends on who is
    asking cannot guess.
    """
    store = get_checkin_store()
    now = store.now()
    if bool(person) == bool(supporter):
        raise HTTPException(status_code=422, detail=AUDIENCE_DETAIL)
    try:
        if person:
            store.settings_of(person)
            return {
                "checkins": [
                    person_view(record, now)
                    for record in store.active(person)
                    if person_sees_open(record)
                ]
            }
        return {
            "checkins": [
                supporter_view(record, store.settings_of(record.person_id), supporter, now)
                for record in store.active()
                if supporter in record.notified
            ]
        }
    except CheckinError as exc:
        raise _http(exc) from exc


@router.post("/checkins/demo")
async def start_demo_checkin(body: DemoCheckinIn) -> dict:
    """Start a check-in by hand (SPEC §18, the demo's own path).

    The same thing a flagged change does, with the same server-owned countdown, so the
    demo can show the flow without waiting for a session to go wrong. With an
    `alert_id`, it is idempotent per alert like the real hook.
    """
    try:
        if body.alert_id is not None:
            record = start_for_alert(body.alert_id, body.person)
        else:
            record = get_checkin_store().start(body.person)
            publish([record])
    except CheckinError as exc:
        raise _http(exc) from exc
    return {"checkin": person_view(record, get_checkin_store().now())}


@router.post("/checkins/{checkin_id}/respond")
async def respond_to_checkin(checkin_id: str, body: RespondIn) -> dict:
    """The person checking in (SPEC §18).

    The safety PIN and the duress PIN answer with the **same payload**, byte for byte:
    the duress one raises a silent alarm to the person's supporters, and their own
    screen says what it would have said if they had simply cancelled it. A wrong PIN
    is a 401 and changes nothing, so whoever is counting carries on counting.
    """
    store = get_checkin_store()
    try:
        record, _kind = store.respond(checkin_id, body.pin)
    except CheckinError as exc:
        raise _http(exc) from exc
    publish([record])
    return {"checkin": person_view(record, store.now())}


@router.post("/checkins/{checkin_id}/ack")
async def acknowledge_checkin(checkin_id: str, body: AckIn) -> dict:
    """A supporter tapping "I'm on it": the escalation stops with them."""
    store = get_checkin_store()
    try:
        record = store.acknowledge(checkin_id, body.supporter)
        settings = store.settings_of(record.person_id)
    except CheckinError as exc:
        raise _http(exc) from exc
    publish([record])
    return {"checkin": supporter_view(record, settings, body.supporter, store.now())}


@router.post("/checkins/{checkin_id}/resolve")
async def resolve_checkin(checkin_id: str, body: ResolveIn) -> dict:
    """A supporter or the person closing it, saying what it was (SPEC §18).

    Answers in the words of whoever closed it: the person gets their own screen's
    payload, a supporter gets theirs.
    """
    store = get_checkin_store()
    try:
        record = store.resolve(checkin_id, body.by, body.reason)
        settings = store.settings_of(record.person_id)
    except CheckinError as exc:
        raise _http(exc) from exc
    publish([record])
    now = store.now()
    if body.by == ACTOR_PERSON:
        return {"checkin": person_view(record, now)}
    return {"checkin": supporter_view(record, settings, body.by, now)}


@router.post("/checkins/{checkin_id}/simulate")
async def simulate_checkin(checkin_id: str, body: SimulateIn) -> dict:
    """Mark the person's device gone or back (SPEC §18): the demo's connectivity
    failure. The countdown is the server's, so it is untouched - which is the point."""
    store = get_checkin_store()
    try:
        record = store.simulate(checkin_id, body.event)
    except CheckinError as exc:
        raise _http(exc) from exc
    publish([record])
    return {"checkin": person_view(record, store.now())}


@router.get("/people/{person_id}/safety")
async def get_safety(person_id: str) -> dict:
    """One person's check-in settings: windows, supporters, what each may see, and
    whether each PIN is set. Never a PIN, a hash or a salt."""
    try:
        return settings_payload(get_checkin_store().settings_of(person_id))
    except CheckinError as exc:
        raise _http(exc) from exc


@router.put("/people/{person_id}/safety")
async def put_safety(person_id: str, body: SafetyIn) -> dict:
    """Change one person's check-in settings (SPEC §18).

    PINs are write-only: they are hashed on the way in and the answer says only that
    they are set. The duress PIN has to differ from the safety one - the same string
    for both would be a duress PIN that cannot be told apart from checking in.
    """
    for pin in (body.safety_pin, body.duress_pin):
        if pin is not None and not _is_pin(pin):
            raise HTTPException(status_code=422, detail=PIN_DETAIL)
    if body.safety_pin is not None and body.safety_pin == body.duress_pin:
        raise HTTPException(status_code=422, detail=SAME_PIN_DETAIL)
    try:
        settings = get_checkin_store().update_settings(person_id, body.changes())
    except CheckinError as exc:
        raise _http(exc) from exc
    return settings_payload(settings)


def _is_pin(pin: str) -> bool:
    """Whether `pin` is a PIN somebody can type under pressure: long enough to guess
    at, short enough to enter, and nothing but visible characters."""
    return PIN_MIN_LEN <= len(pin) <= PIN_MAX_LEN and pin.strip() == pin and " " not in pin


def _http(exc: CheckinError) -> HTTPException:
    """A check-in rule as its HTTP answer. The status lives on the exception
    (`checkin.CheckinError`), so the rules are stated once."""
    return HTTPException(status_code=exc.status, detail=str(exc))
