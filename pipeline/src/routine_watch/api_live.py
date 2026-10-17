"""Per-room monitoring switch and the live WebSocket (SPEC §12, section 16 decision B).

Split out of `api.py`: `GET /monitoring`, `PUT /rooms/{room}/monitoring`,
`GET /rooms/{room}/monitoring/history` and `/ws/live` all turn on the same room-pause
state, kept together here.
"""

import logging
from collections.abc import AsyncIterator
from contextlib import aclosing
from typing import Annotated, Any, Literal

from fastapi import APIRouter, HTTPException, Query, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field

from .capture import CaptureError, camera_frames
from .demo import DEMO_RESIDENT, demo_residents
from .live import SCENARIO_NOT_FOUND, as_json, scenario_path, session_messages
from .live_camera import CAMERA_UNAVAILABLE, camera_session_messages, frames_in_thread
from .monitoring import DEFAULT_BY, get_monitoring_store
from .replay import ReplayError
from .tasks import TaskGraphError

logger = logging.getLogger(__name__)

router = APIRouter()

#: Where `/ws/live` reads its session from: the recorded scenario `?scenario=` names,
#: which is the demo's own path and the default, or this machine's camera.
LiveSource = Literal["scenario", "camera"]

#: `?source=camera`, spelled once.
CAMERA = "camera"


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

    An unknown scenario or task closes with 4404, a camera that cannot be read with 4503
    (`live_camera.CAMERA_UNAVAILABLE`, and why in the API log), a `?source=` that is
    neither of the two is refused at the handshake, and the socket closes normally when
    the session ends.
    """
    await websocket.accept()
    pause_message = _pause_message(DEMO_RESIDENT)
    if pause_message is not None:
        await websocket.send_json(pause_message)
        await websocket.close()
        return
    try:
        async with aclosing(
            _session(source, scenario=scenario, speed=speed, camera=camera, task=task)
        ) as generator:
            async for message in generator:
                pause_message = _pause_message(DEMO_RESIDENT)
                if pause_message is not None:
                    await websocket.send_json(pause_message)
                    await websocket.close()
                    return
                await websocket.send_json(as_json(message))
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
    await websocket.close()
