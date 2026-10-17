"""T339: `GET /residents`'s `scores` is a contract the dashboard's sort depends on.

`web/src/overview/ResidentSort.tsx` (T318) assumes each resident's `scores` list is
already oldest-first with ISO `ts` strings, so it can pick the last entry as the most
recent change without sorting client-side. Nothing on the API side pinned that down,
so a future backend change (a new source of sessions, a re-ordering join) could break
the sort silently. This test plays both the seeded-only path and a completed live
session and checks `scores` stays ascending by `ts` either way.
"""

from datetime import datetime

import pytest
from fastapi.testclient import TestClient

from routine_watch.api import app
from routine_watch.demo import DEMO_RESIDENT, demo_residents

MRS_K = DEMO_RESIDENT

#: The demo's bad session: skip the teabag, pour twice (SPEC section 10 beat 4).
MRS_K_LIVE_SCENARIO = "tea_skip_teabag_pour_twice"

#: Fast enough that a recorded session plays out inside a test.
_FAST = 1000.0


@pytest.fixture(autouse=True)
def _demo_stack(monkeypatch: pytest.MonkeyPatch):
    """`/demo/reset` only answers with `DEMO_RESET` set (SPEC §10, §13)."""
    monkeypatch.setenv("DEMO_RESET", "1")


@pytest.fixture
def client() -> TestClient:
    with TestClient(app) as test_client:
        yield test_client


def _reset(client: TestClient) -> None:
    assert client.post("/demo/reset").status_code == 200


def _play_the_session(client: TestClient) -> None:
    """Play mrs-k's live session over `/ws/live`, the way the stage does, through to
    the end, so her `scores` gain a session newer than anything seeded."""
    url = f"/ws/live?scenario={MRS_K_LIVE_SCENARIO}&speed={_FAST}"
    with client.websocket_connect(url) as websocket:
        message = websocket.receive_json()
        while message["type"] != "session_end":
            message = websocket.receive_json()


def _residents(client: TestClient) -> list[dict]:
    response = client.get("/residents")
    assert response.status_code == 200
    return response.json()


def test_after_a_demo_reset_every_residents_scores_are_oldest_first_iso(
    client: TestClient,
) -> None:
    _reset(client)

    body = _residents(client)
    assert len(body) == len(demo_residents())

    for resident in body:
        timestamps = [point["ts"] for point in resident["scores"]]
        assert timestamps, f"{resident['id']} has no scores to order"

        parsed = [datetime.fromisoformat(ts) for ts in timestamps]
        assert parsed == sorted(parsed), f"{resident['id']}'s scores are not oldest-first"


def test_after_a_live_session_that_residents_newest_score_is_last(
    client: TestClient,
) -> None:
    _reset(client)
    before = next(r for r in _residents(client) if r["id"] == MRS_K)
    before_count = len(before["scores"])

    _play_the_session(client)

    after = next(r for r in _residents(client) if r["id"] == MRS_K)
    assert len(after["scores"]) == before_count + 1

    timestamps = [point["ts"] for point in after["scores"]]
    parsed = [datetime.fromisoformat(ts) for ts in timestamps]
    assert parsed == sorted(parsed), "mrs-k's scores are not oldest-first after a live session"
    assert parsed[-1] == max(parsed), "the live session's score should be the newest"
