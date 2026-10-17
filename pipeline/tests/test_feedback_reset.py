"""T304: `/demo/reset` empties the feedback record, so a second demo run starts clean.

`/demo/reset` (T144) is what puts the demo back between rehearsals, and `GET
/residents/{id}/feedback` (T283) is what shows a nurse the answers her unit gave
and the pattern ranking they moved. If a reset left those behind, the demo's
second run would open on the first run's answers: her alert already marked
"confirmed" by whoever rehearsed, and her patterns weighted two runs deep. So
these tests play that loop - answer, reset, play mrs-k's session again - and check
the second run sees nothing of the first.

`tests/test_feedback_history.py` covers the route itself and
`tests/test_api_demo_reset.py` the rest of what a reset forgets; this file is about
what the feedback record looks like across one. Fakes only: the session is a
recorded scenario and every answer goes into the in-memory store, so nothing here
makes a paid call.
"""

from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient

from routine_watch import api_state
from routine_watch.api import app
from routine_watch.contracts import AlertFeedback, FeedbackVerdict
from routine_watch.demo import DEMO_RESIDENT, demo_residents

#: A live session always lands against the demo resident (`routine_watch.live`), so
#: hers is the one alert a nurse can answer on stage (SPEC section 10 beats 2-4).
MRS_K = DEMO_RESIDENT
MRS_K_ALERT = f"alert-{MRS_K}"

#: The demo's bad session: skip the teabag, pour twice (SPEC section 10 beat 4).
MRS_K_LIVE_SCENARIO = "tea_skip_teabag_pour_twice"

#: Fast enough that a recorded session plays out inside a test.
_FAST = 1000.0

#: The pattern her change leads with, so the one her alert's answers weigh
#: (`tests/test_api_residents.py`).
HER_TOP_PATTERN = "sudden_change"

#: Another resident with answers of her own, to show a reset is not per-resident.
OTHER_RESIDENT = "mr-chen"
OTHER_RESIDENTS_PATTERN = "slow_drift"

#: Answers are logged at a time of our choosing, never the wall clock.
_LOGGED_AT = datetime(2026, 10, 16, 9, 0, tzinfo=UTC)


@pytest.fixture(autouse=True)
def _demo_stack(monkeypatch: pytest.MonkeyPatch):
    """A demo/dev stack with a clean feedback store: `/demo/reset` answers for nothing
    else (`api._demo_reset_enabled`), and `api_state` keeps the store global."""
    monkeypatch.setenv("DEMO_RESET", "1")
    api_state.reset()
    yield
    api_state.reset()


@pytest.fixture
def client(mrs_k_flagged: None) -> TestClient:
    """A client part-way through the demo's first run: mrs-k's live session has been
    played, so her alert - the only thing feedback can be posted against - exists."""
    with TestClient(app) as test_client:
        yield test_client


def _feedback(client: TestClient, resident_id: str = MRS_K) -> dict:
    """One resident's feedback record, the way her detail card fetches it."""
    response = client.get(f"/residents/{resident_id}/feedback")
    assert response.status_code == 200
    return response.json()


def _answer(client: TestClient, verdict: str = "confirmed", **body) -> None:
    """One nurse's one-tap answer on mrs-k's alert, through the route she taps."""
    response = client.post(f"/alerts/{MRS_K_ALERT}/feedback", json={"verdict": verdict, **body})
    assert response.status_code == 200


def _log(
    alert_id: str,
    resident_id: str = MRS_K,
    verdict: FeedbackVerdict = FeedbackVerdict.CONFIRMED,
    **kwargs,
) -> None:
    """An earlier day's answer, logged straight into the store: one run leaves one
    alert per resident, so a second answer - or another resident's - has to come from
    the store rather than from the route."""
    api_state._feedback_store.record(
        alert_id,
        resident_id,
        AlertFeedback(verdict=verdict, by="nurse", at=_LOGGED_AT),
        **kwargs,
    )


def _reset(client: TestClient) -> None:
    assert client.post("/demo/reset").status_code == 200


def _play_the_session(client: TestClient) -> None:
    """The demo's next run: play her bad session over `/ws/live`, as the stage does.

    A reset drops the session log with the feedback, so her alert only exists again
    once this has run (T144).
    """
    url = f"/ws/live?scenario={MRS_K_LIVE_SCENARIO}&speed={_FAST}"
    with client.websocket_connect(url) as websocket:
        message = websocket.receive_json()
        while message["type"] != "session_end":
            message = websocket.receive_json()
    assert message["alert_id"] == MRS_K_ALERT, "the second run has to flag her again"


def _seeded_threshold(resident_id: str) -> float:
    """A resident's own flag threshold, before any feedback tunes it. Built from her
    seeded history alone, so a replayed session never moves it."""
    return next(
        resident["baseline"]["threshold"]
        for resident in demo_residents()
        if resident["id"] == resident_id
    )


def _tuned_threshold(client: TestClient) -> float:
    """The threshold her alert is served with: her baseline as her feedback tunes it."""
    response = client.get(f"/alerts/{MRS_K_ALERT}")
    assert response.status_code == 200
    return response.json()["baseline"]["threshold"]


def test_the_answers_from_the_first_run_are_gone_after_a_reset(client: TestClient):
    """What a nurse answered, and the ranking it moved, both empty again."""
    _answer(client, cause=HER_TOP_PATTERN)
    before = _feedback(client)
    assert [row["alert_id"] for row in before["answers"]] == [MRS_K_ALERT]
    assert before["pattern_weights"] == {HER_TOP_PATTERN: 1.1}

    _reset(client)

    after = _feedback(client)
    assert after["answers"] == []
    assert after["pattern_weights"] == {}
    assert after["pattern_names"] == {}


def test_the_second_runs_answer_weighs_its_pattern_from_scratch(client: TestClient):
    """A weight is counted from the answers still logged, so a reset has to drop the
    count and not just the rows: one answer in the second run is worth one answer of
    weight, not the two runs' worth that would rank her patterns by last rehearsal."""
    _answer(client, cause=HER_TOP_PATTERN)
    _log("alert-mrs-k-yesterday", cause=HER_TOP_PATTERN)
    assert _feedback(client)["pattern_weights"] == {HER_TOP_PATTERN: 1.2}

    _reset(client)
    _play_the_session(client)
    _answer(client, cause=HER_TOP_PATTERN)

    body = _feedback(client)
    assert [row["alert_id"] for row in body["answers"]] == [MRS_K_ALERT]
    assert body["pattern_weights"] == {HER_TOP_PATTERN: 1.1}


def test_the_second_runs_alert_carries_no_verdict_from_the_first(client: TestClient):
    """The same thing where the nurse meets it: a fresh alert nobody has answered,
    rather than one that opens already marked by the last run."""
    _answer(client, cause=HER_TOP_PATTERN)
    assert client.get(f"/alerts/{MRS_K_ALERT}").json()["feedback"] is not None

    _reset(client)
    _play_the_session(client)

    assert client.get(f"/alerts/{MRS_K_ALERT}").json()["feedback"] is None


def test_a_reset_empties_every_residents_record_not_only_the_one_asked_for(client: TestClient):
    """The reset is the whole unit's, so no resident keeps a record the demo's first
    run gave her."""
    _answer(client, cause=HER_TOP_PATTERN)
    _log("alert-mr-chen-yesterday", OTHER_RESIDENT, cause=OTHER_RESIDENTS_PATTERN)
    assert _feedback(client, OTHER_RESIDENT)["pattern_weights"] == {OTHER_RESIDENTS_PATTERN: 1.1}

    _reset(client)

    for resident_id in (MRS_K, OTHER_RESIDENT):
        body = _feedback(client, resident_id)
        assert body["answers"] == []
        assert body["pattern_weights"] == {}


def test_a_reset_puts_her_tuned_threshold_back_to_the_seeded_one(client: TestClient):
    """The other half of what an answer tunes (SPEC MVP 7): the bar her sessions are
    judged against. Left behind, the second run would score her against a threshold
    the first run's false alarms raised, and the same session would flag differently."""
    base = _seeded_threshold(MRS_K)
    for alert_id in ("alert-mrs-k-monday", "alert-mrs-k-tuesday"):
        _log(alert_id, verdict=FeedbackVerdict.FALSE_ALARM)
    assert _tuned_threshold(client) > base

    _reset(client)
    _play_the_session(client)

    assert _tuned_threshold(client) == pytest.approx(base)
