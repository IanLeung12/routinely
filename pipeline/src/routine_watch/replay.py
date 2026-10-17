"""Scenario replay: the whole pipeline, offline, against a recorded capture stream.

Replaying a scenario (`routine_watch.scenario`) runs capture -> steps -> task graph ->
errors -> session score -> change flag with no camera, no network and no clock of its
own, so the same directory always gives the same result. That is what makes it usable
as a test, and it is how the tester checks a change end to end before anybody trusts a
demo to it::

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
from datetime import UTC, datetime, timedelta
from math import isclose
from pathlib import Path
from typing import Any

from .change_detection import Baseline, build_baseline, flag_change
from .contracts import CaptureFrame, StepEvent, TaskError
from .errors import classify_errors
from .patterns import extract_features, score_patterns
from .quality import session_quality
from .scenario import (
    NO_PATTERN,
    SCENARIOS_DIR,
    Expected,
    ExpectedError,
    HistorySession,
    ReplayError,
    Scenario,
    _load_jsonl,
    _Strict,
    load_scenario,
    scenario_dirs,
)
from .scoring import session_score

#: Re-exported for every existing `from .replay import ...`: the scenario file format
#: now lives in `routine_watch.scenario`, this module only runs it.
__all__ = ["ExpectedError", "_Strict", "_load_jsonl"]

STAGE = "replay"

#: A replay has no wall clock, so prior sessions are placed `hours_ago` before this
#: fixed instant. Same scenario, same flag, whenever it runs.
REPLAY_EPOCH = datetime(2026, 1, 1, 9, 0, tzinfo=UTC)

#: Brief passers-by or stray pose detections must not suppress a session's score.
ASSISTED_MIN_S = 2.0


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


def score_session(
    scenario: Scenario, errors: Sequence[TaskError], events: Sequence[StepEvent]
) -> tuple[float, bool, bool]:
    """The same finished-session verdict for offline replay and live playback.

    An unclear session (SPEC §12: too thin, or too much of it low-confidence) is never
    scored or flagged - the same treatment as an assisted one - because the capture
    itself cannot be trusted, not the resident's performance.
    """
    # Read every frame, including ones the live stream downsamples away.
    assisted = assisted_of(scenario.frames)
    if session_quality(events) == "unclear":
        return 0.0, assisted, False
    counts = Counter(str(error.type) for error in errors if not error.self_corrected)
    self_corrected = sum(1 for error in errors if error.self_corrected)
    score = session_score(counts, self_corrected, assisted)
    flag, _ = change_flag(score, scenario.expected.history)
    return score, assisted, flag


def top_pattern_of(
    history: Sequence[HistorySession],
    baseline: Baseline | None,
    errors: Sequence[TaskError],
    assisted: bool,
    *,
    duration_s: float | None = None,
    now: datetime = REPLAY_EPOCH,
) -> str:
    """The best-scoring pattern (SPEC §7.5) this session, against this history, is

    consistent with - or `NO_PATTERN` when nothing clears the threshold, or there is
    no baseline to measure a change against at all.
    """
    if baseline is None:
        return NO_PATTERN
    counts = Counter(str(error.type) for error in errors if not error.self_corrected)
    self_corrected = sum(1 for error in errors if error.self_corrected)
    sessions = [
        {
            "ts": (now - timedelta(hours=session.hours_ago)).isoformat(),
            "errors": {str(error_type): count for error_type, count in session.errors.items()},
            "self_corrected": session.self_corrected,
            "duration_s": session.duration_s,
        }
        for session in history
    ]
    sessions.append(
        {
            "ts": now.isoformat(),
            "errors": dict(counts),
            "self_corrected": self_corrected,
            "assisted": assisted,
            "duration_s": duration_s,
        }
    )
    features = extract_features(sessions, baseline, [], now=now)
    matches = score_patterns(features)
    return matches[0].pattern_id if matches else NO_PATTERN


def run(scenario: Scenario) -> dict[str, Any]:
    """Run one loaded scenario through the pipeline and return the result as JSON data."""
    events = scenario.events
    session_id = session_id_of(scenario)
    errors = classify_errors(events, scenario.graph, session_id=session_id, ended=True)
    score, assisted, flag = score_session(scenario, errors, events)
    # Offline output also includes the baseline's display statistics.
    _, baseline = change_flag(score, scenario.expected.history)
    top_pattern = top_pattern_of(
        scenario.expected.history,
        baseline,
        errors,
        assisted,
        duration_s=scenario.expected.duration_s,
    )

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
        "quality": session_quality(events),
        "top_pattern": top_pattern,
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
    if expected.top_pattern is not None and expected.top_pattern != result["top_pattern"]:
        diffs.append(f"pattern:  expected {expected.top_pattern}, got {result['top_pattern']}")
    if expected.score is not None and not isclose(expected.score, result["score"]):
        diffs.append(f"score:    expected {expected.score}, got {result['score']}")
    if expected.assisted is not None and expected.assisted != result["assisted"]:
        helped = _yes(result["assisted"])
        diffs.append(f"assisted: expected {_yes(expected.assisted)}, got {helped}")
    if expected.quality is not None and expected.quality != result["quality"]:
        diffs.append(f"quality:  expected {expected.quality}, got {result['quality']}")
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
