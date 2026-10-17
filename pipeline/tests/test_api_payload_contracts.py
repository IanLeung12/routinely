"""The dashboard's HTTP payloads, against their schemas in `contracts/`.

`GET /residents`, `GET /residents/{id}`, `GET /handoff` and the drift, pattern,
replay, alert and monitoring routes cross the pipeline/web boundary like any other
shared shape, and the dashboard mirrors them by hand
(`web/src/overview/types.ts`, `web/src/handoff/types.ts`,
`web/src/resident/api.ts`, `web/src/patterns/types.ts`,
`web/src/evidence/api.ts`, `web/src/alert/api.ts`,
`web/src/about/monitoringApi.ts`), which is how fields drift. So `contracts/`
carries a schema for each, generated from `routine_watch.contracts` like the rest,
and these tests hold the routes to them: every demo resident, a resident with a live
session in their history, every resident's drift, every pattern in the library, an
alert before and after a nurse answers it - including the body she posts, the one
payload travelling the other way - the replay window behind that alert's first error
in both layers, and a room paused, resumed and read back off its audit trail.

Fakes only - the template explainer writes the handoff's summary and the session is
a recording replayed through the pipeline, so nothing here makes a paid call.
"""

import json
from dataclasses import fields
from typing import Any

import pytest
from fastapi.testclient import TestClient
from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError as SchemaValidationError
from pydantic import ValidationError

from routine_watch import api as api_module
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
    NormalReplay,
    PatternLibraryEntry,
    PatternTimeProfile,
    Resident,
    ResidentDrift,
    ResidentSummary,
    RoomMonitoring,
    RoomMonitoringHistory,
    SessionReplay,
    repo_root,
    schema_name,
)
from routine_watch.demo import DEMO_RESIDENT, demo_residents
from routine_watch.drift import Drift
from routine_watch.feedback import FeedbackStore
from routine_watch.monitoring import DEFAULT_BY, get_monitoring_store
from routine_watch.patterns_library import LIBRARY as PATTERN_LIBRARY
from routine_watch.patterns_library import Pattern, TimeProfile

CONTRACTS_DIR = repo_root() / "contracts"

#: Every demo resident, so the detail route is checked against all of them and not
#: just the one the demo spends its time on.
RESIDENT_IDS = [resident["id"] for resident in demo_residents()]

#: The demo resident the live session and most of these payloads are about.
MRS_K = next(resident for resident in demo_residents() if resident["id"] == DEMO_RESIDENT)

#: mrs-k's room: the one a live session lands in (`routine_watch.live`).
MRS_K_ROOM = MRS_K["room"]

#: mrs-k's most recent seeded session, in the `resident-index` shape
#: `routine_watch.alerts.session_id_for` builds and the evidence view replays.
MRS_K_SESSION = f"{DEMO_RESIDENT}-{len(MRS_K['sessions']) - 1}"

#: The alert mrs-k's live session raises (`routine_watch.alerts`).
MRS_K_ALERT = f"alert-{DEMO_RESIDENT}"

#: A second of replay: enough frames to be a real answer, few enough to validate fast.
SHORT_WINDOW = {"t_start": 4.0, "t_end": 5.0}

#: What `GET /patterns` keeps to itself: the scoring machinery behind a library
#: entry, which `routine_watch.patterns` owns and no reader of the library is sent.
INTERNAL_PATTERN_FIELDS = {"requires", "context_weights", "max_confidence"}

#: One library entry as the route answers it, to mutate in the rejection cases below.
A_PATTERN_ENTRY: dict[str, Any] = {
    "pattern_id": "sudden_change",
    "name": "Sudden change",
    "signals": {"omissions_up": 3.0, "errors_up": 1.0},
    "time_profile": {
        "onset_days": [0.0, 3.0],
        "tolerance_days": 2.0,
        "note": "a step change within 1-3 days",
    },
    "checks": ["hydration", "Cognitive reassessment"],
    "urgency": "same_shift",
    "source": "SPEC section 7.5",
}


@pytest.fixture(autouse=True)
def _nothing_reviewed_and_every_room_on():
    """Both stores the API keeps are global, so each test starts from the seeded
    demo: nobody has answered an alert and no room is paused."""
    api_module._feedback_store = FeedbackStore()
    get_monitoring_store().reset()
    yield
    api_module._feedback_store = FeedbackStore()
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


@pytest.mark.parametrize("resident_id", RESIDENT_IDS)
def test_every_residents_drift_validates(client: TestClient, resident_id: str) -> None:
    """The drift card's own payload (SPEC section 8), for every resident the demo has:
    `web/src/resident/api.ts` reads it with a hand-written type."""
    payload = client.get(f"/residents/{resident_id}/drift").json()

    check(ResidentDrift, payload)
    assert payload["resident_id"] == resident_id


def test_a_rising_and_a_steady_trend_both_validate(client: TestClient) -> None:
    """`trending` is the card's whole judgement and the demo has residents on both
    sides of it (`routine_watch.demo`), so the schema is held to both answers."""
    answers = [client.get(f"/residents/{rid}/drift").json() for rid in RESIDENT_IDS]

    assert {answer["trending"] for answer in answers} == {True, False}


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


def test_every_pattern_in_the_library_validates(client: TestClient) -> None:
    """`GET /patterns` reads the library out as data (SPEC section 7.5), so every
    entry is held to the schema the pattern screen mirrors
    (`web/src/patterns/types.ts`), signals and time profile and citation included."""
    entries = client.get("/patterns").json()

    assert [entry["pattern_id"] for entry in entries] == [p.pattern_id for p in PATTERN_LIBRARY]
    for entry in entries:
        check(PatternLibraryEntry, entry)
        assert entry["signals"] and entry["checks"] and entry["source"].strip()


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


def test_the_replay_behind_an_alert_validates_in_both_layers(
    client: TestClient, mrs_k_flagged: None
) -> None:
    """What the evidence view really asks for (`web/src/evidence/api.ts`): the first
    error's own window, off the live session's own id, with the resident's normal
    routine over the same window beside it (SPEC section 10, step 5)."""
    error = client.get(f"/alerts/{MRS_K_ALERT}").json()["errors"][0]
    window = {"t_start": error["t_start"], "t_end": error["t_end"]}

    today = client.get(f"/sessions/{error['session_id']}/replay", params=window).json()
    normal = client.get(f"/residents/{DEMO_RESIDENT}/normal_replay", params=window).json()

    check(SessionReplay, today)
    check(NormalReplay, normal)
    assert today["frames"] and normal["frames"]
    assert {frame["session_id"] for frame in today["frames"]} == {error["session_id"]}


def test_a_seeded_sessions_replay_validates(client: TestClient) -> None:
    """A session nobody watched replays off the stand-in recording
    (`routine_watch.evidence`) and answers with the same payload, thinned to the
    frame rate the player asked for."""
    body = client.get(
        f"/sessions/{MRS_K_SESSION}/replay", params={**SHORT_WINDOW, "fps": 2.0}
    ).json()

    check(SessionReplay, body)
    assert body["session_id"] == MRS_K_SESSION
    assert body["frames"]


@pytest.mark.parametrize("resident_id", RESIDENT_IDS)
def test_every_residents_ghost_layer_validates(client: TestClient, resident_id: str) -> None:
    """The ghost layer is asked about the resident, not a session, and comes back
    under a normal session's own id (SPEC section 9, screen 4)."""
    body = client.get(f"/residents/{resident_id}/normal_replay", params=SHORT_WINDOW).json()

    check(NormalReplay, body)
    assert body["resident_id"] == resident_id
    assert {frame["session_id"] for frame in body["frames"]} == {f"{resident_id}-normal"}


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
        ResidentDrift: client.get(f"/residents/{DEMO_RESIDENT}/drift").json(),
        Handoff: client.get("/handoff").json(),
        PatternLibraryEntry: client.get("/patterns").json()[0],
        SessionReplay: client.get(
            f"/sessions/{MRS_K_SESSION}/replay", params=SHORT_WINDOW
        ).json(),
        NormalReplay: client.get(
            f"/residents/{DEMO_RESIDENT}/normal_replay", params=SHORT_WINDOW
        ).json(),
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
        pytest.param(
            ResidentDrift,
            {"resident_id": "mrs-k", "slope_per_day": 0.2, "days": -1, "trending": True},
            id="a-trend-over-less-than-no-days",
        ),
        pytest.param(
            PatternLibraryEntry,
            A_PATTERN_ENTRY | {"signals": {}},
            id="a-pattern-that-looks-for-nothing",
        ),
        pytest.param(
            PatternLibraryEntry,
            A_PATTERN_ENTRY
            | {
                "time_profile": {
                    "onset_days": [0.0, 3.0, 7.0],
                    "tolerance_days": 2.0,
                    "note": "a step change within 1-3 days",
                }
            },
            id="an-onset-window-with-three-ends",
        ),
        pytest.param(
            SessionReplay,
            {"session_id": "mrs-k-22"},
            id="a-replay-without-its-frames",
        ),
        pytest.param(
            NormalReplay,
            {"resident_id": "mrs-k", "frames": [{"t": 1.0}]},
            id="a-ghost-frame-that-is-not-a-capture-frame",
        ),
    ],
)
def test_the_schema_rejects(model: type, payload: dict[str, Any]) -> None:
    with pytest.raises(SchemaValidationError):
        validator(model).validate(payload)

    with pytest.raises(ValidationError):
        model.model_validate(payload)


def test_the_overview_row_is_the_detail_cut_down() -> None:
    """`/residents` serves exactly `api._SUMMARY_FIELDS` of a resident, so the two
    schemas have to agree on which fields those are."""
    assert set(ResidentSummary.model_fields) == set(api_module._SUMMARY_FIELDS)
    assert set(ResidentSummary.model_fields) <= set(Resident.model_fields)


def test_the_drift_card_is_the_drift_the_pipeline_computes() -> None:
    """`/residents/{id}/drift` answers `drift.Drift` plus the resident it was asked
    about (`api_residents.resident_drift`), so a field added on either side alone
    fails here."""
    assert set(ResidentDrift.model_fields) == {f.name for f in fields(Drift)} | {"resident_id"}


def test_the_library_entry_is_the_pattern_without_the_scoring_machinery() -> None:
    """`/patterns` serves the library as data, not how it is weighed
    (`api_residents._pattern_payload`). A new field on `patterns_library.Pattern` has
    to be either served or named here deliberately, never quietly dropped."""
    served = {f.name for f in fields(Pattern)} - INTERNAL_PATTERN_FIELDS

    assert served == set(PatternLibraryEntry.model_fields)
    assert set(PatternTimeProfile.model_fields) == {f.name for f in fields(TimeProfile)}


def test_the_two_replay_windows_differ_only_in_what_was_asked_for() -> None:
    """One player reads both routes (`web/src/evidence/api.ts`): the session's window
    and the resident's normal one carry the same frames under a different key."""
    assert set(SessionReplay.model_fields) - {"session_id"} == {"frames"}
    assert set(NormalReplay.model_fields) - {"resident_id"} == {"frames"}


def test_the_error_counts_cover_every_error_type() -> None:
    """A seventh error type (SPEC section 7) has to reach a session's counts too."""
    assert set(ErrorCounts.model_fields) == {error.value for error in ErrorType}


def test_the_contracts_readme_lists_the_payloads() -> None:
    readme = (CONTRACTS_DIR / "README.md").read_text(encoding="utf-8")

    for model in (*PAYLOADS, *REQUESTS):
        assert f"{schema_name(model)}.schema.json" in readme
