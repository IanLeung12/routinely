"""The stand-in skeleton drawn into frames nobody filmed (T207).

Everything here is made-up data, so the tests are about the shape of it: a full
MediaPipe set, inside the frame, the nearer hand reaching, and the hand where the
caller asked for it - which is what keeps a stand-in frame honest about hand-object
contact (`routine_watch.recogniser` reads hand landmarks as well as hand boxes).
"""

import pytest

from routine_watch.contracts import (
    HAND_LANDMARK_COUNT,
    POSE_LANDMARK_COUNT,
    BoundingBox,
    Handedness,
)
from routine_watch.evidence import _with_skeleton
from routine_watch.recogniser import recognise
from routine_watch.replay import SCENARIOS_DIR, load_scenario
from routine_watch.stick_figure import (
    HAND_SPAN,
    REST,
    Point,
    centre_of,
    reaching_for,
    reaching_into,
)

#: Every scenario written at frame level, the only ones `_with_skeleton` ever touches.
_FRAME_SCENARIOS = [
    path.name for path in sorted(SCENARIOS_DIR.iterdir()) if (path / "frames.jsonl").is_file()
]

#: A spread of places to reach for: the corners, the middle, and well outside the
#: frame, which a caller can ask for and must never get an invalid landmark from.
POINTS: list[Point] = [
    (0.0, 0.0),
    (0.1, 0.8),
    (0.5, 0.5),
    (0.75, 0.4),
    (1.0, 1.0),
    REST,
    (1.4, -0.3),
]


def test_a_figure_has_the_full_mediapipe_set() -> None:
    pose, hand = reaching_for((0.75, 0.4))

    assert len(pose.landmarks) == POSE_LANDMARK_COUNT
    assert len(hand.landmarks) == HAND_LANDMARK_COUNT


@pytest.mark.parametrize("point", POINTS, ids=str)
def test_every_landmark_is_inside_the_frame(point: Point) -> None:
    """Landmarks are normalised to the frame, and the dashboard draws them straight
    onto its canvas, so one outside 0..1 would be drawn off the edge of the view."""
    pose, hand = reaching_for(point)

    for landmark in [*pose.landmarks, *hand.landmarks]:
        assert 0.0 <= landmark.x <= 1.0
        assert 0.0 <= landmark.y <= 1.0


@pytest.mark.parametrize("point", POINTS, ids=str)
def test_the_pose_wrist_is_the_hand_wrist(point: Point) -> None:
    """The two layers are drawn over each other, so the arm has to end where the hand
    begins (pose landmarks 15 and 16 are the wrists, hand landmark 0 is the wrist)."""
    pose, hand = reaching_for(point)

    wrist = pose.landmarks[15 if hand.handedness is Handedness.LEFT else 16]
    assert (wrist.x, wrist.y) == (hand.landmarks[0].x, hand.landmarks[0].y)


@pytest.mark.parametrize(
    ("point", "handedness"),
    [((0.1, 0.8), Handedness.RIGHT), ((0.9, 0.3), Handedness.LEFT)],
)
def test_the_nearer_hand_reaches(point: Point, handedness: Handedness) -> None:
    """Somebody facing the camera uses the hand on the side the thing is on, which in
    the camera's frame is their left for something at the larger x."""
    _, hand = reaching_for(point)

    assert hand.handedness is handedness


@pytest.mark.parametrize("point", POINTS, ids=str)
def test_the_hand_is_within_its_span_of_the_point(point: Point) -> None:
    inside = (min(1.0, max(0.0, point[0])), min(1.0, max(0.0, point[1])))
    _, hand = reaching_for(point)

    for landmark in hand.landmarks:
        assert abs(landmark.x - inside[0]) <= HAND_SPAN / 2.0 + 1e-9
        assert abs(landmark.y - inside[1]) <= HAND_SPAN / 2.0 + 1e-9


@pytest.mark.parametrize(
    "box",
    [
        BoundingBox(x1=0.85, y1=0.85, x2=0.95, y2=0.95),  # the recordings' hand box
        BoundingBox(x1=0.0, y1=0.0, x2=1.0, y2=1.0),
        BoundingBox(x1=0.4, y1=0.1, x2=0.9, y2=0.2),  # wider than it is tall
    ],
    ids=["recorded", "whole-frame", "flat"],
)
def test_a_hand_reaching_into_a_box_stays_inside_it(box: BoundingBox) -> None:
    """`reaching_into` is what `routine_watch.evidence` fills a recorded hand box with:
    a landmark outside the box would be a hand on an object the recording never said
    was touched, and the recogniser reads landmarks as well as boxes."""
    _, hand = reaching_into(box)

    for landmark in hand.landmarks:
        assert box.x1 <= landmark.x <= box.x2
        assert box.y1 <= landmark.y <= box.y2


def test_a_hand_reaching_into_a_box_is_centred_on_it() -> None:
    box = BoundingBox(x1=0.2, y1=0.3, x2=0.4, y2=0.5)
    _, hand = reaching_into(box)

    palm = hand.landmarks[9]  # the middle finger's knuckle, the centre of the template
    assert (palm.x, palm.y) == pytest.approx(centre_of(box))


def test_the_figure_leans_towards_what_it_reaches_for() -> None:
    """The whole body moves through a session, not just an arm, so the skeleton view
    has something to show even while a hand sits still on one object."""
    left, _ = reaching_for((0.1, 0.5))
    right, _ = reaching_for((0.9, 0.5))

    assert left.landmarks[23].x < right.landmarks[23].x  # the hips lean too


def test_the_same_point_always_gives_the_same_figure() -> None:
    """Deterministic, like every other stage: no clock and no random generator."""
    assert reaching_for((0.3, 0.6)) == reaching_for((0.3, 0.6))
    assert reaching_for((0.3, 0.6)) != reaching_for((0.3, 0.61))


@pytest.mark.parametrize("name", _FRAME_SCENARIOS)
def test_the_stand_in_skeleton_never_changes_what_the_recogniser_reads(name: str) -> None:
    """`evidence._with_skeleton` promises a frame read by the recogniser still says
    exactly what it did before (T207): pin that for every frame-level scenario."""
    scenario = load_scenario(SCENARIOS_DIR / name)
    session_id = scenario.frames[0].session_id

    original = recognise(scenario.frames, scenario.graph, session_id=session_id)
    skeletoned = [_with_skeleton(frame) for frame in scenario.frames]
    with_stand_in = recognise(skeletoned, scenario.graph, session_id=session_id)

    assert with_stand_in == original
