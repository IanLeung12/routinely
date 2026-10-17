"""demo_residents() and build_alerts() must be stable across repeated calls when no
live sessions have been recorded (T133/T121: the tester saw the demo alert grow on
every page load)."""

from routine_watch.alerts import build_alerts
from routine_watch.demo import demo_residents


def _resident_summary(residents: list[dict]) -> list[tuple]:
    return [
        (resident["id"], resident["status"], resident["scores"], len(resident["sessions"]))
        for resident in residents
    ]


def _alert_summary(alerts: list) -> list[tuple]:
    return [(alert.alert_id, len(alert.errors), alert.summary) for alert in alerts]


def test_demo_residents_stable_across_calls(_empty_log):
    first = demo_residents()
    second = demo_residents()
    third = demo_residents()

    assert _resident_summary(first) == _resident_summary(second) == _resident_summary(third)


def test_build_alerts_stable_across_calls(_empty_log):
    first = build_alerts(demo_residents())
    second = build_alerts(demo_residents())
    third = build_alerts(demo_residents())

    assert _alert_summary(first) == _alert_summary(second) == _alert_summary(third)
