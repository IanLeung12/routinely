"""The action primitives (SPEC section 6.2): any routine recognised, no new code.

`routine_watch.actions` is the step recogniser's rules taken apart into the handful of
things people do with objects, so a task file names one per step and a routine nobody
wrote code for is still watched. Four things are checked here.

**Each primitive on its own.** One hand-built clip per primitive - boxes on a counter
and a hand on one of them, a frame at a time - and the firing it answers with, plus the
clip that looks nearly the same and must not fire: a hand brushing past is not a hold, a
straight carry is not a shake, a lid that never moved is not an opening.

**The loader.** A task file's `action:` is held to the primitive list and to the step it
is on, so a routine cannot ask to be watched for a thing the task says is not part of it
(`tasks/graph.py` would then read that thing as a substitution).

**A whole routine nobody wrote code for.** `test_a_routine_nobody_wrote_code_for_is_recognised`
is the point of the task: a protein shake, as a task file and nothing else, read off
synthetic frames into the steps it is made of. The detector has no shaker or
protein-powder class yet - that needs a training run, which is a human's job - so it is
written with the classes the running weights do have (`glass` for the shaker, `sugar`
for the scoop of powder). That substitution is in the data, which is exactly the claim:
the recogniser needed nothing.

**The second built-in routine, off frames.** Every `tests/scenarios/meds_*` is written
at step level, so `tasks/meds.yaml` had never been read off a capture stream at all -
and before the primitives it could not be, because the rule table was tea's. The last
test here plays a whole medication session through it.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence

import pytest

from routine_watch import actions
from routine_watch.actions import (
    CARRY_DISTANCE,
    HOLD_STILL_S,
    POUR_CONFIDENCE,
    SHAKE_AMPLITUDE,
    STIR_STILL_PENALTY,
    Reading,
)
from routine_watch.contracts import (
    HAND_LANDMARK_COUNT,
    POSE_LANDMARK_COUNT,
    BoundingBox,
    CaptureFrame,
    CaptureSource,
    Handedness,
    HandLandmarks,
    Landmark,
    ObjectDetection,
    ObjectLabel,
    Pose,
)
from routine_watch.errors import classify_errors
from routine_watch.recogniser import recognise
from routine_watch.tasks import TaskGraphError, load_task, parse_task

#: Fixtures are written at this frame rate: slow, so a clip stays short enough to read.
#: A frame missing at 2 fps is half a second, which is a hand letting go rather than the
#: detector blinking (`actions.FLICKER_GAP_S`), so one empty shot ends a contact.
FPS = 2.0

#: How sure the detector is of every box, held fixed so a primitive's own confidence is
#: the only thing that moves.
CONFIDENCE = 0.9

#: Half the width of a hand box. A hand is written as the detector's own `hand` class
#: rather than 21 landmarks on one spot; both read the same
#: (`test_a_wrist_landmark_reads_the_same_as_a_hand_box`).
HAND_REACH = 0.02

Point = tuple[float, float]


def box(x1: float, y1: float, x2: float, y2: float) -> BoundingBox:
    return BoundingBox(x1=x1, y1=y1, x2=x2, y2=y2)


def grip(at: BoundingBox) -> Point:
    """A hand holding `at`: it lands in the middle of the box."""
    return (at.x1 + at.x2) / 2.0, (at.y1 + at.y2) / 2.0


# ------------------------------------------------------------------------- the counter

#: The shaker, on the shelf and on the counter where it is filled.
GLASS_SHELF = box(0.10, 0.20, 0.20, 0.36)
GLASS_COUNTER = box(0.40, 0.44, 0.50, 0.60)

#: The shaker shaken: up and down, which is what the wrist holding it does. The two
#: places are `SWING` apart, which is well over `actions.SHAKE_AMPLITUDE`.
SWING = 0.08
GLASS_UP = box(0.40, 0.30, 0.50, 0.46)
GLASS_DOWN = box(GLASS_UP.x1, GLASS_UP.y1 + SWING, GLASS_UP.x2, GLASS_UP.y2 + SWING)

#: The shaker up at the mouth.
GLASS_AT_FACE = box(0.40, 0.10, 0.50, 0.26)

#: The scoop of powder, on the counter and tipped into the shaker.
SUGAR_COUNTER = box(0.70, 0.50, 0.78, 0.58)
SUGAR_IN_GLASS = box(0.43, 0.46, 0.47, 0.52)

#: The milk, on the shelf and held over the shaker.
MILK_SHELF = box(0.84, 0.50, 0.94, 0.66)
MILK_POURING = box(0.42, 0.26, 0.52, 0.42)

#: The detector's own `pouring` class, over the shaker.
POURING = box(0.41, 0.34, 0.53, 0.58)

#: A spoon in the shaker, at each end of a stir.
SPOON_COUNTER = box(0.62, 0.62, 0.78, 0.68)
SPOON_LEFT = box(0.43, 0.42, 0.47, 0.58)
SPOON_RIGHT = box(0.45, 0.42, 0.49, 0.58)

#: The pill organiser shut, and with its lid swung open.
ORGANISER_SHUT = box(0.40, 0.50, 0.56, 0.58)
ORGANISER_OPEN = box(0.40, 0.50, 0.72, 0.58)

#: Where the face is in every clip that has a body in it, well clear of the counter.
FACE = (0.45, 0.12)


# ------------------------------------------------------------- building the frames


def hand_box(at: Point) -> ObjectDetection:
    """A hand on `at`, as the detector's `hand` class sees it."""
    x, y = at
    return ObjectDetection(
        label=ObjectLabel.HAND,
        confidence=CONFIDENCE,
        box=box(x - HAND_REACH, y - HAND_REACH, x + HAND_REACH, y + HAND_REACH),
    )


def facing(at: Point) -> Pose:
    """One body in frame with its nose and mouth at `at`.

    The rest of the skeleton is parked at the bottom of the frame: `bring_to_face`
    reads `actions.FACE_LANDMARKS` and nothing else.
    """
    marks = [Landmark(x=0.5, y=0.95, z=0.0, visibility=0.9) for _ in range(POSE_LANDMARK_COUNT)]
    for index in actions.FACE_LANDMARKS:
        marks[index] = Landmark(x=at[0], y=at[1], z=0.0, visibility=0.9)
    return Pose(landmarks=marks, score=0.9)


class Clip:
    """Frames of one hand-built session, numbered and timed as they are added."""

    def __init__(self, session: str = "clip", *, fps: float = FPS) -> None:
        self.session = session
        self.fps = fps
        self.frames: list[CaptureFrame] = []

    def shot(
        self,
        objects: Mapping[str, BoundingBox],
        hands: Sequence[Point] = (),
        *,
        face: Point | None = None,
        confidence: Mapping[str, float] | None = None,
        repeat: int = 1,
    ) -> Clip:
        """`repeat` frames of the counter looking like this."""
        sure = confidence or {}
        for _ in range(repeat):
            seq = len(self.frames)
            self.frames.append(
                CaptureFrame(
                    session_id=self.session,
                    seq=seq,
                    t=round(seq / self.fps, 3),
                    source=CaptureSource.SYNTHETIC,
                    poses=[] if face is None else [facing(face)],
                    hands=[],
                    objects=[
                        ObjectDetection(
                            label=ObjectLabel(label),
                            confidence=sure.get(label, CONFIDENCE),
                            box=where,
                        )
                        for label, where in objects.items()
                    ]
                    + [hand_box(at) for at in hands],
                )
            )
        return self

    def gap(self, objects: Mapping[str, BoundingBox] | None = None, repeat: int = 1) -> Clip:
        """Frames with nothing in a hand: the contact ends here."""
        return self.shot(objects or {}, repeat=repeat)

    @property
    def reading(self) -> Reading:
        """The frames as the primitives read them."""
        return actions.read(self.frames)


def swung(clip: Clip, objects: Mapping[str, BoundingBox], up: str, times: int) -> Clip:
    """`times` frames of `objects` with `up` alternating between its two places.

    `up` names the key of a two-element tuple in `objects`, which is how a shake is
    written: the thing in the hand goes up, down, up, down, and the hand goes with it.
    """
    for step in range(times):
        where = objects[up][step % 2]
        clip.shot({**{k: v for k, v in objects.items() if k != up}, up: where}, [grip(where)])
    return clip


def last(reading: Reading) -> int:
    """The index of the newest frame: what a primitive is usually asked about."""
    return len(reading) - 1


# ------------------------------------------------------------- pick_up, hold, return


def carried() -> Reading:
    """The shaker taken off the shelf and set down on the counter."""
    clip = Clip().gap({"glass": GLASS_SHELF})
    clip.shot({"glass": GLASS_SHELF}, [grip(GLASS_SHELF)])
    clip.shot({"glass": GLASS_COUNTER}, [grip(GLASS_COUNTER)], repeat=2)
    return clip.gap({"glass": GLASS_COUNTER}).reading


def test_pick_up_is_carried_somewhere_not_touched_where_it_stands() -> None:
    reading = carried()
    firing = actions.pick_up(reading, 2, "glass")
    assert firing is not None
    strength, objects = firing
    assert objects == ("glass",)
    assert strength == pytest.approx(actions.PICK_UP_CONFIDENCE * CONFIDENCE)
    # A hand on it before it has gone anywhere is the same contact, so the whole of it
    # reads as a pick-up: the contact is what the rules see, not one frame of it.
    assert actions.pick_up(reading, 1, "glass") == firing
    # Nothing in a hand, nothing picked up.
    assert actions.pick_up(reading, 0, "glass") is None


def test_a_hand_resting_on_something_is_not_picking_it_up() -> None:
    clip = Clip().shot({"glass": GLASS_COUNTER}, [grip(GLASS_COUNTER)], repeat=4)
    reading = clip.reading
    assert actions.pick_up(reading, last(reading), "glass") is None


def test_hold_is_the_contact_that_goes_nowhere() -> None:
    clip = Clip().shot({"glass": GLASS_COUNTER}, [grip(GLASS_COUNTER)], repeat=4)
    reading = clip.reading
    firing = actions.hold(reading, last(reading), "glass")
    assert firing is not None
    assert firing == (pytest.approx(actions.HOLD_CONFIDENCE * CONFIDENCE), ("glass",))
    # Carried off instead: that is a pick-up, and never a hold.
    assert actions.hold(carried(), 2, "glass") is None


def test_brushing_past_something_is_not_holding_it() -> None:
    """`seconds` is the whole point of `hold`: a touch in passing is not the switch."""
    clip = Clip().shot({"glass": GLASS_COUNTER}, [grip(GLASS_COUNTER)], repeat=2)
    reading = clip.reading
    assert reading.contacts[1]["glass"].seconds < HOLD_STILL_S
    assert actions.hold(reading, 1, "glass") is None
    # Asked for less time than it was held for, the same frames do fire.
    assert actions.hold(reading, 1, "glass", seconds=0.5) is not None


def test_return_is_carried_and_set_back_down() -> None:
    clip = Clip().shot({"glass": GLASS_SHELF}, [grip(GLASS_SHELF)])
    clip.shot({"glass": GLASS_COUNTER}, [grip(GLASS_COUNTER)])
    clip.shot({"glass": GLASS_SHELF}, [grip(GLASS_SHELF)])
    reading = clip.reading
    assert reading.contacts[2]["glass"].travel >= CARRY_DISTANCE
    firing = actions.return_(reading, 2, "glass")
    assert firing == (pytest.approx(actions.RETURN_CONFIDENCE * CONFIDENCE), ("glass",))
    # On the way out it is not back yet.
    assert actions.return_(reading, 1, "glass") is None
    # A carry that ends somewhere else is not a return, however far it went.
    assert actions.return_(carried(), 2, "glass") is None


# --------------------------------------------------------------- put_into, take_out


def dropped_in() -> Reading:
    """The scoop of powder taken off the counter and tipped into the shaker."""
    clip = Clip().gap({"glass": GLASS_COUNTER, "sugar": SUGAR_COUNTER})
    clip.shot({"glass": GLASS_COUNTER, "sugar": SUGAR_COUNTER}, [grip(SUGAR_COUNTER)])
    clip.shot(
        {"glass": GLASS_COUNTER, "sugar": SUGAR_IN_GLASS}, [grip(SUGAR_IN_GLASS)], repeat=2
    )
    return clip.reading


def test_put_into_is_carried_in_from_outside() -> None:
    reading = dropped_in()
    firing = actions.put_into(reading, last(reading), "sugar", "glass")
    assert firing is not None
    strength, objects = firing
    assert objects == ("sugar", "glass")
    assert strength == pytest.approx(actions.PUT_INTO_CONFIDENCE * CONFIDENCE)
    # Still outside on the frame the hand took hold of it.
    assert actions.put_into(reading, 1, "sugar", "glass") is None


def test_something_already_in_there_is_not_put_into_it() -> None:
    """What tells putting the teabag in from stirring it about in there: the contact
    started with it already inside."""
    clip = Clip().shot(
        {"glass": GLASS_COUNTER, "sugar": SUGAR_IN_GLASS}, [grip(SUGAR_IN_GLASS)], repeat=3
    )
    reading = clip.reading
    assert actions.put_into(reading, last(reading), "sugar", "glass") is None


def test_take_out_is_put_into_the_other_way_round() -> None:
    clip = Clip().shot(
        {"glass": GLASS_COUNTER, "sugar": SUGAR_IN_GLASS}, [grip(SUGAR_IN_GLASS)]
    )
    clip.shot({"glass": GLASS_COUNTER, "sugar": SUGAR_COUNTER}, [grip(SUGAR_COUNTER)], repeat=2)
    reading = clip.reading
    firing = actions.take_out(reading, last(reading), "sugar", "glass")
    # The thing taken out is what the step was done with; the container is not reported,
    # so a task that does not list it is not read as a substitution.
    assert firing == (pytest.approx(actions.TAKE_OUT_CONFIDENCE * CONFIDENCE), ("sugar",))
    # It has to have been in there: the same frames the other way round say nothing.
    assert actions.take_out(dropped_in(), last(dropped_in()), "sugar", "glass") is None


# --------------------------------------------------------------------- pour and stir


def poured(*, with_class: bool = False) -> Reading:
    """The milk lifted off the shelf and held over the shaker."""
    clip = Clip().gap({"glass": GLASS_COUNTER, "milk": MILK_SHELF})
    clip.shot({"glass": GLASS_COUNTER, "milk": MILK_SHELF}, [grip(MILK_SHELF)])
    over = {"glass": GLASS_COUNTER, "milk": MILK_POURING}
    clip.shot({**over, "pouring": POURING} if with_class else over, [grip(MILK_POURING)], repeat=2)
    return clip.reading


def test_pour_is_held_over_the_thing_it_goes_into() -> None:
    reading = poured()
    firing = actions.pour(reading, last(reading), "milk", "glass")
    assert firing == (pytest.approx(POUR_CONFIDENCE * CONFIDENCE), ("milk", "glass"))
    # Standing on the shelf beside it is not pouring into it.
    assert actions.pour(reading, 1, "milk", "glass") is None


def test_the_pouring_class_is_enough_on_its_own() -> None:
    """The detector has a class for the act itself (SPEC section 6.1). When it fires
    over the thing being filled, that is a pour whether or not a hand is on anything."""
    clip = Clip().shot({"glass": GLASS_COUNTER, "pouring": POURING}, repeat=3)
    reading = clip.reading
    firing = actions.pour(reading, last(reading), "milk", "glass")
    assert firing is not None
    strength, objects = firing
    assert strength == pytest.approx(actions.POURING_CLASS_CONFIDENCE * CONFIDENCE)
    # No milk box to name, so the step is reported with what there was.
    assert objects == ("glass",)
    # Both readings at once: the stronger one is the answer.
    both = poured(with_class=True)
    assert actions.pour(both, last(both), "milk", "glass") == (
        pytest.approx(actions.POURING_CLASS_CONFIDENCE * CONFIDENCE),
        ("milk", "glass"),
    )


def test_stir_is_held_inside_and_going_back_and_forth() -> None:
    clip = Clip().shot({"glass": GLASS_COUNTER, "spoon": SPOON_COUNTER}, [grip(SPOON_COUNTER)])
    for where in (SPOON_LEFT, SPOON_RIGHT, SPOON_LEFT, SPOON_RIGHT):
        clip.shot({"glass": GLASS_COUNTER, "spoon": where}, [grip(where)])
    reading = clip.reading
    firing = actions.stir(reading, last(reading), "spoon", "glass")
    assert firing == (pytest.approx(actions.STIR_CONFIDENCE * CONFIDENCE), ("spoon", "glass"))


def test_a_spoon_left_standing_in_it_is_the_same_picture_with_less_to_say() -> None:
    clip = Clip().shot({"glass": GLASS_COUNTER, "spoon": SPOON_LEFT}, [grip(SPOON_LEFT)], repeat=4)
    reading = clip.reading
    firing = actions.stir(reading, last(reading), "spoon", "glass")
    assert firing is not None
    assert firing[0] == pytest.approx(actions.STIR_CONFIDENCE * CONFIDENCE * STIR_STILL_PENALTY)


# -------------------------------------------------------------------- open and close


def test_open_is_the_box_opening_out_while_it_is_held() -> None:
    clip = Clip().shot({"pill_organiser": ORGANISER_SHUT}, [grip(ORGANISER_SHUT)])
    clip.shot({"pill_organiser": ORGANISER_OPEN}, [grip(ORGANISER_OPEN)], repeat=2)
    reading = clip.reading
    firing = actions.open_(reading, last(reading), "pill_organiser")
    assert firing == (
        pytest.approx(actions.OPEN_CONFIDENCE * CONFIDENCE),
        ("pill_organiser",),
    )
    assert actions.close_(reading, last(reading), "pill_organiser") is None


def test_close_is_the_same_reading_the_other_way_round() -> None:
    clip = Clip().shot({"pill_organiser": ORGANISER_OPEN}, [grip(ORGANISER_OPEN)])
    clip.shot({"pill_organiser": ORGANISER_SHUT}, [grip(ORGANISER_SHUT)], repeat=2)
    reading = clip.reading
    assert actions.close_(reading, last(reading), "pill_organiser") is not None
    assert actions.open_(reading, last(reading), "pill_organiser") is None


def test_a_lid_that_never_moved_is_neither_opened_nor_closed() -> None:
    clip = Clip().shot({"pill_organiser": ORGANISER_SHUT}, [grip(ORGANISER_SHUT)], repeat=4)
    reading = clip.reading
    assert actions.open_(reading, last(reading), "pill_organiser") is None
    assert actions.close_(reading, last(reading), "pill_organiser") is None


# ------------------------------------------------------------------------- the shake


def swings(amplitude: float) -> tuple[BoundingBox, BoundingBox]:
    """The two places the shaker swings between, `amplitude` of the frame apart."""
    low = box(GLASS_UP.x1, GLASS_UP.y1 + amplitude, GLASS_UP.x2, GLASS_UP.y2 + amplitude)
    return GLASS_UP, low


def shaken(times: int = 10, *, amplitude: float = SWING) -> Reading:
    """The shaker held and swung up and down `times` frames running.

    A smaller `amplitude` is how a shake too small to tell from the detector wobbling
    is written.
    """
    return swung(Clip(), {"glass": swings(amplitude)}, "glass", times).reading


def test_shake_is_the_wrist_holding_it_swinging_back_and_forth() -> None:
    reading = shaken()
    firing = actions.shake(reading, last(reading), "glass")
    assert firing == (pytest.approx(actions.SHAKE_CONFIDENCE * CONFIDENCE), ("glass",))


def test_a_shake_needs_enough_swings_to_be_one() -> None:
    """`actions.SHAKE_REVERSALS` changes of direction inside `SHAKE_WINDOW_S`. Two
    swings is somebody adjusting their grip."""
    reading = shaken(times=3)
    assert actions.shake(reading, last(reading), "glass") is None
    assert actions.shake(shaken(times=6), 5, "glass") is not None


def test_a_straight_carry_is_not_a_shake() -> None:
    """The same wrist, moving as far, never turning back."""
    clip = Clip()
    for step in range(10):
        where = box(0.10 + 0.04 * step, 0.30, 0.20 + 0.04 * step, 0.46)
        clip.shot({"glass": where}, [grip(where)])
    reading = clip.reading
    assert reading.contacts[9]["glass"].travel >= CARRY_DISTANCE
    assert actions.shake(reading, last(reading), "glass") is None


def test_a_wobble_too_small_to_see_is_not_a_shake() -> None:
    reading = shaken(amplitude=SHAKE_AMPLITUDE / 2)
    assert actions.shake(reading, last(reading), "glass") is None


def test_a_shake_is_bounded_by_the_contact_it_is_in() -> None:
    """A hand that let go and took hold again did not swing the thing twice: the two
    halves are different contacts, and neither is a shake on its own."""
    clip = swung(Clip(), {"glass": swings(SWING)}, "glass", 3)
    clip.gap({"glass": GLASS_DOWN})
    swung(clip, {"glass": swings(SWING)}, "glass", 3)
    reading = clip.reading
    assert actions.shake(reading, last(reading), "glass") is None


def test_a_wrist_landmark_reads_the_same_as_a_hand_box() -> None:
    """Capture gives both (SPEC section 16, "Hands"); a shake read off MediaPipe's
    wrist landmark has to be the same shake."""
    frames = [
        frame.model_copy(
            update={
                "objects": [
                    found for found in frame.objects if found.label is not ObjectLabel.HAND
                ],
                "hands": [
                    HandLandmarks(
                        handedness=Handedness.RIGHT,
                        score=found.confidence,
                        landmarks=[
                            Landmark(x=grip(found.box)[0], y=grip(found.box)[1], z=0.0)
                            for _ in range(HAND_LANDMARK_COUNT)
                        ],
                    )
                    for found in frame.objects
                    if found.label is ObjectLabel.HAND
                ],
            }
        )
        for frame in swung(Clip(), {"glass": swings(SWING)}, "glass", 10).frames
    ]
    reading = actions.read(frames)
    assert actions.shake(reading, last(reading), "glass") is not None


# ------------------------------------------------------------------- bring_to_face


def test_bring_to_face_is_up_at_the_nose_and_mouth() -> None:
    clip = Clip().shot({"glass": GLASS_COUNTER}, [grip(GLASS_COUNTER)], face=FACE)
    clip.shot({"glass": GLASS_AT_FACE}, [grip(GLASS_AT_FACE)], face=FACE, repeat=2)
    reading = clip.reading
    firing = actions.bring_to_face(reading, last(reading), "glass")
    assert firing == (pytest.approx(actions.BRING_TO_FACE_CONFIDENCE * CONFIDENCE), ("glass",))
    # Down on the counter it is not at anybody's mouth.
    assert actions.bring_to_face(reading, 0, "glass") is None


def test_with_nobody_in_frame_there_is_no_face_to_have_brought_it_to() -> None:
    """Read off the pose landmarks, so a recording of boxes alone says nothing either
    way - which is the honest answer rather than a step that never happened."""
    clip = Clip().shot({"glass": GLASS_AT_FACE}, [grip(GLASS_AT_FACE)], repeat=3)
    reading = clip.reading
    assert reading.scenes[0].face == ()
    assert actions.bring_to_face(reading, last(reading), "glass") is None


# ------------------------------------------------------- what the task file may say


def toy(action: str, *, objects: str = "[cup]", extra: str = "") -> str:
    """The smallest task file with one `action:` in it."""
    return (
        f"id: toy\ntitle: Toy\n{extra}steps:\n"
        f"  - id: first\n    label: First\n    objects: {objects}\n    action: {action}\n"
    )


def test_a_step_says_which_action_it_is() -> None:
    graph = parse_task(
        toy("{type: put_into, object: teabag, target: cup}", objects="[teabag, cup]")
    )
    assert graph.step("first").action == actions.Action(
        type="put_into", objects=("teabag",), target="cup"
    )
    # A step that says nothing has no action, and the recogniser falls back to its own
    # hand-written rules for it.
    silent = parse_task(
        "id: toy\ntitle: Toy\nsteps:\n  - id: first\n    label: F\n    objects: [cup]\n"
    )
    assert silent.step("first").action is None


@pytest.mark.parametrize("spelling", ["target: cup", "into: cup", "in: cup", "from: cup"])
def test_the_thing_it_is_done_to_can_be_spelled_whichever_way_reads_best(spelling: str) -> None:
    graph = parse_task(
        toy(f"{{type: put_into, object: teabag, {spelling}}}", objects="[teabag, cup]")
    )
    assert graph.step("first").action == actions.Action(
        type="put_into", objects=("teabag",), target="cup"
    )


def test_an_action_may_name_either_of_two_things_that_count() -> None:
    """A bottle and a weekly organiser are both how somebody keeps their pills."""
    graph = parse_task(
        toy(
            "{type: open, object: [pill_bottle, pill_organiser]}",
            objects="[pill_bottle, pill_organiser]",
        )
    )
    assert graph.step("first").action == actions.Action(
        type="open", objects=("pill_bottle", "pill_organiser")
    )


def test_an_action_naming_an_alias_is_read_as_the_class_it_means() -> None:
    """`tasks/graph.py` resolves aliases, so the recogniser only ever sees the classes
    the detector actually reports."""
    graph = parse_task(
        toy(
            "{type: stir, object: teaspoon, in: cup}",
            objects="[spoon, cup]",
            extra="aliases:\n  teaspoon: spoon\n",
        )
    )
    assert graph.step("first").action == actions.Action(
        type="stir", objects=("spoon",), target="cup"
    )


def test_hold_takes_how_long_for_and_defaults_to_the_threshold() -> None:
    assert parse_task(toy("{type: hold, object: cup, seconds: 2.5}")).step("first").action == (
        actions.Action(type="hold", objects=("cup",), seconds=2.5)
    )
    held = parse_task(toy("{type: hold, object: cup}")).step("first").action
    assert held is not None and held.seconds is None


@pytest.mark.parametrize(
    ("action", "objects", "message"),
    [
        ("{type: nonsense, object: cup}", "[cup]", "no action called 'nonsense'"),
        ("{type: put_into, object: cup}", "[cup]", "needs a target"),
        ("{type: pick_up, object: cup, target: cup}", "[cup]", "takes no target"),
        ("{type: pick_up, object: cup, seconds: 2}", "[cup]", "takes no seconds"),
        ("{type: pick_up, object: spoon}", "[cup]", "names \\['spoon'\\]"),
        ("{type: put_into, object: cup, into: spoon}", "[cup]", "names \\['spoon'\\]"),
        ("{type: pick_up, object: cup, sideways: true}", "[cup]", "Extra inputs"),
        ("{object: cup}", "[cup]", "type"),
        ("{type: pick_up, object: []}", "[cup]", "object"),
    ],
)
def test_an_action_the_step_cannot_be_watched_for_is_refused(
    action: str, objects: str, message: str
) -> None:
    """A routine cannot ask to be watched for a thing its own step says is not part of
    it: `routine_watch.errors` would read that thing as a substitution."""
    with pytest.raises(TaskGraphError, match=message):
        parse_task(toy(action, objects=objects))


def test_every_primitive_is_named_and_says_what_it_is() -> None:
    """The names are the task file's vocabulary and the drafter's prompt, so a
    primitive with no summary would reach a model as a bare word."""
    assert set(actions.ACTION_TYPES) == set(actions.PRIMITIVES)
    assert len(actions.ACTION_TYPES) == len(actions.PRIMITIVES)
    for name, primitive in actions.PRIMITIVES.items():
        assert primitive.name == name
        assert primitive.summary
        assert not (primitive.target and primitive.seconds), name


# ---------------------------------------------- a whole routine, with no new code

PROTEIN_SHAKE = """
id: protein_shake
title: Make a protein shake

steps:
  - id: get_shaker
    label: Get the shaker
    objects: [glass]
    action: {type: pick_up, object: glass}

  - id: powder_in
    label: Put a scoop of powder in
    deps: [get_shaker]
    objects: [sugar, glass]
    action: {type: put_into, object: sugar, into: glass}

  - id: milk_in
    label: Pour the milk in
    deps: [get_shaker]
    objects: [milk, glass]
    action: {type: pour, object: milk, into: glass}

  - id: shake_it
    label: Shake it
    deps: [powder_in, milk_in]
    objects: [glass]
    action: {type: shake, object: glass}

  - id: drink_it
    label: Drink it
    deps: [shake_it]
    objects: [glass]
    once_only: false
    action: {type: bring_to_face, object: glass}
"""


def protein_shake_clip() -> Clip:
    """One good protein shake: fetch the shaker, powder, milk, shake, drink.

    Every contact ends with a frame of nothing in a hand, which at `FPS` is the hand
    letting go rather than the detector blinking.
    """
    clip = Clip("protein-shake")

    # Fetch the shaker off the shelf.
    counter = {"sugar": SUGAR_COUNTER, "milk": MILK_SHELF}
    clip.shot({**counter, "glass": GLASS_SHELF}, face=FACE)
    clip.shot({**counter, "glass": GLASS_SHELF}, [grip(GLASS_SHELF)], face=FACE)
    clip.shot({**counter, "glass": GLASS_COUNTER}, [grip(GLASS_COUNTER)], face=FACE, repeat=2)
    clip.shot({**counter, "glass": GLASS_COUNTER}, face=FACE)

    # A scoop of powder into it.
    clip.shot({**counter, "glass": GLASS_COUNTER}, [grip(SUGAR_COUNTER)], face=FACE)
    filled = {"sugar": SUGAR_IN_GLASS, "milk": MILK_SHELF, "glass": GLASS_COUNTER}
    clip.shot(filled, [grip(SUGAR_IN_GLASS)], face=FACE, repeat=3)
    clip.shot(filled, face=FACE)

    # Milk from the shelf, held over it.
    clip.shot(filled, [grip(MILK_SHELF)], face=FACE)
    pouring = {**filled, "milk": MILK_POURING}
    clip.shot(pouring, [grip(MILK_POURING)], face=FACE, repeat=3)
    clip.shot(filled, face=FACE)

    # Shake it: the shaker, the powder in it and the wrist all go up and down together.
    for step in range(10):
        up = step % 2 == 0
        clip.shot(
            {
                "glass": GLASS_UP if up else GLASS_DOWN,
                "sugar": SUGAR_IN_GLASS if up else SUGAR_IN_GLASS,
                "milk": MILK_SHELF,
            },
            [grip(GLASS_UP if up else GLASS_DOWN)],
            face=FACE,
        )
    clip.shot(filled, face=FACE)

    # Drink it.
    clip.shot(filled, [grip(GLASS_COUNTER)], face=FACE)
    at_face = {"glass": GLASS_AT_FACE, "sugar": SUGAR_IN_GLASS, "milk": MILK_SHELF}
    clip.shot(at_face, [grip(GLASS_AT_FACE)], face=FACE, repeat=3)
    return clip.shot(filled, face=FACE)


def test_a_routine_nobody_wrote_code_for_is_recognised() -> None:
    """The point of the task: a protein shake is a task file and nothing else.

    No rule anywhere mentions a shaker, a scoop of powder or shaking something, and the
    session still comes out as the five steps it is made of, in order, each confidently
    seen - and the error classifier has nothing to say about a routine done properly.
    """
    graph = parse_task(PROTEIN_SHAKE)
    events = recognise(protein_shake_clip().frames, graph, session_id="shake-1")

    assert [event.step_id for event in events] == [
        "get_shaker",
        "powder_in",
        "milk_in",
        "shake_it",
        "drink_it",
    ]
    assert graph.is_valid_order([event.step_id for event in events])
    for event in events:
        assert not event.unclear, event
        assert event.t_start < event.t_end
        assert {str(label) for label in event.objects} <= graph.allowed_objects(event.step_id)
    for before, after in zip(events, events[1:], strict=False):
        assert before.t_end < after.t_start, f"{before.step_id} runs into {after.step_id}"
    assert classify_errors(events, graph, session_id="shake-1") == []


def test_shaking_the_shaker_is_not_also_picking_it_up_again() -> None:
    """Plain handling: `pick_up` is the reading left over when nothing more specific
    happened in the same contact. Without that, shaking the thing you are holding would
    read as fetching it a second time - which `get_shaker` being `once_only` would then
    report as perseveration.
    """
    graph = parse_task(PROTEIN_SHAKE)
    events = recognise(protein_shake_clip().frames, graph, session_id="shake-1")
    assert [event.step_id for event in events].count("get_shaker") == 1


def test_a_task_can_mix_an_action_with_the_hand_written_rules() -> None:
    """A task file written before actions existed keeps working, step by step.

    `boil` says nothing about how to see it, so the recogniser reads it with the rule it
    always had; `shake_it` says, and is read with the primitive. The hand-written rules
    carry their own exclusions and know nothing about actions, so a task that mixes the
    two on the *same* object is on its own - which is why `tasks/tea.yaml` names an
    action for every step rather than some of them.
    """
    mixed = parse_task(
        "id: mixed\ntitle: Mixed\nsteps:\n"
        "  - id: boil\n    label: Boil the kettle\n    objects: [kettle]\n"
        "  - id: shake_it\n    label: Shake it\n    deps: [boil]\n    objects: [cup]\n"
        "    action: {type: shake, object: cup}\n"
    )
    assert mixed.step("boil").action is None
    assert mixed.step("shake_it").action is not None

    clip = Clip("mixed")
    clip.shot({"kettle": GLASS_COUNTER}, [grip(GLASS_COUNTER)], repeat=4)
    clip.gap()
    swung(clip, {"cup": swings(SWING)}, "cup", 10)
    events = recognise(clip.frames, mixed, session_id="mixed-1")
    assert [event.step_id for event in events] == ["boil", "shake_it"]


# ------------------------------------------------- the second built-in routine, live

#: The glass on the shelf, on the counter, and up at the mouth.
MEDS_GLASS_SHELF = box(0.08, 0.20, 0.18, 0.36)
MEDS_GLASS_COUNTER = box(0.30, 0.44, 0.40, 0.60)
MEDS_GLASS_AT_FACE = box(0.40, 0.10, 0.50, 0.26)

#: The water jug on its shelf, and held over the glass.
JUG_SHELF = box(0.84, 0.46, 0.96, 0.66)
JUG_POURING = box(0.32, 0.26, 0.44, 0.42)

#: The organiser, shut and with its lid swung open.
MEDS_SHUT = box(0.58, 0.50, 0.74, 0.58)
MEDS_OPEN = box(0.58, 0.50, 0.90, 0.58)


def meds_clip() -> Clip:
    """One good medication session: glass, water, organiser, pill, swallow, shut it."""
    clip = Clip("meds")
    shelf = {"water_jug": JUG_SHELF, "pill_organiser": MEDS_SHUT}

    # Fetch the glass and fill it from the jug.
    clip.shot({**shelf, "glass": MEDS_GLASS_SHELF}, face=FACE)
    clip.shot({**shelf, "glass": MEDS_GLASS_SHELF}, [grip(MEDS_GLASS_SHELF)], face=FACE)
    clip.shot({**shelf, "glass": MEDS_GLASS_COUNTER}, [grip(MEDS_GLASS_COUNTER)], face=FACE,
              repeat=2)
    counter = {"glass": MEDS_GLASS_COUNTER, "pill_organiser": MEDS_SHUT}
    clip.shot({**counter, "water_jug": JUG_SHELF}, face=FACE)
    clip.shot({**counter, "water_jug": JUG_SHELF}, [grip(JUG_SHELF)], face=FACE)
    clip.shot({**counter, "water_jug": JUG_POURING}, [grip(JUG_POURING)], face=FACE, repeat=3)
    clip.shot({**counter, "water_jug": JUG_SHELF}, face=FACE)

    # Open the organiser: its box opens out while it is in a hand.
    still = {"glass": MEDS_GLASS_COUNTER, "water_jug": JUG_SHELF}
    clip.shot({**still, "pill_organiser": MEDS_SHUT}, [grip(MEDS_SHUT)], face=FACE)
    clip.shot({**still, "pill_organiser": MEDS_OPEN}, [grip(MEDS_OPEN)], face=FACE, repeat=2)
    clip.shot({**still, "pill_organiser": MEDS_OPEN}, face=FACE)

    # Take the pill out: a hand in the open organiser, where it stands.
    clip.shot({**still, "pill_organiser": MEDS_OPEN}, [grip(MEDS_OPEN)], face=FACE, repeat=4)
    clip.shot({**still, "pill_organiser": MEDS_OPEN}, face=FACE)

    # Swallow it with the water.
    clip.shot({**still, "pill_organiser": MEDS_OPEN}, [grip(MEDS_GLASS_COUNTER)], face=FACE)
    up = {"glass": MEDS_GLASS_AT_FACE, "water_jug": JUG_SHELF, "pill_organiser": MEDS_OPEN}
    clip.shot(up, [grip(MEDS_GLASS_AT_FACE)], face=FACE, repeat=3)
    clip.shot({**still, "pill_organiser": MEDS_OPEN}, face=FACE)

    # Shut the organiser again.
    clip.shot({**still, "pill_organiser": MEDS_OPEN}, [grip(MEDS_OPEN)], face=FACE)
    clip.shot({**still, "pill_organiser": MEDS_SHUT}, [grip(MEDS_SHUT)], face=FACE, repeat=2)
    return clip.shot({**still, "pill_organiser": MEDS_SHUT}, face=FACE)


def test_the_medication_routine_is_recognised_off_its_own_task_file() -> None:
    """`tasks/meds.yaml` names an action per step now, and nothing else in the repo
    mentions a pill organiser. Every meds scenario is written at step level
    (`tests/scenarios/meds_*/steps.jsonl`), so this is the only place the second
    built-in routine is read off frames at all.
    """
    graph = load_task("meds")
    events = recognise(meds_clip().frames, graph, session_id="meds-1")

    assert [event.step_id for event in events] == [
        "get_glass",
        "fill_glass",
        "open_organiser",
        "take_pill",
        "drink_water",
        "close_organiser",
    ]
    assert graph.is_valid_order([event.step_id for event in events])
    for event in events:
        assert not event.unclear, event
        assert {str(label) for label in event.objects} <= graph.allowed_objects(event.step_id)
    assert classify_errors(events, graph, session_id="meds-1") == []
