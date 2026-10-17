"""Resident detail shows the same feedback-tuned threshold as the alert (T414).

`api_state._tuned` already recomputed `status`/`top_pattern` against the
feedback-tuned threshold for `/residents` and `/residents/{id}`, but returned
`baseline.threshold` unchanged, so a nurse confirming an alert lowered the
threshold `/alerts` showed while the resident's own baseline chart kept
showing the old, raw one (SPEC MVP 7: the threshold visibly changes).
"""

import pytest
from fastapi.testclient import TestClient

from routine_watch import api_state
from routine_watch.api import app

MRS_K = "mrs-k"


@pytest.fixture(autouse=True)
def _clean_feedback_store():
    """Each test gets a clean feedback store: `api_state` keeps it global."""
    api_state.reset()
    yield
    api_state.reset()


def test_resident_detail_threshold_matches_the_alert_after_confirming_feedback(
    mrs_k_flagged,
):
    with TestClient(app) as client:
        before = client.get(f"/residents/{MRS_K}").json()
        raw_threshold = before["baseline"]["threshold"]

        alert_id = next(
            alert["alert_id"]
            for alert in client.get("/alerts").json()
            if alert["resident_id"] == MRS_K
        )

        feedback = client.post(f"/alerts/{alert_id}/feedback", json={"verdict": "confirmed"})
        assert feedback.status_code == 200
        alert_threshold = feedback.json()["baseline"]["threshold"]
        assert alert_threshold != raw_threshold, "sanity check: feedback must tune the threshold"

        after = client.get(f"/residents/{MRS_K}").json()

    assert after["baseline"]["threshold"] == alert_threshold


def test_resident_detail_threshold_is_unchanged_with_no_feedback(mrs_k_flagged):
    with TestClient(app) as client:
        detail = client.get(f"/residents/{MRS_K}").json()
        residents_list = {r["id"]: r for r in client.get("/residents").json()}

    raw_threshold = next(
        r for r in api_state.demo_residents() if r["id"] == MRS_K
    )["baseline"]["threshold"]

    assert detail["baseline"]["threshold"] == raw_threshold
    assert "baseline" not in residents_list[MRS_K]
