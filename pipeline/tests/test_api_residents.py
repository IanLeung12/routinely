import pytest
from fastapi.testclient import TestClient

from routine_watch import api as api_module
from routine_watch.api import app
from routine_watch.contracts import AlertFeedback, FeedbackVerdict
from routine_watch.demo import DEMO_NOW, demo_residents
from routine_watch.feedback import FeedbackStore

MRS_K = "mrs-k"

#: The pattern mrs-k's change scores highest on with nobody's answers in play.
RAW_TOP_PATTERN = "sudden_change"

#: The runner-up on the same change: what her ranking reorders to once her nurses
#: have dismissed `RAW_TOP_PATTERN` twice and confirmed this twice.
ANSWERED_TOP_PATTERN = "evening_worsening"


def test_demo_residents_is_deterministic() -> None:
    assert demo_residents() == demo_residents()


def test_demo_residents_has_a_spike_a_drift_and_normals() -> None:
    statuses = {resident["id"]: resident["status"] for resident in demo_residents()}
    # Her seeded history leaves her on watch; a live session is what flags her
    # (SPEC section 10 beats 2-4, T124).
    assert statuses[MRS_K] == "watch"
    assert sum(1 for status in statuses.values() if status == "normal") >= 1
    assert len(statuses) >= 3


def test_list_residents_returns_summary_fields() -> None:
    with TestClient(app) as client:
        response = client.get("/residents")

    assert response.status_code == 200
    body = response.json()
    assert len(body) == len(demo_residents())
    for resident in body:
        assert set(resident) == {"id", "name", "room", "status", "top_pattern", "scores"}
        assert resident["scores"]
        for point in resident["scores"]:
            assert set(point) == {"ts", "score"}

    by_id = {resident["id"]: resident for resident in body}
    assert by_id[MRS_K]["status"] == "watch"
    assert by_id[MRS_K]["name"] == "Mrs. K"


def test_flagged_and_watch_residents_show_their_top_pattern() -> None:
    """SPEC §9 screen 1 and demo step 6: each flagged or watch row names the pattern
    the change is consistent with; normal residents show nothing (no clear pattern)."""
    by_id = {resident["id"]: resident for resident in demo_residents()}

    sudden = by_id[MRS_K]["top_pattern"]
    assert sudden is not None
    assert sudden["pattern_id"] == "sudden_change"
    assert set(sudden) == {"pattern_id", "name", "urgency"}

    drift_resident = next(r for r in by_id.values() if r["status"] == "watch" and r["id"] != MRS_K)
    assert drift_resident["top_pattern"]["pattern_id"] == "slow_drift"

    normal_residents = [r for r in by_id.values() if r["status"] == "normal"]
    assert normal_residents
    assert all(r["top_pattern"] is None for r in normal_residents)


def test_mrs_k_flagged_still_shows_sudden_change(mrs_k_flagged) -> None:
    """A live session that flags Mrs. K keeps her top pattern, not just her watch
    status (SPEC section 10 beats 2-5)."""
    by_id = {resident["id"]: resident for resident in demo_residents()}
    assert by_id[MRS_K]["status"] == "flagged"
    assert by_id[MRS_K]["top_pattern"]["pattern_id"] == "sudden_change"


def test_get_resident_returns_detail() -> None:
    with TestClient(app) as client:
        response = client.get(f"/residents/{MRS_K}")

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == MRS_K
    assert body["status"] == "watch"
    assert body["sessions"]
    assert body["care_records"]
    assert set(body["baseline"]) == {
        "mean",
        "std",
        "threshold",
        "usual_duration_s",
        "usual_errors",
    }


def test_get_resident_404s_for_unknown_id() -> None:
    with TestClient(app) as client:
        response = client.get("/residents/does-not-exist")

    assert response.status_code == 404


def test_resident_scoped_routes_404_for_unknown_id() -> None:
    """``_resident_or_404`` backs every resident-scoped route the same way."""
    with TestClient(app) as client:
        responses = [
            client.get("/residents/does-not-exist"),
            client.get("/residents/does-not-exist/drift"),
            client.get(
                "/residents/does-not-exist/normal_replay",
                params={"t_start": 0.0, "t_end": 1.0},
            ),
        ]

    for response in responses:
        assert response.status_code == 404
        assert response.json() == {"detail": "resident not found"}


def test_no_resident_is_flagged_by_default() -> None:
    """A live session is what flags mrs-k (SPEC section 10 beats 2-4, T124)."""
    statuses = [resident["status"] for resident in demo_residents()]
    assert statuses.count("flagged") == 0


# ------------------------------- one pattern: the overview chip and the alert agree


@pytest.fixture
def feedback_store():
    """A clean feedback store for the API module, which keeps one global (SPEC MVP 7)."""
    api_module._feedback_store = FeedbackStore()
    yield api_module._feedback_store
    api_module._feedback_store = FeedbackStore()


def _answer(
    store: FeedbackStore,
    alert_id: str,
    verdict: FeedbackVerdict,
    cause: str | None = None,
    top_pattern: str | None = None,
) -> None:
    """One earlier alert of mrs-k's, answered: a verdict and what the nurse said it was.

    The demo gives her one live alert, so her earlier answers are logged straight into
    the store under their own alert ids, the way a week of them would have piled up
    (same as `tests/test_api_feedback.py`).
    """
    store.record(
        alert_id,
        MRS_K,
        AlertFeedback(verdict=verdict, by="nurse", at=DEMO_NOW),
        cause=cause,
        top_pattern=top_pattern,
    )


def _alert_id_for(client: TestClient, resident_id: str) -> str:
    alerts = {alert["resident_id"]: alert["alert_id"] for alert in client.get("/alerts").json()}
    return alerts[resident_id]


def test_top_pattern_names_the_pattern_her_alert_leads_with(mrs_k_flagged, feedback_store) -> None:
    """SPEC §9 screen 1: with nobody's answers in play the overview chip and the alert
    are already one ranking - the field `demo.py` writes and `alerts.py`'s."""
    with TestClient(app) as client:
        row = {r["id"]: r for r in client.get("/residents").json()}[MRS_K]
        alert = client.get(f"/alerts/{_alert_id_for(client, MRS_K)}").json()

    assert row["top_pattern"]["pattern_id"] == alert["patterns"][0]["pattern_id"]
    assert row["top_pattern"]["pattern_id"] == RAW_TOP_PATTERN


def test_top_pattern_follows_her_nurses_answers_about_what_it_was(
    mrs_k_flagged, feedback_store
) -> None:
    """T183: once her answers reorder the ranking (SPEC Nice to have 8), `/residents`
    and `/residents/{id}` name the pattern her alert leads with rather than the
    unweighted one, so the chip and the alert are about the same change."""
    with TestClient(app) as client:
        alert_id = _alert_id_for(client, MRS_K)
        # Two earlier alerts led with the raw top pattern and turned out to be nothing,
        # one was this other pattern...
        for i in range(2):
            _answer(
                feedback_store,
                f"past-{i}",
                FeedbackVerdict.FALSE_ALARM,
                top_pattern=RAW_TOP_PATTERN,
            )
        _answer(feedback_store, "past-cause", FeedbackVerdict.CONFIRMED, cause=ANSWERED_TOP_PATTERN)
        # ...and so is this one, answered through the route a nurse's tap goes through.
        posted = client.post(
            f"/alerts/{alert_id}/feedback",
            json={"verdict": "confirmed", "cause": ANSWERED_TOP_PATTERN},
        )

        row = {r["id"]: r for r in client.get("/residents").json()}[MRS_K]
        detail = client.get(f"/residents/{MRS_K}").json()
        alert = client.get(f"/alerts/{alert_id}").json()

    assert posted.status_code == 200
    # Her answers really did reorder it: the raw ranking leads with RAW_TOP_PATTERN.
    assert alert["patterns"][0]["pattern_id"] == ANSWERED_TOP_PATTERN
    assert row["status"] == "flagged"
    assert row["top_pattern"]["pattern_id"] == alert["patterns"][0]["pattern_id"]
    assert set(row["top_pattern"]) == {"pattern_id", "name", "urgency"}
    assert detail["top_pattern"] == row["top_pattern"]


def test_answers_about_one_resident_leave_the_rest_of_the_unit_alone(
    mrs_k_flagged, feedback_store
) -> None:
    """Pattern weights are per resident (`feedback.pattern_weights`): nobody else's
    chip moves because mrs-k's nurse answered about her."""
    with TestClient(app) as client:
        before = {r["id"]: r["top_pattern"] for r in client.get("/residents").json()}
        _answer(feedback_store, "past-0", FeedbackVerdict.CONFIRMED, cause=ANSWERED_TOP_PATTERN)
        after = {r["id"]: r["top_pattern"] for r in client.get("/residents").json()}

    assert before.pop(MRS_K)["pattern_id"] == RAW_TOP_PATTERN
    assert after.pop(MRS_K) is not None
    assert after == before
