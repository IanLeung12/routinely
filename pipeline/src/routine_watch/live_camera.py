"""The live session from a camera (SPEC section 16 decision B, section 10).

`routine_watch.live` plays a *recording*: it loads the whole scenario before it sends
anything, so it knows every frame and every step in advance and only has to schedule
them. A camera has no such file. This module is the same session read from the other
end - one frame at a time, with nothing known about what comes next - and it yields the
messages `live.session_messages` yields, so the dashboard cannot tell which of the two
it is talking to::

    async for message in camera_session_messages(frames):
        await websocket.send_json(as_json(message))

`frames` is the capture stream: `CaptureFrame` records as `routine_watch.capture` writes
them, from a camera or from a video file, handed over as an async or a plain iterable.
The message types and the order they come in are `live`'s table, which that module
documents; the two differences are both about not knowing the future: the opening
`session_start` waits for the first record, which is where a camera session learns its
id, and a step lands a beat after the frames it was read from rather than exactly on the
last of them. `tests/test_live_camera.py` holds the two paths to the same messages over
every recorded capture stream in the repo.

**A step is sent once no later frame can take it back.** The recogniser is a batch pass
over the frames so far (`recogniser.recognise`, "a live session re-reads the frames so
far"), and reading it again a frame later can change its mind about the past: what the
rules see in a frame depends on the whole contact it belongs to - how far the object has
travelled while held, whether it ever went over the cup, how long it has been held - and
those only settle when the hand lets go. A hand resting on the kettle reads as `boil`
until the kettle is carried off, at which point the whole contact is `fill_kettle`
instead and the `boil` never happened. A step already sent cannot be unsaid, so every
step waits for the contact it was read from to end (`_settled`). That is a fraction of a
second after the resident lets go, and it is the difference between a live session and a
correct one. Which frames those are is the recogniser's own reading of what is in a hand
and for how long, so `_settled` asks it with the three helpers in `recogniser.py` that
answer the question (`_Scene`, `_scenes`, `_spans`): a copy of them here would be a
second reading of a hand on a kettle to keep in step with the rules.

**What a camera session has not got is history.** A session is only flagged against
prior sessions of the same resident, and at least three of them (SPEC section 7: a
single bad session never alerts). A live session is not attached to a resident yet, so
`session_end` carries the finished session's errors and its score with `flag: false`; a
scenario replay can flag because the scenario carries its own history in
`expected.yaml`. Attaching the resident, and with them their history and their alert,
is a follow-up.

Nothing here holds a frame. The records are landmarks, boxes and timestamps (SPEC
section 8), which is all the recogniser reads, and they are kept for the session because
every reading is of the whole session so far. That is also what `REREAD_EVERY_S` is
about: reading again on every frame of a three-minute session is minutes of work, and
twice a second of session time is near enough for a task map at a tenth of the cost.
"""

from __future__ import annotations

import asyncio
import threading
from collections.abc import AsyncIterable, AsyncIterator, Callable, Iterable, Iterator, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .contracts import CaptureFrame, StepEvent, TaskError
from .errors import classify_errors
from .live import MAX_FRAME_FPS, StepState, step_states
from .quality import session_quality
from .recogniser import FLICKER_GAP_S, _Scene, _scenes, _spans, recognise
from .replay import Expected, ReplayError, Scenario, score_session
from .tasks import TaskGraph, load_task

STAGE = "live_camera"

#: Read the frames so far again this often, in seconds of session time. Each reading is
#: over the whole session, so this is what keeps a long session cheap; a step arrives at
#: most this late, which a task map does not notice.
REREAD_EVERY_S = 0.5

#: Close code for `?source=camera` when there is no camera session to be had: no camera
#: at that index, no `capture` extra, no MediaPipe bundles, or a camera that opened and
#: saw nothing. 4000-4999 is the application's own range, and the dashboard reads any
#: close before the first message as "fall back to the recorded demo" (SPEC section 10).
CAMERA_UNAVAILABLE = 4503

#: How many records may be waiting to be read before the camera starts dropping the
#: newest ones: about two seconds at `capture.DEFAULT_FPS`. A live view is better off
#: current than complete, and the reading is of the whole session so far, so a session
#: long enough to read slowly is exactly the one that must not also fall behind.
MAX_PENDING_FRAMES = 30


async def camera_session_messages(
    frames: AsyncIterator[CaptureFrame] | Iterable[CaptureFrame], task: str = "tea"
) -> AsyncIterator[dict[str, Any]]:
    """Play a live capture stream through the pipeline as a live session.

    `frames` is the capture stream, oldest record first, as `capture.record_stream`
    numbers and times them; `task` names the task graph they are read against
    (`routine_watch.tasks.load_task`). The session ends when the stream does, which for a
    camera is the human stopping the recording.

    Raises :class:`routine_watch.tasks.TaskGraphError` on the first step if there is no
    such task, and :class:`routine_watch.replay.ReplayError` if the stream ends without
    a single record: a camera that saw nothing is not a session, which is what
    `replay.session_id_of` says about a recording with nothing in it.
    """
    graph = load_task(task)
    sent = _Sent(graph)
    records: list[CaptureFrame] = []  # the session so far: landmarks and boxes, no images
    scenes: list[_Scene] = []  # the same records as the recogniser reads them
    events: list[StepEvent] = []  # the steps sent, which is all a live session knows
    session_id = ""
    last_sent: float | None = None  # when the last frame was sent, and the last reading
    last_read: float | None = None

    def announce(event: StepEvent) -> list[dict[str, Any]]:
        """The messages one newly settled step produces: the step, then what this
        reading of the session makes of it.

        Errors are classified again after every step, unfinished (`ended=False`), just
        as in `live.session_messages`: the map flashes red mid-session without an
        unfinished task being called incomplete.
        """
        events.append(event)
        found = classify_errors(events, graph, session_id=session_id, ended=False)
        return [{"type": "step", "event": event}, *sent.reading(events, found)]

    async for frame in _streamed(frames):
        if not records:
            # A replay knows the session before it starts; a camera learns it from the
            # first record, so the opening messages wait for it - which is still before
            # anything has been read, so the client sees the same two messages first.
            session_id = frame.session_id
            yield _session_start(graph, session_id)
            for message in sent.reading(events, ()):  # the map before anything: all pending
                yield message
        records.append(frame)
        scenes += _scenes([frame])  # one scene per record: `_scenes` reads each on its own
        if last_sent is None or frame.t - last_sent >= 1.0 / MAX_FRAME_FPS - 1e-9:
            last_sent = frame.t  # `live._downsampled`'s rule, a frame at a time
            yield {"type": "frame", "frame": frame}
        if last_read is not None and frame.t - last_read < REREAD_EVERY_S:
            continue
        last_read = frame.t
        read = recognise(records, graph, session_id=session_id)
        # The settled steps are a prefix of every later reading, so the ones past the
        # steps already sent are new, in the order they happened.
        for event in _settled(read, scenes)[len(events) :]:
            for message in announce(event):
                yield message

    if not records:
        raise ReplayError("no records in the stream: a session needs at least one frame")

    # The stream is over, so nothing can change its mind any more: whatever the whole
    # recording reads as is the session, including a step it was stopped in the middle of.
    for event in recognise(records, graph, session_id=session_id)[len(events) :]:
        for message in announce(event):
            yield message

    # The task is over, which is the other half of the omission rule: a required step
    # that never happened is an error now, with nothing left that could still do it.
    final = classify_errors(events, graph, session_id=session_id, ended=True)
    for message in sent.reading(events, final):
        yield message

    score, _, flag = score_session(_as_session(graph, records, events, session_id), final, events)
    yield {
        "type": "session_end",
        # The finished session's errors, the same authoritative list `live`'s
        # `session_end` carries: the streamed ones are every reading on the way.
        "errors": final,
        "score": score,
        "flag": flag,
        "alert_id": f"alert-{session_id}" if flag else None,
        # Whether the camera saw enough of it to be scored at all (SPEC section 12): a
        # walker, a blocked view or a dim kitchen reads as `unclear`, which is the one
        # thing a live session can say about its own capture and the reason the score
        # beside it is 0.0. `live.session_messages` sends the same field off the same
        # rule, so neither path can say more about a recording than the other.
        "quality": session_quality(events),
    }


def _session_start(graph: TaskGraph, session_id: str) -> dict[str, Any]:
    """The task graph itself, sent first and once, so the dashboard draws the map this
    session ran rather than assuming it is always tea.

    `live.session_messages` builds this inline, so it is written out again here;
    `tests/test_live_camera.py` is what holds the two to the same message.
    """
    return {
        "type": "session_start",
        "session_id": session_id,
        "task_id": graph.id,
        "steps": [
            {"id": step.id, "label": step.label, "optional": step.optional}
            for step in graph.steps
        ],
    }


@dataclass
class _Sent:
    """What the client has already been told.

    The same bookkeeping as the `reading` closure in `live.session_messages`: each error
    is sent once, keyed by the `error_id` that is stable across classifications, and the
    task map is sent only when this reading of it differs from the one the client is
    drawing. It is written out here because a closure cannot be imported;
    `tests/test_live_camera.py` is what holds the two to the same messages.
    """

    graph: TaskGraph
    #: Error ids already sent. An error a nurse has seen is neither unsaid nor repeated.
    errors: set[str] = field(default_factory=set)
    #: The task map as the client last saw it.
    states: dict[str, StepState] = field(default_factory=dict)

    def reading(
        self, events: Sequence[StepEvent], errors: Sequence[TaskError]
    ) -> list[dict[str, Any]]:
        """One classification as messages: the errors that are new, then the task map if
        this reading of it differs from the client's."""
        messages: list[dict[str, Any]] = []
        for error in errors:
            if error.error_id not in self.errors:
                self.errors.add(error.error_id)
                messages.append({"type": "error", "error": error})
        now = step_states(self.graph, events, errors)
        if now != self.states:
            self.states = now
            messages.append({"type": "step_state", "states": dict(now)})
        return messages


def _settled(events: Sequence[StepEvent], scenes: Sequence[_Scene]) -> list[StepEvent]:
    """The steps read off these frames that no later frame can change: the ones it is
    safe to send.

    Always a prefix of `events`, and always a prefix of what the finished recording
    reads as, which is what makes a live camera session and a replay of the same
    recording agree.
    """
    now, mutable = scenes[-1].t, _mutable_from(scenes)
    settled: list[StepEvent] = []
    for event in events:
        # Two ways a later frame could still have a say: the run of frames this step was
        # read from is still open, because a frame close enough behind the last of them
        # carries it on (`recogniser._continues`); or a contact that was live over those
        # frames has not finished, so what the rules make of them can still change.
        if now - event.t_end <= FLICKER_GAP_S or event.t_end >= mutable:
            break
        settled.append(event)
    return settled


def _mutable_from(scenes: Sequence[_Scene]) -> float:
    """When the part of the session that can still be re-read begins, in session time.

    A contact - one unbroken run of frames with a hand on one object - is what the
    recogniser's rules read, and what they make of *any* frame of a contact depends on
    the whole of it (`recogniser._Contact`: how far the object travelled, whether it ever
    went over the cup, how long it was held). So while a contact is live, every step read
    off it is still open to question, and the answer is the start of the earliest one
    still live - or `inf` when nothing is in a hand, when the whole session so far is
    settled.
    """
    now, last = scenes[-1].t, len(scenes) - 1
    held = {label for scene in scenes for label in scene.touched}
    return min(
        (
            scenes[first].t
            for label in held
            for first, end in _spans(scenes, label)
            # Live: in a hand in the newest frame, or let go of so recently that the next
            # frame would read as the same contact rather than a new one.
            if end == last or now - scenes[end].t <= FLICKER_GAP_S
        ),
        default=float("inf"),
    )


def _as_session(
    graph: TaskGraph, records: Sequence[CaptureFrame], events: Sequence[StepEvent], name: str
) -> Scenario:
    """This session as the thing `replay.score_session` scores.

    The score is the finished session's, and it is the number a resident's baseline is
    fed (`routine_watch.scoring`), so it has to be the replay's to the last decimal -
    including the assisted-session rule, which is read off the frames (SPEC section 7).
    The history is empty: with no prior sessions there is no baseline, so nothing flags.
    """
    return Scenario(
        name=name,
        path=Path(),  # no scenario directory: these records came off a camera
        expected=Expected(task=graph.id, steps=[], errors=[], flag=False),
        graph=graph,
        frames=tuple(records),
        events=tuple(events),
    )


async def frames_in_thread(
    open_frames: Callable[[], Iterator[CaptureFrame]],
    *,
    max_pending: int = MAX_PENDING_FRAMES,
) -> AsyncIterator[CaptureFrame]:
    """A blocking capture stream as an async one, read on a thread of its own.

    `open_frames` is called once, on that thread, and must return the records as they
    are read - `capture.camera_frames` is the one that matters. Opening a camera and
    reading a frame off it both block for as long as the camera feels like, and MediaPipe
    is a tenth of a second of arithmetic per frame, so none of it can happen on the event
    loop: the API would stop answering for the length of the session. This is the seam
    between the two, and `camera_session_messages` takes what comes out of it::

        frames = frames_in_thread(lambda: camera_frames(0))
        async for message in camera_session_messages(frames):
            ...

    Whatever `open_frames` raises is raised here instead, at the record it happened on,
    so a camera that will not open reads as `CaptureError` on the first `__anext__` -
    which is how `/ws/live?source=camera` knows to close rather than stream nothing.

    **Closing this closes the camera.** The thread is asked to stop as soon as the
    consumer stops reading (the socket closing, mid-session), and the capture stream is
    closed on the thread itself, which is where the camera was opened: one frame later at
    worst, nothing is being filmed. The thread is a daemon so a camera blocked on a frame
    that never comes cannot hold the API open either.

    A consumer slower than the camera drops records rather than lagging behind it: once
    `max_pending` are waiting the newest is thrown away. The pipeline reads session time
    off the records themselves, so a gap costs a little precision and nothing else.
    """
    loop = asyncio.get_running_loop()
    queue: asyncio.Queue[CaptureFrame | BaseException | None] = asyncio.Queue()
    stop = threading.Event()

    def hand_over(item: CaptureFrame | BaseException | None) -> None:
        """One record (or the exception, or the end) over to the event loop."""
        try:
            loop.call_soon_threadsafe(queue.put_nowait, item)
        except RuntimeError:
            stop.set()  # the loop has closed: there is nobody left to read this

    def read() -> None:
        frames: Iterator[CaptureFrame] | None = None
        try:
            frames = open_frames()  # the camera is opened here, never on the event loop
            for frame in frames:
                if stop.is_set():
                    return
                if queue.qsize() < max_pending:
                    hand_over(frame)
        except BaseException as exc:  # every one of them is raised again on the far side
            hand_over(exc)
        finally:
            close = getattr(frames, "close", None)
            if close is not None:
                close()  # the camera is released here, on the thread that opened it
            hand_over(None)

    thread = threading.Thread(target=read, name="routine-watch-capture", daemon=True)
    thread.start()
    try:
        while True:
            item = await queue.get()
            if item is None:
                return  # the stream is over, which for a camera is the human stopping it
            if isinstance(item, BaseException):
                raise item
            yield item
    finally:
        stop.set()


async def _streamed(
    frames: AsyncIterator[CaptureFrame] | Iterable[CaptureFrame],
) -> AsyncIterator[CaptureFrame]:
    """The capture stream as one async iterator, however it was handed over.

    A camera reads its frames somewhere that can wait - a thread, a queue - and hands
    them over asynchronously; a recording read back off disk is a plain iterable. A sync
    stream gives the event loop a turn between frames, so the messages for one frame are
    on their way before the next is read (`live._Clock` does the same for a replay).
    """
    if isinstance(frames, AsyncIterable):
        async for frame in frames:
            yield frame
        return
    for frame in frames:
        yield frame
        await asyncio.sleep(0)
