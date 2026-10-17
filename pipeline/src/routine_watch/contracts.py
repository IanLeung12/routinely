"""Shared contracts: the data that flows between stages (SPEC sections 6, 7 and 16).

This module is the one source of truth. Running it regenerates everything else, so
the copies other languages read cannot drift:

    uv run python -m routine_watch.contracts          # write
    uv run python -m routine_watch.contracts --check  # fail if anything is stale

    contracts/<type>.schema.json      one standalone JSON Schema per top-level type
    contracts/examples/capture.jsonl  a few sample frames, for fixtures and scenarios
    web/src/contracts.ts              TypeScript types for the dashboard

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
from datetime import datetime
from enum import StrEnum
from pathlib import Path
from typing import Annotated, Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

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


class FeedbackVerdict(StrEnum):
    """The nurse's answer to an alert, which tunes this resident's threshold."""

    CONFIRMED = "confirmed"
    FALSE_ALARM = "false_alarm"


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
    feedback: AlertFeedback | None = Field(
        default=None, description="Null until a nurse confirms it or calls it a false alarm."
    )


#: Every top-level contract, one JSON Schema file each.
CONTRACTS: tuple[type[_Contract], ...] = (
    CaptureFrame,
    ObjectDetection,
    StepEvent,
    TaskError,
    Session,
    Alert,
)


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
        for model in CONTRACTS
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
