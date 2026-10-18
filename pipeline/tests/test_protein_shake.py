"""The protein-shake graph (Ian's own routine), which is only a data file plus three
detector classes - the same shape `test_meds_graph.py` showed for the second task.

These tests check the shape the error classifier will read: the two branches meeting
at `close_lid`, the lid closed before the shake, the optional tail, and the extra
names for the shaker, the tub and the water. The scenarios under
`tests/scenarios/protein_shake_*` cover the same graph end to end, through the
classifier and the change flag.
"""


import pytest

from routine_watch.contracts import ObjectLabel
from routine_watch.tasks import TaskGraph, TaskGraphError, load_task

#: The steps the task asks for, in the task file's order.
PROTEIN_SHAKE_STEPS = (
    "get_shaker",
    "open_tub",
    "scoop_powder",
    "add_liquid",
    "close_lid",
    "shake",
    "close_tub",
    "drink",
)

#: A correct run with both optional steps skipped: powder first, then the liquid.
POWDER_FIRST = ("get_shaker", "open_tub", "scoop_powder", "add_liquid", "close_lid", "shake")

#: The same task done the other way round, and just as correct.
LIQUID_FIRST = ("get_shaker", "add_liquid", "open_tub", "scoop_powder", "close_lid", "shake")


@pytest.fixture(scope="module")
def protein_shake() -> TaskGraph:
    return load_task("protein_shake")


# ------------------------------------------------------------------------- the data


def test_the_detector_classes_the_task_needs_are_in_the_contract() -> None:
    classes = {str(label) for label in ObjectLabel}
    assert {"shaker", "protein_tub", "scoop"} <= classes
    # The liquid side reuses meds' water class rather than adding a new one.
    assert "water_jug" in classes


def test_milk_and_water_both_count_for_the_liquid(protein_shake: TaskGraph) -> None:
    assert {"milk", "water_jug"} <= protein_shake.allowed_objects("add_liquid")
    # Pouring into a cup instead of the shaker is a substitution, not adding liquid.
    assert "cup" not in protein_shake.allowed_objects("add_liquid")


def test_the_everyday_names_for_the_shaker_tub_and_bottle_count_too(
    protein_shake: TaskGraph,
) -> None:
    assert {"shaker_bottle", "blender_bottle"} <= protein_shake.allowed_objects("get_shaker")
    assert {"protein", "powder", "tub"} <= protein_shake.allowed_objects("open_tub")
    assert "water_bottle" in protein_shake.allowed_objects("add_liquid")
    # An alias is another name for a detector class, never a class of its own.
    assert protein_shake.step("get_shaker").objects == (ObjectLabel.SHAKER,)
    assert protein_shake.step("add_liquid").objects == (
        ObjectLabel.MILK,
        ObjectLabel.WATER_JUG,
        ObjectLabel.SHAKER,
    )


def test_every_step_lists_the_objects_it_is_done_with(protein_shake: TaskGraph) -> None:
    for step_id in protein_shake.step_ids:
        objects = {str(label) for label in protein_shake.step(step_id).objects}
        assert objects
        assert objects <= protein_shake.allowed_objects(step_id)


# -------------------------------------------------------------------- the ordering


def test_powder_and_liquid_can_be_done_in_either_order(protein_shake: TaskGraph) -> None:
    assert protein_shake.is_valid_order(POWDER_FIRST)
    assert protein_shake.is_valid_order(LIQUID_FIRST)
    # Neither branch waits on the other, in either direction.
    assert "add_liquid" not in protein_shake.prerequisites("scoop_powder")
    assert "open_tub" not in protein_shake.prerequisites("add_liquid")


def test_shaking_waits_on_the_lid(protein_shake: TaskGraph) -> None:
    assert protein_shake.deps("shake") == {"close_lid"}
    assert not protein_shake.is_valid_order(
        ("get_shaker", "open_tub", "scoop_powder", "add_liquid", "shake", "close_lid")
    )


def test_shaking_with_the_lid_open_is_not_a_valid_order(protein_shake: TaskGraph) -> None:
    # What tests/scenarios/protein_shake_lid_open_shake records, as a sequence error.
    assert not protein_shake.is_valid_order(
        ("get_shaker", "open_tub", "scoop_powder", "add_liquid", "shake", "close_lid")
    )


def test_forgetting_the_powder_is_not_a_valid_order(protein_shake: TaskGraph) -> None:
    # What tests/scenarios/protein_shake_omit_powder records, as an omission.
    assert not protein_shake.is_valid_order(
        [s for s in POWDER_FIRST if s != "scoop_powder"]
    )


def test_valid_orders_needs_the_dependencies_too(protein_shake: TaskGraph) -> None:
    with pytest.raises(TaskGraphError, match="get_shaker"):
        protein_shake.valid_orders(["close_lid", "add_liquid"])
    with pytest.raises(KeyError):
        protein_shake.valid_orders(["teabag_in_cup"])


# ------------------------------------------------------- one loader, three task files


def test_the_three_tasks_are_separate_graphs(protein_shake: TaskGraph) -> None:
    tea = load_task("tea")
    meds = load_task("meds")
    assert protein_shake.id not in (tea.id, meds.id)
    assert not set(tea.step_ids) & set(protein_shake.step_ids)
    assert not set(meds.step_ids) & set(protein_shake.step_ids)
    # A step of another task is not a step of this one.
    with pytest.raises(KeyError):
        protein_shake.deps("teabag_in_cup")
    with pytest.raises(KeyError):
        protein_shake.deps("take_pill")
    with pytest.raises(KeyError):
        tea.deps("shake")


def test_the_tea_and_meds_graphs_are_untouched() -> None:
    tea = load_task("tea")
    meds = load_task("meds")
    assert tea.id == "make_tea"
    assert meds.id == "take_meds"
    # protein_shake's aliases are its own: neither other file can widen them.
    assert "shaker_bottle" not in {name for s in tea.step_ids for name in tea.allowed_objects(s)}
    assert "shaker_bottle" not in {name for s in meds.step_ids for name in meds.allowed_objects(s)}


def test_load_task_is_cached(protein_shake: TaskGraph) -> None:
    assert load_task("protein_shake") is protein_shake


def test_the_shake_routine_ian_signed_off(protein_shake: TaskGraph) -> None:
    ids = [step.id for step in protein_shake.steps]
    assert ids == [
        "get_shaker", "open_tub", "scoop_powder", "add_liquid", "close_lid", "shake", "close_tub",
    ]
    assert protein_shake.step("get_shaker").label == "Pick up the shaker"
    assert {s.id for s in protein_shake.steps if s.optional} == {"open_tub", "close_tub"}
    # picking the shaker up again, or scooping twice, is never a repeat
    assert not protein_shake.step("get_shaker").once_only
    assert not protein_shake.step("scoop_powder").once_only
    assert protein_shake.deps("scoop_powder") == {"get_shaker"}
    assert protein_shake.deps("close_lid") == {"scoop_powder", "add_liquid"}
    assert protein_shake.deps("shake") == {"close_lid"}
