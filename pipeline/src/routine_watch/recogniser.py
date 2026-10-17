"""Step recogniser (SPEC section 6.2).

State rules over hand-object interactions turn the capture stream into timestamped
step events with a confidence score::

    from routine_watch.tasks import load_task
    events = recognise(frames, load_task("tea"), session_id="tea-1")

What the rules read is one frame at a time: where each object is, and which objects a
hand is on (SPEC section 16, "Hands": steps are hand-object interactions). What they
need beyond that is *state*, because the objects alone cannot tell two steps apart -
filling the kettle and boiling it are both "a hand on the kettle". So the stream is
first cut into **contacts**: one unbroken run of frames with a hand on one object. A
contact knows how far the object travelled while it was held, whether it changed
direction, how long it lasted and whether it went over the cup, and that is what
separates carrying the kettle to the tap (`fill_kettle`) from resting a hand on it at
its base (`boil`), or a spoon going back and forth in the cup (`stir`) from one left
standing in it.

Each frame then votes for at most one step: every rule that fires on it is scored, and
the strongest wins. Consecutive frames voting for the same step are one step event,
spanning the first and last of them. One step at a time is a deliberate simplification
for the MVP - steps in these tasks are done one after another - and it is what keeps
the output clean: two rules cannot both claim the same moment.

**Confidence** is the rule's own base confidence times the detector's confidence in the
least certain object it used, scaled down when only a frame or two support it. An event
below `MIN_STEP_CONFIDENCE` is emitted with `unclear=True` and is never dropped: the
spec's rule is that an unclear moment is never counted as an error (SPEC section 7),
and dropping it silently would instead read as a step that never happened. Those are
the events the Gemini verifier is for; `needs_verifier` is the hook it will pick them
up by (SPEC section 16, decision A). Nothing here calls it, so until that task lands
`unclear` means "low confidence and no verifier asked".

Two limits worth knowing:

* **The rule table is written for the tea graph**, the MVP's one task. Rules whose step
  the graph does not have are skipped, so another task recognises nothing until its
  rules are added here.
* **Substitution (SPEC section 7) cannot come out of these rules.** Every rule is keyed
  to a detector class the tea graph already allows for its step, so the wrong object
  can only be reported once the detector has a class for it. The rules report the
  objects they actually saw and leave the judging to `routine_watch.errors`.

Nothing in this module holds a frame: it reads boxes, landmarks and timestamps and
keeps boxes, labels and timestamps (SPEC section 8).
"""

from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass, replace

from .contracts import BoundingBox, CaptureFrame, ObjectLabel, StepEvent, StepSource
from .tasks import TaskGraph

STAGE = "recogniser"

#: A step event below this confidence needs the verifier (SPEC section 7).
MIN_STEP_CONFIDENCE = 0.6

#: Give up on the verifier after this long and mark the event `unclear`.
VERIFIER_TIMEOUT_S = 3.0

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
#: it stands: the kettle's switch.
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

#: A step seen in this many frames is as supported as it gets; one seen in fewer is
#: scaled towards `WEAK_SUPPORT`, so a single-frame flash comes out unclear.
FULL_SUPPORT_FRAMES = 3
WEAK_SUPPORT = 0.55

#: How far each rule can be trusted when the detector is certain and the frames agree.
#: `boil` is the weakest: a hand resting on the kettle is all there is to see.
POUR_CONFIDENCE = 0.90
POURING_CLASS_CONFIDENCE = 0.95
TEABAG_IN_CUP_CONFIDENCE = 0.90
REMOVE_TEABAG_CONFIDENCE = 0.85
STIR_CONFIDENCE = 0.85
FILL_KETTLE_CONFIDENCE = 0.85
GET_CUP_CONFIDENCE = 0.85
MILK_CONFIDENCE = 0.85
SUGAR_CONFIDENCE = 0.85
BOIL_CONFIDENCE = 0.75


# ------------------------------------------------------------------ what a rule reads


@dataclass(frozen=True)
class _Seen:
    """One object class in one frame: the detector's most confident box for it."""

    box: BoundingBox
    confidence: float


@dataclass(frozen=True)
class _Scene:
    """One capture frame, reduced to what the rules read."""

    seq: int
    t: float
    #: Label -> where it is. The `hand` class is not here; it is what `touched` is made
    #: of.
    objects: Mapping[str, _Seen]
    #: The labels a hand is on in this frame.
    touched: frozenset[str]


@dataclass(frozen=True)
class _Contact:
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
    #: else happens during it.
    over_cup: bool
    #: It was already inside the cup when the hand took hold of it.
    started_in_cup: bool


@dataclass(frozen=True)
class _Held:
    """An object that is both detected in this frame and currently in a hand."""

    seen: _Seen
    contact: _Contact


def _held(scene: _Scene, contacts: Mapping[str, _Contact], label: str) -> _Held | None:
    seen, contact = scene.objects.get(label), contacts.get(label)
    return None if seen is None or contact is None else _Held(seen=seen, contact=contact)


# ------------------------------------------------------------------------ the rules

#: What one rule says about one frame: how strongly it fired, and the objects the step
#: was done with. Those objects are what `routine_watch.errors` checks against the
#: task's allowed list, so they are the ones the step was done *with*, not every object
#: the rule looked at.
_Firing = tuple[float, tuple[str, ...]] | None


@dataclass(frozen=True)
class _Rule:
    """One state rule: the step it proposes, and what a frame has to look like."""

    step_id: str
    fire: Callable[[_Scene, Mapping[str, _Contact]], _Firing]


def _pour(scene: _Scene, contacts: Mapping[str, _Contact]) -> _Firing:
    """The kettle held over the cup, or the detector's own `pouring` class over it."""
    cup = scene.objects.get("cup")
    if cup is None:
        return None
    strengths = []
    kettle = _held(scene, contacts, "kettle")
    if kettle is not None and _over(kettle.seen.box, cup.box):
        strengths.append(POUR_CONFIDENCE * min(kettle.seen.confidence, cup.confidence))
    pouring = scene.objects.get("pouring")
    if pouring is not None and _overlaps(pouring.box, cup.box):
        strengths.append(POURING_CLASS_CONFIDENCE * min(pouring.confidence, cup.confidence))
    if not strengths:
        return None
    objects = ("kettle", "cup") if "kettle" in scene.objects else ("cup",)
    return max(strengths), objects


def _teabag_in_cup(scene: _Scene, contacts: Mapping[str, _Contact]) -> _Firing:
    """A hand on the teabag, and the teabag now in the cup: it went in during this
    contact, which is what tells it from a teabag already sitting there."""
    teabag, cup = _held(scene, contacts, "teabag"), scene.objects.get("cup")
    if teabag is None or cup is None or teabag.contact.started_in_cup:
        return None
    if not _inside(teabag.seen.box, cup.box):
        return None
    strength = TEABAG_IN_CUP_CONFIDENCE * min(teabag.seen.confidence, cup.confidence)
    return strength, ("teabag", "cup")


def _remove_teabag(scene: _Scene, contacts: Mapping[str, _Contact]) -> _Firing:
    """The same contact the other way round: it was in the cup, and now it is out."""
    teabag, cup = _held(scene, contacts, "teabag"), scene.objects.get("cup")
    if teabag is None or cup is None or not teabag.contact.started_in_cup:
        return None
    if _inside(teabag.seen.box, cup.box):
        return None
    return REMOVE_TEABAG_CONFIDENCE * min(teabag.seen.confidence, cup.confidence), ("teabag",)


def _stir(scene: _Scene, contacts: Mapping[str, _Contact]) -> _Firing:
    """A spoon held in the cup. Going back and forth is a stir; standing still in it is
    the same picture with much less to say for itself."""
    spoon, cup = _held(scene, contacts, "spoon"), scene.objects.get("cup")
    if spoon is None or cup is None or not _inside(spoon.seen.box, cup.box):
        return None
    moving = spoon.contact.reversals >= STIR_REVERSALS
    strength = STIR_CONFIDENCE * min(spoon.seen.confidence, cup.confidence)
    return strength * (1.0 if moving else STIR_STILL_PENALTY), ("spoon", "cup")


def _fill_kettle(scene: _Scene, contacts: Mapping[str, _Contact]) -> _Firing:
    """The kettle picked up and carried: to the tap, and back to its base."""
    kettle = _held(scene, contacts, "kettle")
    if kettle is None or kettle.contact.over_cup:
        return None
    if kettle.contact.travel < CARRY_DISTANCE:
        return None
    return FILL_KETTLE_CONFIDENCE * kettle.seen.confidence, ("kettle",)


def _boil(scene: _Scene, contacts: Mapping[str, _Contact]) -> _Firing:
    """A hand resting on the kettle where it stands, long enough to be the switch."""
    kettle = _held(scene, contacts, "kettle")
    if kettle is None or kettle.contact.over_cup:
        return None
    if kettle.contact.travel >= CARRY_DISTANCE or kettle.contact.seconds < HOLD_STILL_S:
        return None
    return BOIL_CONFIDENCE * kettle.seen.confidence, ("kettle",)


def _get_cup(scene: _Scene, contacts: Mapping[str, _Contact]) -> _Firing:
    """The cup carried to where the tea gets made. Steadying it is not getting it."""
    cup = _held(scene, contacts, "cup")
    if cup is None or cup.contact.travel < CARRY_DISTANCE:
        return None
    return GET_CUP_CONFIDENCE * cup.seen.confidence, ("cup",)


def _milk(scene: _Scene, contacts: Mapping[str, _Contact]) -> _Firing:
    """The milk held over the cup."""
    milk, cup = _held(scene, contacts, "milk"), scene.objects.get("cup")
    if milk is None or cup is None or not _over(milk.seen.box, cup.box):
        return None
    return MILK_CONFIDENCE * min(milk.seen.confidence, cup.confidence), ("milk", "cup")


def _sugar(scene: _Scene, contacts: Mapping[str, _Contact]) -> _Firing:
    """The sugar held over the cup. Spooning it out of a jar that never moves is not
    recognised yet: the sugar's own box has to come over the cup."""
    sugar, cup = _held(scene, contacts, "sugar"), scene.objects.get("cup")
    if sugar is None or cup is None or not _over(sugar.seen.box, cup.box):
        return None
    strength = SUGAR_CONFIDENCE * min(sugar.seen.confidence, cup.confidence)
    objects = ("sugar", "spoon") if "spoon" in contacts else ("sugar",)
    return strength, objects


#: Every rule, strongest claim first: a tie between two rules on one frame goes to the
#: first of them here.
RULES: tuple[_Rule, ...] = (
    _Rule("pour", _pour),
    _Rule("teabag_in_cup", _teabag_in_cup),
    _Rule("remove_teabag", _remove_teabag),
    _Rule("stir", _stir),
    _Rule("fill_kettle", _fill_kettle),
    _Rule("boil", _boil),
    _Rule("get_cup", _get_cup),
    _Rule("milk", _milk),
    _Rule("sugar", _sugar),
)


# ------------------------------------------------------------------- the recogniser


@dataclass(frozen=True)
class _Hit:
    """One rule firing on one frame."""

    step_id: str
    strength: float
    objects: tuple[str, ...]


@dataclass(frozen=True)
class _Run:
    """Consecutive frames whose strongest rule is the same step: one step event."""

    step_id: str
    first: int
    last: int
    hits: tuple[_Hit, ...]


def recognise(
    frames: Iterable[CaptureFrame], graph: TaskGraph, *, session_id: str
) -> list[StepEvent]:
    """The steps of `graph` visible in `frames`, oldest first.

    `frames` is one session's capture records in any order; they are read in time
    order, so the same session always gives the same events however they arrive. The
    frames' own `session_id` is not read: `session_id` is what the caller says this
    session is, and it is what the events carry.

    Every event has ``source="rule"``. One below `MIN_STEP_CONFIDENCE` comes back with
    ``unclear=True`` rather than being dropped (SPEC section 7); `needs_verifier` picks
    those out for the Gemini verifier.

    This is a batch pass over the frames it is given, not a running state machine: a
    live session re-reads the frames so far, which is cheap at these sizes and means a
    replay and the live camera cannot drift apart.
    """
    scenes = _scenes(frames)
    contacts = _contacts(scenes)
    rules = tuple(rule for rule in RULES if rule.step_id in graph.step_ids)
    hits = [_strongest(rules, scene, held) for scene, held in zip(scenes, contacts, strict=True)]
    return [_event(scenes, run, session_id) for run in _runs(scenes, hits)]


def needs_verifier(event: StepEvent) -> bool:
    """True if this event is too weak to stand on its own.

    The hook the Gemini verifier task hangs off: these are the moments worth spending a
    few cropped, low-res frames on (SPEC section 16, decision A). Until then they come
    back `unclear`, and an unclear event is never counted as an error.
    """
    return event.confidence < MIN_STEP_CONFIDENCE


def _scenes(frames: Iterable[CaptureFrame]) -> list[_Scene]:
    """Each frame reduced to the objects in it and the ones a hand is on.

    Two boxes of the same class in one frame (two cups) collapse to the detector's more
    confident one: the MVP's tasks are done with one of each.
    """
    scenes = []
    for frame in sorted(frames, key=lambda record: (record.t, record.seq)):
        objects: dict[str, _Seen] = {}
        hands = [found.box for found in frame.objects if found.label is ObjectLabel.HAND]
        for found in frame.objects:
            if found.label is ObjectLabel.HAND:
                continue
            label = str(found.label)
            if label not in objects or found.confidence > objects[label].confidence:
                objects[label] = _Seen(box=found.box, confidence=found.confidence)
        points = [(mark.x, mark.y) for hand in frame.hands for mark in hand.landmarks]
        scenes.append(
            _Scene(
                seq=frame.seq,
                t=frame.t,
                objects=objects,
                touched=frozenset(
                    label for label, seen in objects.items() if _in_hand(seen.box, hands, points)
                ),
            )
        )
    return scenes


def _contacts(scenes: Sequence[_Scene]) -> list[dict[str, _Contact]]:
    """For each frame, the contact each object it is holding belongs to."""
    by_frame: list[dict[str, _Contact]] = [{} for _ in scenes]
    for label in sorted({label for scene in scenes for label in scene.touched}):
        for first, last in _spans(scenes, label):
            contact = _describe(scenes, label, first, last)
            for index in range(first, last + 1):
                by_frame[index][label] = contact
    return by_frame


def _spans(scenes: Sequence[_Scene], label: str) -> list[tuple[int, int]]:
    """Index ranges where a hand is on `label`, a `FLICKER_GAP_S` blink bridged."""
    spans: list[list[int]] = []
    for index, scene in enumerate(scenes):
        if label not in scene.touched:
            continue
        if spans and _continues(scenes, spans[-1][1], index):
            spans[-1][1] = index
        else:
            spans.append([index, index])
    return [(first, last) for first, last in spans]


def _continues(scenes: Sequence[_Scene], last: int, index: int) -> bool:
    """True if frame `index` carries on from frame `last` rather than starting again."""
    return index == last + 1 or scenes[index].t - scenes[last].t <= FLICKER_GAP_S


def _describe(scenes: Sequence[_Scene], label: str, first: int, last: int) -> _Contact:
    """What was done with `label` over one contact: how far it went, whether it changed
    direction, and whether it ever went over the cup."""
    path = [
        (index, scene.objects[label].box)
        for index, scene in enumerate(scenes[first : last + 1], start=first)
        if label in scene.objects
    ]
    centres = [_centre(box) for _, box in path]
    steps = [_delta(one, other) for one, other in zip(centres, centres[1:], strict=False)]
    moves = [move for move in steps if _length(move) >= MOVE_EPS]
    over_cup = any(
        (cup := scenes[index].objects.get("cup")) is not None and _over(box, cup.box)
        for index, box in path
    )
    started_in_cup = False
    if path:
        index, box = path[0]
        cup = scenes[index].objects.get("cup")
        started_in_cup = cup is not None and _inside(box, cup.box)
    return _Contact(
        label=label,
        first=first,
        last=last,
        travel=sum(_length(move) for move in moves),
        reversals=sum(
            1 for one, other in zip(moves, moves[1:], strict=False) if _turns_back(one, other)
        ),
        seconds=scenes[last].t - scenes[first].t,
        over_cup=over_cup,
        started_in_cup=started_in_cup,
    )


def _strongest(
    rules: Sequence[_Rule], scene: _Scene, contacts: Mapping[str, _Contact]
) -> _Hit | None:
    """The one step this frame speaks for: the strongest rule that fires on it."""
    best: _Hit | None = None
    for rule in rules:
        firing = rule.fire(scene, contacts)
        if firing is None:
            continue
        strength, objects = firing
        if best is None or strength > best.strength:
            best = _Hit(step_id=rule.step_id, strength=strength, objects=objects)
    return best


def _runs(scenes: Sequence[_Scene], hits: Sequence[_Hit | None]) -> list[_Run]:
    """Frames voting for the same step, back to back, as one run each."""
    runs: list[_Run] = []
    for index, hit in enumerate(hits):
        if hit is None:
            continue
        previous = runs[-1] if runs else None
        if (
            previous is not None
            and previous.step_id == hit.step_id
            and _continues(scenes, previous.last, index)
        ):
            runs[-1] = replace(previous, last=index, hits=(*previous.hits, hit))
        else:
            runs.append(_Run(step_id=hit.step_id, first=index, last=index, hits=(hit,)))
    return runs


def _event(scenes: Sequence[_Scene], run: _Run, session_id: str) -> StepEvent:
    """One run of frames as a step event, scored by how well the frames support it."""
    start, end = scenes[run.first], scenes[run.last]
    support = WEAK_SUPPORT + (1.0 - WEAK_SUPPORT) * min(
        1.0, len(run.hits) / FULL_SUPPORT_FRAMES
    )
    strength = sum(hit.strength for hit in run.hits) / len(run.hits)
    confidence = round(min(1.0, strength * support), 3)
    objects = dict.fromkeys(label for hit in run.hits for label in hit.objects)
    return StepEvent(
        event_id=f"{session_id}:{run.step_id}:{start.seq}",
        session_id=session_id,
        step_id=run.step_id,
        objects=[ObjectLabel(label) for label in objects],
        t_start=start.t,
        t_end=end.t,
        confidence=confidence,
        source=StepSource.RULE,
        unclear=confidence < MIN_STEP_CONFIDENCE,
    )


# -------------------------------------------------------------------- the geometry
# Boxes are normalised to the frame, so every distance below is a fraction of it.


def _centre(box: BoundingBox) -> tuple[float, float]:
    return (box.x1 + box.x2) / 2.0, (box.y1 + box.y2) / 2.0


def _delta(one: tuple[float, float], other: tuple[float, float]) -> tuple[float, float]:
    return other[0] - one[0], other[1] - one[1]


def _length(move: tuple[float, float]) -> float:
    return (move[0] ** 2 + move[1] ** 2) ** 0.5


def _turns_back(one: tuple[float, float], other: tuple[float, float]) -> bool:
    """True if the object reversed between these two moves, rather than carrying on."""
    return one[0] * other[0] + one[1] * other[1] < 0.0


def _overlaps(one: BoundingBox, other: BoundingBox) -> bool:
    """True if the two boxes share any area. Touching edges do not count."""
    return one.x1 < other.x2 and other.x1 < one.x2 and one.y1 < other.y2 and other.y1 < one.y2


def _inside(inner: BoundingBox, outer: BoundingBox) -> bool:
    """True if most of `inner` is within `outer`: a teabag in the cup, a spoon in it."""
    width = min(inner.x2, outer.x2) - max(inner.x1, outer.x1)
    height = min(inner.y2, outer.y2) - max(inner.y1, outer.y1)
    if width <= 0.0 or height <= 0.0:
        return False
    area = (inner.x2 - inner.x1) * (inner.y2 - inner.y1)
    return area <= 0.0 or width * height >= IN_CUP_FRACTION * area


def _over(upper: BoundingBox, lower: BoundingBox) -> bool:
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


def _in_hand(
    box: BoundingBox,
    hand_boxes: Sequence[BoundingBox],
    points: Sequence[tuple[float, float]],
) -> bool:
    """True if a hand is on this object (SPEC section 16): a hand box overlapping it,
    or a MediaPipe hand landmark inside it, either within `HAND_MARGIN` of its edge.

    Both because capture gives both, and a synthetic fixture may carry whichever is
    less work to write.
    """
    x1, y1 = box.x1 - HAND_MARGIN, box.y1 - HAND_MARGIN
    x2, y2 = box.x2 + HAND_MARGIN, box.y2 + HAND_MARGIN
    if any(x1 <= x <= x2 and y1 <= y <= y2 for x, y in points):
        return True
    return any(
        x1 < hand.x2 and hand.x1 < x2 and y1 < hand.y2 and hand.y1 < y2 for hand in hand_boxes
    )
