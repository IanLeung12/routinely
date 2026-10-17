"""Nurse feedback's tuned threshold (SPEC MVP 7) reads the same status everywhere
it is shown - not just `/handoff` and the alert payload, which already applied it,
but `/residents`, `/residents/{id}` and `/alerts` too (T167).
"""

from datetime import datetime

import pytest
from fastapi.testclient import TestClient

from routine_watch import api as api_module
from routine_watch import feedback as feedback_module
from routine_watch.api import app
from routine_watch.change_detection import Baseline, flag_change
from routine_watch.contracts import AlertFeedback, FeedbackVerdict
from routine_watch.demo import DEMO_NOW, status_for
from routine_watch.feedback import FeedbackStore

#: The demo resident on a slow drift: her seeded history alone leaves her on watch,
#: just under the bar, until a nurse's feedback lowers it (T124, `tests/test_handoff.py`).
DRIFT_RESIDENT = "mr-chen"

#: Enough confirmed alerts to pull a threshold down to its floor (`feedback.MIN_FACTOR`).
MANY_CONFIRMED = 6

MRS_K = "mrs-k"
MRS_K_ALERT = f"alert-{MRS_K}"


@pytest.fixture(autouse=True)
def _clean_feedback_store():
    """Each test gets a clean feedback store: the API module keeps it global."""
    api_module._feedback_store = FeedbackStore()
    yield
    api_module._feedback_store = FeedbackStore()


def _confirmed(resident_id: str, n: int) -> None:
    """`n` confirmed alerts logged against `resident_id`, as distinct alert ids so
    they all count (re-posting one alert id replaces its verdict rather than piling
    up, `routine_watch.feedback`)."""
    for i in range(n):
        api_module._feedback_store.record(
            f"alert-{resident_id}-{i}",
            resident_id,
            AlertFeedback(verdict=FeedbackVerdict.CONFIRMED, by="nurse", at=DEMO_NOW),
        )


def _false_alarms(resident_id: str, n: int) -> None:
    for i in range(n):
        api_module._feedback_store.record(
            f"alert-{resident_id}-{i}",
            resident_id,
            AlertFeedback(verdict=FeedbackVerdict.FALSE_ALARM, by="nurse", at=DEMO_NOW),
        )


def _row(handoff: dict, resident_id: str) -> dict:
    return next(row for row in handoff["residents"] if row["resident_id"] == resident_id)


def test_residents_status_agrees_with_handoff_once_feedback_tunes_the_threshold():
    with TestClient(app) as client:
        before = {r["id"]: r for r in client.get("/residents").json()}
        before_handoff = client.get("/handoff").json()

        assert before[DRIFT_RESIDENT]["status"] == "watch"
        assert _row(before_handoff, DRIFT_RESIDENT)["flags"] == 0

        _confirmed(DRIFT_RESIDENT, MANY_CONFIRMED)

        after = {r["id"]: r for r in client.get("/residents").json()}
        after_handoff = client.get("/handoff").json()

    assert after[DRIFT_RESIDENT]["status"] == "flagged"
    assert _row(after_handoff, DRIFT_RESIDENT)["flags"] >= 1


def test_get_resident_detail_status_also_follows_the_tuned_threshold():
    with TestClient(app) as client:
        _confirmed(DRIFT_RESIDENT, MANY_CONFIRMED)
        detail = client.get(f"/residents/{DRIFT_RESIDENT}").json()

    assert detail["status"] == "flagged"


def test_a_resident_feedback_never_tunes_to_flagged_has_no_top_pattern():
    """A normal resident stays normal, with no top pattern to show (SPEC §9 screen 1),
    whatever feedback is logged against somebody else."""
    with TestClient(app) as client:
        _confirmed(DRIFT_RESIDENT, MANY_CONFIRMED)
        residents = {r["id"]: r for r in client.get("/residents").json()}

    normal = next(r for r in residents.values() if r["status"] == "normal")
    assert normal["top_pattern"] is None


def test_still_flagged_residents_keep_their_alert(mrs_k_flagged):
    """Regression guard: a resident whose feedback cannot tune the threshold past her
    qualifying sessions (mrs-k's margin is too wide, T167) stays flagged and keeps
    showing up in `/alerts`, status and all."""
    with TestClient(app) as client:
        _false_alarms(MRS_K, 3)

        residents = {r["id"]: r for r in client.get("/residents").json()}
        alerts = client.get("/alerts").json()

    assert residents[MRS_K]["status"] == "flagged"
    assert [alert["resident_id"] for alert in alerts] == [MRS_K]


def test_false_alarm_that_unflags_the_resident_still_lets_the_alert_be_read_and_answered(
    mrs_k_flagged, monkeypatch
):
    """T182 regression: a false alarm big enough to tune mrs-k off `/alerts` must not
    make her alert 404 - `GET /alerts/{id}` and the next feedback POST (the "what was
    it?" cause) still need to find it, or a nurse can never correct a mistaken tap.

    Mrs-k's margin is wide enough that the real `FALSE_ALARM_STEP`/`MAX_FACTOR` can
    never clear her (`test_still_flagged_residents_keep_their_alert`), so this widens
    both just for this test to simulate "a threshold step big enough to un-flag".
    """
    monkeypatch.setattr(feedback_module, "FALSE_ALARM_STEP", 2.0)
    monkeypatch.setattr(feedback_module, "MAX_FACTOR", 5.0)

    with TestClient(app) as client:
        before = client.get("/alerts").json()
        alert_id = next(a["alert_id"] for a in before if a["resident_id"] == MRS_K)

        verdict = client.post(f"/alerts/{alert_id}/feedback", json={"verdict": "false_alarm"})
        assert verdict.status_code == 200

        after = [a["resident_id"] for a in client.get("/alerts").json()]
        assert MRS_K not in after, "sanity check: the false alarm must un-flag her"

        detail = client.get(f"/alerts/{alert_id}")
        assert detail.status_code == 200

        cause = client.post(
            f"/alerts/{alert_id}/feedback",
            json={"verdict": "false_alarm", "cause": "other"},
        )
        assert cause.status_code == 200
        assert cause.json()["feedback"]["cause"] == "other"


def test_status_for_flips_a_flagged_resident_once_the_tuned_threshold_clears_it():
    """Unit-level check of the helper `demo.status_for` exposes for this fix: the
    same flag rule `demo_residents` uses, just measured against a threshold a nurse's
    feedback has moved rather than the resident's own baseline."""
    early = [
        {
            "resident_id": "res-x",
            "ts": "2025-12-01T08:00:00+00:00",
            "task": "tea",
            "errors": {},
            "self_corrected": 0,
            "duration_s": 120.0,
            "assisted": False,
        }
        for _ in range(3)
    ]
    recent = [
        {
            "resident_id": "res-x",
            "ts": ts,
            "task": "tea",
            "errors": {},
            "self_corrected": 0,
            "duration_s": 120.0,
            "assisted": False,
        }
        for ts in ("2025-12-31T00:00:00+00:00", "2026-01-01T00:00:00+00:00")
    ]
    sessions = early + recent
    scores = [0.0, 0.0, 0.0, 2.5, 2.5]
    resident = {
        "id": "res-x",
        "sessions": sessions,
        "scores": [
            {"ts": s["ts"], "score": score}
            for s, score in zip(sessions, scores, strict=True)
        ],
        "baseline": {"mean": 0.0, "std": 1.0, "threshold": 2.0},
    }

    timestamped = [
        (datetime.fromisoformat(s["ts"]), score) for s, score in zip(sessions, scores, strict=True)
    ]
    assert flag_change(
        timestamped, Baseline(mean=0.0, std=1.0, threshold=2.0), DEMO_NOW
    ), "sanity check: raw threshold flags this resident"

    assert status_for(resident, threshold=2.0) == "flagged"
    assert status_for(resident, threshold=3.0) != "flagged"
