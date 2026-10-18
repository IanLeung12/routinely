"""Per-room monitoring switch and the live WebSocket (SPEC §12, section 16 decision B).

Split out of `api.py`: `GET /monitoring`, `PUT /rooms/{room}/monitoring`,
`GET /rooms/{room}/monitoring/history` and `/ws/live` all turn on the same room-pause
state, kept together here.

`/ws/live` also carries the safety check-ins (SPEC §18, Project KAZE) for a socket
that asks for them: a session that flags a change asks that person to check in, and
the check-in's state changes go out on the same socket as `checkin` messages. A socket
that does not ask (every client before this) sends exactly what it always did.
"""

import asyncio
import logging
from collections.abc import AsyncIterator
from contextlib import aclosing
from typing import Annotated, Any, Literal

from fastapi import APIRouter, HTTPException, Query, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field

from . import api_checkin
from .api_checkin import CHECKIN_AUDIENCE
from .capture import CaptureError, camera_frames
from .checkin import CheckinError
from .demo import DEMO_RESIDENT, demo_residents
from .live import SCENARIO_NOT_FOUND, as_json, scenario_path, session_messages
from .live_camera import CAMERA_UNAVAILABLE, camera_session_messages, frames_in_thread
from .monitoring import DEFAULT_BY, get_monitoring_store
from .replay import ReplayError
from .tasks import TaskGraphError

logger = logging.getLogger(__name__)

router = APIRouter()

#: Where `/ws/live` reads its session from: the recorded scenario `?scenario=` names,
#: which is the demo's own path and the default, this machine's camera, or no session
#: at all - a socket that is only there for the safety check-in pushes (SPEC §18).
LiveSource = Literal["scenario", "camera", "checkins"]

#: `?source=camera` and `?source=checkins`, spelled once.
CAMERA = "camera"
CHECKINS = "checkins"


class RoomMonitoringIn(BaseModel):
    """The pause switch's body (SPEC §12): on resumes a room, off pauses it.

    `by` is who to log the change under in the room's audit trail
    (`GET /rooms/{room}/monitoring/history`). The MVP has no nurse logins, so the
    dashboard leaves it out and every change is one anonymous nurse's.
    """

    on: bool
    by: str = Field(default=DEFAULT_BY, min_length=1, max_length=60)


def _pause_message(resident_id: str) -> dict | None:
    """`{"type": "paused", "room": ...}` if `resident_id`'s room is paused right now
    (SPEC §12), else `None`. `/ws/live` calls this both before a session starts and
    again on every message, since a nurse can pause mid-session.
    """
    room = _room_for(resident_id)
    if room is not None and not get_monitoring_store().is_on(room):
        return {"type": "paused", "room": room}
    return None


def _room_for(resident_id: str) -> str | None:
    """`resident_id`'s room, straight from `demo.demo_residents()` (SPEC §12: a room
    or camera is linked to a resident by configuration), or `None` if there is no
    such resident.
    """
    return next(
        (resident["room"] for resident in demo_residents() if resident["id"] == resident_id),
        None,
    )


def _known_room_or_404(room: str) -> None:
    """Raise a 404 unless some demo resident is in `room` (SPEC §12: rooms come from
    configuration, so an unknown one is a stale client rather than a room to pause).
    """
    if room not in {resident["room"] for resident in demo_residents()}:
        raise HTTPException(status_code=404, detail="room not found")


@router.get("/monitoring")
def get_monitoring() -> dict:
    """Every room a nurse has paused right now (SPEC §12): backs the dashboard's
    pause switch state.
    """
    return {"paused_rooms": get_monitoring_store().paused_rooms()}


@router.put("/rooms/{room}/monitoring")
def set_room_monitoring(room: str, body: RoomMonitoringIn) -> dict:
    """Pause or resume monitoring for one room (SPEC §12), without touching any
    other room, and log the change against the room. 404s for a room no demo
    resident is in.
    """
    _known_room_or_404(room)
    get_monitoring_store().set(room, body.on, by=body.by)
    return {"room": room, "on": body.on}


@router.get("/rooms/{room}/monitoring/history")
def room_monitoring_history(room: str) -> dict:
    """Who paused or resumed monitoring in this room, and when (SPEC §12).

    Newest first, at most `monitoring.MAX_HISTORY` changes, each
    `{"on": bool, "by": str, "at": ISO 8601 str}`: what the resident screen shows
    under the room's switch, so a paused camera is accountable rather than silent.
    Empty until somebody changes the switch, and `/demo/reset` empties it again.
    404s for a room no demo resident is in, like the switch itself.
    """
    _known_room_or_404(room)
    return {"room": room, "history": get_monitoring_store().history(room)}


def _stream(
    source: LiveSource,
    subscriber: api_checkin.Subscriber | None,
    *,
    scenario: str,
    speed: float,
    camera: int,
    task: str,
) -> AsyncIterator[dict[str, Any]]:
    """Everything this socket sends: the live session, the check-in pushes, or both.

    A socket that asked for neither audience gets the session generator itself, so the
    path every client took before check-ins existed is the same object it always was.
    """
    session = None if source == CHECKINS else _session(
        source, scenario=scenario, speed=speed, camera=camera, task=task
    )
    if subscriber is None:
        assert session is not None  # `?source=checkins` without an audience is refused
        return session
    return _merged(session, subscriber)


async def _merged(
    session: AsyncIterator[dict[str, Any]] | None, subscriber: api_checkin.Subscriber
) -> AsyncIterator[dict[str, Any]]:
    """The session's messages and this socket's `checkin` pushes, from one place.

    One writer, so a push cannot land in the middle of a session message, and **the
    session always wins a tie**: the check-in a session's own flag starts is pushed
    after `session_end`, never in front of it, so a session's transcript is what it
    was before any of this (`pipeline/tests/test_live_contract.py` holds it to that).

    A socket watching check-ins **stays open after the session ends**: the countdown
    the session just started is the whole point, and it has barely begun. It closes
    when the client closes it, or with the app.
    """
    session_task: asyncio.Task | None = None
    push_task: asyncio.Task | None = None
    try:
        while True:
            if session is not None and session_task is None:
                session_task = asyncio.ensure_future(session.__anext__())
            if push_task is None:
                push_task = asyncio.ensure_future(subscriber.get())
            await asyncio.wait(
                {task for task in (session_task, push_task) if task is not None},
                return_when=asyncio.FIRST_COMPLETED,
            )
            if session_task is not None and session_task.done():
                finished, session_task = session_task, None
                try:
                    message = finished.result()
                except StopAsyncIteration:
                    session = None  # over; this socket is here for the check-in now
                else:
                    yield message
                continue
            if push_task is not None and push_task.done():
                finished, push_task = push_task, None
                yield finished.result()
    finally:
        waiting = [task for task in (session_task, push_task) if task is not None]
        for task in waiting:
            task.cancel()
        if waiting:
            await asyncio.gather(*waiting, return_exceptions=True)
        if session is not None:
            await session.aclose()


def _ask_to_check_in(message: dict[str, Any]) -> None:
    """Ask the person to check in, now that a session has flagged a change (SPEC §18).

    This is the hook from an alert to a safety check-in: `session_end` carrying a flag
    and an `alert_id` is the moment this pipeline raises one (`routine_watch.live`;
    `/alerts` only reads flags back). Idempotent per alert, so the same flag read
    again never asks twice, and a camera session - which never flags - asks nothing.

    A person with no safety settings (somebody linked but not set up) is logged and
    left alone: a flag is still an alert on the dashboard, check-in or no check-in.
    """
    if message.get("type") != "session_end" or not message.get("flag"):
        return
    alert_id = message.get("alert_id")
    if not alert_id:
        return
    try:
        api_checkin.start_for_alert(str(alert_id), DEMO_RESIDENT)
    except CheckinError as exc:
        logger.info("no safety check-in for %s: %s", alert_id, exc)


def _session(
    source: LiveSource, *, scenario: str, speed: float, camera: int, task: str
) -> AsyncIterator[dict[str, Any]]:
    """The live session `/ws/live` was asked for, as its messages.

    A recorded scenario played in real time (`routine_watch.live`), or this machine's
    camera read as it films (`routine_watch.live_camera`). The two are the same session
    from opposite ends and say the same things in the same order, so everything after
    this point - the pause check, the serialising, the socket - cannot tell them apart.

    Nothing is opened here: both are generators, so the scenario is loaded, and the
    camera and MediaPipe started, on the first message. A camera is read on a thread of
    its own, because opening one and waiting for a frame would otherwise stop the API
    answering anything else for the length of the session.
    """
    if source == CAMERA:
        return camera_session_messages(frames_in_thread(lambda: camera_frames(camera)), task)
    return session_messages(scenario_path(scenario), speed=speed)


@router.websocket("/ws/live")
async def live_session(
    websocket: WebSocket,
    scenario: str = "",
    speed: Annotated[float, Query(gt=0)] = 1.0,
    source: LiveSource = "scenario",
    camera: Annotated[int, Query(ge=0)] = 0,
    task: str = "tea",
    checkin_person: Annotated[str, Query(max_length=60)] = "",
    checkin_supporter: Annotated[str, Query(max_length=60)] = "",
) -> None:
    """The live view and its alerts, on one socket (SPEC section 16, decision B).

    Plays the recorded scenario named by `?scenario=` through the pipeline in real
    time, `?speed=` times as fast: frames, steps, the task map, errors as they are
    classified, then the session's score and flag (`routine_watch.live`). That is the
    demo's own path, and its fallback for a camera that fails (SPEC section 10), so it
    stays the default.

    `?source=camera` watches this machine's camera instead - `?camera=` picks the index,
    0 being the laptop's own - and reads it against the `?task=` graph, tea unless asked
    otherwise (`scripts/camera.sh` starts the stack and points the dashboard here).
    Everything else is the same: the same messages in the same order, because it is the
    same pipeline reading the same records (`routine_watch.live_camera`). What a camera
    session has not got is a resident's history, so it never flags: `session_end` carries
    the session's errors and score with `flag: false`.

    A session always lands against `demo.DEMO_RESIDENT` (`routine_watch.live`), so if
    that resident's room is paused (SPEC §12), this sends one `paused` message naming
    the room and closes instead - no scenario is loaded, no camera is opened and no
    frames go out, the same as monitoring being off for a real camera. The room is
    re-checked on every message, so a nurse pausing mid-session stops the stream there
    too: the `paused` message replaces whatever would have been sent next, and the
    session generator is closed early so `session_messages` never records the unfinished
    session (same as a dashboard disconnect). Closing the generator is also what lets go
    of the camera, so nothing is being filmed once the socket is gone.

    `?checkin_person=` or `?checkin_supporter=` also puts this socket on the safety
    check-in feed (SPEC §18), as `checkin` messages carrying only what that audience
    may see - the person's own countdown, or the alarms that have actually reached that
    supporter, filtered by what the person shared with them. Such a socket **stays open
    after `session_end`**, because the check-in the session's own flag just started is
    the thing it is there for; `?source=checkins` is the same feed with no session at
    all, for a screen that is not watching one. Exactly one of the two audiences, and
    `?source=checkins` needs one: both or neither closes with 4400. Without either, a
    socket sends exactly what it did before check-ins existed.

    An unknown scenario or task closes with 4404, a camera that cannot be read with 4503
    (`live_camera.CAMERA_UNAVAILABLE`, and why in the API log), a `?source=` that is
    none of the three is refused at the handshake, and the socket closes normally when
    the session ends.
    """
    await websocket.accept()
    watching = bool(checkin_person) != bool(checkin_supporter)
    if (checkin_person and checkin_supporter) or (source == CHECKINS and not watching):
        await websocket.close(code=CHECKIN_AUDIENCE)
        return
    if source != CHECKINS:
        # A check-in feed is not watching anybody, so a paused room has nothing to say
        # to it: pausing the camera stops the watching (SPEC §12), not an alarm that
        # has already been raised.
        pause_message = _pause_message(DEMO_RESIDENT)
        if pause_message is not None:
            await websocket.send_json(pause_message)
            await websocket.close()
            return
    subscriber = (
        api_checkin.subscribe(
            person=checkin_person or None, supporter=checkin_supporter or None
        )
        if watching
        else None
    )
    try:
        async with aclosing(
            _stream(
                source, subscriber, scenario=scenario, speed=speed, camera=camera, task=task
            )
        ) as generator:
            async for message in generator:
                if source != CHECKINS:
                    pause_message = _pause_message(DEMO_RESIDENT)
                    if pause_message is not None:
                        await websocket.send_json(pause_message)
                        await websocket.close()
                        return
                await websocket.send_json(as_json(message))
                _ask_to_check_in(message)
    except (CaptureError, ReplayError) as exc:
        if source == CAMERA:
            # The dashboard only learns the socket closed, so this is where whoever is
            # holding the laptop finds out why: no camera at that index, no `capture`
            # extra, no MediaPipe bundles, or a camera that saw nothing.
            logger.warning("no camera session on camera %s: %s", camera, exc)
            await websocket.close(code=CAMERA_UNAVAILABLE)
            return
        await websocket.close(code=SCENARIO_NOT_FOUND)
        return
    except TaskGraphError:  # `?task=` naming a graph there is no file for
        await websocket.close(code=SCENARIO_NOT_FOUND)
        return
    except WebSocketDisconnect:  # the dashboard closed the tab mid-session
        return
    finally:
        if subscriber is not None:
            api_checkin.release(subscriber)
    await websocket.close()
