import re
from pathlib import Path


def test_scenarios_readme_lists_every_scenario_folder():
    repo_root = Path(__file__).resolve().parents[2]
    scenarios_dir = repo_root / "tests" / "scenarios"
    readme = scenarios_dir / "README.md"

    folders = {
        p.name
        for p in scenarios_dir.iterdir()
        if p.is_dir() and not p.name.startswith(".")
    }

    text = readme.read_text()
    section = text.split("## The scenarios here", 1)[1]
    listed = set(re.findall(r"^\| `([^`]+)` \|", section, re.MULTILINE))

    missing = folders - listed
    extra = listed - folders

    assert not missing and not extra, (
        f"missing from README table: {sorted(missing)}; "
        f"extra rows with no folder: {sorted(extra)}"
    )
