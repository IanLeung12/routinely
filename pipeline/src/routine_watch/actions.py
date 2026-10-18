"""The action primitives a task file names, and the state they read (SPEC section 6.2).

`recogniser.py` turns a capture stream into timestamped step events. What it reads has
always been state rules over hand-object interactions - but the rules themselves were
hand-written for making tea, so any other routine recognised nothing at all. This
module is the rules taken apart into the handful of things people actually do with
objects, so a task file can *name* one per step::

    # tasks/tea.yaml
    - id: teabag_in_cup
      label: Put the teabag in the cup
      objects: [teabag, cup]
      action: {type: put_into, object: teabag, target: cup}

A routine somebody wrote this morning is then recognised by the same code that reads
tea, with no new rule anywhere. The primitives:

=================  ==================================================================
``pick_up``        taken hold of and carried somewhere
``put_into``       let into another thing's box, having come from outside it
``take_out``       the same contact the other way round
``pour``           held over another thing, tipped: or the detector's `pouring` class
``stir``           held inside another thing, going back and forth
``hold``           held where it stands for a while: a switch, a hand in a drawer
``open``           held while its own box opens out, or a `<x>_open` class appears
``close``          the same, closing
``shake``          held while the wrist it is in swings back and forth
``bring_to_face``  held up to the nose and mouth: a drink, a tablet, a toothbrush
``return``         carried, and set down where it was picked up from
=================  ==================================================================

**What a primitive reads.** One `Reading`: the session's frames reduced to the objects
in each of them (`Scene`) and, per frame, the contact each held object belongs to
(`Contact`) - one unbroken run of frames with a hand on one object, which is what says
*what is being done* with a thing rather than merely which thing is in a hand. Each
primitive is a pure function of that reading, a frame index and the object names it was
given, and answers the same `(strength, objects)` the hand-written rules answer, so
confidences, `unclear` and the Gemini verifier hook are exactly as they were.

**Plain handling.** `pick_up` and `hold` are what is left over when nothing more
specific happened: carrying the kettle to the tap is `pick_up`, and carrying it over
the cup is a pour, not a pick-up of it on the way. So a *plain* primitive is dropped
for a whole contact in which something more specific was read off the same object
(`recogniser._without_plain_handling`). That is the general form of the rule the tea
rules spelled out by hand ("the kettle was never over the cup during this contact"),
and it is why one pour comes out as one step event rather than carry/pour/carry.

Nothing here holds a frame: it reads boxes, landmarks and timestamps, and keeps boxes,
labels and timestamps (SPEC section 8).
"""

from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass

from .contracts import BoundingBox, CaptureFrame, ObjectLabel

STAGE = "actions"

# ----------------------------------------------------------------- the thresholds
# All normalised to the frame (0..1) or in seconds, and all hand-set for the MVP.

#: A hand this close to a box counts as on the object: landmarks land on the near edge
#: of a thing as often as inside it.
HAND_MARGIN = 0.02

#: A gap shorter than this is the detector blinking, not the hand letting go. It keeps
#: one dropped frame from splitting one step into two.
FLICKER_GAP_S = 0.4

#: Box centres moving less than this between frames are detector jitter, not motion.
MOVE_EPS = 0.005

#: An object whose centre travels this far while it is held was carried somewhere,
#: rather than touched where it stood.
CARRY_DISTANCE = 0.06

#: A hand resting this long on an object it does not move is working the object where
#: it stands: the kettle's switch, a hand in the pill organiser.
HOLD_STILL_S = 1.0

#: This much of a smaller box inside a bigger one is the small thing being in it: a
#: teabag in the cup, a spoon standing in it.
IN_CUP_FRACTION = 0.6

#: Pouring, read without any rotation to go on: the kettle's box sits above the cup's,
#: covers at least this much of the cup's width, and its base is no higher than
#: `POUR_REACH` above the cup's rim and no lower than the cup's own base.
POUR_OVERLAP_FRACTION = 0.5
POUR_REACH = 0.10

#: Stirring is the spoon going back and forth: this many direction changes while it is
#: held in the cup is a confident stir.
STIR_REVERSALS = 2

#: How much less confident a spoon that is in the cup but barely moving is.
STIR_STILL_PENALTY = 0.6

#: Shaking: the wrist holding the thing swings back and forth. This many direction
#: changes within `SHAKE_WINDOW_S`, each swing at least `SHAKE_AMPLITUDE` of the frame
#: long, is somebody shaking something rather than carrying it across the kitchen.
SHAKE_REVERSALS = 3
SHAKE_WINDOW_S = 2.0
SHAKE_AMPLITUDE = 0.02

#: Opening something changes the shape of its box: a lid swings out, a drawer slides.
#: This much growth in area (or in width for its height) while it is in a hand is it
#: being opened, and the same shrinking is it being closed.
OPEN_CHANGE = 0.25

#: The detector may one day have a class for a thing standing open. Until it does this
#: suffix matches nothing, and the box-shape reading above is all there is to go on.
OPEN_SUFFIX = "_open"

#: Up to the face: this close to a nose or mouth landmark counts as at it.
FACE_REACH = 0.06

#: Put back: carried, and set down this close to where it was picked up from.
RETURN_SLACK = 0.04

#: The nose and the two mouth corners, in MediaPipe pose's own landmark order. The
#: three points that say where somebody's face is without saying whose it is.
FACE_LANDMARKS = (0, 9, 10)

# ---------------------------------------------------------- how far each one is trusted
# A primitive's own confidence when the detector is certain and the frames agree; the
# detector's confidence in the least certain object it used scales it down from there.
# `hold` is the weakest: a hand resting on a thing is all there is to see.

POUR_CONFIDENCE = 0.90
POURING_CLASS_CONFIDENCE = 0.95
PUT_INTO_CONFIDENCE = 0.90
TAKE_OUT_CONFIDENCE = 0.85
STIR_CONFIDENCE = 0.85
PICK_UP_CONFIDENCE = 0.85
RETURN_CONFIDENCE = 0.88
SHAKE_CONFIDENCE = 0.90
BRING_TO_FACE_CONFIDENCE = 0.85
OPEN_CONFIDENCE = 0.80
OPEN_CLASS_CONFIDENCE = 0.95
HOLD_CONFIDENCE = 0.75


# ------------------------------------------------------------------ what a rule reads


@dataclass(frozen=True)
class Seen:
    """One object class in one frame: the detector's most confident box for it."""

    box: BoundingBox
    confidence: float


@dataclass(frozen=True)
class Hand:
    """One hand in one frame, however capture saw it (SPEC section 16, "Hands").

    `at` is the wrist - MediaPipe's landmark 0, or the middle of the detector's own
    `hand` box when that is all there is - and it is the point a shake is read off.
    """

    at: tuple[float, float]
    #: The 21 MediaPipe landmarks, when the frame carries them.
    points: tuple[tuple[float, float], ...] = ()
    #: The detector's `hand` box, when the frame carries that instead.
    box: BoundingBox | None = None


@dataclass(frozen=True)
class Scene:
    """One capture frame, reduced to what the rules read."""

    seq: int
    t: float
    #: Label -> where it is. The `hand` class is not here; it is what `touched` is made
    #: of.
    objects: Mapping[str, Seen]
    #: The labels a hand is on in this frame.
    touched: frozenset[str]
    #: Every hand in the frame, landmarks or box.
    hands: tuple[Hand, ...] = ()
    #: Where the faces in frame are: the nose and mouth landmarks of each pose.
    face: tuple[tuple[float, float], ...] = ()


@dataclass(frozen=True)
class Contact:
    """One unbroken run of frames with a hand on one object.

    This is the state the rules need: the objects in a frame say *what* is being
    handled, and the contact says *what is being done with it*.
    """

    label: str
    first: int
    last: int
    #: How far the object's centre travelled while it was held, along its path.
    travel: float
    #: How many times it changed direction: stirring rather than carrying.
    reversals: int
    seconds: float
    #: It was held over the cup at some point, so this contact is a pour, whatever
    #: else happens during it. Read by the hand-written tea rules only; a step with an
    #: `action:` gets the same answer from `pour` and plain-handling suppression.
    over_cup: bool
    #: It was already inside the cup when the hand took hold of it. Tea rules only,
    #: as above.
    started_in_cup: bool


@dataclass(frozen=True)
class Held:
    """An object that is both detected in this frame and currently in a hand."""

    seen: Seen
    contact: Contact


@dataclass(frozen=True)
class Reading:
    """One session's frames as the rules read them.

    Built once per reading of a session (`read`), and all the state every primitive
    gets: `scenes[i]` is the i-th frame in time order, and `contacts[i]` maps each
    object a hand is on in that frame to the contact it belongs to.
    """

    scenes: tuple[Scene, ...]
    contacts: tuple[Mapping[str, Contact], ...]

    def __len__(self) -> int:
        return len(self.scenes)

    def seen(self, index: int, label: str) -> Seen | None:
        """Where `label` is in frame `index`, or None if the detector did not see it."""
        return self.scenes[index].objects.get(label)

    def held(self, index: int, label: str) -> Held | None:
        """`label` in frame `index` if a hand is on it, with the contact it is part of."""
        seen = self.scenes[index].objects.get(label)
        contact = self.contacts[index].get(label)
        return None if seen is None or contact is None else Held(seen=seen, contact=contact)

    def holding(self, index: int, label: str) -> Hand | None:
        """The hand that is on `label` in frame `index`, or None if none is."""
        seen = self.scenes[index].objects.get(label)
        if seen is None:
            return None
        return next((hand for hand in self.scenes[index].hands if on(hand, seen.box)), None)


def read(frames: Iterable[CaptureFrame]) -> Reading:
    """One session's capture records as the state the rules read, in time order."""
    found = scenes_of(frames)
    return Reading(scenes=tuple(found), contacts=tuple(contacts_of(found)))


# ------------------------------------------------------------------------ the firing

#: What one primitive says about one frame: how strongly it fired, and the objects the
#: step was done with. Those objects are what `routine_watch.errors` checks against the
#: task's allowed list, so they are the ones the step was done *with*, not every object
#: the primitive looked at.
Firing = tuple[float, tuple[str, ...]] | None


# -------------------------------------------------------------------- the primitives
# Each one is a pure function of the reading, the frame it is asked about, and the
# object names the task file gave it. `x` is the thing in the hand; `y`, where there is
# one, is what it is done to.


def pick_up(reading: Reading, index: int, x: str) -> Firing:
    """`x` taken hold of and carried somewhere, rather than touched where it stood."""
    held = reading.held(index, x)
    if held is None or held.contact.travel < CARRY_DISTANCE:
        return None
    return PICK_UP_CONFIDENCE * held.seen.confidence, (x,)


def hold(reading: Reading, index: int, x: str, seconds: float = HOLD_STILL_S) -> Firing:
    """A hand resting on `x` where it stands for `seconds`: the kettle's switch.

    The other half of `pick_up`: this is the contact that goes nowhere, which is why a
    touch in passing is not it and carrying the thing off is not either.
    """
    held = reading.held(index, x)
    if held is None or held.contact.travel >= CARRY_DISTANCE:
        return None
    if held.contact.seconds < seconds:
        return None
    return HOLD_CONFIDENCE * held.seen.confidence, (x,)


def put_into(reading: Reading, index: int, x: str, y: str) -> Firing:
    """`x` carried into `y`'s box: it came from outside, which is what tells this from
    an `x` that was already sitting in there. The hand lets go a frame or two later,
    inside the same contact."""
    held, into = reading.held(index, x), reading.seen(index, y)
    if held is None or into is None or _started_inside(reading, held.contact, x, y):
        return None
    if not inside(held.seen.box, into.box):
        return None
    return PUT_INTO_CONFIDENCE * min(held.seen.confidence, into.confidence), (x, y)


def take_out(reading: Reading, index: int, x: str, y: str) -> Firing:
    """The same contact the other way round: `x` was in `y`, and now it is out."""
    held, outof = reading.held(index, x), reading.seen(index, y)
    if held is None or outof is None or not _started_inside(reading, held.contact, x, y):
        return None
    if inside(held.seen.box, outof.box):
        return None
    return TAKE_OUT_CONFIDENCE * min(held.seen.confidence, outof.confidence), (x,)


def pour(reading: Reading, index: int, x: str, y: str) -> Firing:
    """`x` held over `y` and tipped, or the detector's own `pouring` class over `y`.

    Boxes carry no rotation, so the geometry is all there is for the first reading:
    `x`'s box above `y`'s, over its mouth, low enough to be at its rim. The second
    reading is a class trained on the act itself (SPEC section 6.1), and it needs no
    hand on anything - a kettle can be held by somebody out of frame.
    """
    into = reading.seen(index, y)
    if into is None:
        return None
    strengths = []
    held = reading.held(index, x)
    if held is not None and over(held.seen.box, into.box):
        strengths.append(POUR_CONFIDENCE * min(held.seen.confidence, into.confidence))
    pouring = reading.seen(index, str(ObjectLabel.POURING))
    if pouring is not None and overlaps(pouring.box, into.box):
        strengths.append(POURING_CLASS_CONFIDENCE * min(pouring.confidence, into.confidence))
    if not strengths:
        return None
    objects = (x, y) if reading.seen(index, x) is not None else (y,)
    return max(strengths), objects


def stir(reading: Reading, index: int, x: str, y: str) -> Firing:
    """`x` held inside `y`. Going back and forth is a stir; standing still in it is the
    same picture with much less to say for itself."""
    held, into = reading.held(index, x), reading.seen(index, y)
    if held is None or into is None or not inside(held.seen.box, into.box):
        return None
    moving = held.contact.reversals >= STIR_REVERSALS
    strength = STIR_CONFIDENCE * min(held.seen.confidence, into.confidence)
    return strength * (1.0 if moving else STIR_STILL_PENALTY), (x, y)


def open_(reading: Reading, index: int, x: str) -> Firing:
    """`x` in a hand and opening out: its box grows, or a `<x>_open` class appears.

    A lid swinging back or a drawer sliding out makes the box bigger, or wider for its
    height, than it was when the hand took hold - which is as much as boxes can say
    about it. A detector trained on the thing standing open says it outright, and that
    is the reading to trust when it exists.
    """
    held = reading.held(index, x)
    if held is None:
        return None
    strengths = []
    spread = _spread(reading, held.contact, x, held.seen)
    if spread is not None and spread >= 1.0 + OPEN_CHANGE:
        strengths.append(OPEN_CONFIDENCE * held.seen.confidence)
    standing_open = reading.seen(index, f"{x}{OPEN_SUFFIX}")
    if standing_open is not None and not _was_open(reading, held.contact, x):
        strengths.append(OPEN_CLASS_CONFIDENCE * standing_open.confidence)
    if not strengths:
        return None
    return max(strengths), (x,)


def close_(reading: Reading, index: int, x: str) -> Firing:
    """`x` in a hand and closing up: `open_` read the other way round."""
    held = reading.held(index, x)
    if held is None:
        return None
    strengths = []
    spread = _spread(reading, held.contact, x, held.seen)
    if spread is not None and spread > 0.0 and 1.0 / spread >= 1.0 + OPEN_CHANGE:
        strengths.append(OPEN_CONFIDENCE * held.seen.confidence)
    if _was_open(reading, held.contact, x) and reading.seen(index, f"{x}{OPEN_SUFFIX}") is None:
        strengths.append(OPEN_CLASS_CONFIDENCE * held.seen.confidence)
    if not strengths:
        return None
    return max(strengths), (x,)


def shake(reading: Reading, index: int, x: str) -> Firing:
    """`x` in a hand, and that hand's wrist swinging back and forth.

    `SHAKE_REVERSALS` changes of direction inside `SHAKE_WINDOW_S`, each swing at least
    `SHAKE_AMPLITUDE` long, which is what tells shaking a bottle from carrying it: a
    carry is one long move, a shake is many short ones that keep turning back.
    """
    held = reading.held(index, x)
    if held is None:
        return None
    trail = _wrist_trail(reading, index, x, held.contact)
    swings = [move for move in _moves(trail) if length(move) >= SHAKE_AMPLITUDE]
    reversals = sum(
        1 for one, other in zip(swings, swings[1:], strict=False) if turns_back(one, other)
    )
    if reversals < SHAKE_REVERSALS:
        return None
    return SHAKE_CONFIDENCE * held.seen.confidence, (x,)


def bring_to_face(reading: Reading, index: int, x: str) -> Firing:
    """`x` in a hand and up at the nose and mouth: a drink, a tablet, a toothbrush.

    Read off the pose landmarks, so a frame with nobody's body in it says nothing
    either way - which is the honest answer: there is no face to have brought it to.
    """
    held = reading.held(index, x)
    scene = reading.scenes[index]
    if held is None or not scene.face:
        return None
    if not any(near(point, held.seen.box, FACE_REACH) for point in scene.face):
        return None
    return BRING_TO_FACE_CONFIDENCE * held.seen.confidence, (x,)


def return_(reading: Reading, index: int, x: str) -> Firing:
    """`x` carried, and set down where it was picked up from."""
    held = reading.held(index, x)
    if held is None or held.contact.travel < CARRY_DISTANCE:
        return None
    was = reading.seen(held.contact.first, x)
    if was is None:
        return None
    moved = length(delta(centre(was.box), centre(held.seen.box)))
    if moved > RETURN_SLACK:
        return None
    return RETURN_CONFIDENCE * held.seen.confidence, (x,)


# ------------------------------------------------------ what the primitives read back


def _started_inside(reading: Reading, contact: Contact, x: str, y: str) -> bool:
    """True if `x` was already inside `y` when the hand took hold of it."""
    was, into = reading.seen(contact.first, x), reading.seen(contact.first, y)
    return was is not None and into is not None and inside(was.box, into.box)


def _spread(reading: Reading, contact: Contact, x: str, now: Seen) -> float | None:
    """How much bigger `x`'s box is than when the hand took hold of it.

    The larger of the change in area and the change in width-for-height, so a lid that
    swings sideways and one that swings up both read as the box opening out. None when
    there is nothing to compare against.
    """
    was = reading.seen(contact.first, x)
    if was is None:
        return None
    then, size = _shape(was.box), _shape(now.box)
    if then[0] <= 0.0 or then[1] <= 0.0:
        return None
    return max(size[0] / then[0], size[1] / then[1])


def _shape(box: BoundingBox) -> tuple[float, float]:
    """A box's area, and how wide it is for its height."""
    width, height = box.x2 - box.x1, box.y2 - box.y1
    return width * height, width / height if height > 0.0 else 0.0


def _was_open(reading: Reading, contact: Contact, x: str) -> bool:
    """True if `x` was already standing open when the hand took hold of it."""
    return reading.seen(contact.first, f"{x}{OPEN_SUFFIX}") is not None


def _wrist_trail(
    reading: Reading, index: int, x: str, contact: Contact
) -> list[tuple[float, float]]:
    """Where the hand on `x` has been over the last `SHAKE_WINDOW_S`, oldest first.

    Bounded by the contact, because a hand that let go and took hold again is not one
    swing of the same shake.
    """
    now = reading.scenes[index].t
    trail: list[tuple[float, float]] = []
    for step in range(index, contact.first - 1, -1):
        if now - reading.scenes[step].t > SHAKE_WINDOW_S:
            break
        hand = reading.holding(step, x)
        if hand is not None:
            trail.append(hand.at)
    trail.reverse()
    return trail


def _moves(trail: Sequence[tuple[float, float]]) -> list[tuple[float, float]]:
    """The moves between consecutive points of a trail, detector jitter dropped."""
    steps = [delta(one, other) for one, other in zip(trail, trail[1:], strict=False)]
    return [move for move in steps if length(move) >= MOVE_EPS]


# ------------------------------------------------------- one action, as the rule for it


@dataclass(frozen=True)
class Action:
    """What a step's `action:` says is being done, as the recogniser reads it.

    `objects` is one or more detector classes, aliases already resolved by
    `tasks/graph.py`: a step the task file allows a bottle *or* an organiser for names
    both, and whichever is in the hand is the one read. `target` is the thing it is
    done to (`put_into`'s container, `pour`'s cup); `seconds` is `hold`'s duration.
    """

    type: str
    objects: tuple[str, ...]
    target: str | None = None
    seconds: float | None = None


@dataclass(frozen=True)
class Primitive:
    """One action a task file may name, and what it has to be given."""

    name: str
    #: The function itself: `(reading, index, x)`, or `(reading, index, x, y)` when it
    #: takes a target.
    fire: Callable[..., Firing]
    #: One line, for the drafter's prompt and the loader's error message.
    summary: str
    #: Does it need a second object to be done to?
    target: bool = False
    #: Does it take a duration?
    seconds: bool = False
    #: Is it "just handling the thing": the reading left over when nothing more
    #: specific was done with it in the same contact?
    plain: bool = False


#: Every action a task file may name. The names are the YAML's, so `return` is here
#: under its own name even though the function behind it cannot be.
PRIMITIVES: dict[str, Primitive] = {
    primitive.name: primitive
    for primitive in (
        Primitive("pick_up", pick_up, "picked up and carried somewhere", plain=True),
        Primitive("put_into", put_into, "put into the target", target=True),
        Primitive("take_out", take_out, "taken back out of the target", target=True),
        Primitive("pour", pour, "held over the target and tipped", target=True),
        Primitive("stir", stir, "moved back and forth inside the target", target=True),
        Primitive("hold", hold, "held where it stands, for `seconds`", seconds=True, plain=True),
        Primitive("open", open_, "opened: its box opens out"),
        Primitive("close", close_, "closed again"),
        Primitive("shake", shake, "shaken: the wrist holding it swings back and forth"),
        Primitive("bring_to_face", bring_to_face, "brought up to the nose and mouth"),
        Primitive("return", return_, "carried back to where it was picked up from"),
    )
}

#: The action names a task file or a drafted routine may use, in the table's order.
ACTION_TYPES: tuple[str, ...] = tuple(PRIMITIVES)


def primitive(action_type: str) -> Primitive | None:
    """The primitive `action_type` names, or None if nothing does."""
    return PRIMITIVES.get(action_type)


def rule(action: Action) -> Callable[[Reading, int], Firing]:
    """`action` as the function that reads one frame of a session.

    An action naming more than one object (a pill bottle *or* a weekly organiser) is
    read for each of them, and the strongest answer is the one the frame gives.
    """
    found = PRIMITIVES[action.type]
    extra: tuple[object, ...] = ()
    if found.target:
        extra = (action.target,)
    elif found.seconds and action.seconds is not None:
        extra = (action.seconds,)

    def fire(reading: Reading, index: int) -> Firing:
        firings = [found.fire(reading, index, x, *extra) for x in action.objects]
        strongest = [firing for firing in firings if firing is not None]
        return max(strongest, key=lambda firing: firing[0]) if strongest else None

    return fire


# ------------------------------------------------------- the frames, as the rules read


def scenes_of(frames: Iterable[CaptureFrame]) -> list[Scene]:
    """Each frame reduced to the objects in it and the ones a hand is on.

    Two boxes of the same class in one frame (two cups) collapse to the detector's more
    confident one: the MVP's tasks are done with one of each.
    """
    scenes = []
    for frame in sorted(frames, key=lambda record: (record.t, record.seq)):
        objects: dict[str, Seen] = {}
        hands = [
            Hand(at=centre(found.box), box=found.box)
            for found in frame.objects
            if found.label is ObjectLabel.HAND
        ]
        for found in frame.objects:
            if found.label is ObjectLabel.HAND:
                continue
            label = str(found.label)
            if label not in objects or found.confidence > objects[label].confidence:
                objects[label] = Seen(box=found.box, confidence=found.confidence)
        hands += [
            # MediaPipe's landmark 0 is the wrist, which is the one a shake is read off.
            Hand(
                at=(hand.landmarks[0].x, hand.landmarks[0].y),
                points=tuple((mark.x, mark.y) for mark in hand.landmarks),
            )
            for hand in frame.hands
        ]
        scenes.append(
            Scene(
                seq=frame.seq,
                t=frame.t,
                objects=objects,
                touched=frozenset(
                    label for label, seen in objects.items() if in_hand(seen.box, hands)
                ),
                hands=tuple(hands),
                face=tuple(
                    (pose.landmarks[mark].x, pose.landmarks[mark].y)
                    for pose in frame.poses
                    for mark in FACE_LANDMARKS
                ),
            )
        )
    return scenes


def contacts_of(scenes: Sequence[Scene]) -> list[dict[str, Contact]]:
    """For each frame, the contact each object it is holding belongs to."""
    by_frame: list[dict[str, Contact]] = [{} for _ in scenes]
    for label in sorted({label for scene in scenes for label in scene.touched}):
        for first, last in spans_of(scenes, label):
            contact = describe(scenes, label, first, last)
            for index in range(first, last + 1):
                by_frame[index][label] = contact
    return by_frame


def spans_of(scenes: Sequence[Scene], label: str) -> list[tuple[int, int]]:
    """Index ranges where a hand is on `label`, a `FLICKER_GAP_S` blink bridged."""
    spans: list[list[int]] = []
    for index, scene in enumerate(scenes):
        if label not in scene.touched:
            continue
        if spans and continues(scenes, spans[-1][1], index):
            spans[-1][1] = index
        else:
            spans.append([index, index])
    return [(first, last) for first, last in spans]


def continues(scenes: Sequence[Scene], last: int, index: int) -> bool:
    """True if frame `index` carries on from frame `last` rather than starting again."""
    return index == last + 1 or scenes[index].t - scenes[last].t <= FLICKER_GAP_S


def describe(scenes: Sequence[Scene], label: str, first: int, last: int) -> Contact:
    """What was done with `label` over one contact: how far it went, whether it changed
    direction, and whether it ever went over the cup."""
    path = [
        (index, scene.objects[label].box)
        for index, scene in enumerate(scenes[first : last + 1], start=first)
        if label in scene.objects
    ]
    centres = [centre(box) for _, box in path]
    steps = [delta(one, other) for one, other in zip(centres, centres[1:], strict=False)]
    moves = [move for move in steps if length(move) >= MOVE_EPS]
    over_cup = any(
        (cup := scenes[index].objects.get(str(ObjectLabel.CUP))) is not None
        and over(box, cup.box)
        for index, box in path
    )
    started_in_cup = False
    if path:
        index, box = path[0]
        cup = scenes[index].objects.get(str(ObjectLabel.CUP))
        started_in_cup = cup is not None and inside(box, cup.box)
    return Contact(
        label=label,
        first=first,
        last=last,
        travel=sum(length(move) for move in moves),
        reversals=sum(
            1 for one, other in zip(moves, moves[1:], strict=False) if turns_back(one, other)
        ),
        seconds=scenes[last].t - scenes[first].t,
        over_cup=over_cup,
        started_in_cup=started_in_cup,
    )


# -------------------------------------------------------------------- the geometry
# Boxes are normalised to the frame, so every distance below is a fraction of it.


def centre(box: BoundingBox) -> tuple[float, float]:
    return (box.x1 + box.x2) / 2.0, (box.y1 + box.y2) / 2.0


def delta(one: tuple[float, float], other: tuple[float, float]) -> tuple[float, float]:
    return other[0] - one[0], other[1] - one[1]


def length(move: tuple[float, float]) -> float:
    return (move[0] ** 2 + move[1] ** 2) ** 0.5


def turns_back(one: tuple[float, float], other: tuple[float, float]) -> bool:
    """True if the object reversed between these two moves, rather than carrying on."""
    return one[0] * other[0] + one[1] * other[1] < 0.0


def overlaps(one: BoundingBox, other: BoundingBox) -> bool:
    """True if the two boxes share any area. Touching edges do not count."""
    return one.x1 < other.x2 and other.x1 < one.x2 and one.y1 < other.y2 and other.y1 < one.y2


def inside(inner: BoundingBox, outer: BoundingBox) -> bool:
    """True if most of `inner` is within `outer`: a teabag in the cup, a spoon in it."""
    width = min(inner.x2, outer.x2) - max(inner.x1, outer.x1)
    height = min(inner.y2, outer.y2) - max(inner.y1, outer.y1)
    if width <= 0.0 or height <= 0.0:
        return False
    area = (inner.x2 - inner.x1) * (inner.y2 - inner.y1)
    return area <= 0.0 or width * height >= IN_CUP_FRACTION * area


def over(upper: BoundingBox, lower: BoundingBox) -> bool:
    """True if `upper` is held over `lower`: a kettle over a cup, which is what
    pouring looks like when the boxes carry no rotation.

    The kettle's top has to be above the cup's, it has to cover `POUR_OVERLAP_FRACTION`
    of the cup's width, and its base has to be around the cup's rim - no more than
    `POUR_REACH` above it and no lower than the cup's own base - so a kettle on a shelf
    above the cup is not pouring into it.
    """
    overlap = min(upper.x2, lower.x2) - max(upper.x1, lower.x1)
    if overlap < POUR_OVERLAP_FRACTION * (lower.x2 - lower.x1):
        return False
    return upper.y1 < lower.y1 and lower.y1 - POUR_REACH <= upper.y2 <= lower.y2


def near(point: tuple[float, float], box: BoundingBox, margin: float) -> bool:
    """True if `point` is inside `box`, or within `margin` of its edge."""
    x, y = point
    return box.x1 - margin <= x <= box.x2 + margin and box.y1 - margin <= y <= box.y2 + margin


def on(hand: Hand, box: BoundingBox) -> bool:
    """True if this one hand is on `box`: a landmark in it, or its own box over it."""
    x1, y1 = box.x1 - HAND_MARGIN, box.y1 - HAND_MARGIN
    x2, y2 = box.x2 + HAND_MARGIN, box.y2 + HAND_MARGIN
    if any(x1 <= x <= x2 and y1 <= y <= y2 for x, y in hand.points):
        return True
    reach = hand.box
    return reach is not None and x1 < reach.x2 and reach.x1 < x2 and y1 < reach.y2 and reach.y1 < y2


def in_hand(box: BoundingBox, hands: Sequence[Hand]) -> bool:
    """True if a hand is on this object (SPEC section 16): a hand box overlapping it,
    or a MediaPipe hand landmark inside it, either within `HAND_MARGIN` of its edge.

    Both because capture gives both, and a synthetic fixture may carry whichever is
    less work to write.
    """
    return any(on(hand, box) for hand in hands)
