"""The step recogniser (SPEC section 6.2): state rules over hand-object interactions.

Every fixture here is hand-built by the helpers below - boxes on a counter and a hand
on one of them, a frame at a time - and written out to `fixtures/recogniser/*.jsonl`
in the one capture format (SPEC section 16). Nothing is recorded from video: a
scenario you can read is a scenario you can argue with, and the fixture files are
small enough to read.

The clips are the four steps T011 asks for - filling the kettle, putting the teabag in
the cup, pouring and stirring - plus a whole session, which is where ordering is
checked, and one clip the detector barely sees, which is where `unclear` is.

`tasks/tea.yaml` names an action per step (`routine_watch.actions`, T463), so these
clips are read by the primitives now rather than by the hand-written rules this module
started as. Both still exist, and
`test_the_primitives_read_these_clips_exactly_as_the_hand_written_rules_did` is what
holds them to the same answer; `test_actions.py` is the primitives themselves.
"""

from __future__ import annotations

import json
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path

import pytest
import yaml

from routine_watch.contracts import (
    HAND_LANDMARK_COUNT,
    BoundingBox,
    CaptureFrame,
    CaptureSource,
    Handedness,
    HandLandmarks,
    Landmark,
    ObjectDetection,
    ObjectLabel,
    StepEvent,
    StepSource,
)
from routine_watch.errors import classify_errors
from routine_watch.recogniser import MIN_STEP_CONFIDENCE, needs_verifier, recognise
from routine_watch.tasks import TaskGraph, load_task, parse_task
from routine_watch.tasks.graph import TASKS_DIR, parse_task_data

#: The session every fixture is recognised as. The frames carry their own id; the
#: caller's is the one the events get.
SESSION = "tea-recognise-1"

#: The make-tea graph is immutable and cached, so every test shares one.
TEA = load_task("tea")

#: Fixtures are written at this frame rate: slow, so a clip stays short enough to read.
FPS = 2.0

FIXTURES = Path(__file__).parent / "fixtures" / "recogniser"

#: How sure the detector is of each class, held fixed so a fixture's confidences are
#: the only thing that moves. The `pouring` class is the least certain, as it is in
#: `contracts/examples/capture.jsonl`.
DETECTED = {
    "kettle": 0.94,
    "cup": 0.91,
    "teabag": 0.78,
    "spoon": 0.86,
    "milk": 0.88,
    "sugar": 0.84,
    "pouring": 0.66,
    "hand": 0.88,
}

#: Half the width of a hand box. A hand is written to the fixture files as the
#: detector's own `hand` class rather than 21 MediaPipe landmarks on one spot: it is
#: the same signal to the recogniser (`test_hand_landmarks_read_the_same_as_hand_boxes`)
#: and it keeps a clip small enough to read.
HAND_REACH = 0.02

Point = tuple[float, float]


# --------------------------------------------------------------------- the counter


def box(x1: float, y1: float, x2: float, y2: float) -> BoundingBox:
    return BoundingBox(x1=x1, y1=y1, x2=x2, y2=y2)


#: Where the cup is fetched from, on its way, and where tea gets made.
CUP_SHELF = box(0.26, 0.44, 0.36, 0.58)
CUP_CARRIED = box(0.33, 0.44, 0.43, 0.58)
CUP = box(0.40, 0.44, 0.50, 0.58)

#: The kettle on its base, held at counter height on the way to the tap, at the tap,
#: and lifted over the cup to pour.
KETTLE_BASE = box(0.66, 0.26, 0.84, 0.54)
KETTLE_CARRIED = box(0.46, 0.34, 0.64, 0.62)
KETTLE_TAP = box(0.10, 0.26, 0.28, 0.54)
KETTLE_POURING = box(0.38, 0.18, 0.56, 0.46)

#: The detector's own `pouring` class, over the cup.
POURING = box(0.40, 0.30, 0.56, 0.56)

TEABAG_COUNTER = box(0.16, 0.30, 0.23, 0.37)
TEABAG_IN_CUP = box(0.43, 0.46, 0.47, 0.51)
TEABAG_LIFTED = box(0.33, 0.34, 0.37, 0.39)

#: The milk on the shelf, and held over the cup.
MILK_SHELF = box(0.84, 0.60, 0.94, 0.72)
MILK_POURING = box(0.42, 0.30, 0.52, 0.48)

#: The spoon on the counter, and standing in the cup at each end of a stir.
SPOON_COUNTER = box(0.22, 0.60, 0.38, 0.66)
SPOON_LEFT = box(0.43, 0.40, 0.47, 0.56)
SPOON_RIGHT = box(0.45, 0.40, 0.49, 0.56)


def grip(at: BoundingBox) -> Point:
    """A hand holding `at`: it lands in the middle of the box."""
    return (at.x1 + at.x2) / 2.0, (at.y1 + at.y2) / 2.0


# ------------------------------------------------------------- building the frames


def hand_box(at: Point) -> ObjectDetection:
    """A hand on `at`, as the detector's `hand` class sees it."""
    x, y = at
    return ObjectDetection(
        label=ObjectLabel.HAND,
        confidence=DETECTED["hand"],
        box=box(x - HAND_REACH, y - HAND_REACH, x + HAND_REACH, y + HAND_REACH),
    )


def as_landmarks(frames: Sequence[CaptureFrame]) -> list[CaptureFrame]:
    """The same frames with every hand box replaced by MediaPipe hand landmarks, all
    on the middle of it: capture gives both, and the rules read either (SPEC section
    16, "Hands")."""
    swapped = []
    for frame in frames:
        hands = [found for found in frame.objects if found.label is ObjectLabel.HAND]
        swapped.append(
            frame.model_copy(
                update={
                    "objects": [
                        found for found in frame.objects if found.label is not ObjectLabel.HAND
                    ],
                    "hands": [
                        HandLandmarks(
                            handedness=Handedness.LEFT if index else Handedness.RIGHT,
                            score=found.confidence,
                            landmarks=[
                                Landmark(
                                    x=(found.box.x1 + found.box.x2) / 2.0,
                                    y=(found.box.y1 + found.box.y2) / 2.0,
                                    z=0.0,
                                )
                                for _ in range(HAND_LANDMARK_COUNT)
                            ],
                        )
                        for index, found in enumerate(hands)
                    ],
                }
            )
        )
    return swapped


class Take:
    """Frames of one hand-built session, numbered and timed as they are added.

    No poses: the recogniser reads hands and object boxes (SPEC section 16, "Hands"),
    and 33 body landmarks a frame would bury the part of the fixture worth reading.
    """

    def __init__(self, session: str, *, fps: float = FPS) -> None:
        self.session = session
        self.fps = fps
        self.frames: list[CaptureFrame] = []

    def shot(
        self,
        objects: Mapping[str, BoundingBox],
        hands: Sequence[Point] = (),
        *,
        confidence: Mapping[str, float] | None = None,
        repeat: int = 1,
    ) -> Take:
        """`repeat` frames of the counter looking like this."""
        seen = {**DETECTED, **(confidence or {})}
        for _ in range(repeat):
            seq = len(self.frames)
            self.frames.append(
                CaptureFrame(
                    session_id=self.session,
                    seq=seq,
                    t=round(seq / self.fps, 3),
                    source=CaptureSource.SYNTHETIC,
                    poses=[],
                    hands=[],
                    objects=[
                        ObjectDetection(
                            label=ObjectLabel(label), confidence=seen[label], box=where
                        )
                        for label, where in objects.items()
                    ]
                    + [hand_box(at) for at in hands],
                )
            )
        return self


# ------------------------------------------------------------------- the fixtures


def fill_kettle_clip() -> list[CaptureFrame]:
    """The kettle is picked up, carried to the tap, filled and brought back."""
    counter = {"cup": CUP, "teabag": TEABAG_COUNTER, "spoon": SPOON_COUNTER}
    take = Take("fill-kettle")
    take.shot({**counter, "kettle": KETTLE_BASE})
    take.shot({**counter, "kettle": KETTLE_BASE}, [grip(KETTLE_BASE)])
    take.shot({**counter, "kettle": KETTLE_CARRIED}, [grip(KETTLE_CARRIED)])
    take.shot({**counter, "kettle": KETTLE_TAP}, [grip(KETTLE_TAP)], repeat=2)
    take.shot({**counter, "kettle": KETTLE_CARRIED}, [grip(KETTLE_CARRIED)])
    take.shot({**counter, "kettle": KETTLE_BASE}, [grip(KETTLE_BASE)])
    take.shot({**counter, "kettle": KETTLE_BASE})
    return take.frames


def teabag_in_cup_clip(confidence: Mapping[str, float] | None = None) -> list[CaptureFrame]:
    """The teabag is taken off the counter and dropped in the cup."""
    counter = {"cup": CUP, "kettle": KETTLE_BASE, "spoon": SPOON_COUNTER}
    take = Take("teabag-in-cup")
    take.shot({**counter, "teabag": TEABAG_COUNTER}, confidence=confidence)
    take.shot({**counter, "teabag": TEABAG_COUNTER}, [grip(TEABAG_COUNTER)], confidence=confidence)
    take.shot(
        {**counter, "teabag": TEABAG_IN_CUP},
        [grip(TEABAG_IN_CUP)],
        confidence=confidence,
        repeat=3,
    )
    take.shot({**counter, "teabag": TEABAG_IN_CUP}, confidence=confidence)
    return take.frames


def barely_seen_teabag_clip() -> list[CaptureFrame]:
    """The same again, with the teabag half out of sight: this is what the verifier is
    for, and what comes back `unclear` until it exists."""
    return teabag_in_cup_clip(confidence={"teabag": 0.42})


def pour_clip() -> list[CaptureFrame]:
    """The kettle is lifted over the cup and tipped. Both signals are here: the kettle
    over the cup, and the detector's own `pouring` class."""
    counter = {"cup": CUP, "teabag": TEABAG_IN_CUP, "spoon": SPOON_COUNTER}
    take = Take("pour")
    take.shot({**counter, "kettle": KETTLE_BASE})
    take.shot({**counter, "kettle": KETTLE_BASE}, [grip(KETTLE_BASE)])
    take.shot({**counter, "kettle": KETTLE_CARRIED}, [grip(KETTLE_CARRIED)])
    take.shot(
        {**counter, "kettle": KETTLE_POURING, "pouring": POURING},
        [grip(KETTLE_POURING)],
        repeat=3,
    )
    take.shot({**counter, "kettle": KETTLE_BASE}, [grip(KETTLE_BASE)])
    take.shot({**counter, "kettle": KETTLE_BASE})
    return take.frames


def stir_clip() -> list[CaptureFrame]:
    """The spoon goes into the cup, back and forth, and out again."""
    counter = {"cup": CUP, "kettle": KETTLE_BASE, "teabag": TEABAG_COUNTER}
    take = Take("stir")
    take.shot({**counter, "spoon": SPOON_COUNTER})
    take.shot({**counter, "spoon": SPOON_COUNTER}, [grip(SPOON_COUNTER)])
    for where in (SPOON_LEFT, SPOON_RIGHT, SPOON_LEFT, SPOON_RIGHT, SPOON_LEFT):
        take.shot({**counter, "spoon": where}, [grip(where)])
    take.shot({**counter, "spoon": SPOON_COUNTER}, [grip(SPOON_COUNTER)])
    take.shot({**counter, "spoon": SPOON_COUNTER})
    return take.frames


def make_tea_clip() -> list[CaptureFrame]:
    """A whole good session: cup, kettle filled and boiled, teabag, pour, stir, teabag
    out. Milk and sugar are skipped, which the graph allows."""
    take = Take("make-tea")
    counter = {"kettle": KETTLE_BASE, "teabag": TEABAG_COUNTER, "spoon": SPOON_COUNTER}

    # Fetch the cup.
    take.shot({**counter, "cup": CUP_SHELF})
    take.shot({**counter, "cup": CUP_SHELF}, [grip(CUP_SHELF)])
    take.shot({**counter, "cup": CUP_CARRIED}, [grip(CUP_CARRIED)])
    take.shot({**counter, "cup": CUP}, [grip(CUP)])
    counter = {"cup": CUP, "teabag": TEABAG_COUNTER, "spoon": SPOON_COUNTER}
    take.shot({**counter, "kettle": KETTLE_BASE})

    # Fill the kettle at the tap and put it back.
    take.shot({**counter, "kettle": KETTLE_BASE}, [grip(KETTLE_BASE)])
    take.shot({**counter, "kettle": KETTLE_CARRIED}, [grip(KETTLE_CARRIED)])
    take.shot({**counter, "kettle": KETTLE_TAP}, [grip(KETTLE_TAP)], repeat=2)
    take.shot({**counter, "kettle": KETTLE_CARRIED}, [grip(KETTLE_CARRIED)])
    take.shot({**counter, "kettle": KETTLE_BASE}, [grip(KETTLE_BASE)])
    take.shot({**counter, "kettle": KETTLE_BASE})

    # Press the switch: a hand on the kettle that does not move it.
    take.shot({**counter, "kettle": KETTLE_BASE}, [grip(KETTLE_BASE)], repeat=4)
    take.shot({**counter, "kettle": KETTLE_BASE})

    # Teabag in the cup.
    take.shot({**counter, "kettle": KETTLE_BASE}, [grip(TEABAG_COUNTER)])
    counter = {"cup": CUP, "teabag": TEABAG_IN_CUP, "spoon": SPOON_COUNTER}
    take.shot({**counter, "kettle": KETTLE_BASE}, [grip(TEABAG_IN_CUP)], repeat=3)
    take.shot({**counter, "kettle": KETTLE_BASE})

    # Pour.
    take.shot({**counter, "kettle": KETTLE_BASE}, [grip(KETTLE_BASE)])
    take.shot({**counter, "kettle": KETTLE_CARRIED}, [grip(KETTLE_CARRIED)])
    take.shot({**counter, "kettle": KETTLE_POURING}, [grip(KETTLE_POURING)], repeat=3)
    take.shot({**counter, "kettle": KETTLE_CARRIED}, [grip(KETTLE_CARRIED)])
    take.shot({**counter, "kettle": KETTLE_BASE}, [grip(KETTLE_BASE)])
    take.shot({**counter, "kettle": KETTLE_BASE})

    # Stir.
    take.shot({**counter, "kettle": KETTLE_BASE}, [grip(SPOON_COUNTER)])
    for where in (SPOON_LEFT, SPOON_RIGHT, SPOON_LEFT, SPOON_RIGHT, SPOON_LEFT):
        take.shot(
            {"cup": CUP, "teabag": TEABAG_IN_CUP, "spoon": where, "kettle": KETTLE_BASE},
            [grip(where)],
        )
    take.shot({**counter, "kettle": KETTLE_BASE}, [grip(SPOON_COUNTER)])
    take.shot({**counter, "kettle": KETTLE_BASE})

    # Teabag out.
    take.shot({**counter, "kettle": KETTLE_BASE}, [grip(TEABAG_IN_CUP)])
    out = {"cup": CUP, "teabag": TEABAG_LIFTED, "spoon": SPOON_COUNTER, "kettle": KETTLE_BASE}
    take.shot(out, [grip(TEABAG_LIFTED)], repeat=3)
    take.shot(out)
    return take.frames


#: Every fixture file, and the helper that builds it.
CLIPS: dict[str, Callable[[], list[CaptureFrame]]] = {
    "fill_kettle": fill_kettle_clip,
    "teabag_in_cup": teabag_in_cup_clip,
    "pour": pour_clip,
    "stir": stir_clip,
    "barely_seen_teabag": barely_seen_teabag_clip,
    "make_tea": make_tea_clip,
}

#: What the whole session is, in the order it happens.
MAKE_TEA_STEPS = (
    "get_cup",
    "fill_kettle",
    "boil",
    "teabag_in_cup",
    "pour",
    "stir",
    "remove_teabag",
)


def as_jsonl(frames: Sequence[CaptureFrame]) -> str:
    return "".join(json.dumps(frame.model_dump(mode="json")) + "\n" for frame in frames)


def write_fixtures() -> None:
    """Rewrite the fixture files: `uv run python tests/test_recogniser.py`."""
    FIXTURES.mkdir(parents=True, exist_ok=True)
    for name, build in CLIPS.items():
        (FIXTURES / f"{name}.jsonl").write_text(as_jsonl(build()), encoding="utf-8")


def load(name: str) -> list[CaptureFrame]:
    """One fixture file, read back the way the pipeline reads a capture stream."""
    path = FIXTURES / f"{name}.jsonl"
    return [
        CaptureFrame.model_validate_json(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def steps_in(events: Sequence[StepEvent]) -> list[str]:
    return [event.step_id for event in events]


def recognised(name: str, graph: TaskGraph = TEA) -> list[StepEvent]:
    """The steps in one fixture file."""
    return recognise(load(name), graph, session_id=SESSION)


# ---------------------------------------------------------------- the four clips


@pytest.mark.parametrize(
    ("name", "step_id", "objects"),
    [
        ("fill_kettle", "fill_kettle", ["kettle"]),
        ("teabag_in_cup", "teabag_in_cup", ["teabag", "cup"]),
        ("pour", "pour", ["kettle", "cup"]),
        ("stir", "stir", ["spoon", "cup"]),
    ],
)
def test_one_clip_is_one_confident_step(name: str, step_id: str, objects: list[str]) -> None:
    """Each of the four steps T011 asks for, on its own, with nothing else read into
    it: the other things on the counter are there and are not being touched."""
    events = recognised(name)
    assert len(events) == 1, steps_in(events)
    found = events[0]
    assert found.step_id == step_id
    assert [str(label) for label in found.objects] == objects
    assert found.source is StepSource.RULE
    assert found.session_id == SESSION
    assert not found.unclear
    assert found.confidence >= MIN_STEP_CONFIDENCE
    assert found.t_start < found.t_end


# ------------------------------------------------------------- the whole session


def test_a_whole_session_comes_out_in_order() -> None:
    events = recognised("make_tea")
    assert steps_in(events) == list(MAKE_TEA_STEPS)
    assert TEA.is_valid_order(steps_in(events))
    assert len({event.event_id for event in events}) == len(events)
    for event in events:
        assert event.t_start <= event.t_end
        assert not event.unclear
    for before, after in zip(events, events[1:], strict=False):
        assert before.t_end < after.t_start, f"{before.step_id} runs into {after.step_id}"


def test_a_whole_session_holds_no_errors() -> None:
    """The point of getting the order right: the classifier has nothing to say about a
    session that was done properly."""
    assert classify_errors(recognised("make_tea"), TEA, session_id=SESSION) == []


def test_filling_the_kettle_and_boiling_it_are_told_apart() -> None:
    """The pair the replay stub cannot separate (tests/scenarios/README.md): both are
    a hand on the kettle, and only the state tells them apart - carried to the tap, or
    held where it stands."""
    events = {event.step_id: event for event in recognised("make_tea")}
    fill, boil = events["fill_kettle"], events["boil"]
    assert fill.t_end < boil.t_start
    assert [str(label) for label in boil.objects] == ["kettle"]
    assert boil.confidence >= MIN_STEP_CONFIDENCE
    # The switch is the weaker reading of the two, and should say so.
    assert boil.confidence < fill.confidence


# --------------------------------------------------- what the verifier is left to do


def test_a_barely_seen_step_is_unclear_and_still_reported() -> None:
    """Never dropped silently (SPEC section 7): a step nobody is sure of is a step the
    verifier should look at, not a step that never happened."""
    events = recognised("barely_seen_teabag")
    assert steps_in(events) == ["teabag_in_cup"]
    found = events[0]
    assert found.unclear
    assert found.confidence < MIN_STEP_CONFIDENCE
    assert needs_verifier(found)


def test_a_spoon_left_standing_in_the_cup_is_unclear() -> None:
    """The same picture as a stir with none of the movement."""
    take = Take("resting-spoon")
    take.shot({"cup": CUP, "spoon": SPOON_LEFT})
    take.shot({"cup": CUP, "spoon": SPOON_LEFT}, [grip(SPOON_LEFT)], repeat=4)
    events = recognise(take.frames, TEA, session_id=SESSION)
    assert steps_in(events) == ["stir"]
    assert events[0].unclear and needs_verifier(events[0])


def test_every_event_is_confident_or_unclear_and_never_both() -> None:
    for name in CLIPS:
        for event in recognised(name):
            assert event.unclear == (event.confidence < MIN_STEP_CONFIDENCE), event
            assert 0.0 <= event.confidence <= 1.0


# ----------------------------------------------------------------- the rules alone


def test_the_pouring_class_is_enough_on_its_own() -> None:
    """The detector has a `pouring` class (SPEC section 6.1); when it fires over the
    cup, that is a pour whether or not a hand is on the kettle."""
    take = Take("pouring-class")
    take.shot({"cup": CUP, "pouring": POURING}, repeat=4)
    events = recognise(take.frames, TEA, session_id=SESSION)
    assert steps_in(events) == ["pour"]
    assert not events[0].unclear


def test_hand_landmarks_read_the_same_as_hand_boxes() -> None:
    """Capture gives both (SPEC section 16, "Hands"). The fixtures are written with
    hand boxes because they are smaller; a hand read off MediaPipe landmarks has to
    give the same session."""
    frames = load("make_tea")
    assert recognise(as_landmarks(frames), TEA, session_id=SESSION) == recognise(
        frames, TEA, session_id=SESSION
    )


def test_an_object_moving_with_no_hand_on_it_is_not_a_step() -> None:
    """Steps are hand-object interactions (SPEC section 16). A box that drifts across
    the counter on its own is the tracker wobbling, not somebody making tea."""
    take = Take("no-hands")
    for where in (KETTLE_BASE, KETTLE_CARRIED, KETTLE_TAP, KETTLE_CARRIED):
        take.shot({"cup": CUP, "kettle": where})
    assert recognise(take.frames, TEA, session_id=SESSION) == []


def carry_clip(fps: float = FPS, *, blink: int | None = None) -> list[CaptureFrame]:
    """The kettle carried to the tap and back. `blink` is the frame the detector loses
    the hand in, the frame itself still arriving."""
    take = Take("carry", fps=fps)
    route = (KETTLE_BASE, KETTLE_CARRIED, KETTLE_TAP, KETTLE_TAP, KETTLE_CARRIED, KETTLE_BASE)
    for seq, where in enumerate(route):
        take.shot({"cup": CUP, "kettle": where}, () if seq == blink else [grip(where)])
    return take.frames


def test_the_detector_losing_a_hand_for_a_frame_does_not_split_a_step() -> None:
    """A blink inside `FLICKER_GAP_S` is the detector, not the hand letting go."""
    whole = recognise(carry_clip(fps=10.0), TEA, session_id=SESSION)
    blinked = recognise(carry_clip(fps=10.0, blink=3), TEA, session_id=SESSION)
    assert steps_in(whole) == steps_in(blinked) == ["fill_kettle"]
    assert (whole[0].t_start, whole[0].t_end) == (blinked[0].t_start, blinked[0].t_end)


def test_a_long_blink_is_two_contacts() -> None:
    """A slow stream is not a blink: at 2 fps the same missing frame is half a second
    of the kettle standing untouched, which is the hand letting go and taking hold
    again."""
    events = recognise(carry_clip(blink=3), TEA, session_id=SESSION)
    assert steps_in(events) == ["fill_kettle", "fill_kettle"]


def test_a_dropped_frame_does_not_split_a_step() -> None:
    """A record that never arrives says nothing about what happened: consecutive
    records carry a step on, whatever the clock says between them."""
    frames = carry_clip(fps=10.0)
    kept = [frame for frame in frames if frame.seq != 3]
    assert steps_in(recognise(kept, TEA, session_id=SESSION)) == ["fill_kettle"]


def test_brushing_past_the_kettle_is_not_switching_it_on() -> None:
    """`boil` is a hand resting on the kettle for `HOLD_STILL_S`; a touch in passing
    is not enough to call the step."""
    take = Take("brush")
    take.shot({"cup": CUP, "kettle": KETTLE_BASE})
    take.shot({"cup": CUP, "kettle": KETTLE_BASE}, [grip(KETTLE_BASE)], repeat=2)
    take.shot({"cup": CUP, "kettle": KETTLE_BASE})
    assert recognise(take.frames, TEA, session_id=SESSION) == []


def test_a_step_done_twice_is_reported_twice() -> None:
    """The demo's bad session pours twice (SPEC section 10). Perseveration is the
    classifier's call, so the recogniser has to hand it both pours rather than
    smoothing them into one."""
    take = Take("pour-twice")
    for _ in range(2):
        take.shot({"cup": CUP, "kettle": KETTLE_BASE}, [grip(KETTLE_BASE)])
        take.shot({"cup": CUP, "kettle": KETTLE_POURING}, [grip(KETTLE_POURING)], repeat=3)
        take.shot({"cup": CUP, "kettle": KETTLE_BASE})
    events = recognise(take.frames, TEA, session_id=SESSION)
    assert steps_in(events) == ["pour", "pour"]
    assert events[0].t_end < events[1].t_start
    assert events[0].event_id != events[1].event_id


def tea_without_actions() -> TaskGraph:
    """The tea graph with every `action:` taken out of it.

    `tasks/tea.yaml` as it stood before the action primitives existed, which is also
    what any task file somebody wrote by hand back then still looks like: the
    recogniser has to read it with the rules it always had.
    """
    data = yaml.safe_load((TASKS_DIR / "tea.yaml").read_text(encoding="utf-8"))
    for step in data["steps"]:
        step.pop("action", None)
    return parse_task_data(data, source="tea.yaml with no actions")


def test_the_primitives_read_these_clips_exactly_as_the_hand_written_rules_did() -> None:
    """The primitives are the hand-written rules generalised, not new ones: every clip
    in this file has to come out event for event the same read either way."""
    old = tea_without_actions()
    assert all(step.action is None for step in old.steps)
    for name in CLIPS:
        frames = load(name)
        assert recognise(frames, TEA, session_id=SESSION) == recognise(
            frames, old, session_id=SESSION
        ), name


def test_milk_is_read_as_a_pour_like_any_other_container() -> None:
    """The one thing the primitives changed, and what it was.

    The kettle over the cup, the milk over it and the sugar over it are one picture, so
    they are one primitive now (`pour`). Each used to be its own rule, and milk's and
    sugar's base confidence was 0.85 against the kettle's 0.90 for no reason anybody
    wrote down - so adding milk is now read exactly as confidently as pouring the water
    is. Same step, same frames, same objects; a larger number on it.
    """
    take = Take("milk")
    take.shot({"cup": CUP, "teabag": TEABAG_IN_CUP, "milk": MILK_SHELF})
    take.shot({"cup": CUP, "teabag": TEABAG_IN_CUP, "milk": MILK_SHELF}, [grip(MILK_SHELF)])
    take.shot(
        {"cup": CUP, "teabag": TEABAG_IN_CUP, "milk": MILK_POURING},
        [grip(MILK_POURING)],
        repeat=3,
    )
    now = recognise(take.frames, TEA, session_id=SESSION)
    before = recognise(take.frames, tea_without_actions(), session_id=SESSION)

    assert steps_in(now) == steps_in(before) == ["milk"]
    assert (now[0].t_start, now[0].t_end, now[0].objects) == (
        before[0].t_start,
        before[0].t_end,
        before[0].objects,
    )
    assert now[0].confidence > before[0].confidence
    assert not now[0].unclear and not before[0].unclear


def test_a_step_the_task_graph_does_not_have_is_not_reported() -> None:
    """The rule table is written for the tea graph; another task reports only the
    steps it actually has."""
    kettle_only = parse_task(
        "id: kettle_only\ntitle: Kettle only\n"
        "steps:\n  - id: fill_kettle\n    label: Fill the kettle\n    objects: [kettle]\n"
    )
    assert steps_in(recognised("make_tea", kettle_only)) == ["fill_kettle"]


# ------------------------------------------------------------------- housekeeping


def test_no_frames_no_events() -> None:
    assert recognise([], TEA, session_id=SESSION) == []


def test_the_order_frames_arrive_in_does_not_matter() -> None:
    frames = load("make_tea")
    assert recognise(reversed(frames), TEA, session_id=SESSION) == recognise(
        frames, TEA, session_id=SESSION
    )


def test_every_event_was_done_with_objects_the_task_allows() -> None:
    """A recognised step reports what it was done with, and `routine_watch.errors`
    reads that as a substitution when the task does not allow it. These rules are all
    keyed to allowed classes, so nothing here should look like one."""
    for name in CLIPS:
        for event in recognised(name):
            allowed = TEA.allowed_objects(event.step_id)
            assert {str(label) for label in event.objects} <= allowed, event


def test_the_fixture_files_match_the_helpers_that_built_them() -> None:
    for name, build in CLIPS.items():
        path = FIXTURES / f"{name}.jsonl"
        assert path.is_file(), f"{path} is missing"
        expected = as_jsonl(build())
        assert path.read_text(encoding="utf-8") == expected, (
            f"{name}.jsonl is stale: run `uv run python tests/test_recogniser.py`"
        )


def test_a_fixture_holds_no_video() -> None:
    """Boxes, landmarks and timestamps only (SPEC section 8). Every contract forbids
    unknown fields, so a line that parses cannot be hiding a frame in it."""
    for path in sorted(FIXTURES.glob("*.jsonl")):
        assert path.stem in CLIPS, f"{path.name} is not one of ours"
        assert load(path.stem)


if __name__ == "__main__":
    write_fixtures()
