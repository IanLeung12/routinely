"""What nurses said, read back: `GET /residents/{id}/feedback` (T283).

The feedback loop (SPEC Nice to have 8) re-weights a resident's patterns from her
own nurses' answers, and until now it did it silently: the only way to see it was
to notice a later alert ranked differently. This route serves the record behind
it - every answer newest first, the weights they add up to, and the name each
pattern id is shown under - so the resident detail can show the learning.

Fakes only: the answers here are posted through the API or logged straight into
the in-memory store, so nothing makes a paid call.
"""

from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from routine_watch import api_state
from routine_watch.api import app
from routine_watch.contracts import AlertFeedback, FeedbackVerdict
from routine_watch.feedback import FeedbackStore
from routine_watch.patterns_library import BY_ID as PATTERNS_BY_ID

MRS_K = "mrs-k"
MRS_K_ALERT = f"alert-{MRS_K}"

#: The pattern mrs-k's change leads with, so what a false alarm on her alert is a
#: false alarm *on* (`tests/test_api_residents.py`).
HER_TOP_PATTERN = "sudden_change"

#: A different library pattern, for the answer "it was this other thing instead".
OTHER_PATTERN = "evening_worsening"

#: A cause the pattern library has no pattern for (`api_alerts.OTHER_CAUSE`).
OTHER_CAUSE = "other"


@pytest.fixture(autouse=True)
def _clean_feedback_store():
    """Each test gets a clean feedback store: `api_state` keeps it global."""
    api_state.reset()
    yield
    api_state.reset()


@pytest.fixture
def client(mrs_k_flagged: None) -> TestClient:
    """A client whose mrs-k has the live session that flags her, so her alert - the
    only thing feedback can be posted against - exists (SPEC section 10 beats 2-4)."""
    with TestClient(app) as test_client:
        yield test_client


def _log(alert_id: str, verdict: FeedbackVerdict, at: datetime, **kwargs) -> None:
    """One answer logged straight into the store, at a timestamp of our choosing."""
    api_state._feedback_store.record(
        alert_id,
        MRS_K,
        AlertFeedback(verdict=verdict, by="nurse", at=at),
        **kwargs,
    )


def _feedback(client: TestClient, resident_id: str = MRS_K) -> dict:
    response = client.get(f"/residents/{resident_id}/feedback")
    assert response.status_code == 200
    return response.json()


def test_a_resident_nobody_has_answered_about_has_nothing_to_show(client: TestClient):
    body = _feedback(client)

    assert body == {
        "resident_id": MRS_K,
        "answers": [],
        "pattern_weights": {},
        "pattern_names": {},
    }


def test_an_answer_posted_on_her_alert_comes_back_as_her_history(client: TestClient):
    posted = client.post(
        f"/alerts/{MRS_K_ALERT}/feedback",
        json={"verdict": "confirmed", "cause": OTHER_PATTERN},
    )
    assert posted.status_code == 200

    body = _feedback(client)

    assert len(body["answers"]) == 1
    answer = body["answers"][0]
    assert answer["alert_id"] == MRS_K_ALERT
    assert answer["verdict"] == "confirmed"
    assert answer["cause"] == OTHER_PATTERN
    assert datetime.fromisoformat(answer["at"]).tzinfo is not None
    # The same answer, read as the ranking it moved.
    assert body["pattern_weights"] == {OTHER_PATTERN: 1.1}
    assert body["pattern_names"][OTHER_PATTERN] == PATTERNS_BY_ID[OTHER_PATTERN].name


def test_the_answer_a_nurse_just_posted_sits_above_her_older_ones(client: TestClient):
    """Newest first, through the route a nurse's one-tap answer really takes."""
    client.post(f"/alerts/{MRS_K_ALERT}/feedback", json={"verdict": "confirmed"})
    just_posted = datetime.fromisoformat(_feedback(client)["answers"][0]["at"])

    _log("alert-last-week", FeedbackVerdict.FALSE_ALARM, just_posted - timedelta(days=7))
    _log("alert-yesterday", FeedbackVerdict.CONFIRMED, just_posted - timedelta(days=1))

    answers = _feedback(client)["answers"]

    assert [answer["alert_id"] for answer in answers] == [
        MRS_K_ALERT,
        "alert-yesterday",
        "alert-last-week",
    ]


def test_re_answering_one_alert_replaces_its_row_rather_than_adding_one(client: TestClient):
    client.post(f"/alerts/{MRS_K_ALERT}/feedback", json={"verdict": "confirmed"})
    client.post(f"/alerts/{MRS_K_ALERT}/feedback", json={"verdict": "false_alarm"})

    answers = _feedback(client)["answers"]

    assert len(answers) == 1
    assert answers[0]["verdict"] == "false_alarm"


def test_a_false_alarm_names_the_pattern_it_ranked_lower(client: TestClient):
    """A dismissed alert is evidence against the pattern it led with, so the card has
    a name to show for the weight that moved."""
    client.post(f"/alerts/{MRS_K_ALERT}/feedback", json={"verdict": "false_alarm"})

    body = _feedback(client)

    assert body["answers"][0]["cause"] is None
    assert body["pattern_weights"] == {HER_TOP_PATTERN: 0.9}
    assert body["pattern_names"] == {HER_TOP_PATTERN: PATTERNS_BY_ID[HER_TOP_PATTERN].name}


def test_other_is_an_answer_with_no_pattern_to_name(client: TestClient):
    """"What was it?" can be answered with something the library has no pattern for:
    the answer is still logged, it just weighs nothing and names nothing."""
    client.post(
        f"/alerts/{MRS_K_ALERT}/feedback",
        json={"verdict": "confirmed", "cause": OTHER_CAUSE},
    )

    body = _feedback(client)

    assert body["answers"][0]["cause"] == OTHER_CAUSE
    assert body["pattern_weights"] == {}
    assert body["pattern_names"] == {}


def test_one_residents_answers_stay_out_of_anothers_history(client: TestClient):
    client.post(f"/alerts/{MRS_K_ALERT}/feedback", json={"verdict": "confirmed"})

    assert _feedback(client, "mr-chen")["answers"] == []
    assert len(_feedback(client)["answers"]) == 1


def test_demo_reset_empties_what_nurses_said(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setenv("DEMO_RESET", "1")
    client.post(
        f"/alerts/{MRS_K_ALERT}/feedback",
        json={"verdict": "confirmed", "cause": OTHER_PATTERN},
    )
    assert _feedback(client)["answers"]

    assert client.post("/demo/reset").status_code == 200

    body = _feedback(client)
    assert body["answers"] == []
    assert body["pattern_weights"] == {}
    assert body["pattern_names"] == {}


def test_an_unknown_resident_is_a_404(client: TestClient):
    response = client.get("/residents/nobody/feedback")

    assert response.status_code == 404
    assert response.json()["detail"] == "resident not found"


def test_the_store_orders_answers_made_at_the_same_moment_by_when_they_arrived():
    """Two answers logged with one timestamp still have an order: the last one in is
    the one a nurse just gave, so it goes on top."""
    store = FeedbackStore()
    at = datetime(2026, 1, 1, 13, 40, tzinfo=UTC)
    for alert_id in ("alert-first", "alert-second"):
        store.record(
            alert_id, MRS_K, AlertFeedback(verdict=FeedbackVerdict.CONFIRMED, by="n", at=at)
        )

    assert [row["alert_id"] for row in store.history(MRS_K)] == ["alert-second", "alert-first"]


def test_the_store_sorts_a_hand_built_naive_timestamp_as_utc():
    """`AlertFeedback.at` is aware everywhere the API writes it, but a caller can build
    a naive one; sorting the two kinds against each other must order them, not raise."""
    store = FeedbackStore()
    store.record(
        "alert-naive",
        MRS_K,
        AlertFeedback(verdict=FeedbackVerdict.CONFIRMED, by="n", at=datetime(2026, 1, 2, 9, 0)),
    )
    store.record(
        "alert-aware",
        MRS_K,
        AlertFeedback(
            verdict=FeedbackVerdict.CONFIRMED, by="n", at=datetime(2026, 1, 1, 9, 0, tzinfo=UTC)
        ),
    )

    assert [row["alert_id"] for row in store.history(MRS_K)] == ["alert-naive", "alert-aware"]
