"""Capture is the privacy boundary, so these tests are mostly about what it writes.

Nothing here needs a camera, mediapipe or opencv: the landmarks are plain objects
shaped like MediaPipe's, the detector is the fake one, and the frames are stand-ins.
That is the point - the heavy dependencies live in the ``capture`` extra, and CI must
be able to check the record format, the write loop and the CLI without them.
"""

import gc
import json
import re
import subprocess
import sys
import weakref
from dataclasses import dataclass
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator
from pydantic import ValidationError

from routine_watch.capture import (
    COORD_DIGITS,
    DEFAULT_FPS,
    DEFAULT_POSE_MODEL,
    POSE_MODEL_ENV,
    CaptureError,
    FakeLandmarker,
    Hand,
    Landmarks,
    MediaPipeLandmarker,
    default_session_id,
    frame_record,
    handedness_of,
    model_path,
    record_stream,
)
from routine_watch.contracts import (
    HAND_LANDMARK_COUNT,
    POSE_LANDMARK_COUNT,
    BoundingBox,
    CaptureFrame,
    CaptureSource,
    Handedness,
    ObjectDetection,
    ObjectLabel,
)
from routine_watch.detector import (
    DetectorError,
    FakeDetector,
    Letterbox,
    LocalDetector,
    build_detector,
    decode_rows,
    iou,
    label_for,
    letterbox,
    non_max_suppression,
    normalised_box,
    parse_names,
)

REPO = Path(__file__).resolve().parents[2]

#: Nothing a capture record holds may name, or be, an image (SPEC section 8).
BANNED_FIELD = re.compile(r"image|frame|video|clip|pixel|jpeg|jpg|png|base64|bytes", re.IGNORECASE)
BASE64_RUN = re.compile(r"[A-Za-z0-9+/=]{200,}")


@dataclass(frozen=True)
class FakeLandmark:
    """One landmark, shaped like `mediapipe.tasks` `NormalizedLandmark`."""

    x: float
    y: float
    z: float
    visibility: float | None = None


class FakeImage:
    """A stand-in for a decoded frame: weak-referenceable, and nothing else."""

    shape = (480, 640, 3)


def fake_landmarks(count: int, *, offset: float = 0.0, visibility: float | None = 0.9):
    return [
        FakeLandmark(
            x=0.1 + 0.01 * index + offset,
            y=0.2 + 0.02 * index + offset,
            z=-0.05 + 0.001 * index,
            visibility=visibility,
        )
        for index in range(count)
    ]


def fake_pose(**kwargs):
    return fake_landmarks(POSE_LANDMARK_COUNT, **kwargs)


def fake_hand(handedness: str = "Left", score: float = 0.88) -> Hand:
    # MediaPipe reports visibility 0.0 on every hand landmark; it means nothing.
    return Hand(
        handedness=handedness,
        score=score,
        landmarks=fake_landmarks(HAND_LANDMARK_COUNT, offset=0.3, visibility=0.0),
    )


def fake_detection(label: ObjectLabel = ObjectLabel.KETTLE) -> ObjectDetection:
    return ObjectDetection(
        label=label, confidence=0.9, box=BoundingBox(x1=0.1, y1=0.2, x2=0.3, y2=0.4)
    )


@pytest.fixture(scope="module")
def frame_schema() -> Draft202012Validator:
    schema = json.loads((REPO / "contracts/capture_frame.schema.json").read_text("utf-8"))
    return Draft202012Validator(schema)


def banned_fields(node, location=""):
    """Every field name in a record that names an image, however deeply nested."""
    offenders = []
    if isinstance(node, dict):
        for key, value in node.items():
            where = f"{location}/{key}"
            if BANNED_FIELD.search(str(key)):
                offenders.append(where)
            offenders.extend(banned_fields(value, where))
    elif isinstance(node, list):
        for index, value in enumerate(node):
            offenders.extend(banned_fields(value, f"{location}/{index}"))
    return offenders


# ------------------------------------------------------------------- frame_record


def test_frame_record_validates_against_the_contract_schema(frame_schema):
    record = frame_record(
        1.5,
        [fake_pose()],
        [fake_hand("Left"), fake_hand("Right", 0.74)],
        [fake_detection()],
        "camera",
        session_id="tea-1",
        seq=22,
    )

    frame_schema.validate(record.model_dump(mode="json"))
    assert record.session_id == "tea-1"
    assert record.seq == 22
    assert record.t == 1.5
    assert record.source is CaptureSource.CAMERA
    assert record.schema_version >= 1


def test_frame_record_keeps_the_landmarks_it_was_given():
    record = frame_record(
        0.0, [fake_pose()], [fake_hand()], [], "video", session_id="tea-1", seq=0
    )

    assert len(record.poses) == 1
    assert len(record.poses[0].landmarks) == POSE_LANDMARK_COUNT
    assert len(record.hands) == 1
    assert len(record.hands[0].landmarks) == HAND_LANDMARK_COUNT
    first = record.poses[0].landmarks[0]
    assert (first.x, first.y, first.z) == (0.1, 0.2, -0.05)


def test_frame_record_keeps_pose_visibility_and_drops_the_hands_version():
    record = frame_record(
        0.0, [fake_pose()], [fake_hand()], [], "video", session_id="tea-1", seq=0
    )

    assert record.poses[0].landmarks[0].visibility == 0.9
    # MediaPipe says 0.0 for every hand landmark, which is not a measurement.
    assert all(point.visibility is None for point in record.hands[0].landmarks)


def test_frame_record_rounds_landmarks_to_keep_a_session_small():
    long_values = [FakeLandmark(x=0.123456789, y=0.98765432, z=-0.555555, visibility=0.4444444)]
    record = frame_record(
        1.0 / 3,
        [long_values * POSE_LANDMARK_COUNT],
        [],
        [],
        "video",
        session_id="tea-1",
        seq=0,
    )

    point = record.poses[0].landmarks[0]
    assert (point.x, point.y, point.z) == (0.1235, 0.9877, -0.5556)
    assert point.visibility == 0.4444
    assert record.t == round(1.0 / 3, COORD_DIGITS)


def test_frame_record_normalises_mediapipes_handedness():
    record = frame_record(
        0.0,
        [],
        [fake_hand("Left"), fake_hand("RIGHT"), fake_hand(Handedness.LEFT)],
        [],
        "video",
        session_id="tea-1",
        seq=0,
    )

    assert [hand.handedness for hand in record.hands] == [
        Handedness.LEFT,
        Handedness.RIGHT,
        Handedness.LEFT,
    ]


def test_handedness_of_rejects_anything_else():
    with pytest.raises(ValueError, match="neither hand"):
        handedness_of("middle")


def test_frame_record_clamps_scores_into_the_contracts_range():
    record = frame_record(
        0.0,
        [fake_pose(visibility=1.4), fake_pose(visibility=-0.2)],
        [fake_hand(score=1.2)],
        [],
        "video",
        session_id="tea-1",
        seq=0,
        pose_scores=[1.9, None],
    )

    assert record.poses[0].score == 1.0
    assert record.poses[1].score is None
    assert record.poses[0].landmarks[0].visibility == 1.0
    assert record.poses[1].landmarks[0].visibility == 0.0
    assert record.hands[0].score == 1.0


def test_frame_record_records_everybody_in_frame():
    """Two poses is how a session is known to be assisted (SPEC section 7)."""
    record = frame_record(
        2.0, [fake_pose(), fake_pose(offset=0.2)], [], [], "camera", session_id="tea-1", seq=1
    )

    assert len(record.poses) == 2


def test_frame_record_rejects_a_half_detected_skeleton():
    with pytest.raises(ValidationError):
        frame_record(
            0.0,
            [fake_landmarks(POSE_LANDMARK_COUNT - 1)],
            [],
            [],
            "video",
            session_id="tea-1",
            seq=0,
        )


def test_frame_record_rejects_a_negative_timestamp():
    with pytest.raises(ValidationError):
        frame_record(-0.5, [], [], [], "video", session_id="tea-1", seq=0)


def test_a_capture_record_has_no_field_that_could_hold_an_image(frame_schema):
    record = frame_record(
        0.0, [fake_pose()], [fake_hand()], [fake_detection()], "camera", session_id="tea-1", seq=0
    )

    assert banned_fields(record.model_dump(mode="json")) == []
    with pytest.raises(ValidationError):
        CaptureFrame.model_validate({**record.model_dump(mode="json"), "image": "AAAA"})


# ------------------------------------------------------------------ record_stream


def fake_images(count: int, *, refs: list | None = None, fps: int = DEFAULT_FPS):
    """`(t, image)` pairs the way a camera or a video file hands them over."""
    for index in range(count):
        image = FakeImage()
        if refs is not None:
            refs.append(weakref.ref(image))
        yield index / fps, image


def test_record_stream_writes_one_jsonl_record_per_frame(tmp_path):
    out = tmp_path / "nested" / "session.jsonl"

    result = record_stream(
        fake_images(4),
        out,
        landmarker=FakeLandmarker(Landmarks(poses=(fake_pose(),), hands=(fake_hand(),))),
        detector=FakeDetector([fake_detection()]),
        source="video",
        session_id="tea-1",
    )

    lines = out.read_text("utf-8").splitlines()
    records = [CaptureFrame.model_validate_json(line) for line in lines]
    assert [record.seq for record in records] == [0, 1, 2, 3]
    assert [record.t for record in records] == [0.0, 0.0667, 0.1333, 0.2]
    assert all(record.session_id == "tea-1" for record in records)
    assert all(record.source is CaptureSource.VIDEO for record in records)
    assert result.frames == 4
    assert result.with_people == 4
    assert result.with_objects == 4
    assert result.duration_s == 0.2
    assert result.out == out
    assert result.session_id == "tea-1"


def test_record_stream_writes_an_empty_session_without_complaining(tmp_path):
    out = tmp_path / "session.jsonl"

    result = record_stream(
        fake_images(2),
        out,
        landmarker=FakeLandmarker(),
        detector=FakeDetector(),
        source="camera",
        session_id="tea-2",
    )

    records = [CaptureFrame.model_validate_json(line) for line in out.read_text().splitlines()]
    assert [(record.poses, record.hands, record.objects) for record in records] == [
        ([], [], []),
        ([], [], []),
    ]
    assert (result.frames, result.with_people, result.with_objects) == (2, 0, 0)


def test_record_stream_stops_at_the_limit(tmp_path):
    out = tmp_path / "session.jsonl"

    result = record_stream(
        fake_images(100),
        out,
        landmarker=FakeLandmarker(),
        detector=FakeDetector(),
        source="camera",
        session_id="tea-3",
        limit=3,
    )

    assert result.frames == 3
    assert len(out.read_text().splitlines()) == 3


def test_record_stream_writes_nothing_that_looks_like_an_image(tmp_path):
    """The same checks tests/test_privacy.py makes of the recordings in git."""
    out = tmp_path / "session.jsonl"

    record_stream(
        fake_images(5),
        out,
        landmarker=FakeLandmarker(Landmarks(poses=(fake_pose(),), hands=(fake_hand(),))),
        detector=FakeDetector([fake_detection()]),
        source="camera",
        session_id="tea-4",
    )

    offenders = []
    for number, line in enumerate(out.read_bytes().splitlines(), start=1):
        text = line.decode("utf-8")
        if len(line) >= 20_000:
            offenders.append(f"line {number}: {len(line)} bytes")
        if "data:image" in text.lower() or BASE64_RUN.search(text):
            offenders.append(f"line {number}: image data or a long base64-like run")
        offenders.extend(f"line {number}: {field}" for field in banned_fields(json.loads(text)))
    assert offenders == []


def test_record_stream_drops_every_frame_it_was_given(tmp_path):
    """SPEC section 8: a frame is processed and gone, never stored, never kept."""
    refs: list[weakref.ref] = []

    record_stream(
        fake_images(3, refs=refs),
        tmp_path / "session.jsonl",
        landmarker=FakeLandmarker(Landmarks(poses=(fake_pose(),))),
        detector=FakeDetector(),
        source="camera",
        session_id="tea-5",
    )

    gc.collect()
    assert len(refs) == 3
    assert [ref() for ref in refs] == [None, None, None]


def test_record_stream_keeps_what_was_written_when_the_human_stops_it(tmp_path):
    out = tmp_path / "session.jsonl"

    def interrupted():
        yield from fake_images(2)
        raise KeyboardInterrupt

    result = record_stream(
        interrupted(),
        out,
        landmarker=FakeLandmarker(),
        detector=FakeDetector(),
        source="camera",
        session_id="tea-6",
    )

    assert result.frames == 2
    assert len(out.read_text().splitlines()) == 2


def test_default_session_id_names_the_source_and_the_time():
    assert default_session_id(CaptureSource.CAMERA).startswith("camera-")
    assert default_session_id(CaptureSource.VIDEO).startswith("video-")


# ----------------------------------------------------------------- model bundles


def test_model_path_prefers_the_flag_then_the_environment(tmp_path, monkeypatch):
    flag = tmp_path / "flag.task"
    env = tmp_path / "env.task"
    flag.touch()
    env.touch()
    monkeypatch.setenv(POSE_MODEL_ENV, str(env))

    assert model_path(flag, POSE_MODEL_ENV, DEFAULT_POSE_MODEL) == flag
    assert model_path(None, POSE_MODEL_ENV, DEFAULT_POSE_MODEL) == env
    monkeypatch.delenv(POSE_MODEL_ENV)
    assert model_path(None, POSE_MODEL_ENV, DEFAULT_POSE_MODEL).name.endswith(".task")


def test_mediapipe_landmarker_says_what_is_missing(tmp_path, monkeypatch):
    """Whichever is missing - the library or the bundle - the message says how to fix it."""
    monkeypatch.setenv(POSE_MODEL_ENV, str(tmp_path / "absent.task"))

    with pytest.raises(CaptureError) as raised:
        MediaPipeLandmarker()

    assert re.search(r"uv sync --extra capture|curl", str(raised.value))


# --------------------------------------------------------------------- detectors


def test_fake_detector_reports_nothing_by_default():
    assert FakeDetector().detect(FakeImage()) == []


def test_fake_detector_hands_back_what_it_was_given():
    detection = fake_detection()
    assert FakeDetector([detection]).detect(FakeImage()) == [detection]


def test_build_detector_falls_back_to_the_fake_when_there_are_no_weights():
    detector = build_detector(None)
    assert isinstance(detector, FakeDetector)
    assert detector.detect(FakeImage()) == []


def test_local_detector_needs_weights_on_disk(tmp_path):
    with pytest.raises(DetectorError, match="no detector weights"):
        LocalDetector(tmp_path / "detector.onnx")


def test_local_detector_refuses_weights_it_cannot_run_locally(tmp_path):
    weights = tmp_path / "detector.weights"
    weights.write_bytes(b"not a model")

    with pytest.raises(DetectorError, match="unsupported weights"):
        LocalDetector(weights)


def test_label_for_reads_the_contracts_classes_and_the_obvious_synonyms():
    assert label_for("kettle") is ObjectLabel.KETTLE
    assert label_for("Cup") is ObjectLabel.CUP
    assert label_for("tea bag") is ObjectLabel.TEABAG
    assert label_for(" Mug ") is ObjectLabel.CUP
    assert label_for("teaspoon") is ObjectLabel.SPOON
    assert label_for("pouring-water") is ObjectLabel.POURING


def test_label_for_drops_a_class_the_pipeline_cannot_read():
    assert label_for("toaster") is None
    assert label_for("") is None


def test_parse_names_reads_every_way_an_exporter_writes_them():
    assert parse_names("{0: 'cup', 1: 'kettle'}") == ["cup", "kettle"]
    assert parse_names('{"1": "kettle", "0": "cup"}') == ["cup", "kettle"]
    assert parse_names('["cup", "kettle"]') == ["cup", "kettle"]
    assert parse_names("cup\nkettle\n") == ["cup", "kettle"]


def test_normalised_box_clamps_to_the_frame_and_orders_the_corners():
    box = normalised_box(-20, 10, 320, 720, 640, 480)

    assert (box.x1, box.y1, box.x2, box.y2) == (0.0, 0.0208, 0.5, 1.0)
    # A model happily swaps the corners; the contract does not allow it.
    assert normalised_box(320, 240, 64, 48, 640, 480) == normalised_box(64, 48, 320, 240, 640, 480)


def test_normalised_box_needs_a_frame_with_a_size():
    with pytest.raises(ValueError, match="positive size"):
        normalised_box(0, 0, 1, 1, 0, 480)


def test_iou_of_boxes_that_do_and_do_not_overlap():
    assert iou((0, 0, 10, 10), (0, 0, 10, 10)) == 1.0
    assert iou((0, 0, 10, 10), (20, 20, 30, 30)) == 0.0
    assert iou((0, 0, 10, 10), (5, 0, 15, 10)) == pytest.approx(1 / 3)


def test_non_max_suppression_keeps_the_strongest_of_each_object():
    boxes = [(0, 0, 10, 10), (1, 1, 11, 11), (50, 50, 60, 60)]
    scores = [0.6, 0.9, 0.4]

    assert non_max_suppression(boxes, scores, 0.45) == [1, 2]
    assert non_max_suppression(boxes, scores, 0.95) == [1, 0, 2]


def test_letterbox_scales_and_pads_without_distorting_the_frame():
    box = letterbox(1280, 720, 640, 640)

    assert box.scale == 0.5
    assert (box.pad_x, box.pad_y) == (0.0, 140.0)
    # A box the model predicts in input pixels, back where it came from.
    assert box.to_frame(320.0, 320.0, 64.0, 32.0) == (576.0, 328.0, 704.0, 392.0)


def test_letterbox_needs_real_sizes():
    with pytest.raises(ValueError, match="positive"):
        letterbox(0, 720, 640, 640)


def test_decode_rows_turns_model_output_into_detections():
    rows = [
        [320.0, 320.0, 64.0, 64.0, 0.9, 0.1],  # a kettle, strong
        [321.0, 321.0, 64.0, 64.0, 0.7, 0.1],  # the same kettle, weaker
        [100.0, 100.0, 20.0, 20.0, 0.1, 0.8],  # a cup elsewhere
        [500.0, 500.0, 20.0, 20.0, 0.1, 0.2],  # nothing convincing
    ]

    detections = decode_rows(
        rows, ["kettle", "cup"], box=Letterbox(1.0, 0.0, 0.0), width=640, height=640
    )

    assert [(str(d.label), d.confidence) for d in detections] == [("kettle", 0.9), ("cup", 0.8)]
    kettle = detections[0].box
    assert (kettle.x1, kettle.y1, kettle.x2, kettle.y2) == (0.45, 0.45, 0.55, 0.55)
    assert all(detection.track_id is None for detection in detections)


def test_decode_rows_drops_classes_the_contract_has_no_label_for():
    rows = [[320.0, 320.0, 64.0, 64.0, 0.95, 0.0], [100.0, 100.0, 20.0, 20.0, 0.0, 0.95]]

    detections = decode_rows(
        rows, ["toaster", "cup"], box=Letterbox(1.0, 0.0, 0.0), width=640, height=640
    )

    assert [str(detection.label) for detection in detections] == ["cup"]


def test_decode_rows_rejects_output_that_does_not_match_the_class_list():
    rows = [[320.0, 320.0, 64.0, 64.0, 0.1, 0.9]]

    with pytest.raises(ValueError, match="outside the model's"):
        decode_rows(rows, ["kettle"], box=Letterbox(1.0, 0.0, 0.0), width=640, height=640)


# --------------------------------------------------------------------------- CLI


def run_module(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-m", "routine_watch.capture", *args],
        capture_output=True,
        text=True,
        timeout=120,
    )


def test_the_cli_help_works_without_the_capture_extra_installed():
    done = run_module("--help")

    assert done.returncode == 0, done.stderr
    for flag in ("--camera", "--video", "--out", "--fps", "--weights"):
        assert flag in done.stdout


def test_the_cli_needs_a_source_and_an_out_file():
    assert run_module().returncode == 2
    assert run_module("--camera", "0").returncode == 2
    assert run_module("--camera", "0", "--video", "clip.mp4", "--out", "x.jsonl").returncode == 2


def test_the_cli_fails_politely_when_it_cannot_capture(tmp_path):
    """No mediapipe, no bundles or no video: one line on stderr, never a traceback."""
    done = run_module("--video", str(tmp_path / "absent.mp4"), "--out", str(tmp_path / "o.jsonl"))

    assert done.returncode == 1
    assert done.stderr.startswith("capture:")
    assert "Traceback" not in done.stderr


def test_the_cli_fails_politely_when_the_weights_are_missing(tmp_path):
    done = run_module(
        "--video",
        str(tmp_path / "clip.mp4"),
        "--out",
        str(tmp_path / "o.jsonl"),
        "--weights",
        str(tmp_path / "absent.onnx"),
    )

    assert done.returncode == 1
    assert done.stderr.startswith("capture: no detector weights")


def test_importing_capture_pulls_in_none_of_the_heavy_dependencies():
    """`--help`, the tests and the rest of the pipeline must not need the extra."""
    done = subprocess.run(
        [
            sys.executable,
            "-c",
            "import sys, routine_watch.capture, routine_watch.detector;"
            "print([m for m in ('cv2', 'mediapipe', 'onnxruntime', 'ultralytics')"
            " if m in sys.modules])",
        ],
        capture_output=True,
        text=True,
        timeout=120,
    )

    assert done.returncode == 0, done.stderr
    assert done.stdout.strip() == "[]"
