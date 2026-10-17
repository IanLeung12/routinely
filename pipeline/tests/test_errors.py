"""The error classifier (SPEC section 7): the graph rules, and what is not an error.

Two halves, and the second is the important one. The first half shows each of the five
graph-based error types being found: a missing step, a step out of order, a step done
twice, a step done with the wrong object, and the resident walking away. The second
half pins everything the spec says is *not* an error - valid alternative orders,
skipped optional steps, slips put right straight away, and anything only an `unclear`
event points at - because a classifier that cries wolf is worse than no classifier at
all for a product whose whole claim is that an alert is worth a nurse's attention.

Hesitation is not here: it needs this resident's own baseline rather than the graph
(`routine_watch.hesitation`).
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Sequence
from pathlib import Path

import pytest

from routine_watch.contracts import (
    ErrorType,
    EvidenceKind,
    ObjectLabel,
    StepEvent,
    StepSource,
    TaskError,
)
from routine_watch.errors import ERROR_TYPES, classify_errors
from routine_watch.replay import load_scenario, scenario_dirs
from routine_watch.tasks import load_task

SESSION = "tea-test-1"

#: The make-tea graph is immutable and cached, so every test shares one.
TEA = load_task("tea")

#: The demo's bad session (SPEC section 10): the teabag never goes in, and the
#: resident pours twice with a stir in between.
DEMO = ("fill_kettle", "boil", "get_cup", "pour", "stir", "pour", "remove_teabag")


# --------------------------------------------------------------------------- helpers


def event(
    step_id: str,
    t_start: float,
    t_end: float,
    *,
    objects: Sequence[ObjectLabel] | None = None,
    unclear: bool = False,
) -> StepEvent:
    """One step event, done with the objects the task expects unless told otherwise."""
    return StepEvent(
        event_id=f"{SESSION}:{step_id}@{t_start:g}",
        session_id=SESSION,
        step_id=step_id,
        objects=list(TEA.step(step_id).objects if objects is None else objects),
        t_start=t_start,
        t_end=t_end,
        confidence=0.4 if unclear else 0.93,
        source=StepSource.RULE,
        unclear=unclear,
    )


def run(*steps: str, each: float = 5.0, gap: float = 5.0) -> list[StepEvent]:
    """`steps` one after another, each taking `each` seconds with `gap` between them."""
    return [
        event(step_id, 1.0 + index * (each + gap), 1.0 + index * (each + gap) + each)
        for index, step_id in enumerate(steps)
    ]


def classify(events: Sequence[StepEvent], **options: float | bool) -> list[TaskError]:
    """The errors in `events`, against the tea graph."""
    return classify_errors(events, TEA, session_id=SESSION, **options)  # type: ignore[arg-type]


def kinds(errors: Sequence[TaskError]) -> list[tuple[str, str | None]]:
    """The errors as `(type, step)` pairs: what most of these tests are about."""
    return [(str(error.type), error.step_id) for error in errors]


def blurred(step_event: StepEvent) -> StepEvent:
    """The same event, but one the verifier could not resolve."""
    return step_event.model_copy(update={"unclear": True, "confidence": 0.4})


# ------------------------------------------------------------------- not an error


def test_every_valid_order_of_the_required_steps_is_clean() -> None:
    orders = list(TEA.valid_orders())
    assert len(orders) > 1, "the graph would not be a graph if there were only one order"
    for order in orders:
        assert classify(run(*order)) == [], order


def test_optional_steps_can_be_taken_or_skipped() -> None:
    # Every order of the whole task, milk and sugar included. Skipping them is covered
    # by the test above, which runs the required steps only.
    for order in TEA.valid_orders(TEA.step_ids):
        assert classify(run(*order)) == [], order


def test_two_events_in_a_row_for_one_step_are_the_recogniser_not_the_resident() -> None:
    events = run(
        "fill_kettle", "boil", "get_cup", "teabag_in_cup", "pour", "pour", "stir", "remove_teabag"
    )
    assert classify(events) == []


def test_stirring_again_is_not_perseveration() -> None:
    # `stir` is the one tea step marked once_only: false. Stirring twice is normal.
    events = run(
        "fill_kettle", "boil", "get_cup", "teabag_in_cup", "pour", "stir", "milk", "stir",
        "remove_teabag",
    )
    assert classify(events) == []


# ----------------------------------------------------------------------- omission


def test_pouring_without_the_teabag_is_an_omission() -> None:
    events = run("fill_kettle", "boil", "get_cup", "pour", "stir", "remove_teabag")
    errors = classify(events)
    pour = events[3]

    assert kinds(errors) == [("omission", "teabag_in_cup")]
    # Pinned to the pour: the moment the missing step became an error, which is what
    # the nurse replays.
    assert (errors[0].t_start, errors[0].t_end) == (pour.t_start, pour.t_end)
    assert [(ref.kind, ref.event_id) for ref in errors[0].evidence] == [
        (EvidenceKind.STEP_EVENT, pour.event_id)
    ]
    assert not errors[0].self_corrected


def test_a_missing_step_is_reported_once_however_often_it_was_needed() -> None:
    errors = classify(run(*DEMO))  # two pours, neither with a teabag in the cup
    omissions = [error for error in errors if error.type is ErrorType.OMISSION]
    assert [error.step_id for error in omissions] == ["teabag_in_cup"]


def test_a_step_the_session_never_reached_is_an_omission_once_it_ends() -> None:
    events = run("get_cup", "teabag_in_cup", "fill_kettle", "boil", "pour", "stir")
    errors = classify(events)

    assert kinds(errors) == [("omission", "remove_teabag")]
    # Nothing depended on it, so there is no event to point at: the evidence is the
    # skeleton replay of the session it is missing from (SPEC section 8).
    assert (errors[0].t_start, errors[0].t_end) == (0.0, events[-1].t_end)
    assert [ref.kind for ref in errors[0].evidence] == [EvidenceKind.SKELETON_REPLAY]


def test_a_live_session_does_not_omit_what_is_still_to_come() -> None:
    events = run("get_cup", "teabag_in_cup", "fill_kettle", "boil")
    assert classify(events, ended=False) == []
    assert kinds(classify(events)) == [
        ("omission", "pour"),
        ("omission", "stir"),
        ("omission", "remove_teabag"),
    ]


def test_a_live_session_still_flags_what_is_already_wrong() -> None:
    # The other half of the omission rule, and what makes the live task map useful:
    # pouring without the teabag is an error the moment it happens.
    events = run("fill_kettle", "boil", "get_cup", "pour")
    assert kinds(classify(events, ended=False)) == [("omission", "teabag_in_cup")]


def test_a_finished_session_with_no_events_omits_every_required_step() -> None:
    errors = classify([])
    assert [error.step_id for error in errors] == list(TEA.required_steps)
    assert all(error.evidence == [] for error in errors)
    assert classify([], ended=False) == []


# ----------------------------------------------------------------------- sequence


def test_a_step_before_its_dependency_is_a_sequence_error() -> None:
    # Pours the water, then boils the kettle a minute later: out of order, and far too
    # late to be a slip put right.
    events = [
        event("get_cup", 1, 6),
        event("teabag_in_cup", 8, 13),
        event("fill_kettle", 15, 20),
        event("pour", 22, 27),
        event("boil", 80, 86),
        event("stir", 90, 95),
        event("remove_teabag", 97, 102),
    ]
    errors = classify(events)

    assert kinds(errors) == [("sequence", "pour")]
    assert not errors[0].self_corrected
    # The evidence is both halves: the step out of order and the dependency done late.
    assert [ref.event_id for ref in errors[0].evidence] == [events[3].event_id, events[4].event_id]
    assert (errors[0].t_start, errors[0].t_end) == (22.0, 86.0)


@pytest.mark.parametrize(
    ("t_start", "t_end", "self_corrected"),
    [(29.0, 34.0, True), (40.0, 45.0, False)],  # 7 s after the pour, and 18 s after
)
def test_a_dependency_put_right_inside_the_window_is_a_self_corrected_slip(
    t_start: float, t_end: float, self_corrected: bool
) -> None:
    # Pours, sees the teabag still on the counter, and drops it in. Still reported,
    # but as the weaker signal (SPEC section 7).
    events = [
        event("fill_kettle", 1, 6),
        event("boil", 8, 13),
        event("get_cup", 15, 20),
        event("pour", 22, 27),
        event("teabag_in_cup", t_start, t_end),
        event("stir", 50, 55),
        event("remove_teabag", 57, 62),
    ]
    errors = classify(events)

    assert kinds(errors) == [("sequence", "pour")]
    assert errors[0].self_corrected is self_corrected
    assert errors[0].t_end == t_end  # the error spans the slip and the fix


def test_the_self_correct_window_is_the_caller_s_to_set() -> None:
    events = [
        event("fill_kettle", 1, 6),
        event("boil", 8, 13),
        event("get_cup", 15, 20),
        event("pour", 22, 27),
        event("teabag_in_cup", 40, 45),
        event("stir", 50, 55),
        event("remove_teabag", 57, 62),
    ]
    assert classify(events)[0].self_corrected is False
    assert classify(events, self_correct_window_s=60.0)[0].self_corrected is True


# ------------------------------------------------------------------ perseveration


def test_pouring_twice_with_a_step_in_between_is_perseveration() -> None:
    events = run(
        "fill_kettle", "boil", "get_cup", "teabag_in_cup", "pour", "stir", "pour", "remove_teabag"
    )
    errors = classify(events)
    first, again = events[4], events[6]

    assert kinds(errors) == [("perseveration", "pour")]
    assert (errors[0].t_start, errors[0].t_end) == (again.t_start, again.t_end)
    assert [ref.event_id for ref in errors[0].evidence] == [first.event_id, again.event_id]


# -------------------------------------------------------------------- substitution


def test_stirring_with_the_wrong_object_is_a_substitution() -> None:
    # Stirs with the milk bottle. `stir` allows a spoon (or a teaspoon) and the cup.
    events = run(
        "fill_kettle", "boil", "get_cup", "teabag_in_cup", "pour", "stir", "remove_teabag"
    )
    events[5] = event("stir", 51, 56, objects=[ObjectLabel.MILK, ObjectLabel.CUP])
    errors = classify(events)

    assert kinds(errors) == [("substitution", "stir")]
    assert not errors[0].self_corrected
    assert [ref.event_id for ref in errors[0].evidence] == [events[5].event_id]


def test_doing_the_step_again_properly_is_a_self_corrected_slip_not_a_repeat() -> None:
    # Sugar goes in the cup instead of the teabag; the teabag follows two steps later.
    # One self-corrected slip, not a slip plus a perseveration.
    events = [
        event("get_cup", 1, 6),
        event("teabag_in_cup", 8, 12, objects=[ObjectLabel.SUGAR, ObjectLabel.CUP]),
        event("fill_kettle", 14, 18),
        event("teabag_in_cup", 20, 24),
        event("boil", 26, 31),
        event("pour", 33, 38),
        event("stir", 40, 45),
        event("remove_teabag", 47, 52),
    ]
    errors = classify(events)

    assert kinds(errors) == [("substitution", "teabag_in_cup")]
    assert errors[0].self_corrected
    assert [ref.event_id for ref in errors[0].evidence] == [events[1].event_id, events[3].event_id]


# -------------------------------------------------------------------- abandonment


def _walked_off() -> list[StepEvent]:
    """A session with nearly three minutes of nothing in the middle of it."""
    return [
        event("get_cup", 1, 6),
        event("teabag_in_cup", 8, 13),
        event("fill_kettle", 15, 20),
        event("boil", 22, 27),
        event("pour", 200, 206),
        event("stir", 208, 213),
        event("remove_teabag", 215, 220),
    ]


def test_a_long_silence_with_the_task_unfinished_is_abandonment() -> None:
    events = _walked_off()
    errors = classify(events)

    assert kinds(errors) == [("abandonment", None)]
    assert (errors[0].t_start, errors[0].t_end) == (27.0, 200.0)  # the silence itself
    assert [ref.event_id for ref in errors[0].evidence] == [events[3].event_id, events[4].event_id]


def test_a_shorter_silence_is_not_abandonment() -> None:
    events = _walked_off()
    events[4] = event("pour", 140, 146)  # 113 s, inside the default two minutes
    events[5] = event("stir", 150, 155)
    events[6] = event("remove_teabag", 157, 162)
    assert classify(events) == []


def test_the_abandon_gap_is_the_caller_s_to_set() -> None:
    assert classify(_walked_off(), abandon_after_s=600.0) == []
    assert kinds(classify(_walked_off(), abandon_after_s=30.0)) == [("abandonment", None)]


def test_a_silence_after_the_task_is_done_is_not_abandonment() -> None:
    # The tea is made; the resident comes back ten minutes later and adds milk.
    events = run(*TEA.required_steps)
    events.append(event("milk", 700, 706))
    assert classify(events) == []


# ------------------------------------------------- unclear events are never errors


def test_an_unclear_event_is_not_a_substitution() -> None:
    events = run(
        "fill_kettle", "boil", "get_cup", "teabag_in_cup", "pour", "stir", "remove_teabag"
    )
    events[5] = event("stir", 51, 56, objects=[ObjectLabel.MILK, ObjectLabel.CUP])
    assert kinds(classify(events)) == [("substitution", "stir")]

    events[5] = blurred(events[5])
    assert classify(events) == []


def test_an_unclear_repeat_is_not_perseveration() -> None:
    events = run(
        "fill_kettle", "boil", "get_cup", "teabag_in_cup", "pour", "stir", "pour", "remove_teabag"
    )
    assert kinds(classify(events)) == [("perseveration", "pour")]

    events[6] = blurred(events[6])
    assert classify(events) == []


def test_an_unclear_step_is_not_a_missing_one() -> None:
    # A step the verifier could not resolve may still have happened, so it is neither
    # an omission nor a dependency the next step jumped ahead of.
    in_order = run(
        "fill_kettle", "boil", "get_cup", "teabag_in_cup", "pour", "stir", "remove_teabag"
    )
    in_order[3] = blurred(in_order[3])
    assert classify(in_order) == []

    out_of_order = run(
        "fill_kettle", "boil", "get_cup", "pour", "teabag_in_cup", "stir", "remove_teabag"
    )
    assert kinds(classify(out_of_order)) == [("sequence", "pour")]
    out_of_order[4] = blurred(out_of_order[4])
    assert classify(out_of_order) == []


def test_an_unclear_event_breaks_a_silence() -> None:
    events = _walked_off()
    assert kinds(classify(events)) == [("abandonment", None)]

    # Something happened in the middle of the gap; the verifier could not say what.
    events.append(blurred(event("pour", 110, 115)))
    assert classify(events) == []


# --------------------------------------------------- the whole session, and its ids


def test_a_session_with_several_things_wrong_reads_oldest_first() -> None:
    events = [
        event("fill_kettle", 1, 6),
        event("boil", 8, 13),
        event("get_cup", 15, 20),
        event("pour", 200, 206),  # after three minutes of nothing, and with no teabag
        event("stir", 210, 215, objects=[ObjectLabel.MILK, ObjectLabel.CUP]),
        event("pour", 220, 226),
        event("remove_teabag", 230, 235),
    ]
    errors = classify(events)

    assert kinds(errors) == [
        ("abandonment", None),
        ("omission", "teabag_in_cup"),
        ("substitution", "stir"),
        ("perseveration", "pour"),
    ]
    assert [error.t_start for error in errors] == sorted(error.t_start for error in errors)
    assert all(error.session_id == SESSION for error in errors)


def test_the_same_session_always_classifies_the_same_way() -> None:
    events = run(*DEMO)
    errors = classify(events)
    assert classify(events) == errors
    assert classify(list(reversed(events))) == errors  # read in time order, not arrival order


def test_error_ids_are_unique_and_say_what_they_are() -> None:
    errors = classify(run(*DEMO))
    assert len({error.error_id for error in errors}) == len(errors)
    assert all(error.error_id.startswith(f"{SESSION}:{error.type}:") for error in errors)
    # An id is a function of the session, the error and the event it is pinned to, so a
    # live session classified again keeps the ids the dashboard is already showing.
    live = classify(run(*DEMO)[:5], ended=False)
    assert live and {error.error_id for error in live} <= {error.error_id for error in errors}


def test_a_step_the_task_graph_does_not_have_is_rejected() -> None:
    events = [*run("get_cup"), event("make_toast", 20, 25, objects=[ObjectLabel.CUP])]
    with pytest.raises(KeyError, match="make_toast"):
        classify(events)


def test_the_error_types_are_the_spec_s_six_and_hesitation_is_not_ours() -> None:
    assert set(ERROR_TYPES) == {
        "omission",
        "sequence",
        "perseveration",
        "substitution",
        "hesitation",
        "abandonment",
    }
    # Hesitation needs this resident's own baseline, so no session can produce one here.
    assert ErrorType.HESITATION not in {error.type for error in classify(run(*DEMO))}


# ------------------------------------------------------- against the e2e scenarios


@pytest.mark.parametrize("path", scenario_dirs(), ids=lambda path: path.name)
def test_the_recorded_scenarios_expect_what_this_classifier_finds(path: Path) -> None:
    """Every scenario in `tests/scenarios/` gets the errors it expects out of this
    classifier, called the same way `routine_watch.replay` calls it.
    """
    scenario = load_scenario(path)
    expected = Counter(
        (str(error.type), error.step)
        for error in scenario.expected.errors
        if error.type is not ErrorType.HESITATION  # not a graph rule; not ours to find
    )
    errors = classify_errors(
        scenario.events,
        scenario.graph,
        session_id=scenario.events[0].session_id,
    )
    assert Counter((str(error.type), error.step_id) for error in errors) == expected
