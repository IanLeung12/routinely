"""A stand-in skeleton for frames nobody filmed (SPEC sections 8 and 10, step 3).

Two of the demo's screens draw a body: the live "skeleton view" and the alert's
"Today / Usual" ghost replay. Both are fed by frames that were never in front of a
camera - a scenario written at step level (`routine_watch.live._synthetic_frames`) or
the frame-level recordings that stand in for a demo resident's own sessions
(`routine_watch.evidence`) - and a made-up frame with `poses=[]` leaves those screens
with nothing to draw but object boxes (T207).

    pose, hand = reaching_for((0.7, 0.4))   # somebody reaching for the kettle
    pose, hand = reaching_into(hand_box)    # ... for the hand a recording tracks

What comes back is a plain, obviously schematic figure: a person standing at the
counter facing the camera, reaching for a point with whichever hand is nearer it,
leaning that way a little. Everything is normalised to the frame (0..1) and
deterministic, so the same point always gives the same skeleton.

This is made-up data, like `live._PLACEHOLDER_BOXES`, and it is only ever used where
the alternative is an empty frame: real capture (`routine_watch.capture`) brings its
own MediaPipe landmarks and never comes through here. It cannot leak a frame either -
it writes landmarks and nothing else, and `CaptureFrame` has no field for an image
(SPEC section 8).
"""

from __future__ import annotations

from .capture import COORD_DIGITS
from .contracts import BoundingBox, Handedness, HandLandmarks, Landmark, Pose

#: A point in the frame: x, y, normalised to 0..1 like every landmark.
Point = tuple[float, float]

#: Where a hand waits when it is not on anything: off to the side, which is where the
#: frame-level recordings park theirs between steps (`tests/scenarios/tea_normal`).
REST: Point = (0.9, 0.9)

#: How wide a stand-in hand is, as a fraction of the frame.
HAND_SPAN = 0.08

#: Made up, and plausible: these are not measurements of anybody.
_CONFIDENCE = 0.9

#: Pose landmarks carry a visibility; hand landmarks do not (`routine_watch.capture`).
_VISIBILITY = 0.9

#: How far the figure leans towards what it is reaching for, as a share of how far off
#: centre that is: enough that the whole body moves through a session, not just an arm.
_LEAN = 0.15

#: How much lower than the straight shoulder-to-wrist line the elbow sits, so the arm
#: reads as an arm with a bend in it rather than one straight line.
_ELBOW_SAG = 0.03

#: The figure at rest, as (x, y) per MediaPipe pose landmark 0..32, in MediaPipe's own
#: order: somebody standing at the counter facing the camera, both hands down. The
#: subject's left landmarks sit at the larger x, the way a person facing a camera comes
#: out in its frame.
_FIGURE: tuple[Point, ...] = (
    (0.500, 0.556),  # 0 nose
    (0.512, 0.540),  # 1 left eye, inner
    (0.524, 0.540),  # 2 left eye
    (0.536, 0.540),  # 3 left eye, outer
    (0.488, 0.540),  # 4 right eye, inner
    (0.476, 0.540),  # 5 right eye
    (0.464, 0.540),  # 6 right eye, outer
    (0.548, 0.548),  # 7 left ear
    (0.452, 0.548),  # 8 right ear
    (0.516, 0.576),  # 9 mouth, left
    (0.484, 0.576),  # 10 mouth, right
    (0.570, 0.640),  # 11 left shoulder
    (0.430, 0.640),  # 12 right shoulder
    (0.610, 0.740),  # 13 left elbow
    (0.390, 0.740),  # 14 right elbow
    (0.628, 0.830),  # 15 left wrist
    (0.372, 0.830),  # 16 right wrist
    (0.648, 0.858),  # 17 left pinky
    (0.352, 0.858),  # 18 right pinky
    (0.636, 0.864),  # 19 left index
    (0.364, 0.864),  # 20 right index
    (0.620, 0.856),  # 21 left thumb
    (0.380, 0.856),  # 22 right thumb
    (0.546, 0.860),  # 23 left hip
    (0.454, 0.860),  # 24 right hip
    (0.540, 0.930),  # 25 left knee
    (0.460, 0.930),  # 26 right knee
    (0.536, 0.972),  # 27 left ankle
    (0.464, 0.972),  # 28 right ankle
    (0.544, 0.980),  # 29 left heel
    (0.456, 0.980),  # 30 right heel
    (0.516, 0.988),  # 31 left foot index
    (0.484, 0.988),  # 32 right foot index
)

#: One hand, as (x, y) per MediaPipe hand landmark 0..20 in MediaPipe's own order,
#: in a unit square around the middle of the palm: wrist at the bottom, fingers up,
#: thumb to the left, which is a right hand with its palm to the camera. The left hand
#: is this one mirrored. Every offset stays inside +/- 0.5, so a hand scaled by `span`
#: and centred on a point lands inside a box of side `span` around that point.
_HAND: tuple[Point, ...] = (
    (0.00, 0.45),  # 0 wrist
    (-0.18, 0.30),  # 1 thumb, carpometacarpal
    (-0.30, 0.14),  # 2 thumb, metacarpophalangeal
    (-0.38, 0.02),  # 3 thumb, interphalangeal
    (-0.44, -0.08),  # 4 thumb, tip
    (-0.14, 0.02),  # 5 index, metacarpophalangeal
    (-0.16, -0.16),  # 6 index, proximal interphalangeal
    (-0.17, -0.30),  # 7 index, distal interphalangeal
    (-0.18, -0.42),  # 8 index, tip
    (0.00, 0.00),  # 9 middle, metacarpophalangeal
    (0.00, -0.18),  # 10 middle, proximal interphalangeal
    (0.00, -0.33),  # 11 middle, distal interphalangeal
    (0.00, -0.46),  # 12 middle, tip
    (0.13, 0.02),  # 13 ring, metacarpophalangeal
    (0.15, -0.15),  # 14 ring, proximal interphalangeal
    (0.16, -0.28),  # 15 ring, distal interphalangeal
    (0.17, -0.40),  # 16 ring, tip
    (0.25, 0.06),  # 17 pinky, metacarpophalangeal
    (0.29, -0.08),  # 18 pinky, proximal interphalangeal
    (0.31, -0.19),  # 19 pinky, distal interphalangeal
    (0.33, -0.29),  # 20 pinky, tip
)

#: Which pose landmarks an arm is: shoulder, elbow, wrist, then the pinky, index and
#: thumb the pose carries for that hand, per side.
_ARM: dict[Handedness, tuple[int, int, int, tuple[int, int, int]]] = {
    Handedness.LEFT: (11, 13, 15, (17, 19, 21)),
    Handedness.RIGHT: (12, 14, 16, (18, 20, 22)),
}

#: Which of the hand's own landmarks the pose's pinky, index and thumb are: the tips,
#: so the two layers agree about where the fingers ended up.
_FINGER_TIPS = (20, 8, 4)


def centre_of(box: BoundingBox) -> Point:
    """The middle of `box`."""
    return (box.x1 + box.x2) / 2.0, (box.y1 + box.y2) / 2.0


def reaching_for(point: Point, *, span: float = HAND_SPAN) -> tuple[Pose, HandLandmarks]:
    """A stand-in figure reaching for `point`, and the hand it reached with.

    The hand nearer `point` is the one that reaches, so the figure uses its left for
    something on the left of the frame and its right for something on the right, and
    the pose's wrist is exactly where the returned hand's wrist is. Every landmark of
    the hand sits within `span` of `point`, so a caller with a hand box of its own can
    pass that box's size and keep the landmarks inside it (see `reaching_into`).
    """
    handedness = Handedness.LEFT if point[0] > 0.5 else Handedness.RIGHT
    hand = _hand(point, handedness, span)
    return _figure(hand, handedness, point), hand


def reaching_into(box: BoundingBox) -> tuple[Pose, HandLandmarks]:
    """A stand-in figure whose hand fills `box`: the hand a recording already tracks.

    The hand lands inside `box` rather than merely near it, so a frame built this way
    says the same thing about hand-object contact as the box alone did
    (`routine_watch.recogniser` reads either, and here they agree).
    """
    span = min(box.x2 - box.x1, box.y2 - box.y1)
    return reaching_for(centre_of(box), span=span)


def _hand(point: Point, handedness: Handedness, span: float) -> HandLandmarks:
    """The 21 hand landmarks, `_HAND` scaled by `span` around `point`."""
    mirrored = -1.0 if handedness is Handedness.LEFT else 1.0
    x, y = point
    return HandLandmarks(
        handedness=handedness,
        score=_CONFIDENCE,
        landmarks=[
            _landmark(x + mirrored * dx * span, y + dy * span) for dx, dy in _HAND
        ],
    )


def _figure(hand: HandLandmarks, handedness: Handedness, point: Point) -> Pose:
    """The 33 pose landmarks: `_FIGURE`, leaning towards `point`, one arm out to `hand`."""
    lean = _LEAN * (point[0] - 0.5)
    places = [(x + lean, y) for x, y in _FIGURE]

    shoulder, elbow, wrist, fingers = _ARM[handedness]
    places[wrist] = (hand.landmarks[0].x, hand.landmarks[0].y)
    places[elbow] = (
        (places[shoulder][0] + places[wrist][0]) / 2.0,
        (places[shoulder][1] + places[wrist][1]) / 2.0 + _ELBOW_SAG,
    )
    for index, tip in zip(fingers, _FINGER_TIPS, strict=True):
        places[index] = (hand.landmarks[tip].x, hand.landmarks[tip].y)

    return Pose(
        landmarks=[_landmark(x, y, visibility=_VISIBILITY) for x, y in places],
        score=_CONFIDENCE,
    )


def _landmark(x: float, y: float, *, visibility: float | None = None) -> Landmark:
    """One landmark, kept inside the frame and rounded the way capture rounds."""
    return Landmark(
        x=_clamped(x), y=_clamped(y), z=0.0, visibility=visibility
    )


def _clamped(value: float) -> float:
    return round(min(1.0, max(0.0, value)), COORD_DIGITS)
