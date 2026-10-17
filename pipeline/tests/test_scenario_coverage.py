"""Guards against scenario rot (T372).

Scenarios are the only test that exercises the pipeline's stages together (`tests/
scenarios/README.md`), but nothing stops one from quietly disappearing, or a new
`ErrorType` or pattern from shipping without ever being replayed. This file loads
every scenario once and checks the corpus as a whole still covers:

* every `ErrorType` (`contracts.py`), in a session's own errors or in a history
  session's error breakdown (hesitation never appears any other way: see
  `tests/scenarios/README.md`)
* a `*_normal` and a `*_abandoned` scenario for every task graph
* a `pattern_*` scenario for every pattern in the library, unless the pattern is on
  the explicit, commented allow-list below
"""

from __future__ import annotations

import pytest

from routine_watch.contracts import ErrorType
from routine_watch.patterns_library import LIBRARY
from routine_watch.replay import load_scenario, scenario_dirs
from routine_watch.tasks import TASKS_DIR

#: Kept out of the demo (SPEC); no scenario is expected to exercise it.
EXEMPT_PATTERN_IDS = {"one_sided_change"}

_SCENARIOS = [load_scenario(path) for path in scenario_dirs()]


def test_every_error_type_has_a_scenario() -> None:
    found: set[ErrorType] = set()
    for scenario in _SCENARIOS:
        found.update(error.type for error in scenario.expected.errors)
        for history in scenario.expected.history:
            found.update(history.errors)

    missing = {error_type.value for error_type in ErrorType} - {t.value for t in found}
    assert not missing, f"error type(s) with no scenario at all: {sorted(missing)}"


@pytest.mark.parametrize("task_name", sorted(path.stem for path in TASKS_DIR.glob("*.yaml")))
def test_every_task_has_a_normal_and_an_abandoned_scenario(task_name: str) -> None:
    names = {scenario.name for scenario in _SCENARIOS if scenario.expected.task == task_name}
    for suffix in ("normal", "abandoned"):
        expected_name = f"{task_name}_{suffix}"
        assert expected_name in names, (
            f"{task_name!r} task has no {suffix!r} scenario: expected a scenario "
            f"directory named {expected_name!r} with task: {task_name}"
        )


def test_every_shippable_pattern_has_a_pattern_scenario() -> None:
    shippable = {
        pattern.pattern_id for pattern in LIBRARY if pattern.pattern_id not in EXEMPT_PATTERN_IDS
    }
    covered = {
        scenario.expected.top_pattern
        for scenario in _SCENARIOS
        if scenario.name.startswith("pattern_") and scenario.expected.top_pattern
    }

    missing = shippable - covered
    assert not missing, f"pattern(s) with no pattern_* scenario: {sorted(missing)}"
