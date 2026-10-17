"""contracts/ is the one place shared schemas live (AGENTS.md).

The pydantic models in `routine_watch.contracts` are the source. The JSON Schemas, the
sample `capture.jsonl` and `web/src/contracts.ts` are generated from them, so these
tests check four things: every type round-trips through JSON into its own schema, the
sample frames validate, nothing on disk has drifted away from the models, and what the
dashboard still writes by hand against a schema - its `Alert` type, the feedback body
its client posts, the two bodies its monitoring client casts inline - names the same
fields. The payloads it used to copy by hand (the drift card's, a pattern library
entry's, both replay windows', the overview row, the shift handoff and the monitoring
audit trail's logged change) are generated into `web/src/contracts.ts` instead, so a
changed field breaks its build; what is left to test here is that they are in the
generated file and that nothing keeps a second copy of them.
"""

import json
import re
from datetime import UTC, datetime
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError as SchemaValidationError
from pydantic import ValidationError

from routine_watch.capture import FRAME_SCHEMA_VERSION
from routine_watch.contracts import (
    CONTRACTS,
    HAND_LANDMARK_COUNT,
    POSE_LANDMARK_COUNT,
    SCHEMAS,
    WEB_PAYLOADS,
    Alert,
    AlertDetail,
    AlertFeedback,
    AlertKind,
    BaselineComparison,
    BaselineMetric,
    BoundingBox,
    CaptureFrame,
    ErrorType,
    EvidenceKind,
    EvidenceRef,
    Feedback,
    Handedness,
    HandLandmarks,
    Monitoring,
    MonitoringChange,
    ObjectDetection,
    ObjectLabel,
    PatternTimeProfile,
    Pose,
    RoomMonitoringHistory,
    Session,
    StepEvent,
    StepSource,
    SuggestedCheck,
    TaskError,
    example_capture_frames,
    schema_name,
    stale_files,
)

REPO = Path(__file__).resolve().parents[2]
CONTRACTS_DIR = REPO / "contracts"

#: The dashboard's copy of the shapes, generated from the same models.
WEB_CONTRACTS = REPO / "web" / "src" / "contracts.ts"

#: The dashboard's feedback client, which writes the POST body out by hand.
WEB_ALERT_API = REPO / "web" / "src" / "alert" / "api.ts"

#: The dashboard's monitoring client, which casts the bodies of the pause switch's
#: routes by hand (SPEC section 12).
WEB_MONITORING_API = REPO / "web" / "src" / "about" / "monitoringApi.ts"

#: Every source file the dashboard is written in: where a second copy of a generated
#: payload would turn up if somebody wrote one.
WEB_SOURCES = [
    path
    for path in sorted((REPO / "web" / "src").rglob("*"))
    if path.suffix in {".ts", ".tsx"}
]

#: The one field of the audit trail its client has no use for: it asked about the
#: room, so the answer naming it again tells the screen nothing new.
TRAIL_ROOM = {"room"}

#: What the server stamps on a stored verdict, so a nurse's POST never sends it.
SERVER_STAMPED = {"by", "at"}

#: What a map's values may be where a schema cannot list its fields: a closed enum
#: (the live protocol's `step_state`, keyed by step id) or a number (a pattern
#: entry's signal weights). Neither leaves anywhere for an image to go; a string
#: would.
MAP_VALUE_TYPES = {"number", "integer", "boolean"}

#: Nothing in a contract may name an image, a frame or a clip (SPEC section 8).
BANNED_FIELD_WORDS = (
    "image",
    "frame",
    "video",
    "clip",
    "pixel",
    "jpeg",
    "jpg",
    "png",
    "base64",
    "thumbnail",
)


def _object_detection() -> ObjectDetection:
    return ObjectDetection(
        label=ObjectLabel.KETTLE,
        confidence=0.93,
        box=BoundingBox(x1=0.56, y1=0.28, x2=0.74, y2=0.61),
        track_id="kettle-1",
    )


def _step_event() -> StepEvent:
    return StepEvent(
        event_id="evt-1",
        session_id="demo-session-1",
        step_id="teabag_in_cup",
        objects=[ObjectLabel.TEABAG, ObjectLabel.CUP],
        t_start=12.0,
        t_end=14.5,
        confidence=0.82,
        source=StepSource.RULE,
    )


def _task_error() -> TaskError:
    return TaskError(
        error_id="err-1",
        session_id="demo-session-1",
        type=ErrorType.OMISSION,
        step_id="fill_kettle",
        t_start=12.0,
        t_end=61.0,
        evidence=[
            EvidenceRef(kind=EvidenceKind.SKELETON_REPLAY, t_start=10.0, t_end=20.0),
            EvidenceRef(kind=EvidenceKind.STEP_EVENT, t_start=12.0, t_end=14.5, event_id="evt-1"),
        ],
    )


def _session() -> Session:
    return Session(
        session_id="demo-session-1",
        resident_id="resident-a",
        task_id="make_tea",
        started_at=datetime(2026, 10, 17, 9, 0, tzinfo=UTC),
        ended_at=datetime(2026, 10, 17, 9, 4, tzinfo=UTC),
        score=3.5,
    )


def _alert() -> Alert:
    return Alert(
        alert_id="alert-1",
        resident_id="resident-a",
        created_at=datetime(2026, 10, 17, 9, 5, tzinfo=UTC),
        kind=AlertKind.CHANGE_FLAG,
        session_ids=["demo-session-1", "demo-session-2"],
        errors=[_task_error()],
        baseline=BaselineComparison(
            task_id="make_tea",
            metric=BaselineMetric.ERRORS_PER_DAY,
            observed=3.0,
            baseline_mean=0.2,
            baseline_sd=0.4,
            baseline_days=14,
            threshold=1.5,
        ),
        summary="Three errors making tea this morning, against 0.2 a day for this resident.",
        suggested_checks=[SuggestedCheck.INFECTION_OR_UTI, SuggestedCheck.HYDRATION],
    )


#: One filled-in example per top-level contract.
SAMPLES = {
    CaptureFrame: example_capture_frames()[1],
    ObjectDetection: _object_detection(),
    StepEvent: _step_event(),
    TaskError: _task_error(),
    Session: _session(),
    Alert: _alert(),
}

CASES = [pytest.param(model, sample, id=model.__name__) for model, sample in SAMPLES.items()]


def validator(model: type) -> Draft202012Validator:
    """The on-disk schema for one contract, checked against the JSON Schema metaschema."""
    schema = json.loads((CONTRACTS_DIR / f"{schema_name(model)}.schema.json").read_text())
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema)


def walk_objects(node: object) -> list[dict]:
    """Every object subschema inside a schema, however deeply nested."""
    found = []
    if isinstance(node, dict):
        if node.get("type") == "object":
            found.append(node)
        for child in node.values():
            found += walk_objects(child)
    elif isinstance(node, list):
        for child in node:
            found += walk_objects(child)
    return found


def closed_to_images(extra: object) -> bool:
    """Whether one object's `additionalProperties` leaves nowhere for an image.

    Every contract forbids unknown fields outright. A map is the exception - its
    fields cannot be listed - and then its values have to be a closed enum or a
    number, which still leaves nowhere for an image to go.
    """
    if extra is False:
        return True
    return isinstance(extra, dict) and ("enum" in extra or extra.get("type") in MAP_VALUE_TYPES)


def carries_a_contract(node: dict) -> bool:
    """Whether a property is nothing but a reference to another contract, or a list of
    them, so this loop checks it where that contract is defined.

    That is how the live protocol's envelope holds a `frame` (one CaptureFrame, which
    is skeletons, boxes and timestamps) and a replay payload holds `frames` (a list
    of the same) without either having a field of its own to hide an image in.
    """
    if set(node) == {"$ref"}:
        return True
    items = node.get("items")
    return node.get("type") == "array" and isinstance(items, dict) and set(items) == {"$ref"}


def test_contracts_dir_is_documented() -> None:
    assert (CONTRACTS_DIR / "README.md").read_text().strip()


def test_every_contract_has_a_schema_file() -> None:
    wanted = {f"{schema_name(model)}.schema.json" for model in SCHEMAS}
    assert {path.name for path in CONTRACTS_DIR.glob("*.schema.json")} == wanted


def test_samples_cover_every_contract() -> None:
    assert set(SAMPLES) == set(CONTRACTS)


@pytest.mark.parametrize(("model", "sample"), CASES)
def test_round_trips_through_json_into_its_schema(model: type, sample: object) -> None:
    payload = json.loads(json.dumps(sample.model_dump(mode="json")))

    validator(model).validate(payload)

    assert model.model_validate(payload) == sample


@pytest.mark.parametrize(("model", "sample"), CASES)
def test_schema_rejects_a_smuggled_frame(model: type, sample: object) -> None:
    payload = sample.model_dump(mode="json") | {"frame_jpeg": "iVBORw0KGgo="}

    with pytest.raises(SchemaValidationError):
        validator(model).validate(payload)

    with pytest.raises(ValidationError):
        model.model_validate(payload)


def test_no_schema_can_carry_a_raw_frame() -> None:
    for path in sorted(CONTRACTS_DIR.glob("*.schema.json")):
        for node in walk_objects(json.loads(path.read_text())):
            assert closed_to_images(node["additionalProperties"]), path.name
            for field, sub in node.get("properties", {}).items():
                if carries_a_contract(sub):
                    continue
                banned = [word for word in BANNED_FIELD_WORDS if word in field]
                assert not banned, f"{path.name}: {field} looks like raw video"


def test_example_capture_jsonl_validates() -> None:
    check = validator(CaptureFrame)
    lines = (CONTRACTS_DIR / "examples" / "capture.jsonl").read_text().splitlines()

    assert len(lines) > 1
    for number, line in enumerate(lines):
        payload = json.loads(line)
        check.validate(payload)
        frame = CaptureFrame.model_validate(payload)
        assert frame.schema_version == FRAME_SCHEMA_VERSION
        assert frame.seq == number
        assert len(frame.poses[0].landmarks) == POSE_LANDMARK_COUNT


def test_generated_files_are_up_to_date() -> None:
    stale = [str(path.relative_to(REPO)) for path in stale_files(REPO)]

    assert not stale, "run `uv run python -m routine_watch.contracts` in pipeline/"


def test_error_types_match_the_errors_stage() -> None:
    from routine_watch.errors import ERROR_TYPES

    assert [error.value for error in ErrorType] == list(ERROR_TYPES)


def test_landmark_counts_are_fixed() -> None:
    hand = HandLandmarks(
        handedness=Handedness.LEFT,
        score=0.9,
        landmarks=example_capture_frames()[1].hands[0].landmarks,
    )
    assert len(hand.landmarks) == HAND_LANDMARK_COUNT

    with pytest.raises(ValidationError):
        Pose(landmarks=hand.landmarks)


def test_times_and_boxes_must_make_sense() -> None:
    with pytest.raises(ValidationError):
        BoundingBox(x1=0.6, y1=0.1, x2=0.2, y2=0.4)

    with pytest.raises(ValidationError):
        StepEvent.model_validate(_step_event().model_dump() | {"t_end": 1.0})

    with pytest.raises(ValidationError):
        ObjectDetection.model_validate(_object_detection().model_dump() | {"confidence": 1.4})


def test_an_alert_needs_at_least_one_session() -> None:
    with pytest.raises(ValidationError):
        Alert.model_validate(_alert().model_dump() | {"session_ids": []})


def ts_fields(type_name: str, path: Path = WEB_CONTRACTS) -> set[str]:
    """The field names of one TypeScript object type, generated or hand-written."""
    source = path.read_text(encoding="utf-8")
    block = re.search(rf"^export type {type_name} = \{{$(.*?)^\}}$", source, re.S | re.M)
    assert block, f"{path.name} has no type {type_name}"
    return set(re.findall(r"^  (\w+)\??:", block.group(1), re.M))


def ts_read_fields(function: str, path: Path = WEB_MONITORING_API) -> set[str]:
    """The fields one client function reads a response body through.

    The monitoring client casts the bodies of the pause switch's routes inline
    (`as { paused_rooms: string[] }`) instead of naming a type, which is still a
    hand-written copy of a payload and still drifts.
    """
    source = path.read_text(encoding="utf-8")
    body = re.search(rf"^(?:export )?async function {function}\b.*?^\}}$", source, re.S | re.M)
    assert body, f"{path.name} has no function {function}"
    cast = re.search(r"\bas \{([^}]*)\}", body.group(0))
    assert cast, f"{function} no longer casts the body it reads"
    return set(re.findall(r"(\w+)\??:", cast.group(1)))


def test_the_alert_detail_is_the_record_with_nothing_left_out() -> None:
    """`GET /alerts/{id}` and every row of `GET /alerts` dump the whole alert
    (`api_alerts._alert_payload`), so the detail is the stored record's fields with
    the two it lets default always sent: an empty list and a null, never a gap."""
    assert set(AlertDetail.model_fields) == set(Alert.model_fields)
    assert all(field.is_required() for field in AlertDetail.model_fields.values())
    optional = {name for name, f in Alert.model_fields.items() if not f.is_required()}
    assert optional == {"patterns", "feedback"}


def test_the_detail_schema_fails_an_alert_that_left_its_feedback_out() -> None:
    """The record's schema takes it; the route's does not. That difference is the
    whole reason `alert_detail.schema.json` exists beside `alert.schema.json`."""
    payload = _alert().model_dump(mode="json")
    del payload["feedback"]

    validator(Alert).validate(payload)
    with pytest.raises(SchemaValidationError):
        validator(AlertDetail).validate(payload)


def test_the_feedback_body_is_the_stored_verdict_minus_who_and_when() -> None:
    """A nurse posts `Feedback`; the alert comes back carrying `AlertFeedback`, which
    is the same answer plus the two fields the server stamps on it."""
    assert set(AlertFeedback.model_fields) == set(Feedback.model_fields) | SERVER_STAMPED


def test_the_dashboards_alert_type_names_every_detail_field() -> None:
    assert ts_fields("Alert") == set(AlertDetail.model_fields)


def test_the_dashboards_feedback_type_names_every_posted_field() -> None:
    assert ts_fields("AlertFeedback") == set(Feedback.model_fields) | SERVER_STAMPED


def test_the_dashboard_posts_exactly_the_feedback_body() -> None:
    """`postFeedback` writes the POST body out by hand (`web/src/alert/api.ts`), the
    one copy of a contract that is not generated, so a field added on either side
    alone fails here."""
    source = WEB_ALERT_API.read_text(encoding="utf-8")
    body = re.search(r"body: JSON\.stringify\(\{(.*?)\}\)", source, re.S)
    assert body, "web/src/alert/api.ts no longer posts a JSON.stringify body"

    posted = set(re.findall(r"(?:^|,)\s*(\w+)", body.group(1)))
    assert posted == set(Feedback.model_fields)


def test_the_dashboard_reads_exactly_the_monitoring_state() -> None:
    """`fetchPausedRooms` casts `GET /monitoring`'s body by hand (SPEC section 12),
    so a field added to the state on either side alone fails here."""
    assert ts_read_fields("fetchPausedRooms") == set(Monitoring.model_fields)


def test_the_dashboard_reads_the_whole_audit_trail() -> None:
    """`fetchMonitoringHistory` leaves out only the `room` it asked about: anything
    else the route grows has to reach the screen, and anything the screen reads has
    to be something the route sends."""
    assert ts_read_fields("fetchMonitoringHistory") | TRAIL_ROOM == set(
        RoomMonitoringHistory.model_fields
    )


def test_the_dashboards_payload_types_are_generated_not_copied() -> None:
    """The drift card's payload, a pattern library entry, both replay windows, the
    overview row, the shift handoff and the monitoring audit trail's logged change
    were written out by hand in dashboard modules (`web/src/resident/api.ts`,
    `web/src/patterns/types.ts`, `web/src/evidence/api.ts`, `web/src/overview/types.ts`,
    `web/src/handoff/types.ts`, `web/src/about/monitoringApi.ts`) and held to the
    models by a field-name test over their source. They are in `WEB_PAYLOADS` now, so
    the dashboard imports them and a changed field fails its build instead. What is
    left to check here is that the generated file really carries them - a model
    dropped from `WEB_PAYLOADS` would regenerate clean - and that nobody has started
    a second copy, time profile included."""
    for model in WEB_PAYLOADS:
        assert ts_fields(model.__name__) == set(model.model_fields)

    copied = {model.__name__ for model in WEB_PAYLOADS} | {PatternTimeProfile.__name__}
    for path in WEB_SOURCES:
        if path == WEB_CONTRACTS:
            continue
        source = path.read_text(encoding="utf-8")
        for name in sorted(copied):
            assert f"type {name} = {{" not in source, f"{path.relative_to(REPO)}: {name}"


def test_a_logged_change_is_what_the_monitoring_store_writes() -> None:
    """The route serves the store's own trail (`routine_watch.monitoring`), so what
    the store appends has to validate as the contract - including the `by` and `at`
    that make a paused camera accountable rather than silent (SPEC section 12)."""
    from routine_watch.monitoring import MonitoringStore

    store = MonitoringStore()
    store.set("204", False)
    store.set("204", True, by="Ward B")

    trail = store.history("204")

    validator(RoomMonitoringHistory).validate({"room": "204", "history": trail})
    assert [set(change) for change in trail] == [set(MonitoringChange.model_fields)] * 2
