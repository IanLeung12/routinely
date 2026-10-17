"""Every scenario's step ids are real task-graph steps.

`expected.yaml`'s `steps:` and `errors[].step:`, and a hand-written `steps.jsonl`'s
`step_id`, are plain strings: nothing validates them against the task graph the
scenario claims (`expected.yaml`'s `task:`). A typo there does not fail loudly - it
just makes the scenario test nothing, because the step it meant to exercise never
happens. `routine_watch.tasks.load_task` is the one place that knows which ids are
real; this file checks every scenario's ids against it.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from routine_watch.replay import load_scenario, scenario_dirs
from routine_watch.tasks import load_task


@pytest.mark.parametrize("path", scenario_dirs(), ids=lambda path: path.name)
def test_every_scenario_step_id_is_in_its_task_graph(path: Path) -> None:
    scenario = load_scenario(path)
    known = set(scenario.graph.step_ids)

    referenced: set[str] = set(scenario.expected.steps)
    referenced.update(error.step for error in scenario.expected.errors if error.step is not None)
    referenced.update(event.step_id for event in scenario.events)

    bad = sorted(referenced - known)
    assert not bad, (
        f"{scenario.name}: step id(s) {bad} are not in the {scenario.graph.id!r} task "
        f"graph (known: {sorted(known)})"
    )


def test_load_task_rejects_an_unknown_step_id() -> None:
    """Pins the message the scenario test above relies on, without touching a real
    scenario file: `load_task`'s graph has no notion of a step it was never told
    about, so the check above is the only thing that can catch a typo.
    """
    graph = load_task("tea")
    with pytest.raises(KeyError, match="no step 'typo_step'"):
        graph.step("typo_step")
