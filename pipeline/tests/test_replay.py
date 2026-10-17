"""The scenario replay harness: `tests/scenarios/` and `routine_watch.replay`.

Two halves. The first replays every scenario in the repo and checks it against its
own `expected.yaml`, which is the same thing `scripts/e2e.sh` does, so a broken
pipeline fails here as well as in e2e. The second pins the rules the scenarios rely
on but do not all exercise: the score and the change flag. The recogniser's own rules
are `routine_watch.recogniser`'s to pin (`tests/test_recogniser.py`); SPEC section 7's
error types are `routine_watch.errors`'s (`tests/test_errors.py`); this module just
wires the real recogniser and classifier in.
"""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import pytest

from routine_watch.contracts import (
    POSE_LANDMARK_COUNT,
    BoundingBox,
    CaptureFrame,
    CaptureSource,
    ErrorType,
    Landmark,
    ObjectDetection,
    ObjectLabel,
    Pose,
    StepEvent,
    StepSource,
)
from routine_watch.replay import (
    NO_PATTERN,
    SCENARIOS_DIR,
    Expected,
    HistorySession,
    ReplayError,
    assisted_of,
    change_flag,
    check,
    compare,
    load_scenario,
    main,
    replay,
    run,
    scenario_dirs,
)

SESSION = "test-session"

#: The two scenarios T005 asked for by name. Later tasks add more; these stay.
REQUIRED_SCENARIOS = ("tea_normal", "tea_skip_teabag_pour_twice")

#: A scenario directory holds these and nothing else. Never a clip (SPEC section 8).
ALLOWED_FILES = {"expected.yaml", "frames.jsonl", "steps.jsonl", "README.md"}


def test_run_rejects_an_empty_scenario() -> None:
    scenario = replace(load_scenario(SCENARIOS_DIR / "tea_normal"), frames=(), events=())
    with pytest.raises(ReplayError, match="no frames or events"):
        run(scenario)


# ---------------------------------------------------------------------- helpers


def step(
    step_id: str,
    objects: list[str],
    t_start: float,
    t_end: float,
    *,
    unclear: bool = False,
) -> StepEvent:
    """One step event, the way a scenario's steps.jsonl would spell it."""
    return StepEvent(
        event_id=f"{SESSION}:{step_id}@{t_start}",
        session_id=SESSION,
        step_id=step_id,
        objects=[ObjectLabel(label) for label in objects],
        t_start=t_start,
        t_end=t_end,
        confidence=0.4 if unclear else 0.9,
        source=StepSource.RULE,
        unclear=unclear,
    )


def box(x1: float, y1: float, x2: float, y2: float) -> BoundingBox:
    return BoundingBox(x1=x1, y1=y1, x2=x2, y2=y2)


def frame(
    seq: int,
    t: float,
    objects: list[tuple[str, BoundingBox]],
    *,
    people: int = 0,
) -> CaptureFrame:
    """One capture record: object boxes and optional people."""
    landmarks = [Landmark(x=0.5, y=0.5, z=0.0, visibility=0.9) for _ in range(POSE_LANDMARK_COUNT)]
    return CaptureFrame(
        session_id=SESSION,
        seq=seq,
        t=t,
        source=CaptureSource.SYNTHETIC,
        poses=[Pose(landmarks=landmarks, score=0.9) for _ in range(people)],
        hands=[],
        objects=[
            ObjectDetection(label=ObjectLabel(label), confidence=0.9, box=at)
            for label, at in objects
        ],
    )


def write_scenario(path: Path, expected: str, *, steps: str = "", frames: str = "") -> Path:
    """A scenario directory made up on the spot, for the paths no fixture covers."""
    path.mkdir(parents=True, exist_ok=True)
    (path / "expected.yaml").write_text(expected, encoding="utf-8")
    if steps:
        (path / "steps.jsonl").write_text(steps, encoding="utf-8")
    if frames:
        (path / "frames.jsonl").write_text(frames, encoding="utf-8")
    return path


# ------------------------------------------------------------------- the scenarios


def test_the_scenarios_t005_asked_for_are_here() -> None:
    assert SCENARIOS_DIR.is_dir(), f"no scenarios at {SCENARIOS_DIR}"
    names = {path.name for path in scenario_dirs()}
    assert set(REQUIRED_SCENARIOS) <= names


@pytest.mark.parametrize("path", scenario_dirs(), ids=lambda path: path.name)
def test_every_scenario_matches_its_expected_file(path: Path) -> None:
    """What scripts/e2e.sh checks, checked again here so pytest alone catches it."""
    assert check(path) == []


@pytest.mark.parametrize("path", scenario_dirs(), ids=lambda path: path.name)
def test_a_scenario_holds_no_video(path: Path) -> None:
    """Skeletons, boxes and timestamps only (SPEC section 8)."""
    unexpected = {item.name for item in path.iterdir()} - ALLOWED_FILES
    assert not unexpected, f"{path.name}: {sorted(unexpected)}"


def test_tea_normal_is_a_clean_session() -> None:
    result = replay(SCENARIOS_DIR / "tea_normal")
    assert result["errors"] == []
    assert result["score"] == 0.0
    assert result["flag"] is False
    # The scenario's point: neither of these is an error.
    assert result["steps"].index("get_cup") < result["steps"].index("boil")
    assert "sugar" not in result["steps"]


def test_tea_skip_teabag_pour_twice_flags_the_two_errors() -> None:
    result = replay(SCENARIOS_DIR / "tea_skip_teabag_pour_twice")
    assert [(error["type"], error["step"]) for error in result["errors"]] == [
        ("omission", "teabag_in_cup"),
        ("perseveration", "pour"),
    ]
    assert result["score"] == 5.0
    # A second session above this resident's own threshold inside 48 h.
    assert result["flag"] is True
    assert result["baseline"]["threshold"] < result["score"]
    assert result["quality"] == "ok"


def test_an_unclear_session_never_scores_or_flags() -> None:
    """SPEC section 12: a session hard to read (bad lighting, a walker) must not push
    a resident toward a flag just because recognition could not keep up with it -
    the same history that flags a clean read must not flag an unclear one."""
    scenario = load_scenario(SCENARIOS_DIR / "tea_skip_teabag_pour_twice")

    # Three of the seven events unclear or low-confidence: over the 40% threshold.
    unclear_events = tuple(
        event.model_copy(update={"unclear": True, "confidence": 0.2})
        if event.step_id in ("fill_kettle", "boil", "get_cup")
        else event
        for event in scenario.events
    )
    result = run(replace(scenario, events=unclear_events))
    assert result["quality"] == "unclear"
    assert result["score"] == 0.0
    assert result["flag"] is False


def test_tea_no_kettle_comes_from_capture_frames() -> None:
    scenario = load_scenario(SCENARIOS_DIR / "tea_no_kettle")
    assert scenario.source == "frames"
    assert len(scenario.frames) > len(scenario.events)
    result = replay(scenario.path)
    assert sorted(error["step"] for error in result["errors"]) == ["boil", "fill_kettle"]
    assert {error["type"] for error in result["errors"]} == {"omission"}
    # One bad session on its own never alerts, baseline or no baseline (SPEC section 7).
    assert result["flag"] is False


def test_pattern_sudden_change_is_the_top_pattern() -> None:
    result = replay(SCENARIOS_DIR / "pattern_sudden_change")
    assert result["flag"] is True
    assert result["top_pattern"] == "sudden_change"


def test_pattern_slow_drift_is_the_top_pattern() -> None:
    result = replay(SCENARIOS_DIR / "pattern_slow_drift")
    assert result["flag"] is True
    assert result["top_pattern"] == "slow_drift"


def test_pattern_none_matches_no_pattern() -> None:
    result = replay(SCENARIOS_DIR / "pattern_none")
    assert result["flag"] is True
    assert result["top_pattern"] == NO_PATTERN


def test_a_flag_with_no_baseline_has_no_pattern() -> None:
    """`tea_skip_teabag_pour_twice` has a baseline; a scenario with none never does."""
    result = replay(SCENARIOS_DIR / "tea_normal")
    assert result["top_pattern"] == NO_PATTERN


def test_scenario_frames_are_valid_capture_records() -> None:
    """The scenario files really are the format the live camera produces."""
    path = SCENARIOS_DIR / "tea_no_kettle" / "frames.jsonl"
    lines = [line for line in path.read_text("utf-8").splitlines() if line.strip()]
    frames = [CaptureFrame.model_validate_json(line) for line in lines]
    assert [f.seq for f in frames] == list(range(len(frames)))
    assert all("image" not in json.loads(line) for line in lines)


# --------------------------------------------------------------- score and flag


def history(*scores: tuple[float, float]) -> list[HistorySession]:
    return [HistorySession(hours_ago=hours, score=score) for hours, score in scores]


def test_a_resident_with_no_history_never_flags() -> None:
    flag, baseline = change_flag(99.0, history((30.0, 0.0), (24.0, 0.0)))
    assert (flag, baseline) == (False, None)


def test_one_bad_session_never_flags() -> None:
    flag, baseline = change_flag(9.0, history((72.0, 0.0), (48.0, 0.5), (24.0, 0.0)))
    assert flag is False
    assert baseline is not None and baseline.threshold < 9.0


#: A week of quiet tea, which is what a resident's baseline is usually built from.
QUIET_WEEK = ((168.0, 0.0), (144.0, 0.0), (120.0, 0.5), (96.0, 0.0), (72.0, 0.0), (52.0, 0.0))


def test_two_bad_sessions_inside_the_window_flag() -> None:
    assert change_flag(9.0, history(*QUIET_WEEK, (30.0, 9.0)))[0] is True


def test_two_bad_sessions_too_far_apart_do_not_flag() -> None:
    """Same two sessions, 60 hours apart instead of 30: a flag needs 24-48 h."""
    assert change_flag(9.0, history(*QUIET_WEEK, (60.0, 9.0)))[0] is False


def test_history_can_be_written_as_errors_instead_of_a_score() -> None:
    assert HistorySession(hours_ago=1.0, errors={ErrorType.OMISSION: 1}).score_value == 3.0
    assert HistorySession(hours_ago=1.0, score=2.0).score_value == 2.0
    with pytest.raises(ValueError, match="not both"):
        HistorySession(hours_ago=1.0, score=2.0, errors={ErrorType.OMISSION: 1})


def test_a_session_with_staff_in_frame_is_assisted_and_scores_zero(tmp_path: Path) -> None:
    """A second person in frame means somebody is helping: excluded (SPEC section 7).

    Only a frame-level scenario can show this, because only frames carry the poses.
    """
    # The cup travels while held, which is what the recogniser's `get_cup` rule reads.
    carried_from = [("cup", box(0.10, 0.70, 0.20, 0.82)), ("hand", box(0.12, 0.72, 0.18, 0.80))]
    carried_to = [("cup", box(0.40, 0.44, 0.50, 0.58)), ("hand", box(0.42, 0.46, 0.48, 0.56))]
    frames = [
        frame(0, 0.0, carried_from, people=2),
        frame(1, 0.5, carried_to, people=2),
        frame(2, 2.0, carried_to, people=2),
    ]
    path = write_scenario(
        tmp_path / "assisted",
        "steps: [get_cup]\nerrors: []\nflag: false\n",
        frames="".join(f.model_dump_json() + "\n" for f in frames),
    )
    result = replay(path)
    assert result["assisted"] is True
    assert result["steps"] == ["get_cup"]
    assert result["errors"]  # the rest of the task never happened
    assert result["score"] == 0.0


def test_one_stray_second_pose_does_not_suppress_session_score() -> None:
    scenario = load_scenario(SCENARIOS_DIR / "tea_no_kettle")
    frames = list(scenario.frames)
    frames[1] = frame(frames[1].seq, frames[1].t, [], people=2)
    result = run(replace(scenario, frames=tuple(frames)))
    assert result["assisted"] is False
    assert result["score"] == 6.0


@pytest.mark.parametrize("duration, expected", [(1.999, False), (2.0, True), (3.0, True)])
def test_assistance_requires_consecutive_frames_spanning_two_seconds(duration, expected) -> None:
    frames = [frame(0, 0, [], people=2), frame(1, duration, [], people=2)]
    assert assisted_of(frames) is expected


def test_single_person_frame_resets_the_assistance_timer() -> None:
    frames = [
        frame(0, 0, [], people=2), frame(1, 1, [], people=1),
        frame(2, 2, [], people=2), frame(3, 3, [], people=2),
    ]
    assert not assisted_of(frames)


def test_assistance_uses_elapsed_time_and_custom_threshold() -> None:
    frames = [frame(1, 11, [], people=2), frame(0, 10, [], people=2)]
    assert not assisted_of(frames)
    assert assisted_of(frames, min_seconds=1.0)
    assert not assisted_of([])
    assert not assisted_of([frame(0, 0, [], people=2)])


# ------------------------------------------------------- expected vs got, and the CLI


def expected_for(**overrides: object) -> Expected:
    fields: dict[str, object] = {"steps": ["get_cup"], "errors": [], "flag": False}
    return Expected.model_validate(fields | overrides)


def result_for(**overrides: object) -> dict[str, object]:
    fields: dict[str, object] = {
        "steps": ["get_cup"],
        "errors": [],
        "flag": False,
        "score": 0.0,
        "assisted": False,
        "top_pattern": NO_PATTERN,
    }
    return fields | overrides


def test_a_matching_result_has_no_diff() -> None:
    assert compare(expected_for(), result_for()) == []


def test_a_diff_names_the_steps_that_differ() -> None:
    diff = compare(expected_for(), result_for(steps=["get_cup", "pour"]))
    assert "steps" in diff[0] and "pour" in diff[1]


def test_a_diff_separates_missing_from_unexpected_errors() -> None:
    expected = expected_for(errors=[{"type": "omission", "step": "boil"}])
    got = result_for(errors=[{"type": "sequence", "step": "pour"}])
    diff = "\n".join(compare(expected, got))
    assert "missing" in diff and "omission/boil" in diff
    assert "unexpected" in diff and "sequence/pour" in diff


def test_optional_assertions_are_only_checked_when_the_file_sets_them() -> None:
    assert compare(expected_for(), result_for(score=7.0, assisted=True)) == []
    assert compare(expected_for(score=0.0), result_for(score=7.0)) != []
    assert compare(expected_for(assisted=False), result_for(assisted=True)) != []


def test_an_unknown_key_in_expected_yaml_is_a_failure() -> None:
    with pytest.raises(ValueError, match="flagg"):
        Expected.model_validate({"steps": [], "errors": [], "flag": True, "flagg": True})


def test_top_pattern_is_only_checked_when_the_file_sets_it() -> None:
    # Absent: a scenario without the key is unaffected by whatever the result holds.
    assert compare(expected_for(), result_for(top_pattern="sudden_change")) == []
    # Match.
    drift = result_for(top_pattern="slow_drift")
    assert compare(expected_for(top_pattern="slow_drift"), drift) == []
    assert compare(expected_for(top_pattern="none"), result_for(top_pattern="none")) == []
    # Mismatch.
    diff = compare(expected_for(top_pattern="sudden_change"), result_for(top_pattern="slow_drift"))
    assert diff and "sudden_change" in diff[0] and "slow_drift" in diff[0]


def test_top_pattern_rejects_an_unknown_pattern_id() -> None:
    with pytest.raises(ValueError, match="top_pattern"):
        Expected.model_validate(
            {"steps": [], "errors": [], "flag": True, "top_pattern": "not_a_real_pattern"}
        )


# -------------------------------------------------------------- broken scenarios


ONE_STEP = json.dumps(step("get_cup", ["cup"], 0.0, 1.0).model_dump(mode="json")) + "\n"
EXPECTED_ONE_STEP = "steps: [get_cup]\nerrors: []\nflag: false\n"


def test_a_directory_that_is_not_there_is_an_error(tmp_path: Path) -> None:
    with pytest.raises(ReplayError, match="not a scenario directory"):
        load_scenario(tmp_path / "nope")


def test_a_scenario_without_expected_yaml_is_an_error(tmp_path: Path) -> None:
    (tmp_path / "steps.jsonl").write_text(ONE_STEP, encoding="utf-8")
    with pytest.raises(ReplayError, match="no expected.yaml"):
        load_scenario(tmp_path)


def test_a_scenario_needs_exactly_one_input_file(tmp_path: Path) -> None:
    neither = write_scenario(tmp_path / "neither", EXPECTED_ONE_STEP)
    with pytest.raises(ReplayError, match="exactly one"):
        load_scenario(neither)
    both = write_scenario(
        tmp_path / "both", EXPECTED_ONE_STEP, steps=ONE_STEP, frames=ONE_STEP
    )
    with pytest.raises(ReplayError, match="exactly one"):
        load_scenario(both)


def test_a_bad_record_names_its_line(tmp_path: Path) -> None:
    path = write_scenario(
        tmp_path / "bad", EXPECTED_ONE_STEP, steps=ONE_STEP + '{"step_id": "pour"}\n'
    )
    with pytest.raises(ReplayError, match="steps.jsonl:2"):
        load_scenario(path)


def test_an_unknown_task_names_the_task(tmp_path: Path) -> None:
    path = write_scenario(
        tmp_path / "task", "task: pancakes\n" + EXPECTED_ONE_STEP, steps=ONE_STEP
    )
    with pytest.raises(ReplayError, match="pancakes"):
        load_scenario(path)


def test_check_mode_passes_the_real_scenarios_and_fails_a_broken_one(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert main(["--check", *(str(path) for path in scenario_dirs())]) == 0
    assert "FAIL" not in capsys.readouterr().out

    broken = write_scenario(
        tmp_path / "broken", "steps: [pour]\nerrors: []\nflag: false\n", steps=ONE_STEP
    )
    assert main(["--check", str(broken)]) == 1
    assert "FAIL broken" in capsys.readouterr().out


def test_a_broken_scenario_fails_rather_than_crashing_the_run(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert main(["--check", str(tmp_path / "missing")]) == 1
    assert "not a scenario directory" in capsys.readouterr().out


def test_printing_one_scenario_prints_one_json_object(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert main([str(SCENARIOS_DIR / "tea_normal")]) == 0
    printed = json.loads(capsys.readouterr().out)
    assert printed["scenario"] == "tea_normal"
    assert printed["task"] == "make_tea"


def test_printing_several_scenarios_prints_a_json_array(
    capsys: pytest.CaptureFixture[str],
) -> None:
    paths = [str(SCENARIOS_DIR / name) for name in REQUIRED_SCENARIOS]
    assert main(paths) == 0
    printed = json.loads(capsys.readouterr().out)
    assert [item["scenario"] for item in printed] == list(REQUIRED_SCENARIOS)
