"""Shared contracts: the data that flows between stages (SPEC sections 6, 7 and 16).

This module is the one source of truth. Running it regenerates everything else, so
the copies other languages read cannot drift:

    uv run python -m routine_watch.contracts          # write
    uv run python -m routine_watch.contracts --check  # fail if anything is stale

    contracts/<type>.schema.json      one standalone JSON Schema per top-level type
    contracts/examples/capture.jsonl  a few sample frames, for fixtures and scenarios
    web/src/contracts.ts              TypeScript types for the dashboard

Four kinds live here. `CONTRACTS` are the records that flow between the stages and
into the dashboard. `PROTOCOLS` are the messages a socket carries - the live view's
`oneOf`, an envelope around those records. `PAYLOADS` are what an HTTP route answers
with: a resident, the overview's row for one, a shift handoff, an alert in full.
`REQUESTS` are what the dashboard sends back: a nurse's feedback on an alert. The
last three get a schema but no TypeScript, because the dashboard reads the socket
and those routes through its own types.

Privacy (SPEC section 8): nothing here has a field for an image, a video frame or a
clip, and every model forbids unknown fields, so a raw frame cannot travel through a
contract even by accident. Skeletons, boxes and timestamps only.

Times inside a session (``t``, ``t_start``, ``t_end``) are seconds since the session
started, so a recording replays identically to the live camera. Wall-clock times
(``started_at``, ``created_at``) are timezone-aware datetimes.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import textwrap
from datetime import date, datetime
from enum import StrEnum
from pathlib import Path
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, RootModel, model_validator

#: Bump whenever the per-frame JSONL record changes shape. It lives here, with the
#: record it describes; `routine_watch.capture` re-exports it, because the capture
#: process is what stamps it on every frame.
FRAME_SCHEMA_VERSION = 1

#: MediaPipe pose gives exactly this many body landmarks per person.
POSE_LANDMARK_COUNT = 33

#: MediaPipe hands gives exactly this many landmarks per hand.
HAND_LANDMARK_COUNT = 21

#: A probability or score, always 0..1.
Confidence = Annotated[float, Field(ge=0.0, le=1.0)]

#: An identifier: non-empty, otherwise opaque.
Id = Annotated[str, Field(min_length=1)]


class _Contract(BaseModel):
    """Base for every shared payload: unknown fields are an error, not a free-for-all."""

    model_config = ConfigDict(extra="forbid")


# --------------------------------------------------------------------------- enums


class CaptureSource(StrEnum):
    """Where a capture frame came from. All three produce the same record."""

    CAMERA = "camera"
    VIDEO = "video"
    SYNTHETIC = "synthetic"


class Handedness(StrEnum):
    """Which hand MediaPipe thinks it is looking at."""

    LEFT = "left"
    RIGHT = "right"


class ObjectLabel(StrEnum):
    """Classes the local detector reports (SPEC section 6.1).

    Making tea first, then taking medication with water (SPEC nice-to-have 4), then
    the two classes every task shares. A task graph says which of these count for
    which step, so a new task adds classes here and a `tasks/<name>.yaml` file and
    nothing else. A class the running weights were not trained on is simply never
    reported, and `routine_watch.detector.label_for` drops a class it does not know,
    so the two lists may land one training run apart.
    """

    KETTLE = "kettle"
    CUP = "cup"
    TEABAG = "teabag"
    SPOON = "spoon"
    MILK = "milk"
    SUGAR = "sugar"
    PILL_BOTTLE = "pill_bottle"
    PILL_ORGANISER = "pill_organiser"
    GLASS = "glass"
    WATER_JUG = "water_jug"
    HAND = "hand"
    POURING = "pouring"


class StepSource(StrEnum):
    """What decided a step happened: the state rules, or the Gemini verifier."""

    RULE = "rule"
    VERIFIER = "verifier"


class ErrorType(StrEnum):
    """The everyday-action error types in SPEC section 7."""

    OMISSION = "omission"
    SEQUENCE = "sequence"
    PERSEVERATION = "perseveration"
    SUBSTITUTION = "substitution"
    HESITATION = "hesitation"
    ABANDONMENT = "abandonment"


class EvidenceKind(StrEnum):
    """What a piece of evidence points at. Never a video clip (SPEC section 8)."""

    STEP_EVENT = "step_event"
    SKELETON_REPLAY = "skeleton_replay"


class AlertKind(StrEnum):
    """How urgent the flag is: two bad sessions in 24-48 h, or a slow upward drift."""

    CHANGE_FLAG = "change_flag"
    TREND = "trend"


class BaselineMetric(StrEnum):
    """What a baseline comparison measures."""

    ERROR_SCORE = "error_score"
    ERRORS_PER_DAY = "errors_per_day"
    STEP_DURATION_S = "step_duration_s"
    STEP_GAP_S = "step_gap_s"


class SuggestedCheck(StrEnum):
    """Checks an alert may suggest to the care team (SPEC section 6.4)."""

    INFECTION_OR_UTI = "infection_or_uti"
    HYDRATION = "hydration"
    MEDICATION_REVIEW = "medication_review"
    CAM_SCREEN = "cam_screen"


class PatternUrgency(StrEnum):
    """How soon a pattern wants a human to look (SPEC section 7.5)."""

    ROUTINE = "routine"
    NEXT_ROUND = "next_round"
    SAME_SHIFT = "same_shift"
    URGENT = "urgent"


class FeedbackVerdict(StrEnum):
    """The nurse's answer to an alert, which tunes this resident's threshold."""

    CONFIRMED = "confirmed"
    FALSE_ALARM = "false_alarm"


class ResidentStatus(StrEnum):
    """The chip on a resident's overview row (SPEC section 9, screen 1): nothing to
    say, worth a look, or a change flagged for review."""

    NORMAL = "normal"
    WATCH = "watch"
    FLAGGED = "flagged"


class CareRecordKind(StrEnum):
    """A line of the care record the unit already keeps (SPEC section 6.4): the two
    readings a pattern is read against, and a medication change."""

    TEMPERATURE = "temperature"
    FLUID_INTAKE = "fluid_intake"
    MED_CHANGE = "med_change"


# ---------------------------------------------------------------------- capture


class Landmark(_Contract):
    """One MediaPipe landmark, normalised to the frame: x and y in 0..1, z relative."""

    x: float
    y: float
    z: float
    visibility: Confidence | None = Field(
        default=None, description="Pose landmarks only; hand landmarks do not report it."
    )


class Pose(_Contract):
    """One person's body skeleton."""

    landmarks: list[Landmark] = Field(
        min_length=POSE_LANDMARK_COUNT,
        max_length=POSE_LANDMARK_COUNT,
        description="The 33 MediaPipe pose landmarks, in MediaPipe's own order.",
    )
    score: Confidence | None = None


class HandLandmarks(_Contract):
    """One hand. Steps are hand-object interactions (SPEC section 16)."""

    handedness: Handedness
    score: Confidence
    landmarks: list[Landmark] = Field(
        min_length=HAND_LANDMARK_COUNT,
        max_length=HAND_LANDMARK_COUNT,
        description="The 21 MediaPipe hand landmarks, in MediaPipe's own order.",
    )


class BoundingBox(_Contract):
    """An axis-aligned box, normalised to the frame: top-left to bottom-right, 0..1."""

    x1: float = Field(ge=0.0, le=1.0)
    y1: float = Field(ge=0.0, le=1.0)
    x2: float = Field(ge=0.0, le=1.0)
    y2: float = Field(ge=0.0, le=1.0)

    @model_validator(mode="after")
    def _corners_are_ordered(self) -> BoundingBox:
        if self.x2 < self.x1 or self.y2 < self.y1:
            raise ValueError("box corners must run top-left to bottom-right")
        return self


class ObjectDetection(_Contract):
    """One object box in one frame, from the local detector (SPEC section 6.1).

    The detector always runs locally from downloaded weights, never hosted inference.
    """

    label: ObjectLabel
    confidence: Confidence
    box: BoundingBox
    track_id: Id | None = Field(
        default=None, description="Stable across frames while the tracker holds the object."
    )


class CaptureFrame(_Contract):
    """The single per-frame JSONL record (SPEC section 16).

    The live camera, the pre-recorded fallback, tests and scenarios all feed the
    pipeline through this one format. The frame itself is dropped after processing.
    """

    schema_version: int = Field(
        default=FRAME_SCHEMA_VERSION,
        ge=1,
        description="routine_watch.capture.FRAME_SCHEMA_VERSION when the record was written.",
    )
    session_id: Id
    seq: int = Field(ge=0, description="Frame counter within the session, from 0.")
    t: float = Field(ge=0.0, description="Seconds since the session started.")
    source: CaptureSource
    poses: list[Pose] = Field(
        description="One per person in frame. Two or more means somebody is assisting."
    )
    hands: list[HandLandmarks]
    objects: list[ObjectDetection]


# -------------------------------------------------------------- understand stage


class StepEvent(_Contract):
    """A step of the task, seen happening between two times (SPEC section 6.2)."""

    event_id: Id
    session_id: Id
    step_id: Id = Field(description="The step in the task graph, e.g. 'teabag_in_cup'.")
    objects: list[ObjectLabel] = Field(description="Objects the step was done with.")
    t_start: float = Field(ge=0.0)
    t_end: float = Field(ge=0.0)
    confidence: Confidence
    source: StepSource
    unclear: bool = Field(
        default=False,
        description="Low confidence and the verifier could not resolve it. Never an error.",
    )

    @model_validator(mode="after")
    def _times_are_ordered(self) -> StepEvent:
        if self.t_end < self.t_start:
            raise ValueError("t_end must not be before t_start")
        return self


class EvidenceRef(_Contract):
    """A pointer to evidence already stored: a step event, or a span of the skeleton
    replay. Never a video clip (SPEC section 8)."""

    kind: EvidenceKind
    t_start: float = Field(ge=0.0)
    t_end: float = Field(ge=0.0)
    event_id: Id | None = Field(
        default=None, description="Set when kind is step_event: the StepEvent it refers to."
    )

    @model_validator(mode="after")
    def _times_are_ordered(self) -> EvidenceRef:
        if self.t_end < self.t_start:
            raise ValueError("t_end must not be before t_start")
        return self


class TaskError(_Contract):
    """One everyday-action error found in a session (SPEC section 7)."""

    error_id: Id
    session_id: Id
    type: ErrorType
    step_id: Id | None = Field(
        default=None,
        description="The step the error is about. Null only when no single step applies.",
    )
    t_start: float = Field(ge=0.0, description="Seconds since the session started.")
    t_end: float = Field(ge=0.0)
    evidence: list[EvidenceRef]
    self_corrected: bool = Field(
        default=False,
        description="The resident fixed it straight away: a weaker signal, not a full error.",
    )

    @model_validator(mode="after")
    def _times_are_ordered(self) -> TaskError:
        if self.t_end < self.t_start:
            raise ValueError("t_end must not be before t_start")
        return self


# ------------------------------------------------------------- sessions and alerts


class Session(_Contract):
    """One attempt at one task by one resident (SPEC section 6.3)."""

    session_id: Id
    resident_id: Id
    task_id: Id = Field(description="The task graph that was being followed, e.g. 'make_tea'.")
    started_at: datetime
    ended_at: datetime | None = Field(default=None, description="Null while the session is live.")
    assisted: bool = Field(
        default=False,
        description="A second person was in frame. Excluded from the baseline.",
    )
    score: float | None = Field(
        default=None,
        ge=0.0,
        description="Weighted sum of this session's errors. Null until the session ends.",
    )

    @model_validator(mode="after")
    def _times_are_ordered(self) -> Session:
        if self.ended_at is not None and self.ended_at < self.started_at:
            raise ValueError("ended_at must not be before started_at")
        return self


class BaselineComparison(_Contract):
    """This resident's own history against what just happened (SPEC section 7)."""

    task_id: Id
    metric: BaselineMetric
    observed: float
    baseline_mean: float
    baseline_sd: float = Field(ge=0.0)
    baseline_days: int = Field(ge=0, description="Days of history the baseline is built from.")
    threshold: float = Field(description="This resident's current threshold, tuned by feedback.")


class AlertFeedback(_Contract):
    """What the care team said about an alert. Logged, and it moves the threshold."""

    verdict: FeedbackVerdict
    by: Id = Field(description="Who answered.")
    at: datetime
    note: str | None = None
    cause: Id | None = Field(
        default=None,
        description='The optional answer to "what was it?" (SPEC section 5, MVP 8): a '
        "pattern_id from the pattern library, 'other' for a cause the library has no "
        "pattern for, or null when nobody said.",
    )


class PatternMatch(_Contract):
    """One pattern a flagged change is consistent with (SPEC section 7.5).

    A flag says *something* changed; these say what kind of change it looks like, so
    the care team knows what to rule out first. Scored by deterministic rules over
    features the pipeline already has (`routine_watch.patterns`) against a library of
    patterns held as data (`routine_watch.patterns_library`), so the wording is always
    "consistent with ... - consider ruling out ...", and an empty list is a real
    answer: a change was detected with no clear pattern.
    """

    pattern_id: Id = Field(description="The pattern in the library, e.g. 'sudden_change'.")
    name: str = Field(min_length=1, description="How the pattern is shown to a nurse.")
    confidence: Confidence
    urgency: PatternUrgency
    evidence: list[str] = Field(
        description="Plain-language lines read off the features, e.g. 'omissions up to 1.0 "
        "a session from 0.0'."
    )
    checks: list[SuggestedCheck | str] = Field(
        description="What to rule out, from the library: a shared SuggestedCheck where one "
        "fits, otherwise the pattern's own wording."
    )


class Alert(_Contract):
    """A change flagged for a human to review (SPEC section 7).

    Routine Watch flags a change and shows the evidence behind it. It never diagnoses.
    """

    alert_id: Id
    resident_id: Id
    created_at: datetime
    kind: AlertKind
    session_ids: list[Id] = Field(
        min_length=1,
        description="The sessions behind the flag. A single bad session never alerts.",
    )
    errors: list[TaskError]
    baseline: BaselineComparison
    summary: str = Field(
        min_length=1,
        description="Plain language, written from the detected evidence only.",
    )
    suggested_checks: list[SuggestedCheck]
    patterns: list[PatternMatch] = Field(
        default_factory=list,
        description="The patterns this change is consistent with, best first (at most 3). "
        "Empty means a change was detected with no clear pattern.",
    )
    feedback: AlertFeedback | None = Field(
        default=None, description="Null until a nurse confirms it or calls it a false alarm."
    )


# ------------------------------------------------------ the live socket's messages


#: The states the dashboard's task map draws (`web/src/live/TaskMap.tsx`), which is
#: also `routine_watch.live.StepState`: a step is pending until it happens and done
#: once it has, with an error against it painting it red or amber (SPEC section 10).
StepStateName = Literal["pending", "done", "omission", "repeat", "sequence"]


class LiveStep(_Contract):
    """One step of the task map, as `session_start` sends it (SPEC section 10)."""

    id: Id = Field(description="The step in the task graph, e.g. 'teabag_in_cup'.")
    label: str = Field(min_length=1, description="How the step is shown to a nurse.")
    optional: bool = Field(description="A step the task does not require, e.g. sugar.")


class LiveSessionStart(_Contract):
    """Sent first and once: the task graph this session is following, so the dashboard
    draws the map the session actually ran rather than assuming it is always tea."""

    type: Literal["session_start"]
    session_id: Id
    task_id: Id = Field(description="The task graph being followed, e.g. 'make_tea'.")
    steps: list[LiveStep] = Field(description="Every step, in the task map's reading order.")


class LiveStepStates(_Contract):
    """The task map as it stands. Sent first with every step pending, and again
    whenever it changes: that is the map going red and amber mid-session (SPEC
    section 10). Always the current reading, so a step that turns out not to have been
    missing goes back to done."""

    type: Literal["step_state"]
    states: dict[Id, StepStateName] = Field(
        description="One state per step of the task, keyed by step id."
    )


class LiveFrame(_Contract):
    """One capture record for the skeleton view: landmarks, boxes and a timestamp,
    never an image (SPEC section 8). Capped at `routine_watch.live.MAX_FRAME_FPS`."""

    type: Literal["frame"]
    frame: CaptureFrame


class LiveStepEvent(_Contract):
    """One step of the task, sent once the step is over."""

    type: Literal["step"]
    event: StepEvent


class LiveTaskError(_Contract):
    """One error, sent when it is first classified and once only.

    Provisional: an unfinished session is classified again after every step, so this
    is how it read at that moment, and `session_end` carries the list the finished
    session settles on (`routine_watch.live`).
    """

    type: Literal["error"]
    error: TaskError


class LiveSessionEnd(_Contract):
    """The finished session, and the last message a session sends."""

    type: Literal["session_end"]
    errors: list[TaskError] = Field(
        description="The finished session's whole list, which is what it scored: the "
        "reading to settle on, where the error messages are every reading on the way to it."
    )
    score: float = Field(ge=0.0, description="Weighted sum of this session's errors.")
    flag: bool = Field(
        description="Whether this resident's own history, with this session now in it, "
        "flags a change for review (SPEC section 7)."
    )
    alert_id: Id | None = Field(
        description="The alert that flag shows up in, or null when nothing is flagged."
    )


class LivePaused(_Contract):
    """Monitoring is off for this resident's room (SPEC section 12), so nothing is
    being watched: the socket sends this in place of what would have come next - the
    session itself, or the rest of it when a nurse pauses mid-session - and closes."""

    type: Literal["paused"]
    room: str = Field(min_length=1, description="The room whose monitoring is paused.")


#: One message, discriminated on `type`: the schema's `oneOf`.
LiveMessageBody = Annotated[
    LiveSessionStart
    | LiveStepStates
    | LiveFrame
    | LiveStepEvent
    | LiveTaskError
    | LiveSessionEnd
    | LivePaused,
    Field(discriminator="type"),
]


class LiveMessage(RootModel[LiveMessageBody]):
    """One message on the live WebSocket (`/ws/live`, SPEC section 16 decision B).

    The live view crosses the pipeline/web boundary over this one socket, so its
    messages are a shared shape like any other: `routine_watch.live` yields the
    session's own (`session_start`, `step_state`, `frame`, `step`, `error`,
    `session_end`), `routine_watch.api` sends `paused` instead when the room's
    monitoring is off, and the dashboard reads them in
    `web/src/live/useLiveSession.ts`.

    A message is an envelope, not a record: what it carries is the contracts above,
    and nothing is stored from the socket itself.
    """


# ------------------------------------------------------ what the HTTP routes answer


class TopPattern(_Contract):
    """The pattern chip on a resident's row (SPEC section 9, screen 1).

    The best-scoring `PatternMatch` for this resident's change, cut down to what a
    row shows: what it is consistent with and how soon somebody should look.
    """

    pattern_id: Id = Field(description="The pattern in the library, e.g. 'sudden_change'.")
    name: str = Field(min_length=1, description="How the pattern is shown to a nurse.")
    urgency: PatternUrgency


class ScorePoint(_Contract):
    """One point of a resident's sparkline: a session's score, and when it ran."""

    ts: datetime = Field(description="When the session started (wall clock).")
    score: float = Field(ge=0.0, description="Weighted sum of that session's errors.")


class ErrorCounts(_Contract):
    """How many errors of each type one session had (SPEC section 7).

    One optional field per `ErrorType`: a type the session had none of is left out
    rather than sent as a zero, so `{}` is a clean session. Self-corrected slips are
    counted by `ResidentSession.self_corrected` instead, not here.
    """

    omission: int = Field(default=0, ge=0)
    sequence: int = Field(default=0, ge=0)
    perseveration: int = Field(default=0, ge=0)
    substitution: int = Field(default=0, ge=0)
    hesitation: int = Field(default=0, ge=0)
    abandonment: int = Field(default=0, ge=0)


class ResidentSession(_Contract):
    """One attempt at one task in a resident's history (`routine_watch.demo`).

    Generated history and a session played live this run are written the same way, so
    everything downstream reads both alike; the two fields only a watched session can
    fill - `session_id` and the errors the classifier really found in it - are absent
    from a generated one. Not `Session`: that is the record the pipeline stores, this
    is the row the dashboard draws a history from.
    """

    resident_id: Id
    ts: datetime = Field(description="When the session started (wall clock).")
    task: Id = Field(description="The task graph that was followed, e.g. 'tea'.")
    errors: ErrorCounts
    self_corrected: int = Field(
        ge=0, description="Slips the resident put right straight away, which score less."
    )
    duration_s: float = Field(ge=0.0, description="How long the session took.")
    assisted: bool = Field(
        default=False, description="A second person was in frame. Excluded from the baseline."
    )
    session_id: Id | None = Field(
        default=None, description="Absent on a generated session: only a watched one has an id."
    )
    error_events: list[TaskError] | None = Field(
        default=None,
        description="The errors this session really had, with their steps and times. Absent "
        "on a generated session, which only knows how many of each type there were.",
    )


class ResidentBaseline(_Contract):
    """What this resident is normally like, and the bar a session is held to.

    `mean`, `std` and `threshold` are the flag baseline (`change_detection.Baseline`)
    built from this resident's own history and nobody else's (SPEC section 7). The
    two `usual_` fields are what the live screen reads back when a session ends, taken
    over the resident's earliest days so the very change being flagged cannot quietly
    raise them (SPEC section 8, beat 6); both are absent for a resident with no early
    sessions of their own.
    """

    mean: float
    std: float = Field(ge=0.0)
    threshold: float = Field(description="Error score above which a session qualifies.")
    usual_duration_s: float | None = Field(default=None, ge=0.0)
    usual_errors: float | None = Field(default=None, ge=0.0)


class CareRecord(_Contract):
    """One line of the care record the unit already keeps (SPEC section 6.4)."""

    resident_id: Id
    ts: datetime
    kind: CareRecordKind
    value: float | str = Field(
        description="The reading for a temperature or a fluid intake; the drug for a "
        "med_change."
    )
    note: str = Field(description="Free text from whoever wrote the record. Often empty.")


class ConsentRecord(_Contract):
    """Who opted this resident in to being monitored, and when (SPEC section 12)."""

    given_by: str = Field(
        min_length=1, description="The resident themself, or a substitute decision-maker."
    )
    on: date = Field(description="The day consent was given, always before the history it covers.")


class ResidentSummary(_Contract):
    """One row of the unit overview (`GET /residents`, SPEC section 9, screen 1).

    Six fields and no history: the resident, their status chip, the pattern their
    change is consistent with and the sparkline. `routine_watch.api._SUMMARY_FIELDS`
    is this list, because the row is this much of the resident below.
    """

    id: Id
    name: str = Field(min_length=1)
    room: str = Field(min_length=1)
    status: ResidentStatus
    top_pattern: TopPattern | None = Field(
        description="Null for a normal resident, and for a change no pattern fits: an "
        "empty answer is a real one (SPEC section 7.5)."
    )
    scores: list[ScorePoint] = Field(description="One point per session, oldest first.")


class Resident(ResidentSummary):
    """One resident in full (`GET /residents/{id}`, SPEC section 9, screen 2).

    The overview's row plus everything the detail screen draws: the consent this
    monitoring rests on, every session and care record, and the baseline they are
    read against. It inherits `ResidentSummary` because the row really is this
    payload's first six fields and nothing else, which is how `/residents` builds it.
    Synthetic for now (`routine_watch.demo`) - the shape is what the dashboard is held
    to, not where the numbers come from.
    """

    consent: ConsentRecord
    sessions: list[ResidentSession] = Field(description="Every session, oldest first.")
    care_records: list[CareRecord]
    baseline: ResidentBaseline


class HandoffResident(_Contract):
    """One resident's line of the shift handoff (SPEC section 9).

    `flags` counts the sessions inside the window that scored above this resident's
    own threshold, which is the evidence a flag rests on rather than the flag itself:
    one bad session never alerts (SPEC section 7). `pending_review` counts the alerts
    raised for them that nobody has given a verdict on yet.
    """

    resident_id: Id
    name: str = Field(min_length=1)
    room: str = Field(
        min_length=1,
        description="The resident's room, so a handed-over line says where to go "
        "(SPEC section 9) and the printed or pasted handoff is usable on its own.",
    )
    flags: int = Field(ge=0, description="Sessions in the window above this resident's bar.")
    pending_review: int = Field(ge=0, description="Alerts in the window with no verdict yet.")
    trending: bool = Field(
        description="Their error score is on a slow rise. Read over their whole history, "
        "not this window: a drift takes weeks to show (SPEC section 7.5)."
    )
    monitoring_paused: bool = Field(
        description="Their room's monitoring is paused (SPEC section 12), so a quiet row "
        "means nobody was looking rather than nothing happened."
    )


class PausedRoom(_Contract):
    """A room a nurse has paused, and whose it is (SPEC section 12)."""

    room: str = Field(min_length=1)
    resident_id: Id
    name: str = Field(min_length=1)


class Handoff(_Contract):
    """The shift handoff (`GET /handoff`, SPEC section 9).

    What the nurse coming on shift missed: one row per resident for the window,
    rows worth a look first, quiet ones listed too so the unit is visibly looked at
    rather than silently skipped. `paused` is every room nobody was watching.
    """

    window_hours: int = Field(ge=1, le=168, description="How far back the window reaches.")
    residents: list[HandoffResident] = Field(
        description="Every resident, the ones needing review first."
    )
    paused: list[PausedRoom] = Field(description="Rooms whose monitoring is paused right now.")
    summary: str = Field(
        min_length=1,
        description="Plain language, written from the window's own numbers (`Explainer`).",
    )


class AlertDetail(Alert):
    """One alert as the routes answer it (`GET /alerts/{id}` and every row of `GET /alerts`).

    The stored `Alert` plus what `routine_watch.api_alerts._alert_payload` fills in on
    the way out: `feedback` is always there - null until somebody answers, never
    missing - and `baseline.threshold` is this resident's bar as the care team's
    feedback has tuned it, not the one the alert was raised against (SPEC section 5,
    MVP 7).
    Otherwise field for field the record, which is why the dashboard reads both
    through the one generated `Alert` type in `web/src/contracts.ts`. The two the
    record lets default are required here: a route sends the whole alert every time,
    so the dashboard can read an empty answer off an empty list and a missing key is
    a bug rather than "nothing to say".
    """

    patterns: list[PatternMatch] = Field(
        description="The patterns this change is consistent with, best first (at most 3). "
        "Always present: empty is the real answer for a change no pattern fits."
    )
    feedback: AlertFeedback | None = Field(
        description="What the care team said, or null when nobody has answered yet. Always "
        "present: the route reads it from the feedback store for every alert it sends."
    )


# --------------------------------------------------------- what the dashboard posts


class Feedback(_Contract):
    """The body of `POST /alerts/{id}/feedback` (SPEC section 5, MVP 7 and 8).

    One tap on the alert screen: the verdict, and optionally what the nurse thinks
    the change turned out to be. Not `AlertFeedback`: that is the record the alert
    comes back carrying, which also says who answered and when - the server stamps
    those, a client never sends them.

    `routine_watch.api_alerts.AlertFeedbackIn` is this body as FastAPI validates it
    and holds `cause` to the pattern library on top, which a schema cannot: the
    library is data that moves, this is the shape that does not.
    """

    verdict: FeedbackVerdict
    note: str | None = Field(default=None, description="Free text. Usually nobody types any.")
    cause: Id | None = Field(
        default=None,
        description='The answer to "what was it?" (SPEC section 5, MVP 8): a pattern_id from '
        "the pattern library, 'other' for a cause the library has no pattern for, or null "
        "when nobody said.",
    )


#: Every top-level contract: a JSON Schema file and a TypeScript type each.
CONTRACTS: tuple[type[_Contract], ...] = (
    CaptureFrame,
    ObjectDetection,
    StepEvent,
    TaskError,
    Session,
    Alert,
)

#: The wire protocols: a schema file each, like the contracts above, but no
#: TypeScript. A protocol is an envelope around the contracts rather than a record
#: anything stores, and the dashboard reads the live socket through its own types
#: (`web/src/live/useLiveSession.ts`), so the schema is what the two sides are held
#: to - `pipeline/tests/test_live_contract.py` validates a real session against it.
PROTOCOLS: tuple[type[BaseModel], ...] = (LiveMessage,)

#: What the dashboard's HTTP routes answer with: a schema file each, no TypeScript,
#: for the same reason as the protocols above - the dashboard mirrors these by hand
#: in `web/src/overview/types.ts` and `web/src/handoff/types.ts`, or reads them
#: through a record's own type (`AlertDetail` through `Alert`), so the schema is
#: what the two sides are held to. `pipeline/tests/test_api_payload_contracts.py`
#: validates the real routes against them.
PAYLOADS: tuple[type[BaseModel], ...] = (ResidentSummary, Resident, Handoff, AlertDetail)

#: What the dashboard sends the other way: a schema file each, no TypeScript. A
#: request body is hand-written in the client (`web/src/alert/api.ts`) and validated
#: by a FastAPI model (`routine_watch.api_alerts.AlertFeedbackIn`), so the schema is
#: the third copy both are held to.
REQUESTS: tuple[type[BaseModel], ...] = (Feedback,)

#: Everything that has a schema file in `contracts/`.
SCHEMAS: tuple[type[BaseModel], ...] = (*CONTRACTS, *PROTOCOLS, *PAYLOADS, *REQUESTS)


# ------------------------------------------------------------------- generation

_JSON_SCHEMA_DRAFT = "https://json-schema.org/draft/2020-12/schema"

#: Keep generated TypeScript inside this many columns.
_TS_WIDTH = 96

_TS_SCALARS = {
    "string": "string",
    "integer": "number",
    "number": "number",
    "boolean": "boolean",
    "null": "null",
}

_TS_HEADER = """// Generated from pipeline/src/routine_watch/contracts.py by
// `uv run python -m routine_watch.contracts`. Do not edit by hand.
//
// What flows between the pipeline stages and into the dashboard (SPEC sections 6, 7
// and 16). Skeletons, boxes and timestamps only: no raw frames anywhere.
//
// Times inside a session (t, t_start, t_end) are seconds since the session started.
// Wall-clock times (started_at, created_at) are ISO 8601 strings.
"""


def schema_name(model: type[BaseModel]) -> str:
    """``CaptureFrame`` -> ``capture_frame``, the stem of its schema file."""
    return re.sub(r"(?<!^)(?=[A-Z])", "_", model.__name__).lower()


def json_schema(model: type[BaseModel]) -> dict[str, Any]:
    """The standalone JSON Schema for one top-level contract.

    Standalone on purpose: nested types are repeated in each file's ``$defs`` so a
    validator needs no registry and no network.
    """
    return {"$schema": _JSON_SCHEMA_DRAFT, **model.model_json_schema()}


def _landmarks(count: int, drift: float, visibility: float | None) -> list[Landmark]:
    return [
        Landmark(
            x=round(0.30 + 0.004 * i + drift, 4),
            y=round(0.20 + 0.006 * i + drift, 4),
            z=round(-0.10 + 0.002 * i, 4),
            visibility=visibility,
        )
        for i in range(count)
    ]


def example_capture_frames() -> list[CaptureFrame]:
    """A few frames of somebody starting to make tea.

    Shows the shape of the record; the landmark numbers are made up, not measured.
    Fixed values and no randomness, so the sample file regenerates identically.
    """
    session = "demo-session-1"
    pose = Pose(landmarks=_landmarks(POSE_LANDMARK_COUNT, 0.0, 0.97), score=0.95)
    right_hand = HandLandmarks(
        handedness=Handedness.RIGHT,
        score=0.91,
        landmarks=_landmarks(HAND_LANDMARK_COUNT, 0.12, None),
    )
    left_hand = HandLandmarks(
        handedness=Handedness.LEFT,
        score=0.87,
        landmarks=_landmarks(HAND_LANDMARK_COUNT, 0.26, None),
    )
    kettle = ObjectDetection(
        label=ObjectLabel.KETTLE,
        confidence=0.93,
        box=BoundingBox(x1=0.56, y1=0.28, x2=0.74, y2=0.61),
        track_id="kettle-1",
    )
    cup = ObjectDetection(
        label=ObjectLabel.CUP,
        confidence=0.88,
        box=BoundingBox(x1=0.38, y1=0.44, x2=0.49, y2=0.58),
        track_id="cup-1",
    )
    teabag = ObjectDetection(
        label=ObjectLabel.TEABAG,
        confidence=0.71,
        box=BoundingBox(x1=0.41, y1=0.39, x2=0.46, y2=0.45),
        track_id="teabag-1",
    )
    hand_box = ObjectDetection(
        label=ObjectLabel.HAND,
        confidence=0.82,
        box=BoundingBox(x1=0.35, y1=0.33, x2=0.47, y2=0.47),
    )
    pouring = ObjectDetection(
        label=ObjectLabel.POURING,
        confidence=0.64,
        box=BoundingBox(x1=0.40, y1=0.30, x2=0.62, y2=0.59),
    )
    return [
        CaptureFrame(
            session_id=session,
            seq=0,
            t=0.0,
            source=CaptureSource.VIDEO,
            poses=[pose],
            hands=[],
            objects=[kettle, cup],
        ),
        CaptureFrame(
            session_id=session,
            seq=1,
            t=0.5,
            source=CaptureSource.VIDEO,
            poses=[pose],
            hands=[right_hand],
            objects=[kettle, cup, teabag, hand_box],
        ),
        CaptureFrame(
            session_id=session,
            seq=2,
            t=1.0,
            source=CaptureSource.VIDEO,
            poses=[pose],
            hands=[right_hand, left_hand],
            objects=[kettle, cup, teabag],
        ),
        CaptureFrame(
            session_id=session,
            seq=3,
            t=1.5,
            source=CaptureSource.VIDEO,
            poses=[pose],
            hands=[right_hand],
            objects=[kettle, cup, pouring],
        ),
    ]


def _ts_literal(value: Any) -> str:
    if isinstance(value, str):
        return "'" + value.replace("\\", "\\\\").replace("'", "\\'") + "'"
    return json.dumps(value)


def _ts_type(node: dict[str, Any]) -> str:
    """One JSON Schema node as a TypeScript type."""
    if "$ref" in node:
        return node["$ref"].rsplit("/", 1)[-1]
    if "allOf" in node and len(node["allOf"]) == 1:
        return _ts_type(node["allOf"][0])
    if "anyOf" in node:
        return " | ".join(dict.fromkeys(_ts_type(option) for option in node["anyOf"]))
    if "const" in node:
        return _ts_literal(node["const"])
    if "enum" in node:
        return " | ".join(_ts_literal(value) for value in node["enum"])
    if node.get("type") == "array":
        item = _ts_type(node.get("items", {}))
        return f"({item})[]" if " | " in item else f"{item}[]"
    return _TS_SCALARS.get(node.get("type"), "unknown")


def _ts_doc(node: dict[str, Any], indent: str) -> list[str]:
    """A description as a JSDoc comment, on one line where it fits."""
    text = " ".join(node.get("description", "").split())
    if not text:
        return []
    if len(indent) + len(text) + 7 <= _TS_WIDTH:
        return [f"{indent}/** {text} */"]
    body = textwrap.wrap(text, width=_TS_WIDTH - len(indent) - 3)
    return [f"{indent}/**", *(f"{indent} * {line}" for line in body), f"{indent} */"]


def _ts_block(name: str, node: dict[str, Any]) -> str:
    lines = _ts_doc(node, "")
    if "enum" in node:
        const = re.sub(r"(?<!^)(?=[A-Z])", "_", name).upper() + "_VALUES"
        values = [_ts_literal(value) for value in node["enum"]]
        one_line = f"export const {const} = [{', '.join(values)}] as const"
        if len(one_line) <= _TS_WIDTH:
            lines.append(one_line)
        else:
            lines.append(f"export const {const} = [")
            lines += [f"  {value}," for value in values]
            lines.append("] as const")
        lines.append(f"export type {name} = (typeof {const})[number]")
        return "\n".join(lines)
    if node.get("type") != "object" or "properties" not in node:
        return "\n".join([*lines, f"export type {name} = {_ts_type(node)}"])
    required = set(node.get("required", []))
    lines.append(f"export type {name} = {{")
    for field, sub in node["properties"].items():
        lines += _ts_doc(sub, "  ")
        optional = "" if field in required else "?"
        lines.append(f"  {field}{optional}: {_ts_type(sub)}")
    lines.append("}")
    return "\n".join(lines)


def typescript(models: tuple[type[BaseModel], ...] = CONTRACTS) -> str:
    """The dashboard's types, emitted from the same schemas the pipeline validates."""
    named: dict[str, dict[str, Any]] = {}

    def remember(name: str, node: dict[str, Any]) -> None:
        if named.setdefault(name, node) != node:
            raise ValueError(f"two different shapes are both called {name}")

    for model in models:
        schema = model.model_json_schema()
        for name, node in schema.pop("$defs", {}).items():
            remember(name, node)
        remember(schema["title"], schema)
    blocks = [_ts_block(name, node) for name, node in sorted(named.items())]
    return _TS_HEADER + "\n" + "\n\n".join(blocks) + "\n"


def repo_root() -> Path:
    """The monorepo root (this file is pipeline/src/routine_watch/contracts.py)."""
    return Path(__file__).resolve().parents[3]


def generated_files(root: Path | None = None) -> dict[Path, str]:
    """Every file generated from this module: path -> the exact contents it should have."""
    base = root or repo_root()
    files = {
        base / "contracts" / f"{schema_name(model)}.schema.json": json.dumps(
            json_schema(model), indent=2
        )
        + "\n"
        for model in SCHEMAS
    }
    files[base / "contracts" / "examples" / "capture.jsonl"] = "".join(
        json.dumps(frame.model_dump(mode="json")) + "\n" for frame in example_capture_frames()
    )
    files[base / "web" / "src" / "contracts.ts"] = typescript()
    return files


def stale_files(root: Path | None = None) -> list[Path]:
    """Generated files that are missing or no longer match this module."""
    return [
        path
        for path, text in generated_files(root).items()
        if not path.exists() or path.read_text(encoding="utf-8") != text
    ]


def write_files(root: Path | None = None) -> list[Path]:
    """Write every generated file, and say which ones changed."""
    changed = []
    for path, text in generated_files(root).items():
        if not path.exists() or path.read_text(encoding="utf-8") != text:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8")
            changed.append(path)
    return changed


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate the shared contract files.")
    parser.add_argument(
        "--check", action="store_true", help="only report stale files, write nothing"
    )
    parser.add_argument("--root", type=Path, default=None, help="monorepo root (default: inferred)")
    args = parser.parse_args(argv)

    paths = stale_files(args.root) if args.check else write_files(args.root)
    for path in paths:
        print(("stale: " if args.check else "wrote: ") + str(path))
    if args.check and paths:
        print("run `uv run python -m routine_watch.contracts` to regenerate", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
