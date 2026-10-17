"""Per-room monitoring switch and the live WebSocket (SPEC §12, section 16 decision B).

Split out of `api.py`: `GET /monitoring`, `PUT /rooms/{room}/monitoring`,
`GET /rooms/{room}/monitoring/history` and `/ws/live` all turn on the same room-pause
state, kept together here.
"""

from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field

from .demo import DEMO_RESIDENT, demo_residents
from .live import SCENARIO_NOT_FOUND, as_json, scenario_path, session_messages
from .monitoring import DEFAULT_BY, get_monitoring_store
from .replay import ReplayError

router = APIRouter()


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


@router.websocket("/ws/live")
async def live_session(
    websocket: WebSocket,
    scenario: str = "",
    speed: Annotated[float, Query(gt=0)] = 1.0,
) -> None:
    """The live view and its alerts, on one socket (SPEC section 16, decision B).

    Plays the recorded scenario named by `?scenario=` through the pipeline in real
    time, `?speed=` times as fast: frames, steps, the task map, errors as they are
    classified, then the session's score and flag (`routine_watch.live`). That is also
    the demo's fallback for a camera that fails (SPEC section 10), and the camera
    plugs into the same generator later.

    A session always lands against `demo.DEMO_RESIDENT` (`routine_watch.live`), so if
    that resident's room is paused (SPEC §12), this sends one `paused` message naming
    the room and closes instead - no scenario is loaded and no frames go out, the same
    as monitoring being off for a real camera. The room is re-checked on every message,
    so a nurse pausing mid-session stops the stream there too: the `paused` message
    replaces whatever would have been sent next, and the session generator is closed
    early so `session_messages` never records the unfinished session (same as a
    dashboard disconnect).

    An unknown scenario closes with 4404, and the socket closes normally when the
    session ends.
    """
    await websocket.accept()
    pause_message = _pause_message(DEMO_RESIDENT)
    if pause_message is not None:
        await websocket.send_json(pause_message)
        await websocket.close()
        return
    try:
        generator = session_messages(scenario_path(scenario), speed=speed)
        async for message in generator:
            pause_message = _pause_message(DEMO_RESIDENT)
            if pause_message is not None:
                await websocket.send_json(pause_message)
                await generator.aclose()
                await websocket.close()
                return
            await websocket.send_json(as_json(message))
    except ReplayError:
        await websocket.close(code=SCENARIO_NOT_FOUND)
        return
    except WebSocketDisconnect:  # the dashboard closed the tab mid-session
        return
    await websocket.close()
