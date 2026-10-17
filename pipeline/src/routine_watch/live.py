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
                 `MAX_FRAME_FPS`; a scenario written at step level has no
                 recorded frames, so it is sent made-up ones that move the
                 way a recording would (`_synthetic_frames`).
``step``         One `StepEvent`, sent when the step is over.
``error``        One `TaskError`. Errors are classified again after every step
                 (`classify_errors(..., ended=False)`), so a session flashes
                 red while it is still running; each error is sent once,
                 keyed by its `error_id`.
``session_end``  The session's `errors`, its `score`, whether the resident is
                 `flag`ged now that this session is one of theirs, the
                 `alert_id` of the alert that flag shows up in, and the
                 `quality` of the capture it was all read off. `errors` is the
                 finished session's whole list,
                 each `TaskError` serialised the way the `error` message's is:
                 the list to settle on once the session is over, which the
                 `error` messages above are every reading on the way to.
===============  ===========================================================

Two things follow from classifying an unfinished session, and both are deliberate:

* **Errors accumulate; the task map heals.** The spec's omission rule is "a required
  step has not happened and something that depends on it is being done", so a step
  done out of order reports the dependency missing at the time, and reports the step
  itself as a sequence error once the dependency is done later. The `error` messages
  keep both, because an error already shown to a nurse is not unsaid; `step_state` is
  always the current reading, so the step that turned out not to be missing goes back
  to `done`.
* **The end is the finished session's.** `session_end` re-classifies with
  `ended=True`, and that list is both its `errors` and what it scores: the number the
  resident's baseline is fed (`routine_watch.scoring`), not a tally of everything that
  flickered on the way. So a streamed `error` is **provisional** - what the session
  looked like at that moment - and `session_end.errors` is authoritative: the same
  errors `routine_watch.replay` (and so `scripts/e2e.sh`) ends on, which is what lets
  a screen that has been showing the stream settle on the right answer.

* **The finished session becomes one of the resident's.** The point of making tea on
  stage is that it counts (SPEC section 10, step 4), so the last thing a session does
  is record itself against `resident_id` - the demo resident unless the caller says
  otherwise - in `routine_watch.session_log`. From there `routine_watch.demo` merges
  it into that resident's history, which is what makes their sparkline spike and,
  when it is the second qualifying session inside the window, puts the flag and its
  alert on the next `/residents` and `/alerts`. A session that is cut short - the
  dashboard closing the socket - is never recorded, because it never finished, and
  nor is an **unclear** one (`routine_watch.quality`, SPEC section 12): too little of
  the capture can be trusted to make it one of this resident's sessions, so it is
  streamed and scored 0.0 like any session the pipeline cannot read, and then left
  out of their history rather than counted toward a flag. `session_end` carries which
  of the two it was in `quality`, because the score alone cannot say: 0.0 is "nothing
  went wrong" for a clean session and "we could not read it" for an unclear one, and
  the screen has to tell a nurse which (SPEC section 12, "show uncertainty").

**The `flag` is the resident's, not the recording's.** A session only flags against
prior sessions of the same resident (SPEC section 7: a single bad session never
alerts), and there are two histories it could be read over. A scenario carries its own
in `expected.yaml`, which is the recording's verdict and what `routine_watch.replay`
(and so `scripts/e2e.sh`) checks it against; the resident has theirs, with this session
now in it, which is the reading `/residents` and `/alerts` give a nurse. `session_end`
sends the second (`_resident_flagged`), because the live screen sits next to the
dashboard: a flag here means that resident's row has gone red, and `alert_id` names an
alert `/alerts` actually has, so "View alert" opens something (T236 - judging the
scenario's history instead said "flagged" with nothing to open, and said nothing was
flagged while her row was red). The `score` stays the recording's, to the decimal
`routine_watch.replay` scores it: that is the number the resident's baseline is fed, and
the frames to steps stage is whichever one `replay` uses, the stub included, so a live
replay and `scripts/e2e.sh` always agree about what a recording means.
`routine_watch.live_camera` has no resident to read a history over at all, so a camera
session's `flag` is false until one is attached.
"""

from __future__ import annotations

import asyncio
import re
from collections.abc import AsyncIterator, Iterable, Sequence
from dataclasses import dataclass
from datetime import timedelta
from itertools import pairwise
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel

from . import session_log
from .contracts import (
    BoundingBox,
    CaptureFrame,
    ErrorType,
    ObjectDetection,
    ObjectLabel,
    Session,
    StepEvent,
    TaskError,
)
from .demo import DEMO_NOW, DEMO_RESIDENT, demo_residents
from .errors import classify_errors
from .notify import Notifier, get_notifier
from .quality import session_quality
from .replay import SCENARIOS_DIR, ReplayError, load_scenario, score_session, session_id_of
from .stick_figure import HAND_SPAN, REST, Point, centre_of, reaching_for
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
    """One message as JSON data, ready for `WebSocket.send_json`.

    A message's values are contracts (`error`), lists of them (`session_end`'s
    `errors`) or JSON already (`score`, `states`), so only the contracts are dumped.
    """
    return {key: _as_json(value) for key, value in message.items()}


def _as_json(value: Any) -> Any:
    """One message value as JSON data: a contract dumped, a list of them dumped
    item by item, anything else left as it is."""
    if isinstance(value, BaseModel):
        return value.model_dump(mode="json")
    if isinstance(value, list):
        return [_as_json(item) for item in value]
    return value


async def session_messages(
    scenario_dir: Path | str,
    speed: float = 1.0,
    resident_id: str = DEMO_RESIDENT,
    notifier: Notifier | None = None,
) -> AsyncIterator[dict[str, Any]]:
    """Play one recorded scenario through the pipeline as a live session.

    `speed` is how much faster than recorded: `1.0` is the demo's pace, `1000` makes a
    test instant. `resident_id` is whose session this is: once it finishes it is one of
    theirs (`routine_watch.session_log`), and the demo resident is who makes tea on
    stage. Raises :class:`routine_watch.replay.ReplayError` on the first step if
    `scenario_dir` is not a scenario, and ``ValueError`` if `speed` is not positive.

    `notifier` is the seam tests use in place of `routine_watch.notify.get_notifier()`'s
    default: if this session's end flips `resident_id` from not-flagged to flagged
    (SPEC Nice-to-have 3), one push alert goes out through it, never more than once per
    session and never for a session that leaves the resident flagged already or still
    not flagged.
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

    was_flagged = _resident_flagged(resident_id)
    score, assisted, _recording_flag = score_session(scenario, final, events)
    # An unclear session is nobody's history: there is nothing in it to trust about
    # this resident (SPEC section 12), which is why `replay.score_session` neither
    # scores nor flags it. Recording it anyway would have it counted all the same -
    # `routine_watch.demo` scores a recorded session from its errors again and only
    # leaves out assisted ones - so its errors would sit in the 24-48 h window the
    # flag is read over and bad lighting alone could flag a change for review.
    quality = session_quality(events)
    if quality == "ok":
        _record(
            resident_id, session_id, graph, final, score=score, assisted=assisted, seconds=clock.t
        )
    # One reading of the resident, taken once this session is one of theirs: it is both
    # what a push alert goes out for and what `session_end` reports, so the live screen
    # cannot say anything the dashboard does not (see "the `flag` is the resident's").
    resident_name = _resident_flagged(resident_id)
    if not was_flagged and resident_name:
        (notifier or get_notifier()).send(
            {
                "alert_id": f"alert-{resident_id}",
                "resident_id": resident_id,
                "summary": f"A session just flagged a change for {resident_name} to review.",
                "created_at": DEMO_NOW,
            }
        )
    yield {
        "type": "session_end",
        # The finished session's errors, which is the list to show once it is over:
        # the `error` messages are every reading this session went through, this is
        # the reading it ended on (see "the end is the finished session's" above).
        "errors": final,
        "score": score,
        # Whether this resident is flagged now, over their own history (SPEC section 7),
        # which is the flag `/residents` shows: this session's own verdict against the
        # scenario's history is `routine_watch.replay`'s business, not a nurse's.
        "flag": resident_name is not None,
        # The alert that flag shows up in, which is the resident's own
        # (`routine_watch.alerts` builds one alert per flagged resident) rather than
        # one per session: the nurse is being told about a change in a person. Not
        # flagged, no alert - `/alerts` would 404 on one.
        "alert_id": f"alert-{resident_id}" if resident_name else None,
        # Whether the capture could be read well enough to score this session at all
        # (SPEC section 12). `unclear` is the walker, the blocked view, the bad light:
        # the score above is 0.0 because nothing in the capture can be trusted, not
        # because the session went well, and the live screen says which it was.
        "quality": quality,
    }


def _resident_flagged(resident_id: str) -> str | None:
    """The resident's display name if flagged right now (SPEC section 7: over their own
    history, the same reading `/residents` and `/alerts` give a nurse), so a push
    alert goes out exactly when a session's end turns this from absent to present."""
    resident = next(
        (resident for resident in demo_residents() if resident["id"] == resident_id), None
    )
    return resident["name"] if resident and resident["status"] == "flagged" else None


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
#: video, so these are as good as real ones for the dashboard's purposes). Both tasks'
#: objects, because the live view plays either routine (`web/src/live/LiveScreen.tsx`).
_PLACEHOLDER_BOXES: dict[str, BoundingBox] = {
    "cup": BoundingBox(x1=0.05, y1=0.75, x2=0.15, y2=0.87),
    "kettle": BoundingBox(x1=0.66, y1=0.26, x2=0.84, y2=0.54),
    "teabag": BoundingBox(x1=0.16, y1=0.3, x2=0.23, y2=0.37),
    "spoon": BoundingBox(x1=0.22, y1=0.6, x2=0.38, y2=0.66),
    "milk": BoundingBox(x1=0.86, y1=0.6, x2=0.96, y2=0.72),
    "sugar": BoundingBox(x1=0.86, y1=0.3, x2=0.96, y2=0.42),
    "glass": BoundingBox(x1=0.06, y1=0.74, x2=0.17, y2=0.88),
    "water_jug": BoundingBox(x1=0.62, y1=0.22, x2=0.82, y2=0.52),
    "pill_organiser": BoundingBox(x1=0.2, y1=0.28, x2=0.36, y2=0.4),
    "pill_bottle": BoundingBox(x1=0.86, y1=0.28, x2=0.95, y2=0.46),
}

#: How often a scenario written at step level gets a made-up frame, in frames per
#: second of session time: the rate the frame-level recordings were written at
#: (`tests/scenarios/tea_normal`), which is fast enough for the stand-in figure to
#: move and slow enough to keep the socket light.
SYNTHETIC_FPS = 2.0


def _synthetic_frames(events: Sequence[StepEvent], session_id: str) -> list[CaptureFrame]:
    """Made-up frames for a scenario written at step level (no `frames.jsonl`), so the
    skeleton view has something to show (SPEC section 10, step 3) rather than staying
    on "waiting for camera" the whole session.

    One frame every `1 / SYNTHETIC_FPS` seconds, from the start of the session to the
    end of its last step. Each carries the objects this session's steps are done with,
    where `_PLACEHOLDER_BOXES` puts them, and a stand-in figure
    (`routine_watch.stick_figure`) whose hand travels to the object of the step being
    done and back to its rest spot in between: a recording of nobody, shaped like a
    recording of somebody, which is what the skeleton view knows how to draw.
    """
    if not events:
        return []
    steps = sorted(events, key=lambda event: (event.t_start, event.t_end))
    objects = [
        ObjectDetection(label=label, confidence=1.0, box=box)
        for label in dict.fromkeys(label for step in steps for label in step.objects)
        if (box := _PLACEHOLDER_BOXES.get(str(label))) is not None
    ]
    track = _hand_track(steps)
    frames: list[CaptureFrame] = []
    for seq, t in enumerate(_ticks(steps[-1].t_end)):
        point = _hand_at(track, t)
        pose, hand = reaching_for(point)
        frames.append(
            CaptureFrame(
                session_id=session_id,
                seq=seq,
                t=t,
                source="synthetic",
                poses=[pose],
                hands=[hand],
                objects=[*objects, _hand_box(point)],
            )
        )
    return frames


def _ticks(end: float) -> list[float]:
    """Every moment a made-up frame is written for: 0 to `end`, `SYNTHETIC_FPS` apart."""
    gap = 1.0 / SYNTHETIC_FPS
    return [index * gap for index in range(int(end / gap) + 1)]


def _hand_track(steps: Sequence[StepEvent]) -> list[tuple[Point, float]]:
    """Where the stand-in hand is through the session, as (point, t) keyframes.

    At rest until the first step, on the object that step is done with from its start
    to its end, then back at rest halfway through the gap to the next step. Steps that
    overlap in time just leave their keyframes in time order, which is all the track
    is read in.
    """
    track: list[tuple[Point, float]] = [(REST, 0.0)]
    for index, step in enumerate(steps):
        point = _step_anchor(step)
        track.append((point, step.t_start))
        track.append((point, step.t_end))
        following = steps[index + 1] if index + 1 < len(steps) else None
        if following is not None and following.t_start > step.t_end:
            track.append((REST, (step.t_end + following.t_start) / 2.0))
    track.sort(key=lambda keyframe: keyframe[1])
    return track


def _step_anchor(step: StepEvent) -> Point:
    """Where the hand goes for this step: the first of its objects that is on the
    counter, or the rest spot for a step done with nothing `_PLACEHOLDER_BOXES` knows.

    A step event lists the object that was in the hand first (both the recogniser's
    rules and the hand-written `steps.jsonl` files do), so that is the one to reach
    for: the kettle of a pour rather than the cup it is poured into.
    """
    for label in step.objects:
        box = _PLACEHOLDER_BOXES.get(str(label))
        if box is not None:
            return centre_of(box)
    return REST


def _hand_at(track: Sequence[tuple[Point, float]], t: float) -> Point:
    """The hand's place at `t`: evenly between the keyframes on either side of it."""
    for (start, t0), (end, t1) in pairwise(track):
        if t <= t1:
            if t1 <= t0:
                return end
            share = min(1.0, max(0.0, (t - t0) / (t1 - t0)))
            return (
                start[0] + share * (end[0] - start[0]),
                start[1] + share * (end[1] - start[1]),
            )
    return track[-1][0]


def _hand_box(point: Point, span: float = HAND_SPAN) -> ObjectDetection:
    """The hand as the detector would have reported it: a box around the landmarks the
    figure's hand is drawn from, the way the frame-level recordings carry one."""
    x, y = point
    half = span / 2.0
    return ObjectDetection(
        label=ObjectLabel.HAND,
        confidence=1.0,
        box=BoundingBox(
            x1=max(0.0, x - half),
            y1=max(0.0, y - half),
            x2=min(1.0, x + half),
            y2=min(1.0, y + half),
        ),
    )


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
