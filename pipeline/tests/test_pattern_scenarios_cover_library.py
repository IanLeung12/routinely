"""SPEC §8: every shippable pattern needs at least one replayable scenario.

`one_sided_change` is kept out of the demo (SPEC) and is exempt.
"""

from pathlib import Path

import yaml

from routine_watch.patterns_library import LIBRARY

EXEMPT_PATTERN_IDS = {"one_sided_change"}


def _scenario_top_patterns() -> set[str]:
    repo_root = Path(__file__).resolve().parents[2]
    scenarios_dir = repo_root / "tests" / "scenarios"

    found: set[str] = set()
    for expected_path in scenarios_dir.glob("*/expected.yaml"):
        data = yaml.safe_load(expected_path.read_text())
        top_pattern = data.get("top_pattern") if data else None
        if top_pattern:
            found.add(top_pattern)
    return found


def test_every_shippable_pattern_has_a_replayable_scenario():
    shippable_pattern_ids = {
        pattern.pattern_id
        for pattern in LIBRARY
        if pattern.pattern_id not in EXEMPT_PATTERN_IDS
    }

    covered = _scenario_top_patterns()

    missing = shippable_pattern_ids - covered
    assert not missing, (
        f"patterns with no replayable scenario (top_pattern in expected.yaml): "
        f"{sorted(missing)}"
    )
