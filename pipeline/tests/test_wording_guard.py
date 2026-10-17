"""Guard the wording used by patterns, checks and offline summaries (SPEC §7.5)."""

import json
from datetime import datetime

from routine_watch import demo
from routine_watch.alerts import build_alerts
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


def test_demo_alert_wording_stays_review_only(monkeypatch):
    monkeypatch.setenv("LIVE_API", "0")
    monkeypatch.setattr(demo, "_live_sessions", lambda resident_id: [])
    residents = demo.demo_residents()
    # Exercise every demo scenario's alert, including normally unflagged ones,
    # by lowering only this test's flag threshold. Generated sessions stay intact.
    flagged = [
        {
            **resident,
            "status": "flagged",
            "baseline": {**resident["baseline"], "threshold": -1},
        }
        for resident in residents
    ]
    alerts = build_alerts(flagged)
    assert {alert.resident_id for alert in alerts} == {
        resident["id"] for resident in residents
    }
    assert alerts
    for alert in alerts:
        _assert_clean(json.dumps(alert.model_dump(mode="json")))
