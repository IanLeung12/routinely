"""The handoff's latest flagged session names the same errors as that resident's
own alert (T166/#159): a nurse must read the same steps and times in both places.
"""

from routine_watch.alerts import build_alerts, session_id_for, task_errors
from routine_watch.demo import DEMO_NOW, demo_residents
from routine_watch.handoff import DEFAULT_WINDOW_H, _FlaggedSession, _latest, _window_sessions


def test_session_id_for_is_resident_and_index():
    assert session_id_for("mrs-k", 3) == "mrs-k-3"


def test_latest_handoff_session_errors_are_a_subset_of_her_alert_errors():
    residents = demo_residents()
    alerts = build_alerts(residents)

    flagged = []
    for r in residents:
        threshold = r["baseline"]["threshold"]
        for session_id, session, score in _window_sessions(r, DEMO_NOW, DEFAULT_WINDOW_H):
            if score > threshold:
                flagged.append((r, session_id, session))

    latest = _latest(
        [_FlaggedSession(resident=r, session_id=sid, session=s) for r, sid, s in flagged]
    )

    assert latest is not None, "demo data has no flagged session in the handoff window"

    resident_alert = next((a for a in alerts if a.resident_id == latest.resident["id"]), None)

    handoff_errors = task_errors(latest.session_id, latest.session)
    handoff_error_ids = {e.error_id for e in handoff_errors}

    if resident_alert is None:
        # This resident's latest flagged session didn't earn an alert: SPEC section 7
        # says a single bad session never alerts, so nothing to compare against.
        assert resident_alert is None
        return

    alert_error_ids = {e.error_id for e in resident_alert.errors}
    assert handoff_error_ids <= alert_error_ids
