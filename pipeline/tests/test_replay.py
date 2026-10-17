"""The scenario replay harness: `tests/scenarios/` and `routine_watch.replay`.

Two halves. The first replays every scenario in the repo and checks it against its
own `expected.yaml`, which is the same thing `scripts/e2e.sh` does, so a broken
pipeline fails here as well as in e2e. The second pins the rules the scenarios rely
on but do not all exercise: what the stub recogniser makes of a frame, which of
SPEC section 7's errors the stand-in classifier finds, and when a session flags.

The two stubs are stubs on purpose (`tests/scenarios/README.md`). These tests describe
what they do today so that replacing them with the real recogniser and the real error
classifier is a visible change rather than a quiet one.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from routine_watch.contracts import (
    HAND_LANDMARK_COUNT,
    POSE_LANDMARK_COUNT,
    BoundingBox,
    CaptureFrame,
    CaptureSource,
    ErrorType,
    Handedness,
    HandLandmarks,
    Landmark,
    ObjectDetection,
    ObjectLabel,
    Pose,
    StepEvent,
    StepSource,
)
from routine_watch.replay import (
    ABANDON_GAP_S,
    SCENARIOS_DIR,
    Expected,
    HistorySession,
    ReplayError,
    change_flag,
    check,
    compare,
    find_errors,
    load_scenario,
    main,
    replay,
    scenario_dirs,
    steps_from_frames,
    touched_objects,
)
from routine_watch.tasks import TaskGraph, load_task

SESSION = "test-session"

#: The two scenarios T005 asked for by name. Later tasks add more; these stay.
REQUIRED_SCENARIOS = ("tea_normal", "tea_skip_teabag_pour_twice")

#: A scenario directory holds these and nothing else. Never a clip (SPEC section 8).
ALLOWED_FILES = {"expected.yaml", "frames.jsonl", "steps.jsonl", "README.md"}


@pytest.fixture(scope="module")
def tea() -> TaskGraph:
    return load_task("tea")


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
    hands: list[HandLandmarks] | None = None,
    people: int = 0,
) -> CaptureFrame:
    """One capture record: object boxes, optional hand landmarks, optional people."""
    landmarks = [Landmark(x=0.5, y=0.5, z=0.0, visibility=0.9) for _ in range(POSE_LANDMARK_COUNT)]
    return CaptureFrame(
        session_id=SESSION,
        seq=seq,
        t=t,
        source=CaptureSource.SYNTHETIC,
        poses=[Pose(landmarks=landmarks, score=0.9) for _ in range(people)],
        hands=hands or [],
        objects=[
            ObjectDetection(label=ObjectLabel(label), confidence=0.9, box=at)
            for label, at in objects
        ],
    )


def hand_at(x: float, y: float) -> HandLandmarks:
    """MediaPipe hand landmarks, all on one point: the hand is on whatever is there."""
    return HandLandmarks(
        handedness=Handedness.RIGHT,
        score=0.9,
        landmarks=[Landmark(x=x, y=y, z=0.0) for _ in range(HAND_LANDMARK_COUNT)],
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


def errors_of(graph: TaskGraph, events: list[StepEvent]) -> list[tuple[str, str | None]]:
    """`find_errors` as (type, step) pairs, which is how a scenario writes them down."""
    end = max((event.t_end for event in events), default=0.0)
    found = find_errors(graph, events, session_id=SESSION, session_end=end)
    return [(str(error.type), error.step_id) for error in found]


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


def test_tea_no_kettle_comes_from_capture_frames() -> None:
    scenario = load_scenario(SCENARIOS_DIR / "tea_no_kettle")
    assert scenario.source == "frames"
    assert len(scenario.frames) > len(scenario.events)
    result = replay(scenario.path)
    assert sorted(error["step"] for error in result["errors"]) == ["boil", "fill_kettle"]
    assert {error["type"] for error in result["errors"]} == {"omission"}
    # One bad session on its own never alerts, baseline or no baseline (SPEC section 7).
    assert result["flag"] is False


def test_scenario_frames_are_valid_capture_records() -> None:
    """The scenario files really are the format the live camera produces."""
    path = SCENARIOS_DIR / "tea_no_kettle" / "frames.jsonl"
    lines = [line for line in path.read_text("utf-8").splitlines() if line.strip()]
    frames = [CaptureFrame.model_validate_json(line) for line in lines]
    assert [f.seq for f in frames] == list(range(len(frames)))
    assert all("image" not in json.loads(line) for line in lines)


# ---------------------------------------------------------- STUB: the recogniser


def test_a_hand_touches_what_its_box_overlaps() -> None:
    touched = touched_objects(
        frame(
            0,
            0.0,
            [
                ("cup", box(0.40, 0.44, 0.50, 0.58)),
                ("kettle", box(0.66, 0.26, 0.84, 0.54)),
                ("hand", box(0.44, 0.50, 0.54, 0.62)),
            ],
        )
    )
    assert touched == {"cup"}


def test_a_hand_touches_what_its_landmarks_are_inside() -> None:
    """MediaPipe hands work as well as the detector's hand class (SPEC section 16)."""
    touched = touched_objects(
        frame(
            0,
            0.0,
            [("cup", box(0.40, 0.44, 0.50, 0.58)), ("spoon", box(0.20, 0.60, 0.38, 0.66))],
            hands=[hand_at(0.45, 0.50)],
        )
    )
    assert touched == {"cup"}


def test_consecutive_frames_of_one_step_are_one_event(tea: TaskGraph) -> None:
    on_cup = [("cup", box(0.40, 0.44, 0.50, 0.58)), ("hand", box(0.44, 0.50, 0.54, 0.62))]
    events = steps_from_frames([frame(i, i * 0.5, on_cup) for i in range(4)], tea)
    assert [(event.step_id, event.t_start, event.t_end) for event in events] == [
        ("get_cup", 0.0, 1.5)
    ]
    assert events[0].source is StepSource.RULE
    assert not events[0].unclear


def test_a_frame_touching_nothing_ends_the_step(tea: TaskGraph) -> None:
    """Which is what lets a scenario show the same step happening twice."""
    cup = ("cup", box(0.40, 0.44, 0.50, 0.58))
    on_cup = [cup, ("hand", box(0.44, 0.50, 0.54, 0.62))]
    away = [cup, ("hand", box(0.04, 0.70, 0.14, 0.82))]
    frames = [frame(0, 0.0, on_cup), frame(1, 0.5, away), frame(2, 1.0, on_cup)]
    assert [event.step_id for event in steps_from_frames(frames, tea)] == ["get_cup", "get_cup"]


def test_two_steps_with_the_same_objects_are_refused_not_guessed(tea: TaskGraph) -> None:
    """`fill_kettle` and `boil` are both "the kettle": the stub says so and stops."""
    on_kettle = [
        ("kettle", box(0.66, 0.26, 0.84, 0.54)),
        ("hand", box(0.60, 0.30, 0.70, 0.42)),
    ]
    with pytest.raises(ReplayError, match="fill_kettle and boil"):
        steps_from_frames([frame(0, 0.0, on_kettle)], tea)


def test_frames_are_read_in_sequence_order(tea: TaskGraph) -> None:
    on_cup = [("cup", box(0.40, 0.44, 0.50, 0.58)), ("hand", box(0.44, 0.50, 0.54, 0.62))]
    on_spoon_in_cup = [
        ("cup", box(0.40, 0.44, 0.50, 0.58)),
        ("spoon", box(0.43, 0.38, 0.47, 0.56)),
        ("hand", box(0.42, 0.34, 0.52, 0.46)),
    ]
    shuffled = [frame(1, 0.5, on_spoon_in_cup), frame(0, 0.0, on_cup)]
    assert [event.step_id for event in steps_from_frames(shuffled, tea)] == ["get_cup", "stir"]


# ------------------------------------------------- STUB: the task graph and errors


def good_run() -> list[StepEvent]:
    """One correct, complete session, as step events."""
    return [
        step("fill_kettle", ["kettle"], 0.0, 5.0),
        step("boil", ["kettle"], 6.0, 8.0),
        step("get_cup", ["cup"], 9.0, 11.0),
        step("teabag_in_cup", ["teabag", "cup"], 12.0, 15.0),
        step("pour", ["kettle", "cup"], 16.0, 20.0),
        step("stir", ["spoon", "cup"], 21.0, 24.0),
        step("remove_teabag", ["teabag", "spoon"], 25.0, 27.0),
    ]


def test_a_clean_run_has_no_errors(tea: TaskGraph) -> None:
    assert errors_of(tea, good_run()) == []


def test_a_required_step_that_never_happens_is_an_omission(tea: TaskGraph) -> None:
    events = [event for event in good_run() if event.step_id != "stir"]
    assert errors_of(tea, events) == [("omission", "stir")]


def test_skipping_an_optional_step_is_not_an_omission(tea: TaskGraph) -> None:
    assert ("omission", "milk") not in errors_of(tea, good_run())
    assert ("omission", "sugar") not in errors_of(tea, good_run())


def test_a_step_before_a_dependency_done_later_is_a_sequence_error(tea: TaskGraph) -> None:
    events = good_run()
    pour, teabag = events[4], events[3]
    events[3], events[4] = pour, teabag  # pour first, then the teabag goes in
    assert ("sequence", "pour") in errors_of(tea, events)


def test_a_step_before_a_dependency_never_done_is_only_an_omission(tea: TaskGraph) -> None:
    """A sequence error needs the dependency to turn up later. This one never does."""
    events = [event for event in good_run() if event.step_id != "teabag_in_cup"]
    assert errors_of(tea, events) == [("omission", "teabag_in_cup")]


def test_a_once_only_step_done_again_later_is_perseveration(tea: TaskGraph) -> None:
    events = [*good_run(), step("pour", ["kettle", "cup"], 28.0, 31.0)]
    assert errors_of(tea, events) == [("perseveration", "pour")]


def test_a_step_carried_straight_on_with_is_not_perseveration(tea: TaskGraph) -> None:
    """Two events for one long pour is the recogniser blinking, not an error."""
    events = good_run()
    events.insert(5, step("pour", ["kettle", "cup"], 20.5, 22.0))
    assert errors_of(tea, events) == []


def test_stirring_twice_is_never_perseveration(tea: TaskGraph) -> None:
    """`stir` is once_only: false in the task file, because stirring again is normal."""
    events = [*good_run(), step("stir", ["spoon", "cup"], 28.0, 30.0)]
    assert errors_of(tea, events) == []


def test_the_wrong_object_is_a_substitution(tea: TaskGraph) -> None:
    events = good_run()
    events[5] = step("stir", ["milk", "cup"], 21.0, 24.0)  # stirring with the milk
    assert errors_of(tea, events) == [("substitution", "stir")]


def test_a_long_gap_mid_task_is_abandonment(tea: TaskGraph) -> None:
    """They walked off with the kettle boiled and the cup still empty."""
    away = ABANDON_GAP_S + 60.0
    events = [
        *good_run()[:3],
        step("teabag_in_cup", ["teabag", "cup"], 12.0 + away, 15.0 + away),
        step("pour", ["kettle", "cup"], 16.0 + away, 20.0 + away),
        step("stir", ["spoon", "cup"], 21.0 + away, 24.0 + away),
        step("remove_teabag", ["teabag", "spoon"], 25.0 + away, 27.0 + away),
    ]
    assert errors_of(tea, events) == [("abandonment", None)]


def test_a_long_gap_after_the_task_is_done_is_not_abandonment(tea: TaskGraph) -> None:
    """They finished their tea and came back to stir it again. Nothing to report."""
    events = [*good_run(), step("stir", ["spoon", "cup"], 1000.0, 1004.0)]
    assert errors_of(tea, events) == []


def test_an_unclear_event_is_never_an_error(tea: TaskGraph) -> None:
    """Below ~0.6 and the verifier could not resolve it: never counted (SPEC section 7)."""
    events = [*good_run(), step("pour", ["milk"], 28.0, 31.0, unclear=True)]
    assert errors_of(tea, events) == []


def test_an_unclear_step_still_counts_as_having_happened(tea: TaskGraph) -> None:
    """Otherwise "we could not tell" would be reported as the resident skipping it."""
    events = [
        step("stir", ["spoon", "cup"], 21.0, 24.0, unclear=True) if event.step_id == "stir"
        else event
        for event in good_run()
    ]
    assert errors_of(tea, events) == []


def test_a_step_the_task_graph_does_not_have_is_an_error(tea: TaskGraph) -> None:
    with pytest.raises(ReplayError, match="no step 'wash_up'"):
        errors_of(tea, [step("wash_up", ["cup"], 0.0, 1.0)])


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
    on_cup = [("cup", box(0.40, 0.44, 0.50, 0.58)), ("hand", box(0.44, 0.50, 0.54, 0.62))]
    frames = [frame(0, 0.0, on_cup, people=2), frame(1, 0.5, on_cup, people=2)]
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
