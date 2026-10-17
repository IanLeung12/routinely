"""Every scenario directory with an expected.yaml must have a row in the README."""

from pathlib import Path

SCENARIOS_DIR = Path(__file__).resolve().parent / "scenarios"


def test_every_scenario_is_listed_in_readme():
    readme = (SCENARIOS_DIR / "README.md").read_text()
    scenario_names = sorted(
        p.name for p in SCENARIOS_DIR.iterdir() if (p / "expected.yaml").is_file()
    )
    missing = [name for name in scenario_names if f"`{name}`" not in readme]
    assert not missing, f"missing from tests/scenarios/README.md: {missing}"
