"""The live session, as one WebSocket (SPEC section 16 decision B, section 10).

One socket carries the whole live view: the skeleton frames, each step as it is
recognised, the task map, the errors as they are classified and, at the end, the
session's score and whether it flags a change for a nurse to review::

    async for message in session_messages(scenario_path("tea_normal"), speed=4.0):
        ...

What it plays is a **recorded scenario**, run through the pipeline in real time rather
than as fast as the file can be read. That is the demo's fallback for a camera or a
Wi-Fi that fails (SPEC section 10), and it is why this module exists before the camera
does: live capture is the same per-frame record from a different source (SPEC section
16, "single capture stream"), so when it lands it plugs into this generator and
nothing downstream of it changes.

The messages, in the order a session produces them:

===============  ===========================================================
``session_start``  ``{session_id, task_id, steps: [{id, label, optional}]}``, the
                 task graph itself, straight from `scenario.graph`. Sent first
                 and once, so the dashboard draws the task map the session
                 actually ran rather than assuming it is always tea.
``step_state``   ``{step_id: "pending"|"done"|"omission"|"repeat"|"sequence"}``
                 for every step of the task, in the task map's reading order.
                 Sent first, all pending, and again whenever it changes: that
                 is the map going red and amber mid-session (SPEC section 10).
``frame``        One `CaptureFrame`: skeletons, hand landmarks and object
                 boxes, never an image (SPEC section 8). Capped at
                 `MAX_FRAME_FPS`, and absent altogether for a scenario
                 written at step level, which has no frames to send.
``step``         One `StepEvent`, sent when the step is over.
``error``        One `TaskError`. Errors are classified again after every step
                 (`classify_errors(..., ended=False)`), so a session flashes
                 red while it is still running; each error is sent once,
                 keyed by its `error_id`.
``session_end``  The session's `score`, whether it raised a `flag`, and the
                 `alert_id` of the resident's alert that flag shows up in.
===============  ===========================================================

Two things follow from classifying an unfinished session, and both are deliberate:

* **Errors accumulate; the task map heals.** The spec's omission rule is "a required
  step has not happened and something that depends on it is being done", so a step
  done out of order reports the dependency missing at the time, and reports the step
  itself as a sequence error once the dependency is done later. The `error` messages
  keep both, because an error already shown to a nurse is not unsaid; `step_state` is
  always the current reading, so the step that turned out not to be missing goes back
  to `done`.
* **The score is the finished session's.** `session_end` re-classifies with
  `ended=True` and scores that, which is the number the resident's baseline is fed
  (`routine_watch.scoring`), not a tally of everything that flickered on the way.

* **The finished session becomes one of the resident's.** The point of making tea on
  stage is that it counts (SPEC section 10, step 4), so the last thing a session does
  is record itself against `resident_id` - the demo resident unless the caller says
  otherwise - in `routine_watch.session_log`. From there `routine_watch.demo` merges
  it into that resident's history, which is what makes their sparkline spike and,
  when it is the second qualifying session inside the window, puts the flag and its
  alert on the next `/residents` and `/alerts`. A session that is cut short - the
  dashboard closing the socket - is never recorded, because it never finished.

**What is still the scenario's and not the camera's.** A session only flags against
prior sessions of the same resident (SPEC section 7: a single bad session never
alerts), and a scenario carries its own history in `expected.yaml`, so that is what
the `flag` in `session_end` is judged against: it is this recording's verdict, sent
the moment the session ends. The resident's own flag is a separate reading, over
their own history with this session now in it, and the dashboard gets it from
`/residents` and `/alerts` rather than from here. The frames to steps stage is
whichever one `routine_watch.replay` uses, the stub included, so a live replay and
`scripts/e2e.sh` always agree about what a recording means.
"""

from __future__ import annotations

import asyncio
import re
from collections.abc import AsyncIterator, Iterable, Sequence
from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel

from . import session_log
from .contracts import (
    BoundingBox,
    CaptureFrame,
    ErrorType,
    ObjectDetection,
    Session,
    StepEvent,
    TaskError,
)
from .demo import DEMO_NOW, DEMO_RESIDENT
from .errors import classify_errors
from .replay import SCENARIOS_DIR, ReplayError, load_scenario, score_session, session_id_of
from .tasks import TaskGraph

STAGE = "live"

#: Frames are sent no faster than this, in frames per second of session time: enough
#: for a smooth skeleton, little enough to stay ahead of a laptop's Wi-Fi.
MAX_FRAME_FPS = 10.0

#: Close code for `?scenario=` naming a scenario that is not there. 4000-4999 is the
#: application's own range, and 4404 reads the way it looks.
SCENARIO_NOT_FOUND = 4404

#: A scenario is a directory name under `tests/scenarios`, and only that: anything
#: else is "no such scenario" rather than a path to go looking down.
_SCENARIO_NAME = re.compile(r"[a-z0-9][a-z0-9_-]*")

#: The states the dashboard's task map draws (`web/src/live/TaskMap.tsx`).
StepState = Literal["pending", "done", "omission", "repeat", "sequence"]

#: Which error turns a step red or amber. Substitution, hesitation and abandonment
#: have no square of their own in the task map - the first is about the object a step
#: was done with, the other two are about time - so they arrive as `error` messages
#: and leave the map alone.
_ERROR_STATES: dict[ErrorType, StepState] = {
    ErrorType.OMISSION: "omission",
    ErrorType.PERSEVERATION: "repeat",
    ErrorType.SEQUENCE: "sequence",
}

#: Worst last: the state a step keeps when it has more than one error against it.
_SEVERITY: tuple[StepState, ...] = ("pending", "done", "sequence", "repeat", "omission")


def scenario_path(name: str, root: Path = SCENARIOS_DIR) -> Path:
    """The directory of the scenario called `name`.

    Raises :class:`routine_watch.replay.ReplayError` if there is no such scenario,
    which is also what a name that is not a bare directory name gets: `?scenario=` is
    a client's string, so it never becomes a path outside `root`.
    """
    if not _SCENARIO_NAME.fullmatch(name):
        raise ReplayError(f"{name!r} is not a scenario name")
    path = root / name
    if not path.is_dir():
        raise ReplayError(f"no scenario {name!r} in {root}")
    return path


def step_states(
    graph: TaskGraph, events: Iterable[StepEvent], errors: Iterable[TaskError]
) -> dict[str, StepState]:
    """The task map as it stands: one state per step, in the graph's reading order.

    A step with an event is `done`, and an error against it paints it red or amber
    instead. Two readings of the spec are folded in here (section 7): an `unclear`
    event is a step that may well have happened, so it shows as done rather than as a
    gap, and a slip the resident put right is not what the map is for, so a
    self-corrected error leaves the step done.
    """
    states: dict[str, StepState] = {step_id: "pending" for step_id in graph.step_ids}
    for event in events:
        states[event.step_id] = "done"
    for error in errors:
        state = _ERROR_STATES.get(error.type)
        if error.step_id is None or error.self_corrected or state is None:
            continue
        if _SEVERITY.index(state) > _SEVERITY.index(states[error.step_id]):
            states[error.step_id] = state
    return states


def as_json(message: dict[str, Any]) -> dict[str, Any]:
    """One message as JSON data, ready for `WebSocket.send_json`."""
    return {
        key: value.model_dump(mode="json") if isinstance(value, BaseModel) else value
        for key, value in message.items()
    }


async def session_messages(
    scenario_dir: Path | str, speed: float = 1.0, resident_id: str = DEMO_RESIDENT
) -> AsyncIterator[dict[str, Any]]:
    """Play one recorded scenario through the pipeline as a live session.

    `speed` is how much faster than recorded: `1.0` is the demo's pace, `1000` makes a
    test instant. `resident_id` is whose session this is: once it finishes it is one of
    theirs (`routine_watch.session_log`), and the demo resident is who makes tea on
    stage. Raises :class:`routine_watch.replay.ReplayError` on the first step if
    `scenario_dir` is not a scenario, and ``ValueError`` if `speed` is not positive.
    """
    if speed <= 0:
        raise ValueError(f"speed must be positive, not {speed}")
    scenario = load_scenario(scenario_dir)
    graph = scenario.graph
    recorded = scenario.events
    frames = scenario.frames or _synthetic_frames(recorded, session_id_of(scenario))
    session_id = session_id_of(scenario)

    seen: set[str] = set()  # error ids already sent, so each error is sent once
    states: dict[str, StepState] = {}  # the task map as the client last saw it
    events: list[StepEvent] = []  # the steps so far, which is all a live session knows

    yield {
        "type": "session_start",
        "session_id": session_id,
        "task_id": graph.id,
        "steps": [
            {"id": step.id, "label": step.label, "optional": step.optional}
            for step in graph.steps
        ],
    }

    def reading(errors: Sequence[TaskError]) -> list[dict[str, Any]]:
        """The messages one classification produces: the errors that are new, then the
        task map if this reading of it differs from the client's."""
        nonlocal states
        messages: list[dict[str, Any]] = []
        for error in errors:
            if error.error_id not in seen:
                seen.add(error.error_id)
                messages.append({"type": "error", "error": error})
        now = step_states(graph, events, errors)
        if now != states:
            states = now
            messages.append({"type": "step_state", "states": dict(now)})
        return messages

    for message in reading(()):  # the map before anything has happened: all pending
        yield message

    clock = _Clock(speed)
    for t, _, item in _beats(_downsampled(frames), recorded):
        await clock.wait_until(t)
        if isinstance(item, CaptureFrame):
            yield {"type": "frame", "frame": item}
            continue
        events.append(item)
        yield {"type": "step", "event": item}
        for message in reading(
            classify_errors(events, graph, session_id=session_id, ended=False)
        ):
            yield message

    # The task is over, which is the other half of the omission rule: a required step
    # that never happened is an error now, with nothing left that could still do it.
    final = classify_errors(events, graph, session_id=session_id, ended=True)
    for message in reading(final):
        yield message

    score, assisted, flag = score_session(scenario, final)
    _record(resident_id, session_id, graph, final, score=score, assisted=assisted, seconds=clock.t)
    yield {
        "type": "session_end",
        "score": score,
        "flag": flag,
        # The alert this session shows up in, which is the resident's own
        # (`routine_watch.alerts` builds one alert per flagged resident) rather than
        # one per session: the nurse is being told about a change in a person.
        "alert_id": f"alert-{resident_id}" if flag else None,
    }


def _record(
    resident_id: str,
    session_id: str,
    graph: TaskGraph,
    errors: Sequence[TaskError],
    *,
    score: float,
    assisted: bool,
    seconds: float,
) -> None:
    """Make the finished session one of this resident's (SPEC section 10, step 4).

    A recording has no date of its own, only seconds since it started, and the
    dashboard's clock is the demo's fixed today until a real store lands, so the
    session is placed where it belongs on that clock: ending now, having taken as long
    as it took. That is what puts it inside the 24-48 h window the flag is read over.
    """
    session_log.record(
        resident_id,
        Session(
            session_id=session_id,
            resident_id=resident_id,
            task_id=graph.id,
            started_at=DEMO_NOW - timedelta(seconds=seconds),
            ended_at=DEMO_NOW,
            assisted=assisted,
            score=score,
        ),
        errors,
    )


@dataclass
class _Clock:
    """Session time played out in wall-clock time, `speed` times as fast.

    Each wait is measured from the message before it rather than from the start of the
    session, so the work between two messages is not subtracted from the next wait: a
    session plays a touch slower than it was recorded instead of catching up in a
    rush, which is what a demo wants to look at.
    """

    speed: float
    t: float = 0.0

    async def wait_until(self, t: float) -> None:
        """Wait until the session has reached `t` seconds. Yields to the event loop
        even when there is nothing to wait for, so a fast replay still sends."""
        delay = max(t - self.t, 0.0) / self.speed
        self.t = max(self.t, t)
        await asyncio.sleep(delay)


def _beats(
    frames: Sequence[CaptureFrame], events: Sequence[StepEvent]
) -> list[tuple[float, int, CaptureFrame | StepEvent]]:
    """Every moment the session has something to send, in the order it reaches them.

    A frame is sent at its own `t`; a step event once the step is over, at its `t_end`,
    because that is when a recogniser reading frames could know about it. The frame
    comes first where the two land on the same instant - the step is read off frames
    including that one.
    """
    beats: list[tuple[float, int, CaptureFrame | StepEvent]] = [
        (frame.t, 0, frame) for frame in frames
    ]
    beats += [(event.t_end, 1, event) for event in events]
    beats.sort(key=lambda beat: beat[:2])  # stable: never compares two records
    return beats


#: Fixed, made-up positions for the skeleton view when a scenario is written at step
#: level and has no real capture frames to show (SPEC section 8: boxes only, never
#: video, so these are as good as real ones for the dashboard's purposes).
_PLACEHOLDER_BOXES: dict[str, BoundingBox] = {
    "cup": BoundingBox(x1=0.05, y1=0.75, x2=0.15, y2=0.87),
    "kettle": BoundingBox(x1=0.66, y1=0.26, x2=0.84, y2=0.54),
    "teabag": BoundingBox(x1=0.16, y1=0.3, x2=0.23, y2=0.37),
    "spoon": BoundingBox(x1=0.22, y1=0.6, x2=0.38, y2=0.66),
    "milk": BoundingBox(x1=0.86, y1=0.6, x2=0.96, y2=0.72),
    "sugar": BoundingBox(x1=0.86, y1=0.3, x2=0.96, y2=0.42),
}


def _synthetic_frames(events: Sequence[StepEvent], session_id: str) -> list[CaptureFrame]:
    """One made-up frame per step event, for a scenario written at step level (no
    `frames.jsonl`) so the skeleton view still has something to show (SPEC section 10,
    step 3) rather than staying on "waiting for camera" the whole session."""
    frames: list[CaptureFrame] = []
    for seq, event in enumerate(events):
        objects = [
            ObjectDetection(label=label, confidence=1.0, box=box)
            for label in event.objects
            if (box := _PLACEHOLDER_BOXES.get(str(label))) is not None
        ]
        frames.append(
            CaptureFrame(
                session_id=session_id,
                seq=seq,
                t=(event.t_start + event.t_end) / 2.0,
                source="synthetic",
                poses=[],
                hands=[],
                objects=objects,
            )
        )
    return frames


def _downsampled(
    frames: Sequence[CaptureFrame], max_fps: float = MAX_FRAME_FPS
) -> list[CaptureFrame]:
    """The frames worth sending: the first, then one every `1 / max_fps` seconds of
    session time. A recording slower than that is sent whole."""
    gap = 1.0 / max_fps
    kept: list[CaptureFrame] = []
    last: float | None = None
    for frame in sorted(frames, key=lambda frame: (frame.seq, frame.t)):
        if last is None or frame.t - last >= gap - 1e-9:
            kept.append(frame)
            last = frame.t
    return kept
