"""contracts/ is the one place shared schemas live (AGENTS.md).

The pydantic models in `routine_watch.contracts` are the source. The JSON Schemas, the
sample `capture.jsonl` and `web/src/contracts.ts` are generated from them, so these
tests check three things: every type round-trips through JSON into its own schema, the
sample frames validate, and nothing on disk has drifted away from the models.
"""

import json
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
    Alert,
    AlertKind,
    BaselineComparison,
    BaselineMetric,
    BoundingBox,
    CaptureFrame,
    ErrorType,
    EvidenceKind,
    EvidenceRef,
    Handedness,
    HandLandmarks,
    ObjectDetection,
    ObjectLabel,
    Pose,
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


def test_contracts_dir_is_documented() -> None:
    assert (CONTRACTS_DIR / "README.md").read_text().strip()


def test_every_contract_has_a_schema_file() -> None:
    wanted = {f"{schema_name(model)}.schema.json" for model in CONTRACTS}
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
            assert node["additionalProperties"] is False, path.name
            for field in node.get("properties", {}):
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
