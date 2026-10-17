"""The live camera on the dashboard: `/ws/live?source=camera` (SPEC section 16, decision B).

`routine_watch.capture` reads a camera into records and `routine_watch.live_camera` reads
records into a live session; this is the socket that puts the two together, so what is
tested here is that wiring. The dashboard gets from a camera what it gets from the
recorded scenario it falls back to, the camera is read on a thread of its own rather than
on the event loop, the room's pause switch is honoured before anything is filmed, and a
camera that will not open says so instead of streaming nothing.

Nothing here needs a camera, mediapipe or opencv: `capture.camera_frames` is replaced by a
recorded capture stream, which is the same records a camera writes (SPEC section 16,
"single capture stream"), and `scripts/ci.sh` runs without the `capture` extra.
"""

from __future__ import annotations

import asyncio
import json
import threading
import time
from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pytest
from fastapi import WebSocketDisconnect
from fastapi.testclient import TestClient
from jsonschema import Draft202012Validator

from routine_watch import api_live, api_state
from routine_watch.api import app
from routine_watch.capture import CaptureError, recorded
from routine_watch.contracts import CaptureFrame, CaptureSource, repo_root
from routine_watch.demo import DEMO_RESIDENT, demo_residents
from routine_watch.live import SCENARIO_NOT_FOUND
from routine_watch.live_camera import CAMERA_UNAVAILABLE, frames_in_thread
from routine_watch.monitoring import get_monitoring_store

#: One recorded capture stream, standing in for what a camera hands over: the
#: recogniser's whole make-tea clip, with every step of the task in it.
CLIP = Path(__file__).parent / "fixtures" / "recogniser" / "make_tea.jsonl"

#: The recorded session a camera is compared against: the demo's bad one, which is the
#: one recording that sends every message a live session has (`test_live_contract.py`).
SCENARIO = "tea_skip_teabag_pour_twice"

#: Fast enough that a recorded session plays out inside a test.
FAST = 1000.0

#: The live socket's own contract, both sources of it (`contracts/live_message.schema.json`).
SCHEMA = repo_root() / "contracts" / "live_message.schema.json"

#: mrs-k's room: every `/ws/live` session lands against her (`routine_watch.live`).
MRS_K_ROOM = next(r["room"] for r in demo_residents() if r["id"] == DEMO_RESIDENT)


def clip_frames() -> list[CaptureFrame]:
    """The clip as records off a camera: the same frames, labelled where they came from."""
    return [
        CaptureFrame.model_validate_json(line).model_copy(
            update={"source": CaptureSource.CAMERA}
        )
        for line in CLIP.read_text("utf-8").splitlines()
        if line.strip()
    ]


@dataclass
class FakeCamera:
    """`capture.camera_frames` with a recording where the camera would be.

    Stands in for the whole capture process - camera, MediaPipe, detector - and keeps
    what it was asked for, so a test can check the query reached it, which thread it was
    read on, and that it was let go of afterwards. `error` is a camera that will not
    open: raised on the first record, which is where `camera_frames` raises it.
    """

    frames: list[CaptureFrame] = field(default_factory=clip_frames)
    error: CaptureError | None = None
    #: Keep yielding the last record until the reader stops: a camera is never over.
    endless: bool = False
    #: The camera index each call asked for, in order.
    indexes: list[int] = field(default_factory=list)
    #: The thread each stream was read on.
    threads: list[str] = field(default_factory=list)
    #: Set when a stream is closed, which is where a real camera is released.
    released: threading.Event = field(default_factory=threading.Event)

    def __call__(self, index: int = 0, **unused: Any) -> Iterator[CaptureFrame]:
        self.indexes.append(index)
        return self._records()

    def _records(self) -> Iterator[CaptureFrame]:
        self.threads.append(threading.current_thread().name)
        try:
            if self.error is not None:
                raise self.error
            yield from self.frames
            while self.endless:
                time.sleep(0.005)
                yield self.frames[-1]
        finally:
            self.released.set()


@pytest.fixture
def client(monkeypatch):
    monkeypatch.delenv("LIVE_API", raising=False)
    api_state.reset()
    get_monitoring_store().reset()
    with TestClient(app) as test_client:
        yield test_client
    api_state.reset()
    get_monitoring_store().reset()


@pytest.fixture
def camera(monkeypatch) -> FakeCamera:
    """The camera `/ws/live?source=camera` opens, with a recording behind it."""
    fake = FakeCamera()
    monkeypatch.setattr(api_live, "camera_frames", fake)
    return fake


def messages_of(client: TestClient, query: str) -> list[dict[str, Any]]:
    """Every message of one session on `/ws/live?<query>`, until the socket closes."""
    with client.websocket_connect(f"/ws/live?{query}") as websocket:
        messages: list[dict[str, Any]] = []
        with pytest.raises(WebSocketDisconnect) as closed:
            while True:
                messages.append(websocket.receive_json())
    assert closed.value.code == 1000  # a session that ran to the end, not an error
    return messages


def kinds_of(messages: list[dict[str, Any]]) -> list[str]:
    return [message["type"] for message in messages]


def closed_code_of(client: TestClient, query: str) -> int:
    """The close code of a socket that never sends a message."""
    with client.websocket_connect(f"/ws/live?{query}") as websocket:
        with pytest.raises(WebSocketDisconnect) as closed:
            websocket.receive_json()
    return closed.value.code


# ----------------------------------------------- a camera session is a session like any


def test_a_camera_session_sends_what_a_recorded_one_sends(client, camera) -> None:
    """The acceptance case: the Live screen cannot tell which it is watching.

    The task graph first, the map before anything has happened, the frames and steps as
    they are read, the verdict last - and nothing a recorded scenario does not also send.
    """
    kinds = kinds_of(messages_of(client, "source=camera"))
    recorded_kinds = kinds_of(messages_of(client, f"scenario={SCENARIO}&speed={FAST}"))

    assert kinds[:2] == ["session_start", "step_state"]
    assert {"frame", "step"} <= set(kinds)
    assert kinds[-1] == "session_end"
    assert kinds.count("session_end") == 1
    assert set(kinds) <= set(recorded_kinds)


def test_every_message_of_a_camera_session_keeps_to_the_protocol(client, camera) -> None:
    """The socket's contract is the socket's contract, whichever end the frames came
    from (`contracts/live_message.schema.json`): a camera cannot send the dashboard a
    message it has never been shown, or a frame with anything extra in it."""
    check = Draft202012Validator(json.loads(SCHEMA.read_text(encoding="utf-8")))

    for message in messages_of(client, "source=camera"):
        check.validate(message)


def test_the_frames_are_the_records_the_camera_handed_over(client, camera) -> None:
    """Landmarks, boxes and timestamps off this camera, and the session they belong to.
    A frame message carries a capture record, and a capture record cannot hold an image
    (SPEC section 8)."""
    messages = messages_of(client, "source=camera")

    frames = [message["frame"] for message in messages if message["type"] == "frame"]
    assert frames, "a camera session with no frames in it is not a live view"
    assert {frame["source"] for frame in frames} == {CaptureSource.CAMERA.value}
    assert {frame["session_id"] for frame in frames} == {camera.frames[0].session_id}
    assert messages[0]["session_id"] == camera.frames[0].session_id
    assert [frame["seq"] for frame in frames] == sorted(frame["seq"] for frame in frames)


def test_a_camera_session_has_no_history_to_flag_against(client, camera) -> None:
    """Nobody is on camera as far as the pipeline is concerned, and a session only flags
    against prior sessions of the same resident (SPEC section 7), so the verdict is the
    session's errors and score with nothing flagged (`routine_watch.live_camera`)."""
    end = messages_of(client, "source=camera")[-1]

    assert end["flag"] is False
    assert end["alert_id"] is None
    assert end["score"] >= 0.0


def test_the_recorded_scenario_is_still_the_default(client, camera) -> None:
    """The demo's own path, and its fallback when a camera fails (SPEC section 10): a
    socket that does not ask for the camera never goes near one."""
    messages = messages_of(client, f"scenario={SCENARIO}&speed={FAST}")

    assert messages[-1]["type"] == "session_end"
    assert camera.indexes == []


# --------------------------------------------------------------- what the query asks for


@pytest.mark.parametrize(
    ("query", "index"),
    [("source=camera", 0), ("source=camera&camera=0", 0), ("source=camera&camera=2", 2)],
)
def test_the_camera_index_comes_from_the_query(client, camera, query, index) -> None:
    """`?camera=` picks the device, index 0 - the laptop's own - by default."""
    messages_of(client, query)

    assert camera.indexes == [index]


def test_the_camera_is_read_on_a_thread_of_its_own(client, camera) -> None:
    """Opening a camera and waiting for a frame block; the API answering everything else
    while a session runs is why `live_camera.frames_in_thread` exists."""
    messages_of(client, "source=camera")

    assert camera.threads and threading.current_thread().name not in camera.threads
    assert all(name.startswith("routine-watch-capture") for name in camera.threads)


def test_a_camera_that_will_not_open_closes_the_socket(client, camera) -> None:
    """No camera at that index, no `capture` extra, no MediaPipe bundles: one close code
    the dashboard reads as "fall back to the recorded demo" (SPEC section 10), rather
    than an open socket that never says anything."""
    camera.error = CaptureError("no camera at index 7")

    assert closed_code_of(client, "source=camera&camera=7") == CAMERA_UNAVAILABLE


def test_a_task_graph_that_does_not_exist_never_opens_the_camera(client, camera) -> None:
    """`?task=` names the graph the camera is read against. An unknown one is a stale
    client, like an unknown scenario, and is answered before anything is filmed."""
    assert closed_code_of(client, "source=camera&task=knitting") == SCENARIO_NOT_FOUND
    assert camera.indexes == []


def test_a_paused_room_is_never_filmed(client, camera) -> None:
    """Monitoring off means the camera is not opened at all (SPEC §12), not opened and
    then thrown away: the pause switch is checked before the session is started."""
    assert client.put(f"/rooms/{MRS_K_ROOM}/monitoring", json={"on": False}).status_code == 200

    with client.websocket_connect("/ws/live?source=camera") as websocket:
        assert websocket.receive_json() == {"type": "paused", "room": MRS_K_ROOM}
        with pytest.raises(WebSocketDisconnect):
            websocket.receive_json()

    assert camera.indexes == []


def test_the_camera_is_let_go_of_when_the_dashboard_closes_the_tab(client, camera) -> None:
    """A camera nobody is watching is still a camera that is filming, so the stream is
    closed with the socket: the generator is closed on the way out of the handler, which
    stops the reading thread and releases the device."""
    camera.endless = True

    with client.websocket_connect("/ws/live?source=camera") as websocket:
        assert websocket.receive_json()["type"] == "session_start"

    assert camera.released.wait(timeout=5.0), "the camera was still being read"


# --------------------------------------------------- the thread between the two, on its own


def drain(
    open_frames, *, max_pending: int | None = None, stop_after: int | None = None
) -> list[CaptureFrame]:
    """Every record `frames_in_thread` hands over, as an event loop would read them."""

    async def collect() -> list[CaptureFrame]:
        kwargs = {} if max_pending is None else {"max_pending": max_pending}
        stream = frames_in_thread(open_frames, **kwargs)
        frames = []
        async for frame in stream:
            frames.append(frame)
            if stop_after is not None and len(frames) >= stop_after:
                await stream.aclose()
                break
        return frames

    return asyncio.run(collect())


def test_frames_in_thread_hands_over_every_record_in_order() -> None:
    camera = FakeCamera()

    assert drain(camera) == camera.frames


def test_frames_in_thread_raises_what_the_capture_process_raised() -> None:
    """A camera that cannot be opened is a `CaptureError` on the first record, and it has
    to cross the thread to be one: swallowing it would leave the socket waiting for a
    frame that is never coming."""
    camera = FakeCamera(error=CaptureError("mediapipe is not installed"))

    with pytest.raises(CaptureError, match="mediapipe"):
        drain(camera)


def test_frames_in_thread_lets_go_of_a_camera_the_reader_stopped_reading() -> None:
    camera = FakeCamera(endless=True)

    frames = drain(camera, stop_after=1)

    assert frames == camera.frames[:1]
    assert camera.released.wait(timeout=5.0), "the camera was still being read"


def test_frames_in_thread_drops_records_rather_than_queueing_them_up() -> None:
    """A reader slower than the camera gets the newest records thrown away, not a backlog
    it will never catch up with - and the session still ends rather than hanging."""
    camera = FakeCamera()

    assert drain(camera, max_pending=0) == []


# ------------------------------------------------------------- keeping the records (--record)


def test_recorded_writes_the_jsonl_a_replay_reads(tmp_path) -> None:
    """`scripts/camera.sh --record` keeps the capture stream as it goes past, in the one
    format `routine_watch.replay` and the scenarios read, so a live session can be
    replayed offline afterwards."""
    frames = clip_frames()
    out = tmp_path / "kept" / "session.jsonl"

    handed_over = list(recorded(frames, out))

    written = [
        CaptureFrame.model_validate_json(line)
        for line in out.read_text("utf-8").splitlines()
        if line.strip()
    ]
    assert handed_over == frames  # the reader still sees every record, in order
    assert written == frames


def test_recorded_keeps_nothing_that_looks_like_a_frame(tmp_path) -> None:
    """The privacy boundary holds on the way to disk too (SPEC section 8): a record has
    no field that could hold an image, so neither has the file."""
    out = tmp_path / "session.jsonl"

    list(recorded(clip_frames(), out))

    written = out.read_text("utf-8")
    assert "image" not in written and "jpeg" not in written and "frame_b64" not in written
    assert set(json.loads(written.splitlines()[0])) == set(
        CaptureFrame.model_fields
    )
