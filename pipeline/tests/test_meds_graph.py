"""The take-medication graph (SPEC nice-to-have 4), which is only a data file.

The second task is here to show the approach generalises, so these tests are mostly
about that: `meds.yaml` and four detector classes are the whole feature, the same
loader reads it, and the make-tea graph does not notice. The rest check the shape the
error classifier will read - the two branches meeting at `drink_water`, the optional
tail, the two names for the organiser - because getting that wrong would quietly
change what counts as an error.

The scenarios `tests/scenarios/meds_normal` and `meds_skip_water` cover the same graph
end to end, through the classifier and the change flag.
"""

from itertools import permutations

import pytest

from routine_watch.contracts import ObjectLabel
from routine_watch.tasks import TaskGraph, TaskGraphError, load_task

#: The steps the task asks for, in the task file's order.
MEDS_STEPS = (
    "get_glass",
    "fill_glass",
    "open_organiser",
    "take_pill",
    "drink_water",
    "close_organiser",
)

#: A correct run with the optional step skipped: the pill side first, then the glass.
PILL_FIRST = ("open_organiser", "take_pill", "get_glass", "fill_glass", "drink_water")

#: The same task done the other way round, and just as correct.
GLASS_FIRST = ("get_glass", "fill_glass", "open_organiser", "take_pill", "drink_water")


@pytest.fixture(scope="module")
def meds() -> TaskGraph:
    return load_task("meds")


# ------------------------------------------------------------------------- the data


def test_meds_is_a_task_of_its_own(meds: TaskGraph) -> None:
    assert meds.id == "take_meds"
    assert meds.title
    assert meds.step_ids == MEDS_STEPS
    assert all(meds.step(step_id).label for step_id in meds.step_ids)


def test_the_detector_classes_the_task_needs_are_in_the_contract() -> None:
    classes = {str(label) for label in ObjectLabel}
    assert {"pill_bottle", "pill_organiser", "glass", "water_jug"} <= classes


def test_closing_the_organiser_is_the_only_optional_step(meds: TaskGraph) -> None:
    optional = {step_id for step_id in meds.step_ids if meds.is_optional(step_id)}
    assert optional == {"close_organiser"}
    assert meds.required_steps == tuple(s for s in MEDS_STEPS if s != "close_organiser")


def test_repeating_a_step_is_only_fine_for_drinking(meds: TaskGraph) -> None:
    # Another sip of water is normal; opening the organiser twice is not.
    once_only = {step_id for step_id in meds.step_ids if meds.is_once_only(step_id)}
    assert once_only == set(MEDS_STEPS) - {"drink_water"}


def test_a_bottle_and_an_organiser_both_count_for_the_pill(meds: TaskGraph) -> None:
    for step_id in ("open_organiser", "take_pill", "close_organiser"):
        assert {"pill_bottle", "pill_organiser"} <= meds.allowed_objects(step_id)


def test_the_ward_names_for_the_organiser_and_the_glass_count_too(meds: TaskGraph) -> None:
    assert "dosette_box" in meds.allowed_objects("open_organiser")
    assert {"glass", "tumbler"} <= meds.allowed_objects("drink_water")
    # Drinking from the teacup instead is a substitution, not a drink of water.
    assert "cup" not in meds.allowed_objects("drink_water")
    # An alias is another name for a detector class, never a class of its own.
    assert meds.step("drink_water").objects == (ObjectLabel.GLASS,)
    assert meds.step("open_organiser").objects == (
        ObjectLabel.PILL_ORGANISER,
        ObjectLabel.PILL_BOTTLE,
    )


def test_every_step_lists_the_objects_it_is_done_with(meds: TaskGraph) -> None:
    for step_id in meds.step_ids:
        objects = {str(label) for label in meds.step(step_id).objects}
        assert objects
        assert objects <= meds.allowed_objects(step_id)


# -------------------------------------------------------------------- the ordering


def test_the_pill_and_the_glass_can_be_done_in_either_order(meds: TaskGraph) -> None:
    assert meds.is_valid_order(PILL_FIRST)
    assert meds.is_valid_order(GLASS_FIRST)
    # Neither branch waits on the other, in either direction.
    assert "get_glass" not in meds.prerequisites("take_pill")
    assert "open_organiser" not in meds.prerequisites("fill_glass")


def test_drinking_waits_on_both_branches(meds: TaskGraph) -> None:
    # The point of the task: the pill goes down with water, not before it or dry.
    assert meds.deps("drink_water") == {"take_pill", "fill_glass"}
    assert meds.prerequisites("drink_water") == {
        "get_glass",
        "fill_glass",
        "open_organiser",
        "take_pill",
    }
    assert all(order[-1] == "drink_water" for order in meds.valid_orders())


def test_the_pill_comes_out_of_an_open_organiser(meds: TaskGraph) -> None:
    assert meds.deps("take_pill") == {"open_organiser"}
    assert not meds.is_valid_order(
        ("get_glass", "fill_glass", "take_pill", "open_organiser", "drink_water")
    )


def test_the_glass_is_filled_after_it_is_fetched(meds: TaskGraph) -> None:
    assert meds.deps("fill_glass") == {"get_glass"}
    assert not meds.is_valid_order(
        ("fill_glass", "get_glass", "open_organiser", "take_pill", "drink_water")
    )


def test_closing_the_organiser_can_be_skipped_or_done(meds: TaskGraph) -> None:
    assert meds.is_valid_order(GLASS_FIRST)
    assert meds.is_valid_order(
        ("get_glass", "fill_glass", "open_organiser", "take_pill", "close_organiser", "drink_water")
    )
    # Nothing required sits behind the optional step, so skipping it is always possible.
    for step_id in meds.required_steps:
        assert not any(meds.is_optional(dep) for dep in meds.prerequisites(step_id))


def test_a_dry_swallow_is_not_a_valid_order(meds: TaskGraph) -> None:
    # What tests/scenarios/meds_skip_water records, as an omission.
    assert not meds.is_valid_order([s for s in GLASS_FIRST if s != "drink_water"])


def test_valid_orders_are_exactly_the_orders_that_check_out(meds: TaskGraph) -> None:
    enumerated = set(meds.valid_orders())
    brute_force = {o for o in permutations(meds.required_steps) if meds.is_valid_order(o)}
    assert enumerated == brute_force
    assert {PILL_FIRST, GLASS_FIRST} <= enumerated
    # The two branches interleave freely before they meet, and nothing else varies.
    assert len(enumerated) == 6
    # The default is the shortest correct run: the organiser is left open.
    assert all("close_organiser" not in order for order in enumerated)


def test_valid_orders_covers_the_optional_step_too(meds: TaskGraph) -> None:
    with_extras = set(meds.valid_orders(MEDS_STEPS))
    assert all(meds.is_valid_order(order) for order in with_extras)
    assert all(set(order) == set(MEDS_STEPS) for order in with_extras)
    assert len(with_extras) > len(set(meds.valid_orders()))


def test_valid_orders_needs_the_dependencies_too(meds: TaskGraph) -> None:
    with pytest.raises(TaskGraphError, match="fill_glass"):
        meds.valid_orders(["drink_water", "take_pill", "open_organiser"])
    with pytest.raises(KeyError):
        meds.valid_orders(["teabag_in_cup"])


# ------------------------------------------------------- one loader, two task files


def test_the_two_tasks_are_separate_graphs(meds: TaskGraph) -> None:
    tea = load_task("tea")
    assert tea.id != meds.id
    assert not set(tea.step_ids) & set(meds.step_ids)
    # A step of the other task is not a step of this one.
    with pytest.raises(KeyError):
        meds.deps("teabag_in_cup")
    with pytest.raises(KeyError):
        tea.deps("take_pill")


def test_the_tea_graph_is_untouched() -> None:
    tea = load_task("tea")
    assert tea.id == "make_tea"
    assert tea.step_ids[:5] == ("fill_kettle", "boil", "get_cup", "teabag_in_cup", "pour")
    assert {s for s in tea.step_ids if tea.is_optional(s)} == {"milk", "sugar"}
    assert tea.allowed_objects("stir") == {"spoon", "teaspoon", "cup"}
    # tea's aliases are tea's own: the meds file cannot widen them.
    assert "dosette_box" not in {name for s in tea.step_ids for name in tea.allowed_objects(s)}


def test_load_task_is_cached(meds: TaskGraph) -> None:
    assert load_task("meds") is meds
