"""scripts/eval.py (T454): a small cohort, checking the report's shape, not exact
numbers - the synthetic cohort's own randomness means a 5-person split can land
with zero people in a group, so assertions stay loose on counts and tight on ranges.
"""

import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / "scripts" / "eval.py"


def run_eval(*args):
    done = subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        capture_output=True,
        text=True,
        cwd=REPO,
        timeout=60,
    )
    assert done.returncode == 0, done.stderr
    return json.loads(done.stdout)


def test_five_person_cohort_has_expected_keys_and_ranges():
    report = run_eval("--people", "5", "--days", "60", "--seed", "0")

    assert report["params"] == {
        "people": 5, "days": 60, "seed": 0, "baseline_days": 14, "k": 2.0,
    }

    groups = report["groups"]
    assert set(groups) == {"sudden", "drift", "normal"}
    assert sum(groups.values()) == 5
    assert all(count >= 0 for count in groups.values())

    sudden = report["sudden"]
    assert sudden["total"] == groups["sudden"]
    assert sudden["caught"] + sudden["missed"] == sudden["total"]
    if sudden["total"]:
        assert 0.0 <= sudden["catch_rate"] <= 1.0
    else:
        assert sudden["catch_rate"] is None
    if sudden["caught"]:
        assert sudden["hours_to_flag_median"] >= 0.0
        assert sudden["hours_to_flag_p90"] >= sudden["hours_to_flag_median"] - 1e-9
    else:
        assert sudden["hours_to_flag_median"] is None
        assert sudden["hours_to_flag_p90"] is None

    false_alarms = report["false_alarms"]
    assert false_alarms["normal_people"] == groups["normal"]
    assert false_alarms["episodes_total"] >= 0
    if groups["normal"]:
        assert false_alarms["per_person_per_month"] >= 0.0
    else:
        assert false_alarms["per_person_per_month"] is None

    weekly = report["weekly_baseline"]
    assert weekly["matched_n"] >= 0
    assert weekly["matched_n"] <= sudden["caught"]

    drift = report["drift"]
    assert drift["total"] == groups["drift"]
    assert 0 <= drift["trending_count"] <= drift["total"]

    sweep = report["sensitivity_sweep"]
    assert [point["k"] for point in sweep] == [1.5, 2.0, 2.5]
    for point in sweep:
        if point["catch_rate"] is not None:
            assert 0.0 <= point["catch_rate"] <= 1.0
        if point["false_alarms_per_person_month"] is not None:
            assert point["false_alarms_per_person_month"] >= 0.0


def test_deterministic_for_same_seed():
    first = run_eval("--people", "5", "--days", "60", "--seed", "0")
    second = run_eval("--people", "5", "--days", "60", "--seed", "0")
    assert first == second


def _read_eval_md():
    path = REPO / "docs" / "EVAL.md"
    return path.read_bytes() if path.exists() else None


def test_does_not_write_docs_by_default():
    before = _read_eval_md()
    run_eval("--people", "5", "--days", "60")
    after = _read_eval_md()
    assert before == after
