"""The scaffold holds together: every stage in SPEC section 6 has a module."""

import importlib

import routine_watch


def test_version_is_set() -> None:
    assert routine_watch.__version__


def test_every_stage_imports_and_names_itself() -> None:
    for stage in routine_watch.STAGES:
        module = importlib.import_module(f"routine_watch.{stage}")
        assert module.STAGE == stage


def test_error_types_match_the_spec() -> None:
    from routine_watch.errors import ERROR_TYPES

    assert set(ERROR_TYPES) == {
        "omission",
        "sequence",
        "perseveration",
        "substitution",
        "hesitation",
        "abandonment",
    }
