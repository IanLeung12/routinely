"""The dashboard's HTTP payloads, against their schemas in `contracts/`.

`GET /residents`, `GET /residents/{id}`, `GET /handoff` and the alert and monitoring
routes cross the pipeline/web boundary like any other shared shape, and the
dashboard mirrors them by hand (`web/src/overview/types.ts`,
`web/src/handoff/types.ts`, `web/src/alert/api.ts`,
`web/src/about/monitoringApi.ts`), which is how fields drift. So `contracts/`
carries a schema for each, generated from `routine_watch.contracts` like the rest,
and these tests hold the routes to them: every demo resident, a resident with a live
session in their history, a handoff with a room paused, an alert before and after a
nurse answers it - including the body she posts, the one payload travelling the
other way - and a room paused, resumed and read back off its audit trail.

Fakes only - the template explainer writes the handoff's summary and the session is
a recording replayed through the pipeline, so nothing here makes a paid call.
"""

import json
from typing import Any

import pytest
from fastapi.testclient import TestClient
from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError as SchemaValidationError
from pydantic import ValidationError

from routine_watch import api_state
from routine_watch.api import app
from routine_watch.api_alerts import AlertFeedbackIn
from routine_watch.contracts import (
    PAYLOADS,
    REQUESTS,
    AlertDetail,
    ErrorCounts,
    ErrorType,
    Feedback,
    Handoff,
    Monitoring,
    Resident,
    ResidentSummary,
    RoomMonitoring,
    RoomMonitoringHistory,
    repo_root,
    schema_name,
)
from routine_watch.demo import DEMO_RESIDENT, demo_residents
from routine_watch.monitoring import DEFAULT_BY, get_monitoring_store

CONTRACTS_DIR = repo_root() / "contracts"

#: Every demo resident, so the detail route is checked against all of them and not
#: just the one the demo spends its time on.
RESIDENT_IDS = [resident["id"] for resident in demo_residents()]

#: mrs-k's room: the one a live session lands in (`routine_watch.live`).
MRS_K_ROOM = next(r["room"] for r in demo_residents() if r["id"] == DEMO_RESIDENT)

#: The alert mrs-k's live session raises (`routine_watch.alerts`).
MRS_K_ALERT = f"alert-{DEMO_RESIDENT}"


@pytest.fixture(autouse=True)
def _nothing_reviewed_and_every_room_on():
    """Both stores the API keeps are global, so each test starts from the seeded
    demo: nobody has answered an alert and no room is paused."""
    api_state.reset()
    get_monitoring_store().reset()
    yield
    api_state.reset()
    get_monitoring_store().reset()


@pytest.fixture
def client():
    with TestClient(app) as client:
        yield client


def validator(model: type) -> Draft202012Validator:
    """The on-disk schema for one payload, checked against the metaschema first."""
    path = CONTRACTS_DIR / f"{schema_name(model)}.schema.json"
    schema = json.loads(path.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema)


def check(model: type, payload: dict[str, Any]) -> None:
    """Hold one payload to both copies of the shape: the schema the dashboard reads
    and the model it is generated from."""
    validator(model).validate(payload)
    model.model_validate(payload)


def test_every_overview_row_validates(client: TestClient) -> None:
    rows = client.get("/residents").json()

    assert len(rows) == len(RESIDENT_IDS)
    for row in rows:
        check(ResidentSummary, row)


@pytest.mark.parametrize("resident_id", RESIDENT_IDS)
def test_every_resident_detail_validates(client: TestClient, resident_id: str) -> None:
    detail = client.get(f"/residents/{resident_id}").json()

    check(Resident, detail)
    assert detail["sessions"] and detail["care_records"]


def test_a_live_session_is_the_same_shape(client: TestClient, mrs_k_flagged: None) -> None:
    """A session played this run joins the resident's history (SPEC section 10, step
    4) carrying two fields a generated one has not got, so the detail has to stay
    inside the schema with it there."""
    detail = client.get(f"/residents/{DEMO_RESIDENT}").json()

    check(Resident, detail)
    live = [session for session in detail["sessions"] if "session_id" in session]
    assert len(live) == 1
    assert live[0]["error_events"]


def test_the_handoff_validates(client: TestClient) -> None:
    handoff = client.get("/handoff").json()

    check(Handoff, handoff)
    assert handoff["paused"] == []
    assert len(handoff["residents"]) == len(RESIDENT_IDS)


def test_the_handoff_validates_with_a_room_paused(client: TestClient) -> None:
    """The fields T251 added: `paused` and the row's `monitoring_paused` (SPEC §12)."""
    client.put(f"/rooms/{MRS_K_ROOM}/monitoring", json={"on": False})

    handoff = client.get("/handoff").json()

    check(Handoff, handoff)
    assert [room["room"] for room in handoff["paused"]] == [MRS_K_ROOM]
    paused = {row["resident_id"] for row in handoff["residents"] if row["monitoring_paused"]}
    assert paused == {DEMO_RESIDENT}


def test_the_monitoring_state_validates(client: TestClient) -> None:
    """`GET /monitoring` is the state behind every pause switch (SPEC §12): the room
    names and nothing else, empty until a nurse pauses something."""
    check(Monitoring, client.get("/monitoring").json())
    assert client.get("/monitoring").json()["paused_rooms"] == []

    client.put(f"/rooms/{MRS_K_ROOM}/monitoring", json={"on": False})

    state = client.get("/monitoring").json()
    check(Monitoring, state)
    assert state["paused_rooms"] == [MRS_K_ROOM]


@pytest.mark.parametrize("on", [False, True])
def test_the_switch_answers_with_the_rooms_state(client: TestClient, on: bool) -> None:
    """The PUT echoes the room back, so the dashboard draws what the server believes
    rather than what it just sent."""
    answered = client.put(f"/rooms/{MRS_K_ROOM}/monitoring", json={"on": on})

    assert answered.status_code == 200
    check(RoomMonitoring, answered.json())
    assert answered.json() == {"room": MRS_K_ROOM, "on": on}


def test_the_rooms_audit_trail_validates(client: TestClient) -> None:
    """T262's trail under the switch (SPEC §12): a pause and a resume, newest first,
    each saying who made it and when."""
    client.put(f"/rooms/{MRS_K_ROOM}/monitoring", json={"on": False})
    client.put(f"/rooms/{MRS_K_ROOM}/monitoring", json={"on": True, "by": "Ward B"})

    trail = client.get(f"/rooms/{MRS_K_ROOM}/monitoring/history").json()

    check(RoomMonitoringHistory, trail)
    assert trail["room"] == MRS_K_ROOM
    assert [change["on"] for change in trail["history"]] == [True, False]
    assert [change["by"] for change in trail["history"]] == ["Ward B", DEFAULT_BY]


def test_an_untouched_rooms_trail_validates_empty(client: TestClient) -> None:
    """Nothing logged is a real answer, not a missing key."""
    trail = client.get(f"/rooms/{MRS_K_ROOM}/monitoring/history").json()

    check(RoomMonitoringHistory, trail)
    assert trail == {"room": MRS_K_ROOM, "history": []}


def test_every_alert_in_the_list_validates(client: TestClient, mrs_k_flagged: None) -> None:
    alerts = client.get("/alerts").json()

    assert [alert["resident_id"] for alert in alerts] == [DEMO_RESIDENT]
    for alert in alerts:
        check(AlertDetail, alert)


def test_the_alert_detail_validates(client: TestClient, mrs_k_flagged: None) -> None:
    detail = client.get(f"/alerts/{MRS_K_ALERT}").json()

    check(AlertDetail, detail)
    assert detail["errors"] and detail["patterns"]
    assert detail["feedback"] is None


def test_the_alert_still_validates_once_a_nurse_has_answered(
    client: TestClient, mrs_k_flagged: None
) -> None:
    """The POST answers with the alert again, now carrying the verdict and the
    threshold that feedback has tuned (SPEC section 5, MVP 7 and 8), so the body the
    dashboard sent and the two payloads it gets back are all held to their schemas."""
    detail = client.get(f"/alerts/{MRS_K_ALERT}").json()
    body = {"verdict": "confirmed", "cause": detail["patterns"][0]["pattern_id"]}
    check(Feedback, body)

    answered = client.post(f"/alerts/{MRS_K_ALERT}/feedback", json=body)

    assert answered.status_code == 200
    check(AlertDetail, answered.json())
    check(AlertDetail, client.get(f"/alerts/{MRS_K_ALERT}").json())
    assert answered.json()["feedback"]["verdict"] == "confirmed"
    assert answered.json()["feedback"]["cause"] == body["cause"]


@pytest.mark.parametrize(
    "body",
    [
        pytest.param({"verdict": "confirmed"}, id="a-verdict-on-its-own"),
        pytest.param({"verdict": "false_alarm", "cause": "other"}, id="a-cause-off-the-library"),
        pytest.param({"verdict": "confirmed", "note": None, "cause": None}, id="nulls-spelled-out"),
        pytest.param({"verdict": "false_alarm", "note": "She had a visitor."}, id="a-note"),
    ],
)
def test_the_route_takes_every_feedback_body_the_schema_allows(
    client: TestClient, mrs_k_flagged: None, body: dict[str, Any]
) -> None:
    check(Feedback, body)

    assert client.post(f"/alerts/{MRS_K_ALERT}/feedback", json=body).status_code == 200


@pytest.mark.parametrize(
    "body",
    [
        pytest.param({}, id="no-verdict"),
        pytest.param({"verdict": "maybe"}, id="a-verdict-nobody-can-count"),
        pytest.param({"verdict": "confirmed", "cause": ""}, id="an-empty-cause"),
        pytest.param(
            {"verdict": "confirmed", "frame_jpeg": "iVBORw0KGgo="}, id="a-smuggled-frame"
        ),
    ],
)
def test_the_route_refuses_every_feedback_body_the_schema_rejects(
    client: TestClient, mrs_k_flagged: None, body: dict[str, Any]
) -> None:
    with pytest.raises(SchemaValidationError):
        validator(Feedback).validate(body)

    assert client.post(f"/alerts/{MRS_K_ALERT}/feedback", json=body).status_code == 422


def test_the_route_validates_the_feedback_contract_itself() -> None:
    """FastAPI checks the body with `api_alerts.AlertFeedbackIn`, which is the shared
    contract plus the pattern-library check on `cause`, not a second copy of it: a
    field can only be added to the body by adding it to `Feedback`."""
    assert issubclass(AlertFeedbackIn, Feedback)
    assert set(AlertFeedbackIn.model_fields) == set(Feedback.model_fields)


def test_a_payload_cannot_smuggle_a_frame_past_the_schema(client: TestClient) -> None:
    """No route may grow a field for a raw frame (SPEC section 8)."""
    switched = client.put(f"/rooms/{MRS_K_ROOM}/monitoring", json={"on": False})
    payloads = {
        ResidentSummary: client.get("/residents").json()[0],
        Resident: client.get(f"/residents/{DEMO_RESIDENT}").json(),
        Handoff: client.get("/handoff").json(),
        Monitoring: client.get("/monitoring").json(),
        RoomMonitoring: switched.json(),
        RoomMonitoringHistory: client.get(f"/rooms/{MRS_K_ROOM}/monitoring/history").json(),
    }

    for model, payload in payloads.items():
        check(model, payload)
        with pytest.raises(SchemaValidationError):
            validator(model).validate(payload | {"frame_jpeg": "iVBORw0KGgo="})
        with pytest.raises(ValidationError):
            model.model_validate(payload | {"frame_jpeg": "iVBORw0KGgo="})


@pytest.mark.parametrize(
    ("model", "payload"),
    [
        pytest.param(
            ResidentSummary,
            {
                "id": "mrs-k",
                "name": "Mrs. K",
                "room": "204",
                "status": "needs_review",
                "top_pattern": None,
                "scores": [],
            },
            id="a-status-chip-the-overview-cannot-draw",
        ),
        pytest.param(
            Handoff,
            {
                "window_hours": 12,
                "residents": [
                    {
                        "resident_id": "mrs-k",
                        "name": "Mrs. K",
                        "flags": 0,
                        "pending_review": 0,
                        "trending": False,
                    }
                ],
                "paused": [],
                "summary": "Nothing to review.",
            },
            id="a-row-without-monitoring-paused",
        ),
        pytest.param(
            Monitoring,
            {"paused_rooms": [""]},
            id="a-paused-room-with-no-name",
        ),
        pytest.param(
            RoomMonitoringHistory,
            {"room": "204", "history": [{"on": False, "at": "2026-10-17T09:00:00Z"}]},
            id="a-logged-change-with-nobody-to-answer-for-it",
        ),
    ],
)
def test_the_schema_rejects(model: type, payload: dict[str, Any]) -> None:
    with pytest.raises(SchemaValidationError):
        validator(model).validate(payload)

    with pytest.raises(ValidationError):
        model.model_validate(payload)


def test_the_overview_row_is_the_detail_cut_down() -> None:
    """`/residents` serves exactly `api_state._SUMMARY_FIELDS` of a resident, so the
    two schemas have to agree on which fields those are."""
    assert set(ResidentSummary.model_fields) == set(api_state._SUMMARY_FIELDS)
    assert set(ResidentSummary.model_fields) <= set(Resident.model_fields)


def test_the_error_counts_cover_every_error_type() -> None:
    """A seventh error type (SPEC section 7) has to reach a session's counts too."""
    assert set(ErrorCounts.model_fields) == {error.value for error in ErrorType}


def test_the_contracts_readme_lists_the_payloads() -> None:
    readme = (CONTRACTS_DIR / "README.md").read_text(encoding="utf-8")

    for model in (*PAYLOADS, *REQUESTS):
        assert f"{schema_name(model)}.schema.json" in readme
