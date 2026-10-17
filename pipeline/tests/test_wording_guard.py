"""Guard SPEC's wording rule: patterns, checks and summaries never diagnose (SPEC §7.5)."""

from routine_watch.checks import suggest_checks
from routine_watch.contracts import SuggestedCheck
from routine_watch.explain import TemplateExplainer
from routine_watch.patterns_library import LIBRARY

BANNED = (
    "diagnos",
    "has delirium",
    "has dementia",
    "suffers from",
    "prescribe",
    "dose",
)


def _assert_clean(text: str) -> None:
    lowered = text.lower()
    for banned in BANNED:
        assert banned not in lowered, f"banned wording {banned!r} found in: {text!r}"


def test_pattern_library_never_diagnoses():
    for pattern in LIBRARY:
        _assert_clean(pattern.name)
        _assert_clean(pattern.source)
        _assert_clean(pattern.time_profile.note)
        for check in pattern.checks:
            text = check.value if isinstance(check, SuggestedCheck) else check
            _assert_clean(text)


def test_suggested_checks_never_diagnose():
    for check in SuggestedCheck:
        _assert_clean(check.value)


def test_suggest_checks_offline_never_diagnoses():
    now_records = [
        {"ts": "2024-01-01T10:00:00", "kind": "temperature", "value": 38.0},
        {"ts": "2024-01-01T09:00:00", "kind": "fluid_intake", "value": 500},
        {"ts": "2024-01-01T08:00:00", "kind": "med_change", "value": None},
    ]
    from datetime import datetime

    result = suggest_checks(now_records, now=datetime.fromisoformat("2024-01-01T11:00:00"))
    for check in result:
        _assert_clean(check)


def test_template_explainer_never_diagnoses():
    explainer = TemplateExplainer()
    scenarios = [
        {
            "errors": [],
            "baseline": {"observed": 0, "baseline_mean": 1, "baseline_days": 7, "sessions": 1},
            "context": [],
        },
        {
            "errors": [
                {"type": "omission", "step_id": "pour_water", "t_start": 12.0},
                {"type": "perseveration", "step_id": "stir", "t_start": 45.0},
                {"type": "sequence", "step_id": "add_teabag", "t_start": 60.0},
                {"type": "substitution", "step_id": "cup", "t_start": 75.0},
                {"type": "hesitation", "step_id": "drink", "t_start": 90.0},
                {"type": "abandonment", "step_id": None, "t_start": 100.0},
            ],
            "baseline": {"observed": 6, "baseline_mean": 1, "baseline_days": 7, "sessions": 3},
            "context": ["new medication started", "fever noted"],
        },
    ]
    for scenario in scenarios:
        summary = explainer.summarise(
            scenario["errors"], scenario["baseline"], scenario["context"]
        )
        _assert_clean(summary)
