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
standing in it. `routine_watch.actions` is that state and the rules over it.

**Where the rules come from.** A step of a task file that names an `action:` is read by
that action primitive (`actions.PRIMITIVES`: `put_into`, `pour`, `shake`, ...), so a
routine somebody wrote this morning is recognised by the same code that reads tea and
no rule is added here for it. A step with no `action:` falls back to `RULES` below, the
hand-written tea rules this module started as; a step that has neither is not
recognised, which is what a task made of steps nobody has said how to see looks like.

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

One limit worth knowing: **substitution (SPEC section 7) cannot come out of these
rules.** Every rule is keyed to a detector class the task graph already allows for its
step, so the wrong object can only be reported once the detector has a class for it.
The rules report the objects they actually saw and leave the judging to
`routine_watch.errors`.

Nothing in this module holds a frame: it reads boxes, landmarks and timestamps and
keeps boxes, labels and timestamps (SPEC section 8).
"""

from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass, replace

from . import actions
from .actions import (
    CARRY_DISTANCE,
    HOLD_STILL_S,
    POUR_CONFIDENCE,
    POURING_CLASS_CONFIDENCE,
    PUT_INTO_CONFIDENCE,
    STIR_CONFIDENCE,
    STIR_REVERSALS,
    STIR_STILL_PENALTY,
    TAKE_OUT_CONFIDENCE,
    Contact,
    Firing,
    Held,
    Reading,
    Scene,
    continues,
    inside,
    over,
    overlaps,
)
from .contracts import CaptureFrame, ObjectLabel, StepEvent, StepSource
from .tasks import TaskGraph

STAGE = "recogniser"

#: A step event below this confidence needs the verifier (SPEC section 7).
MIN_STEP_CONFIDENCE = 0.6

#: Give up on the verifier after this long and mark the event `unclear`.
VERIFIER_TIMEOUT_S = 3.0

#: A step seen in this many frames is as supported as it gets; one seen in fewer is
#: scaled towards `WEAK_SUPPORT`, so a single-frame flash comes out unclear.
FULL_SUPPORT_FRAMES = 3
WEAK_SUPPORT = 0.55

#: How far each hand-written tea rule can be trusted when the detector is certain and
#: the frames agree. The action primitives carry their own (`actions.py`), and these
#: are the same numbers for the steps that come out of the same evidence.
FILL_KETTLE_CONFIDENCE = actions.PICK_UP_CONFIDENCE
GET_CUP_CONFIDENCE = actions.PICK_UP_CONFIDENCE
BOIL_CONFIDENCE = actions.HOLD_CONFIDENCE
MILK_CONFIDENCE = 0.85
SUGAR_CONFIDENCE = 0.85


# ------------------------------------------------------------------------ the rules


def _held(scene: Scene, contacts: Mapping[str, Contact], label: str) -> Held | None:
    """`label` in this frame if a hand is on it, with the contact it is part of."""
    seen, contact = scene.objects.get(label), contacts.get(label)
    return None if seen is None or contact is None else Held(seen=seen, contact=contact)


@dataclass(frozen=True)
class _Rule:
    """One state rule: the step it proposes, and what a frame has to look like."""

    step_id: str
    fire: Callable[[Reading, int], Firing]
    #: The objects an `action:` rule is *about*, so that a plain reading of a contact
    #: can be dropped when something more specific was read off the same object. Empty
    #: for the hand-written tea rules, which carry their own exclusions.
    subjects: tuple[str, ...] = ()
    #: True when this rule is "just handling the thing" (`actions.Primitive.plain`).
    plain: bool = False


def _per_frame(
    fire: Callable[[Scene, Mapping[str, Contact]], Firing],
) -> Callable[[Reading, int], Firing]:
    """A hand-written rule, which reads one frame and its contacts, as a rule over the
    whole reading."""

    def read(reading: Reading, index: int) -> Firing:
        return fire(reading.scenes[index], reading.contacts[index])

    return read


def _pour(scene: Scene, contacts: Mapping[str, Contact]) -> Firing:
    """The kettle held over the cup, or the detector's own `pouring` class over it."""
    cup = scene.objects.get("cup")
    if cup is None:
        return None
    strengths = []
    kettle = _held(scene, contacts, "kettle")
    if kettle is not None and over(kettle.seen.box, cup.box):
        strengths.append(POUR_CONFIDENCE * min(kettle.seen.confidence, cup.confidence))
    pouring = scene.objects.get("pouring")
    if pouring is not None and overlaps(pouring.box, cup.box):
        strengths.append(POURING_CLASS_CONFIDENCE * min(pouring.confidence, cup.confidence))
    if not strengths:
        return None
    objects = ("kettle", "cup") if "kettle" in scene.objects else ("cup",)
    return max(strengths), objects


def _teabag_in_cup(scene: Scene, contacts: Mapping[str, Contact]) -> Firing:
    """A hand on the teabag, and the teabag now in the cup: it went in during this
    contact, which is what tells it from a teabag already sitting there."""
    teabag, cup = _held(scene, contacts, "teabag"), scene.objects.get("cup")
    if teabag is None or cup is None or teabag.contact.started_in_cup:
        return None
    if not inside(teabag.seen.box, cup.box):
        return None
    strength = PUT_INTO_CONFIDENCE * min(teabag.seen.confidence, cup.confidence)
    return strength, ("teabag", "cup")


def _remove_teabag(scene: Scene, contacts: Mapping[str, Contact]) -> Firing:
    """The same contact the other way round: it was in the cup, and now it is out."""
    teabag, cup = _held(scene, contacts, "teabag"), scene.objects.get("cup")
    if teabag is None or cup is None or not teabag.contact.started_in_cup:
        return None
    if inside(teabag.seen.box, cup.box):
        return None
    return TAKE_OUT_CONFIDENCE * min(teabag.seen.confidence, cup.confidence), ("teabag",)


def _stir(scene: Scene, contacts: Mapping[str, Contact]) -> Firing:
    """A spoon held in the cup. Going back and forth is a stir; standing still in it is
    the same picture with much less to say for itself."""
    spoon, cup = _held(scene, contacts, "spoon"), scene.objects.get("cup")
    if spoon is None or cup is None or not inside(spoon.seen.box, cup.box):
        return None
    moving = spoon.contact.reversals >= STIR_REVERSALS
    strength = STIR_CONFIDENCE * min(spoon.seen.confidence, cup.confidence)
    return strength * (1.0 if moving else STIR_STILL_PENALTY), ("spoon", "cup")


def _fill_kettle(scene: Scene, contacts: Mapping[str, Contact]) -> Firing:
    """The kettle picked up and carried: to the tap, and back to its base."""
    kettle = _held(scene, contacts, "kettle")
    if kettle is None or kettle.contact.over_cup:
        return None
    if kettle.contact.travel < CARRY_DISTANCE:
        return None
    return FILL_KETTLE_CONFIDENCE * kettle.seen.confidence, ("kettle",)


def _boil(scene: Scene, contacts: Mapping[str, Contact]) -> Firing:
    """A hand resting on the kettle where it stands, long enough to be the switch."""
    kettle = _held(scene, contacts, "kettle")
    if kettle is None or kettle.contact.over_cup:
        return None
    if kettle.contact.travel >= CARRY_DISTANCE or kettle.contact.seconds < HOLD_STILL_S:
        return None
    return BOIL_CONFIDENCE * kettle.seen.confidence, ("kettle",)


def _get_cup(scene: Scene, contacts: Mapping[str, Contact]) -> Firing:
    """The cup carried to where the tea gets made. Steadying it is not getting it."""
    cup = _held(scene, contacts, "cup")
    if cup is None or cup.contact.travel < CARRY_DISTANCE:
        return None
    return GET_CUP_CONFIDENCE * cup.seen.confidence, ("cup",)


def _milk(scene: Scene, contacts: Mapping[str, Contact]) -> Firing:
    """The milk held over the cup."""
    milk, cup = _held(scene, contacts, "milk"), scene.objects.get("cup")
    if milk is None or cup is None or not over(milk.seen.box, cup.box):
        return None
    return MILK_CONFIDENCE * min(milk.seen.confidence, cup.confidence), ("milk", "cup")


def _sugar(scene: Scene, contacts: Mapping[str, Contact]) -> Firing:
    """The sugar held over the cup. Spooning it out of a jar that never moves is not
    recognised yet: the sugar's own box has to come over the cup."""
    sugar, cup = _held(scene, contacts, "sugar"), scene.objects.get("cup")
    if sugar is None or cup is None or not over(sugar.seen.box, cup.box):
        return None
    strength = SUGAR_CONFIDENCE * min(sugar.seen.confidence, cup.confidence)
    objects = ("sugar", "spoon") if "spoon" in contacts else ("sugar",)
    return strength, objects


#: The hand-written tea rules, strongest claim first: a tie between two of them on one
#: frame goes to the first here. They are what a step with no `action:` is read by, and
#: `tasks/tea.yaml` names an action for every step, so nothing in the repo needs them -
#: a task file somebody wrote before actions existed still works.
RULES: tuple[_Rule, ...] = (
    _Rule("pour", _per_frame(_pour)),
    _Rule("teabag_in_cup", _per_frame(_teabag_in_cup)),
    _Rule("remove_teabag", _per_frame(_remove_teabag)),
    _Rule("stir", _per_frame(_stir)),
    _Rule("fill_kettle", _per_frame(_fill_kettle)),
    _Rule("boil", _per_frame(_boil)),
    _Rule("get_cup", _per_frame(_get_cup)),
    _Rule("milk", _per_frame(_milk)),
    _Rule("sugar", _per_frame(_sugar)),
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
    reading = actions.read(frames)
    rules = _rules(graph)
    fired = _without_plain_handling(rules, reading)
    hits = [_strongest(rules, fired, index) for index in range(len(reading))]
    return [_event(reading.scenes, run, session_id) for run in _runs(reading.scenes, hits)]


def needs_verifier(event: StepEvent) -> bool:
    """True if this event is too weak to stand on its own.

    The hook the Gemini verifier task hangs off: these are the moments worth spending a
    few cropped, low-res frames on (SPEC section 16, decision A). Until then they come
    back `unclear`, and an unclear event is never counted as an error.
    """
    return event.confidence < MIN_STEP_CONFIDENCE


def _rules(graph: TaskGraph) -> tuple[_Rule, ...]:
    """What this task is read with: its steps' own actions, then the tea fallback.

    A step naming an `action:` is read by that primitive. The steps that name none fall
    back to the hand-written rules, in `RULES`'s order, and a step neither covers is
    simply never proposed.
    """
    rules = []
    for step in graph.steps:
        if step.action is None:
            continue
        found = actions.PRIMITIVES[step.action.type]
        rules.append(
            _Rule(
                step_id=step.id,
                fire=actions.rule(step.action),
                subjects=step.action.objects,
                plain=found.plain,
            )
        )
    hand_written = {step.id for step in graph.steps if step.action is None}
    rules.extend(rule for rule in RULES if rule.step_id in hand_written)
    return tuple(rules)


def _without_plain_handling(rules: Sequence[_Rule], reading: Reading) -> list[list[Firing]]:
    """Every rule's firing on every frame, with the plain readings that something more
    specific explains taken out.

    `pick_up` and `hold` are what is left when nothing else happened: carrying the
    kettle over the cup is a pour, not a pick-up of the kettle on the way to it. So a
    plain rule is dropped for a *whole contact* in which another rule read something
    specific off the same object - the general form of the exclusion the tea rules
    spell out by hand, and what keeps one pour from coming out as carry, pour, carry.
    """
    fired = [[rule.fire(reading, index) for index in range(len(reading))] for rule in rules]
    specific = [index for index, rule in enumerate(rules) if not rule.plain and rule.subjects]
    for index, rule in enumerate(rules):
        if not rule.plain:
            continue
        for contact in _contacts_with(reading, rule.subjects):
            if not _explained(fired, specific, rules, contact):
                continue
            for frame in range(contact.first, contact.last + 1):
                fired[index][frame] = None
    return fired


def _contacts_with(reading: Reading, labels: Sequence[str]) -> list[Contact]:
    """Every contact in this reading that is about one of `labels`, each once."""
    found: dict[tuple[str, int, int], Contact] = {}
    for held in reading.contacts:
        for label in labels:
            contact = held.get(label)
            if contact is not None:
                found.setdefault((label, contact.first, contact.last), contact)
    return list(found.values())


def _explained(
    fired: Sequence[Sequence[Firing]],
    specific: Sequence[int],
    rules: Sequence[_Rule],
    contact: Contact,
) -> bool:
    """True if some rule about this contact's object read something specific in it."""
    return any(
        fired[index][frame] is not None
        for index in specific
        if contact.label in rules[index].subjects
        for frame in range(contact.first, contact.last + 1)
    )


def _strongest(
    rules: Sequence[_Rule], fired: Sequence[Sequence[Firing]], index: int
) -> _Hit | None:
    """The one step this frame speaks for: the strongest rule that fires on it."""
    best: _Hit | None = None
    for rule, firings in zip(rules, fired, strict=True):
        firing = firings[index]
        if firing is None:
            continue
        strength, objects = firing
        if best is None or strength > best.strength:
            best = _Hit(step_id=rule.step_id, strength=strength, objects=objects)
    return best


def _runs(scenes: Sequence[Scene], hits: Sequence[_Hit | None]) -> list[_Run]:
    """Frames voting for the same step, back to back, as one run each."""
    runs: list[_Run] = []
    for index, hit in enumerate(hits):
        if hit is None:
            continue
        previous = runs[-1] if runs else None
        if (
            previous is not None
            and previous.step_id == hit.step_id
            and continues(scenes, previous.last, index)
        ):
            runs[-1] = replace(previous, last=index, hits=(*previous.hits, hit))
        else:
            runs.append(_Run(step_id=hit.step_id, first=index, last=index, hits=(hit,)))
    return runs


def _event(scenes: Sequence[Scene], run: _Run, session_id: str) -> StepEvent:
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
