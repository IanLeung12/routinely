"""The scenario file format: `tests/scenarios/<name>/` as pydantic models.

A scenario is one directory under `tests/scenarios/`:

    <name>/frames.jsonl   capture records, the one per-frame format (SPEC section 16)
    <name>/steps.jsonl    step events, for a scenario written at step level instead
    <name>/expected.yaml  what the pipeline should make of it

This module only reads a scenario directory into a :class:`Scenario`. Running and
comparing it against its `expected.yaml` is `routine_watch.replay`'s job.

Scenario authoring: `tests/scenarios/README.md`.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TypeVar

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from .contracts import CaptureFrame, ErrorType, StepEvent, repo_root
from .patterns_library import BY_ID
from .quality import Quality
from .recogniser import recognise
from .scoring import session_score
from .tasks import TaskGraph, TaskGraphError, load_task

#: Scenarios live at the repo root, beside the rest of the shared test material.
SCENARIOS_DIR = repo_root() / "tests" / "scenarios"

#: `top_pattern`'s value when a scenario expects no pattern to clear the threshold.
NO_PATTERN = "none"


#: Any contract read out of a scenario file.
_Record = TypeVar("_Record", bound=BaseModel)


class ReplayError(ValueError):
    """A scenario is missing, unreadable, or not a scenario."""


class _Strict(BaseModel):
    """A typo in a scenario file is a failure, not a silently ignored key."""

    model_config = ConfigDict(extra="forbid")


class ExpectedError(_Strict):
    """One error the scenario expects. `step` is null when no single step applies."""

    type: ErrorType
    step: str | None = None


class HistorySession(_Strict):
    """A prior session of this resident, `hours_ago` before the replayed one.

    History is what gives the resident a baseline to be measured against, so it is
    what lets a scenario expect `flag: true`. Give a session a `score`, or give the
    `errors` it held and let the scoring weights work it out.

    `duration_s` is optional: set it on this session and on `Expected.duration_s` to
    give a scenario a `duration_ratio` (SPEC §7.5), for example ~10 history sessions
    at 300s and a replayed session at 450s to reach `motor_slowing`. Leave it unset
    and `duration_ratio` stays `None`, exactly as before.
    """

    hours_ago: float = Field(ge=0.0)
    score: float | None = Field(default=None, ge=0.0)
    errors: dict[ErrorType, int] = {}
    self_corrected: int = Field(default=0, ge=0)
    duration_s: float | None = Field(default=None, gt=0.0)

    @model_validator(mode="after")
    def _scored_one_way(self) -> HistorySession:
        if self.score is not None and (self.errors or self.self_corrected):
            raise ValueError("a history session has a score or its errors, not both")
        return self

    @property
    def score_value(self) -> float:
        """This session's score, however the scenario chose to write it down."""
        if self.score is not None:
            return self.score
        counts = {str(error_type): count for error_type, count in self.errors.items()}
        return session_score(counts, self.self_corrected)


class Expected(_Strict):
    """`expected.yaml`: the outcome half of a scenario."""

    #: The task graph to replay against: the stem of a `tasks/<name>.yaml` file.
    task: str = "tea"
    #: Every step event, in order, including any marked `unclear`.
    steps: list[str]
    #: Every error, in no particular order.
    errors: list[ExpectedError]
    #: Whether these errors, against this history, flag a change for review.
    flag: bool
    #: Optional extra assertions, checked only when the file sets them.
    score: float | None = None
    assisted: bool | None = None
    #: Whether the session was clean enough to score, or too thin/low-confidence to
    #: trust (SPEC §12). Unset scenarios are unaffected.
    quality: Quality | None = None
    #: Which pattern (SPEC §7.5) the session should score highest, or `"none"` if the
    #: flag is expected to match no pattern. Unset scenarios are unaffected.
    top_pattern: str | None = None
    #: This session's duration, in seconds. Optional: set it alongside a `duration_s`
    #: on each `HistorySession` to give the scenario a `duration_ratio` (SPEC §7.5).
    #: Left unset, `duration_ratio` stays `None`, exactly as before.
    duration_s: float | None = Field(default=None, gt=0.0)
    #: Prior sessions, oldest or newest first, it makes no difference.
    history: list[HistorySession] = []

    @model_validator(mode="after")
    def _known_pattern(self) -> Expected:
        if self.top_pattern is not None and self.top_pattern != NO_PATTERN:
            if self.top_pattern not in BY_ID:
                raise ValueError(f"top_pattern: unknown pattern {self.top_pattern!r}")
        return self


@dataclass(frozen=True)
class Scenario:
    """One loaded scenario directory, ready to run."""

    name: str
    path: Path
    expected: Expected
    graph: TaskGraph
    #: Capture records, empty when the scenario is written at step level.
    frames: tuple[CaptureFrame, ...]
    #: Step events, either read from `steps.jsonl` or recognised from the frames.
    events: tuple[StepEvent, ...]

    @property
    def source(self) -> str:
        """Which level the scenario was written at: ``frames`` or ``steps``."""
        return "frames" if self.frames else "steps"


def load_scenario(path: Path | str) -> Scenario:
    """Read one scenario directory. Raises :class:`ReplayError` if it is not one."""
    path = Path(path)
    if not path.is_dir():
        raise ReplayError(f"{path} is not a scenario directory")

    expected_path = path / "expected.yaml"
    if not expected_path.is_file():
        raise ReplayError(f"{path}: no expected.yaml")
    try:
        expected = Expected.model_validate(yaml.safe_load(expected_path.read_text("utf-8")))
    except (ValidationError, yaml.YAMLError) as exc:
        raise ReplayError(f"{expected_path}: {exc}") from exc

    try:
        graph = load_task(expected.task)
    except TaskGraphError as exc:
        raise ReplayError(f"{expected_path}: {exc}") from exc

    frames_path, steps_path = path / "frames.jsonl", path / "steps.jsonl"
    if frames_path.is_file() == steps_path.is_file():
        raise ReplayError(f"{path}: needs exactly one of frames.jsonl or steps.jsonl")
    if frames_path.is_file():
        frames = tuple(_load_jsonl(frames_path, CaptureFrame))
        events = tuple(recognise(frames, graph, session_id=frames[0].session_id))
    else:
        frames, events = (), tuple(_load_jsonl(steps_path, StepEvent))

    return Scenario(
        name=path.name, path=path, expected=expected, graph=graph, frames=frames, events=events
    )


def _load_jsonl(path: Path, model: type[_Record]) -> list[_Record]:
    """Every line of a JSONL file as `model`, with the line number in any complaint."""
    records: list[_Record] = []
    for number, line in enumerate(path.read_text("utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            records.append(model.model_validate_json(line))
        except ValidationError as exc:
            raise ReplayError(f"{path}:{number}: {exc}") from exc
    if not records:
        raise ReplayError(f"{path}: no records")
    return records


def scenario_dirs(root: Path = SCENARIOS_DIR) -> list[Path]:
    """Every scenario directory under `root`, in a stable order."""
    if not root.is_dir():
        return []
    return sorted(path for path in root.iterdir() if path.is_dir())
