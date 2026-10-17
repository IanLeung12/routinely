"""Scenario replay: the whole pipeline, offline, against a recorded capture stream.

A scenario is one directory under `tests/scenarios/`:

    <name>/frames.jsonl   capture records, the one per-frame format (SPEC section 16)
    <name>/steps.jsonl    step events, for a scenario written at step level instead
    <name>/expected.yaml  what the pipeline should make of it

Replaying one runs capture -> steps -> task graph -> errors -> session score -> change
flag with no camera, no network and no clock of its own, so the same directory always
gives the same result. That is what makes it usable as a test, and it is how the tester
checks a change end to end before anybody trusts a demo to it::

    python -m routine_watch.replay tests/scenarios/tea_normal   # print the result
    python -m routine_watch.replay --check                      # PASS/FAIL every one
    scripts/e2e.sh                                              # the same, from CI

Scenario authoring: `tests/scenarios/README.md`.

A `frames.jsonl` scenario is recognised by the real `routine_watch.recogniser.recognise`;
errors are the real `routine_watch.errors.classify_errors`, against SPEC section 7's
task graph rules. Hesitation is not folded in yet: it needs a per-step duration
baseline, and no scenario carries one.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from math import isclose
from pathlib import Path
from typing import Any, TypeVar

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from .change_detection import Baseline, build_baseline, flag_change
from .contracts import CaptureFrame, ErrorType, StepEvent, TaskError, repo_root
from .errors import classify_errors
from .recogniser import recognise
from .scoring import session_score
from .tasks import TaskGraph, TaskGraphError, load_task

STAGE = "replay"

#: Scenarios live at the repo root, beside the rest of the shared test material.
SCENARIOS_DIR = repo_root() / "tests" / "scenarios"

#: A replay has no wall clock, so prior sessions are placed `hours_ago` before this
#: fixed instant. Same scenario, same flag, whenever it runs.
REPLAY_EPOCH = datetime(2026, 1, 1, 9, 0, tzinfo=UTC)

#: Brief passers-by or stray pose detections must not suppress a session's score.
ASSISTED_MIN_S = 2.0


#: Any contract read out of a scenario file.
_Record = TypeVar("_Record", bound=BaseModel)


class ReplayError(ValueError):
    """A scenario is missing, unreadable, or not a scenario."""


# ------------------------------------------------------------------- the scenario


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
    """

    hours_ago: float = Field(ge=0.0)
    score: float | None = Field(default=None, ge=0.0)
    errors: dict[ErrorType, int] = {}
    self_corrected: int = Field(default=0, ge=0)

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
    #: Prior sessions, oldest or newest first, it makes no difference.
    history: list[HistorySession] = []


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


# ----------------------------------------------------------------------- the replay


def change_flag(
    score: float, history: Sequence[HistorySession], *, now: datetime = REPLAY_EPOCH
) -> tuple[bool, Baseline | None]:
    """Does this session, against this history, flag a change for review?

    Two rules keep this quiet (SPEC section 7): a single bad session never alerts, and
    a resident with fewer than three prior sessions has no baseline to be measured
    against at all. Returns the flag and the baseline it was judged against, if any.
    """
    scores = [session.score_value for session in history]
    if len(scores) < 3:
        return False, None
    baseline = build_baseline(scores)
    sessions = [(now - timedelta(hours=s.hours_ago), s.score_value) for s in history]
    sessions.append((now, score))
    return flag_change(sessions, baseline, now), baseline


def session_id_of(scenario: Scenario) -> str:
    """Read a session id from either input level, rejecting an empty scenario."""
    if scenario.frames:
        return scenario.frames[0].session_id
    if scenario.events:
        return scenario.events[0].session_id
    raise ReplayError(f"{scenario.path}: no frames or events")


def assisted_of(frames: Sequence[CaptureFrame], min_seconds: float = ASSISTED_MIN_S) -> bool:
    """Whether consecutive multi-person frames show sustained assistance."""
    started: float | None = None
    for frame in sorted(frames, key=lambda frame: frame.t):
        if len(frame.poses) < 2:
            started = None
            continue
        if started is None:
            started = frame.t
        if frame.t - started >= min_seconds:
            return True
    return False


def score_session(scenario: Scenario, errors: Sequence[TaskError]) -> tuple[float, bool, bool]:
    """The same finished-session verdict for offline replay and live playback."""
    # Read every frame, including ones the live stream downsamples away.
    assisted = assisted_of(scenario.frames)
    counts = Counter(str(error.type) for error in errors if not error.self_corrected)
    self_corrected = sum(1 for error in errors if error.self_corrected)
    score = session_score(counts, self_corrected, assisted)
    flag, _ = change_flag(score, scenario.expected.history)
    return score, assisted, flag


def run(scenario: Scenario) -> dict[str, Any]:
    """Run one loaded scenario through the pipeline and return the result as JSON data."""
    events = scenario.events
    session_id = session_id_of(scenario)
    errors = classify_errors(events, scenario.graph, session_id=session_id, ended=True)
    score, assisted, flag = score_session(scenario, errors)
    # Offline output also includes the baseline's display statistics.
    _, baseline = change_flag(score, scenario.expected.history)

    return {
        "scenario": scenario.name,
        "task": scenario.graph.id,
        "session_id": session_id,
        "source": scenario.source,
        "frames": len(scenario.frames),
        "steps": [event.step_id for event in events],
        "unclear": sum(1 for event in events if event.unclear),
        "assisted": assisted,
        "errors": [
            {
                "type": str(error.type),
                "step": error.step_id,
                "t_start": error.t_start,
                "t_end": error.t_end,
                "self_corrected": error.self_corrected,
            }
            for error in sorted(errors, key=lambda e: (e.t_start, str(e.type), e.step_id or ""))
        ],
        "score": score,
        "flag": flag,
        "baseline": None
        if baseline is None
        else {
            "mean": round(baseline.mean, 4),
            "std": round(baseline.std, 4),
            "threshold": round(baseline.threshold, 4),
        },
    }


def replay(path: Path | str) -> dict[str, Any]:
    """Load and run one scenario directory."""
    return run(load_scenario(path))


# ------------------------------------------------------------------ expected vs got


def compare(expected: Expected, result: Mapping[str, Any]) -> list[str]:
    """What the scenario expected against what it got. No lines means it passed."""
    diffs: list[str] = []
    if list(expected.steps) != list(result["steps"]):
        diffs.append(f"steps:    expected {_as_list(expected.steps)}")
        diffs.append(f"          got      {_as_list(result['steps'])}")

    want = Counter((str(error.type), error.step) for error in expected.errors)
    got = Counter((error["type"], error["step"]) for error in result["errors"])
    for label, difference in (("missing   ", want - got), ("unexpected", got - want)):
        if difference:
            diffs.append(f"errors:   {label} {_as_list(_named(difference))}")

    if expected.flag != result["flag"]:
        diffs.append(f"flag:     expected {_yes(expected.flag)}, got {_yes(result['flag'])}")
    if expected.score is not None and not isclose(expected.score, result["score"]):
        diffs.append(f"score:    expected {expected.score}, got {result['score']}")
    if expected.assisted is not None and expected.assisted != result["assisted"]:
        helped = _yes(result["assisted"])
        diffs.append(f"assisted: expected {_yes(expected.assisted)}, got {helped}")
    return diffs


def check(path: Path | str) -> list[str]:
    """Replay one scenario and compare it with its `expected.yaml`."""
    scenario = load_scenario(path)
    return compare(scenario.expected, run(scenario))


def _named(errors: Counter[tuple[str, str | None]]) -> list[str]:
    """``{('omission', 'boil'): 1}`` -> ``['omission/boil']``, repeats spelled out."""
    return sorted(
        f"{error_type}/{step or '-'}"
        for (error_type, step), count in errors.items()
        for _ in range(count)
    )


def _as_list(items: Sequence[str]) -> str:
    return "[" + ", ".join(items) + "]"


def _yes(value: bool) -> str:
    """``true``/``false``, the way the scenario file spells them."""
    return "true" if value else "false"


# ------------------------------------------------------------------------- the CLI


def scenario_dirs(root: Path = SCENARIOS_DIR) -> list[Path]:
    """Every scenario directory under `root`, in a stable order."""
    if not root.is_dir():
        return []
    return sorted(path for path in root.iterdir() if path.is_dir())


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m routine_watch.replay",
        description="Replay recorded scenarios through the pipeline, offline.",
    )
    parser.add_argument(
        "scenarios",
        nargs="*",
        type=Path,
        help=f"scenario directories (default: every one in {SCENARIOS_DIR})",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="compare each result with its expected.yaml: PASS/FAIL and a diff",
    )
    args = parser.parse_args(argv)

    paths = args.scenarios or scenario_dirs()
    if not paths:
        print(f"no scenarios in {SCENARIOS_DIR}", file=sys.stderr)
        return 1

    if not args.check:
        try:
            results = [replay(path) for path in paths]
        except ReplayError as exc:
            print(exc, file=sys.stderr)
            return 1
        print(json.dumps(results[0] if len(results) == 1 else results, indent=2))
        return 0

    failed = 0
    for path in paths:
        try:
            diffs = check(path)
        except ReplayError as exc:
            diffs = [f"error:    {exc}"]
        failed += bool(diffs)
        print(f"{'FAIL' if diffs else 'PASS'} {path.name}")
        for line in diffs:
            print(f"  {line}")
    print(f"{len(paths) - failed}/{len(paths)} scenarios passed")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
