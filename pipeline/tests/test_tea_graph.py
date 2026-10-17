"""The make-tea graph (SPEC section 7) is data, so these tests check the data too.

What the task asked for: "fill kettle" and "get cup" in either order are both valid,
"pour" requires "teabag in cup", and the optional steps can be skipped. The rest guard
the loader: a task file that is not a usable graph has to say so, rather than quietly
produce a graph the error classifier would then read wrongly.
"""

from itertools import permutations

import pytest

from routine_watch.tasks import TaskGraph, TaskGraphError, load_task, parse_task

#: The steps SPEC section 7 and the demo script name, in the task file's order.
TEA_STEPS = (
    "fill_kettle",
    "boil",
    "get_cup",
    "teabag_in_cup",
    "pour",
    "milk",
    "sugar",
    "stir",
    "remove_teabag",
)

#: A valid run of the task with both optional steps skipped.
PLAIN_TEA = ("get_cup", "teabag_in_cup", "fill_kettle", "boil", "pour", "stir", "remove_teabag")

#: The smallest file that is still a task, for the loader's error paths.
TOY_FILE = """
id: toy
title: Toy
steps:
  - id: first
    label: First
    objects: [cup]
  - id: second
    label: Second
    deps: [first]
    objects: [cup]
"""


@pytest.fixture(scope="module")
def tea() -> TaskGraph:
    return load_task("tea")


# ------------------------------------------------------------------------- the data


def test_tea_has_the_steps_from_the_spec(tea: TaskGraph) -> None:
    assert tea.id == "make_tea"
    assert tea.step_ids == TEA_STEPS
    assert all(tea.step(step_id).label for step_id in tea.step_ids)


def test_optional_steps_are_milk_and_sugar(tea: TaskGraph) -> None:
    optional = {step_id for step_id in tea.step_ids if tea.is_optional(step_id)}
    assert optional == {"milk", "sugar"}
    assert tea.required_steps == tuple(s for s in TEA_STEPS if s not in optional)


def test_repeating_a_step_is_only_fine_for_stir(tea: TaskGraph) -> None:
    once_only = {step_id for step_id in tea.step_ids if tea.is_once_only(step_id)}
    assert once_only == set(TEA_STEPS) - {"stir"}


def test_spoon_and_teaspoon_both_count(tea: TaskGraph) -> None:
    assert {"spoon", "teaspoon"} <= tea.allowed_objects("stir")
    assert {"spoon", "teaspoon"} <= tea.allowed_objects("sugar")
    # Stirring with the kettle is a substitution, not a stir.
    assert "kettle" not in tea.allowed_objects("stir")
    # An alias is another name for a detector class, never a class of its own.
    assert tea.step("stir").objects == ("spoon", "cup")


def test_every_step_lists_the_objects_it_is_done_with(tea: TaskGraph) -> None:
    for step_id in tea.step_ids:
        objects = {str(label) for label in tea.step(step_id).objects}
        assert objects
        assert objects <= tea.allowed_objects(step_id)


def test_an_unknown_step_is_a_key_error(tea: TaskGraph) -> None:
    with pytest.raises(KeyError):
        tea.deps("make_toast")


# -------------------------------------------------------------------- the ordering


def test_fill_kettle_and_get_cup_in_either_order(tea: TaskGraph) -> None:
    kettle_first = ("fill_kettle", "boil", "get_cup", "teabag_in_cup")
    cup_first = ("get_cup", "teabag_in_cup", "fill_kettle", "boil")
    tail = ("pour", "stir", "remove_teabag")

    assert tea.is_valid_order(kettle_first + tail)
    assert tea.is_valid_order(cup_first + tail)
    # Neither waits on the other, in either direction.
    assert "get_cup" not in tea.prerequisites("fill_kettle")
    assert "fill_kettle" not in tea.prerequisites("get_cup")


def test_pour_requires_teabag_in_cup(tea: TaskGraph) -> None:
    assert "teabag_in_cup" in tea.deps("pour")
    assert tea.prerequisites("pour") == {"get_cup", "teabag_in_cup", "fill_kettle", "boil"}
    assert not tea.is_valid_order(
        ("fill_kettle", "boil", "get_cup", "pour", "teabag_in_cup", "stir", "remove_teabag")
    )
    assert all(
        order.index("teabag_in_cup") < order.index("pour") for order in tea.valid_orders(TEA_STEPS)
    )


def test_optional_steps_can_be_skipped(tea: TaskGraph) -> None:
    assert tea.is_valid_order(PLAIN_TEA)
    assert tea.is_valid_order((*PLAIN_TEA, "milk", "sugar"))
    # Nothing required sits behind an optional step, so skipping one is always possible.
    for step_id in tea.required_steps:
        assert not any(tea.is_optional(dep) for dep in tea.prerequisites(step_id))


def test_a_missing_required_step_is_not_a_valid_order(tea: TaskGraph) -> None:
    assert not tea.is_valid_order([s for s in PLAIN_TEA if s != "teabag_in_cup"])


def test_a_repeated_or_unknown_step_is_not_a_valid_order(tea: TaskGraph) -> None:
    assert not tea.is_valid_order((*PLAIN_TEA, "pour"))
    assert not tea.is_valid_order((*PLAIN_TEA, "make_toast"))


def test_valid_orders_are_exactly_the_orders_that_check_out(tea: TaskGraph) -> None:
    enumerated = set(tea.valid_orders())
    brute_force = {o for o in permutations(tea.required_steps) if tea.is_valid_order(o)}
    assert enumerated == brute_force
    assert PLAIN_TEA in enumerated
    assert len(enumerated) > 1


def test_valid_orders_covers_the_optional_steps_too(tea: TaskGraph) -> None:
    with_extras = set(tea.valid_orders(TEA_STEPS))
    assert all(tea.is_valid_order(order) for order in with_extras)
    assert all(set(order) == set(TEA_STEPS) for order in with_extras)
    assert len(with_extras) > len(set(tea.valid_orders()))
    # The default is the shortest correct run: no milk, no sugar.
    assert all(not {"milk", "sugar"} & set(order) for order in tea.valid_orders())


def test_valid_orders_needs_the_dependencies_too(tea: TaskGraph) -> None:
    with pytest.raises(TaskGraphError, match="teabag_in_cup"):
        tea.valid_orders(["pour", "boil"])
    with pytest.raises(KeyError):
        tea.valid_orders(["make_toast"])


# --------------------------------------------------------------------- the loader


def test_load_task_is_cached(tea: TaskGraph) -> None:
    assert load_task("tea") is tea


def test_load_task_rejects_unknown_and_unsafe_names() -> None:
    with pytest.raises(TaskGraphError, match="no task"):
        load_task("make_toast")
    for name in ("../contracts", "tea.yaml", "/etc/passwd", ""):
        with pytest.raises(TaskGraphError, match="not a task name"):
            load_task(name)


def test_the_toy_file_round_trips() -> None:
    graph = parse_task(TOY_FILE)
    assert graph.id == "toy"
    assert graph.deps("second") == {"first"}
    assert graph.deps("first") == frozenset()
    assert list(graph.valid_orders()) == [("first", "second")]


@pytest.mark.parametrize(
    ("before", "after", "message"),
    [
        ("deps: [first]", "deps: [third]", "unknown step"),
        ("deps: [first]", "deps: [second]", "dependencies form a cycle"),
        ("id: second", "id: first", "step ids are not unique"),
        ("id: second", "id: Second", "not snake_case"),
        ("id: toy", "id: Toy", "not snake_case"),
        ("objects: [cup]\n  - id: second", "objects: [fork]\n  - id: second", "objects"),
        ("label: First", "label: First\n    sideways: true", "Extra inputs are not permitted"),
        ("label: First", "label: First\n    optional: true", "depends on optional step"),
        ("title: Toy", "title: Toy\naliases:\n  cup: spoon", "already a detector class"),
        ("title: Toy", "title: Toy\naliases:\n  Teaspoon: spoon", "not snake_case"),
    ],
)
def test_a_file_that_is_not_a_graph_says_so(before: str, after: str, message: str) -> None:
    broken = TOY_FILE.replace(before, after)
    assert broken != TOY_FILE
    with pytest.raises(TaskGraphError, match=message):
        parse_task(broken)


def test_what_is_not_a_task_file_at_all_is_rejected() -> None:
    for text in ("id: [unclosed", "id: toy\ntitle: Toy\nsteps: []\n", "", "- a\n- b\n"):
        with pytest.raises(TaskGraphError):
            parse_task(text)
