"""Capture, inside the privacy boundary (SPEC sections 6.1 and 16).

MediaPipe pose and hand landmarks plus the local Roboflow object detector turn each
frame into one JSONL record: landmarks, object boxes and a timestamp. The live camera,
the pre-recorded fallback, tests and scenarios all feed the pipeline through this one
format.

Frames are dropped after processing. Raw video is never stored (SPEC section 8), and
the detector only ever runs locally from downloaded weights, never hosted inference.

    python -m routine_watch.capture --camera 0 --out session.jsonl
    python -m routine_watch.capture --video clip.mp4 --out session.jsonl \
        --weights models/detector.onnx

The output file is exactly what `routine_watch.replay` and the scenarios read, so a
recording made here can be replayed through the whole pipeline with no camera.

`camera_frames` is the same stream without the file in the middle: `/ws/live?source=camera`
reads it on a background thread and plays it through the pipeline as it arrives
(`routine_watch.live_camera`, `scripts/camera.sh`), optionally keeping the records too.

Three pieces, each behind an interface with a fake default, so the module is importable
and testable with none of the heavy dependencies installed:

`Landmarker`
    `MediaPipeLandmarker` in a real session, `FakeLandmarker` in tests. Two people are
    tracked, because a second person in frame means the session was assisted and is
    left out of the resident's baseline (SPEC section 7).
`Detector`
    `routine_watch.detector`: `LocalDetector` from weights on disk, `FakeDetector`
    (no boxes) by default.
`frame_record`
    The pure bit: MediaPipe-shaped landmarks in, one `CaptureFrame` out. Everything
    that decides what is written down lives here, which is what the tests pin.

The one thing that ever sees a frame besides the two models is the optional local
preview (`routine_watch.preview`, off unless `CAMERA_PREVIEW=1`): a small JPEG of the
current frame, served to `127.0.0.1` only, so whoever is standing at this machine can
aim the camera. It is held in memory for one frame at a time and written nowhere, and
the records this module writes are the same with it on or off.

mediapipe and opencv are in the ``capture`` extra (`uv sync --extra capture`) and are
imported lazily, so CI, the pipeline and `--help` never need them. MediaPipe also needs
its two task bundles on disk; `MediaPipeLandmarker` says where to get them if they are
missing.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from collections.abc import Iterable, Iterator, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Protocol

from .contracts import (
    FRAME_SCHEMA_VERSION,
    CaptureFrame,
    CaptureSource,
    Handedness,
    HandLandmarks,
    Landmark,
    ObjectDetection,
    Pose,
    repo_root,
)
from .detector import Detector, DetectorError, build_detector
from .preview import Preview, start_preview

STAGE = "capture"

#: How many records a second the capture process writes. 15 is plenty for steps that
#: take seconds, and it keeps a session's JSONL small enough to replay.
DEFAULT_FPS = 15

#: Landmarks are stored to this many decimals. On a 1080p frame that is sub-pixel, and
#: it keeps one record near a kilobyte instead of several.
COORD_DIGITS = 4

#: Track up to this many people: one resident, one possible helper (SPEC section 7).
MAX_PEOPLE = 2

#: Two hands, because steps are hand-object interactions (SPEC section 16).
MAX_HANDS = 2

#: MediaPipe task bundles: free downloads, no key, no credits. Not in git.
POSE_MODEL_ENV = "MEDIAPIPE_POSE_MODEL"
HAND_MODEL_ENV = "MEDIAPIPE_HAND_MODEL"
DEFAULT_POSE_MODEL = "models/pose_landmarker_lite.task"
DEFAULT_HAND_MODEL = "models/hand_landmarker.task"
_MODEL_URLS = {
    DEFAULT_POSE_MODEL: (
        "https://storage.googleapis.com/mediapipe-models/pose_landmarker/"
        "pose_landmarker_lite/float16/latest/pose_landmarker_lite.task"
    ),
    DEFAULT_HAND_MODEL: (
        "https://storage.googleapis.com/mediapipe-models/hand_landmarker/"
        "hand_landmarker/float16/latest/hand_landmarker.task"
    ),
}

#: Where the local detector's weights are, when no `--weights` is given.
WEIGHTS_ENV = "DETECTOR_WEIGHTS"

#: Where a live camera session also writes its records, when it is asked to keep them
#: (`scripts/camera.sh --record`). Records, never video.
RECORD_ENV = "CAMERA_RECORD"

#: A video file claiming a frame rate outside this is lying; fall back to `--fps`.
_SANE_FPS = (1.0, 240.0)


class CaptureError(RuntimeError):
    """Capture cannot run: no camera, no video, or a missing dependency or model."""


# ------------------------------------------------------- what a landmarker gives us


class LandmarkLike(Protocol):
    """Anything MediaPipe-shaped: one landmark, normalised to the frame.

    Only the three coordinates are required. `visibility` is read when it is there
    (pose landmarks have it, hand landmarks do not).
    """

    x: float
    y: float
    z: float


@dataclass(frozen=True)
class Hand:
    """One hand as MediaPipe reports it: the landmarks, which hand, and how sure.

    `handedness` is MediaPipe's own word - "Left" or "Right", either case.
    """

    handedness: str
    score: float
    landmarks: Sequence[LandmarkLike]


@dataclass(frozen=True)
class Landmarks:
    """What a landmarker saw in one frame: a skeleton per person, and the hands."""

    poses: tuple[Sequence[LandmarkLike], ...] = ()
    hands: tuple[Hand, ...] = ()


class Landmarker(Protocol):
    """Turns one frame into skeletons and hands. Runs on this machine, always."""

    def landmark(self, image: Any, t: float) -> Landmarks:
        """The people and hands in this frame, `t` seconds into the session."""
        ...


class FakeLandmarker:
    """A landmarker with no MediaPipe behind it: whatever it was handed, every frame.

    The default in tests and anywhere a camera would be needed. With no argument it
    sees nobody, which is also what a real session looks like before anyone walks in.
    """

    def __init__(self, landmarks: Landmarks | None = None) -> None:
        self._landmarks = landmarks or Landmarks()

    def landmark(self, image: Any, t: float) -> Landmarks:
        return self._landmarks


# ----------------------------------------------------------------- the pure record


def frame_record(
    t: float,
    pose_landmarks: Iterable[Sequence[LandmarkLike]],
    hand_landmarks: Iterable[Hand],
    detections: Iterable[ObjectDetection],
    source: CaptureSource | str,
    *,
    session_id: str,
    seq: int,
    pose_scores: Sequence[float | None] | None = None,
) -> CaptureFrame:
    """One frame's worth of MediaPipe output as the per-frame JSONL record.

        frame = frame_record(0.0, result.pose_landmarks, hands, boxes, "camera",
                             session_id="tea-1", seq=0)

    `pose_landmarks` is one landmark sequence per person, as MediaPipe's
    `PoseLandmarkerResult.pose_landmarks` already is; `hand_landmarks` is a `Hand` per
    hand, which is where MediaPipe's parallel handedness list gets zipped in.

    This is the whole privacy boundary in one function: a frame goes in and only
    landmarks, boxes and a timestamp come out. There is no path from here to an image,
    because `CaptureFrame` has no field that could hold one (SPEC section 8).

    Raises `pydantic.ValidationError` if the landmarks are not a full MediaPipe set
    (33 per person, 21 per hand) - a half-detected skeleton is a bug, not a record.
    """
    scores = tuple(pose_scores or ())
    poses = [
        Pose(
            landmarks=_landmarks(person, visibility=True),
            score=_score(scores[index]) if index < len(scores) else None,
        )
        for index, person in enumerate(pose_landmarks)
    ]
    hands = [
        HandLandmarks(
            handedness=handedness_of(hand.handedness),
            score=_unit(hand.score),
            landmarks=_landmarks(hand.landmarks, visibility=False),
        )
        for hand in hand_landmarks
    ]
    return CaptureFrame(
        schema_version=FRAME_SCHEMA_VERSION,
        session_id=session_id,
        seq=seq,
        t=round(t, COORD_DIGITS),
        source=CaptureSource(source),
        poses=poses,
        hands=hands,
        objects=list(detections),
    )


def handedness_of(name: str | Handedness) -> Handedness:
    """MediaPipe's "Left"/"Right" as the contract's `Handedness`."""
    try:
        return Handedness(str(name).strip().lower())
    except ValueError as exc:
        raise ValueError(f"{name!r} is neither hand") from exc


def _landmarks(landmarks: Iterable[LandmarkLike], *, visibility: bool) -> list[Landmark]:
    """MediaPipe landmarks as contract landmarks, rounded.

    `visibility` is kept for poses and dropped for hands: MediaPipe reports 0.0 for
    every hand landmark, and a contract field that always says "invisible" would read
    as a fact rather than a gap.
    """
    return [
        Landmark(
            x=round(float(point.x), COORD_DIGITS),
            y=round(float(point.y), COORD_DIGITS),
            z=round(float(point.z), COORD_DIGITS),
            visibility=_score(getattr(point, "visibility", None)) if visibility else None,
        )
        for point in landmarks
    ]


def _unit(value: float) -> float:
    """A score the contract wants in 0..1, rounded and clamped into it."""
    return round(min(1.0, max(0.0, float(value))), COORD_DIGITS)


def _score(value: float | None) -> float | None:
    """`_unit`, for the scores MediaPipe does not always report."""
    return None if value is None else _unit(value)


# --------------------------------------------------------------- writing a session


@dataclass(frozen=True)
class CaptureResult:
    """What one capture run produced. No frames in it, by design."""

    session_id: str
    source: CaptureSource
    out: Path
    frames: int
    #: Seconds from the first record to the last.
    duration_s: float = 0.0
    #: Frames the landmarker found at least one person in.
    with_people: int = 0
    #: Frames the detector found at least one object in.
    with_objects: int = 0


@dataclass
class _Counts:
    """Running totals while a session is being written."""

    frames: int = 0
    with_people: int = 0
    with_objects: int = 0
    first_t: float | None = None
    last_t: float = 0.0


def frame_stream(
    images: Iterable[tuple[float, Any]],
    *,
    landmarker: Landmarker,
    detector: Detector,
    source: CaptureSource | str,
    session_id: str,
    limit: int | None = None,
    preview: Preview | None = None,
) -> Iterator[CaptureFrame]:
    """One record per frame, handed over as the frame is read and then dropped.

    `images` yields `(t, image)` pairs: seconds since the session started, and whatever
    the landmarker and detector take. The camera, a video file and the fakes in tests
    all go through here, so this is the loop that keeps the privacy promise - each frame
    is read by the two models, turned into a record, and dropped before the next one.
    There is no path from here to an image, because `CaptureFrame` has no field that
    could hold one (SPEC section 8).

    Two readers: `record_stream` writes the records to disk, and a live session reads
    them as they arrive (`routine_watch.live_camera`, via `camera_frames`). Both see the
    same records in the same order, which is what makes a live session and a replay of
    the recording it wrote agree.

    `preview` is the optional local camera preview (`routine_watch.preview`, off unless
    `CAMERA_PREVIEW=1`): the frame is offered to it here, between the two models and the
    `del` below, because this is the one loop that has the frame and there is only ever
    one camera handle. What it takes is a small JPEG of the current frame, kept in memory
    for whoever is standing at this machine and never written anywhere; the record this
    loop yields is the same record with or without it.
    """
    for seq, (t, image) in enumerate(images):
        if limit is not None and seq >= limit:
            return
        seen = landmarker.landmark(image, t)
        detections = detector.detect(image)
        if preview is not None:
            preview.offer(image, t)  # a JPEG of this frame, in memory, for this device
        del image  # the frame is gone from here on; only the record survives

        yield frame_record(
            t, seen.poses, seen.hands, detections, source, session_id=session_id, seq=seq
        )


def recorded(frames: Iterable[CaptureFrame], out: Path) -> Iterator[CaptureFrame]:
    """`frames`, with each record also written to `out` as one JSONL line.

    What that file holds is exactly what `routine_watch.replay` and the scenarios read,
    so a live camera session kept this way can be replayed through the whole pipeline
    afterwards with no camera (`scripts/camera.sh --record`). Records only - landmarks,
    boxes and timestamps - because that is all a record can hold (SPEC section 8).

    Lines are flushed as they are written so the live view can tail the file, and the
    file is closed when the stream ends, whether that is the last frame, a Ctrl-C or a
    reader that stopped reading.
    """
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8", buffering=1) as handle:
        for frame in frames:
            handle.write(frame.model_dump_json() + "\n")
            yield frame


def record_stream(
    images: Iterable[tuple[float, Any]],
    out: Path,
    *,
    landmarker: Landmarker,
    detector: Detector,
    source: CaptureSource | str,
    session_id: str,
    limit: int | None = None,
    preview: Preview | None = None,
) -> CaptureResult:
    """Write one JSONL record per frame, then forget the frame.

    `frame_stream` read into `recorded`, which is the capture process's whole job, plus
    the summary it prints. Ctrl-C ends the recording cleanly with everything so far on
    disk. `preview` is handed straight on to `frame_stream`, which is the only thing in
    the capture process that ever has a frame.
    """
    counts = _Counts()
    stream = frame_stream(
        images,
        landmarker=landmarker,
        detector=detector,
        source=source,
        session_id=session_id,
        limit=limit,
        preview=preview,
    )
    try:
        for record in recorded(stream, out):
            counts.frames += 1
            counts.with_people += bool(record.poses)
            counts.with_objects += bool(record.objects)
            if counts.first_t is None:
                counts.first_t = record.t
            counts.last_t = record.t
    except KeyboardInterrupt:
        pass  # the human stopped the recording; what is written is still a session

    return CaptureResult(
        session_id=session_id,
        source=CaptureSource(source),
        out=out,
        frames=counts.frames,
        duration_s=round(counts.last_t - (counts.first_t or 0.0), COORD_DIGITS),
        with_people=counts.with_people,
        with_objects=counts.with_objects,
    )


# -------------------------------------------------------------- MediaPipe, lazily


def model_path(explicit: str | Path | None, env_var: str, default: str) -> Path:
    """Where a MediaPipe task bundle is: the flag, then the env var, then `models/`.

    A relative path is tried against the working directory first and the repo root
    second, so `models/...` works from anywhere in the monorepo.
    """
    candidate = Path(explicit or os.environ.get(env_var) or default).expanduser()
    if candidate.is_absolute() or candidate.exists():
        return candidate
    from_root = repo_root() / candidate
    return from_root if from_root.exists() else candidate


def missing_models() -> dict[Path, str]:
    """The MediaPipe task bundles this machine has not got yet, and where to get them.

    Keyed by where each bundle belongs - `MEDIAPIPE_POSE_MODEL` / `MEDIAPIPE_HAND_MODEL`
    when they are set, `models/` otherwise - with its download URL: free, no key, no
    credits, and not in git. Empty once both are there, which is what lets
    `scripts/camera.sh` download them every run without downloading them twice.
    """
    return {
        path: _MODEL_URLS[default]
        for default, env_var in (
            (DEFAULT_POSE_MODEL, POSE_MODEL_ENV),
            (DEFAULT_HAND_MODEL, HAND_MODEL_ENV),
        )
        if not (path := model_path(None, env_var, default)).is_file()
    }


def _model_file(explicit: str | Path | None, env_var: str, default: str) -> Path:
    path = model_path(explicit, env_var, default)
    if path.is_file():
        return path
    url = _MODEL_URLS[default]
    raise CaptureError(
        f"no MediaPipe model bundle at {path}. Download it once (free, no key):\n"
        f"  curl -L --create-dirs -o {default} {url}\n"
        f"or point {env_var} at a copy you already have."
    )


class MediaPipeLandmarker:
    """MediaPipe pose and hand landmarks, from the task bundles on disk.

    Runs in MediaPipe's VIDEO mode, which tracks people and hands between frames
    instead of looking for them again each time: steadier landmarks, and far cheaper.
    That mode wants timestamps that only ever go up, so `landmark` takes the record's
    own `t` and nudges it forward if a source repeats one.

    Needs the `capture` extra and the two bundles; both missing-dependency paths raise
    `CaptureError` with the command that fixes it.
    """

    def __init__(
        self,
        *,
        pose_model: str | Path | None = None,
        hand_model: str | Path | None = None,
        people: int = MAX_PEOPLE,
        hands: int = MAX_HANDS,
        min_confidence: float = 0.5,
    ) -> None:
        mp, vision = _mediapipe()
        pose_file = _model_file(pose_model, POSE_MODEL_ENV, DEFAULT_POSE_MODEL)
        hand_file = _model_file(hand_model, HAND_MODEL_ENV, DEFAULT_HAND_MODEL)
        base = mp.tasks.BaseOptions
        try:
            self._pose = vision.PoseLandmarker.create_from_options(
                vision.PoseLandmarkerOptions(
                    base_options=base(model_asset_path=str(pose_file)),
                    running_mode=vision.RunningMode.VIDEO,
                    num_poses=people,
                    min_pose_detection_confidence=min_confidence,
                )
            )
            self._hands = vision.HandLandmarker.create_from_options(
                vision.HandLandmarkerOptions(
                    base_options=base(model_asset_path=str(hand_file)),
                    running_mode=vision.RunningMode.VIDEO,
                    num_hands=hands,
                    min_hand_detection_confidence=min_confidence,
                )
            )
        except Exception as exc:  # pragma: no cover - needs mediapipe and the bundles
            raise CaptureError(f"MediaPipe would not start: {exc}") from exc
        self._last_ms = -1

    def landmark(self, image: Any, t: float) -> Landmarks:
        """Pose and hand landmarks for one BGR frame. The frame is read, not kept."""
        import mediapipe as mp
        import numpy as np

        rgb = np.ascontiguousarray(image[:, :, ::-1])
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
        self._last_ms = max(int(t * 1000), self._last_ms + 1)

        poses = self._pose.detect_for_video(mp_image, self._last_ms).pose_landmarks
        found = self._hands.detect_for_video(mp_image, self._last_ms)
        hands = []
        for categories, landmarks in zip(found.handedness, found.hand_landmarks, strict=False):
            if not categories:
                continue  # MediaPipe found a hand but cannot say which; not a record
            hands.append(
                Hand(
                    handedness=categories[0].category_name,
                    score=categories[0].score,
                    landmarks=landmarks,
                )
            )
        return Landmarks(poses=tuple(poses), hands=tuple(hands))

    def close(self) -> None:
        """Let MediaPipe go. Both landmarkers hold native resources."""
        self._pose.close()
        self._hands.close()


def _mediapipe() -> tuple[Any, Any]:
    """mediapipe and its vision tasks, imported on first use."""
    try:
        import mediapipe as mp
        from mediapipe.tasks.python import vision
    except ImportError as exc:
        raise CaptureError(
            "mediapipe is not installed. Install the capture extra: "
            "`cd pipeline && uv sync --extra capture`."
        ) from exc
    return mp, vision


# ------------------------------------------------------------ frames, lazily


def _opencv() -> Any:
    try:
        import cv2
    except ImportError as exc:
        raise CaptureError(
            "opencv is not installed. Install the capture extra: "
            "`cd pipeline && uv sync --extra capture`."
        ) from exc
    return cv2


def camera_images(index: int, fps: float = DEFAULT_FPS) -> Iterator[tuple[float, Any]]:
    """Frames from a webcam, at about `fps`, timestamped from the first one.

    A camera has no clock of its own, so this is the one place a session's times come
    from the wall clock. Frames that arrive between records are read and dropped, which
    is also what keeps the driver's buffer from running behind.
    """
    cv2 = _opencv()
    period = 1.0 / _fps(fps)
    capture = cv2.VideoCapture(index)
    if not capture.isOpened():
        capture.release()
        raise CaptureError(f"no camera at index {index}")
    start: float | None = None
    due = 0.0
    try:
        while True:
            ok, image = capture.read()
            if not ok:
                return
            now = time.monotonic()
            start = now if start is None else start
            t = now - start
            if t + 1e-6 < due:
                continue
            due = t + period
            yield t, image
    finally:
        capture.release()


def video_images(path: str | Path, fps: float = DEFAULT_FPS) -> Iterator[tuple[float, Any]]:
    """Frames from a video file, sampled down to about `fps`.

    Timestamps come from the file - frame number over frame rate - so the same file
    always produces the same records, however slowly it decodes (pipeline guide:
    timestamps from the input, not the clock).
    """
    cv2 = _opencv()
    wanted = _fps(fps)
    path = Path(path)
    if not path.is_file():
        raise CaptureError(f"no video file at {path}")
    capture = cv2.VideoCapture(str(path))
    if not capture.isOpened():
        capture.release()
        raise CaptureError(f"{path.name}: opencv cannot read this video")
    source_fps = capture.get(cv2.CAP_PROP_FPS)
    if not _SANE_FPS[0] <= source_fps <= _SANE_FPS[1]:
        source_fps = wanted
    step = max(1, round(source_fps / wanted))
    try:
        index = 0
        while True:
            ok, image = capture.read()
            if not ok:
                return
            if index % step == 0:
                yield index / source_fps, image
            index += 1
    finally:
        capture.release()


def _fps(fps: float) -> float:
    if fps <= 0:
        raise CaptureError(f"fps must be positive, got {fps}")
    return float(fps)


# ----------------------------------------------------------------------- the run


def default_session_id(source: CaptureSource, now: datetime | None = None) -> str:
    """A session id for a live recording: the source and when it started."""
    stamp = (now or datetime.now(UTC)).strftime("%Y%m%dT%H%M%SZ")
    return f"{source.value}-{stamp}"


def _env_int(name: str, fallback: int) -> int:
    """An int from the environment, ignoring anything that is not one."""
    try:
        return int(os.environ[name])
    except (KeyError, ValueError):
        return fallback


def weights_path(explicit: str | Path | None = None) -> Path | None:
    """Where the local detector's weights are: the argument, then `DETECTOR_WEIGHTS`,
    then nowhere.

    Nowhere is a real answer and the default one: `build_detector` reads it as
    `FakeDetector`, so capture runs with no object detector at all and the session has
    skeletons and hands in it but no objects (`routine_watch.detector`).
    """
    chosen = explicit if explicit is not None else os.environ.get(WEIGHTS_ENV)
    return Path(chosen).expanduser() if chosen else None


def camera_frames(
    index: int = 0,
    *,
    fps: float | None = None,
    weights: str | Path | None = None,
    pose_model: str | Path | None = None,
    hand_model: str | Path | None = None,
    session_id: str | None = None,
    record: str | Path | None = None,
    limit: int | None = None,
) -> Iterator[CaptureFrame]:
    """This machine's camera as a stream of records, for a live session to read.

    The other half of `run`: the same frames, the same two models and the same records,
    handed to a reader as they are made instead of written to a file.
    `/ws/live?source=camera` reads this on a background thread
    (`routine_watch.live_camera.frames_in_thread`) and plays it through the pipeline, so
    the dashboard shows the kitchen it is pointed at.

    `fps`, `weights` and `record` fall back to `CAPTURE_FPS`, `DETECTOR_WEIGHTS` and
    `CAMERA_RECORD` from the environment, which is how `scripts/camera.sh` configures the
    API it starts. With no weights the detector is `FakeDetector`: skeleton and hands
    still stream, there are just no object boxes for the recogniser to read steps from.
    With `record` every record is also written there as JSONL, which makes the session
    replayable offline afterwards - records, never video (SPEC section 8).

    With `CAMERA_PREVIEW=1` (`scripts/camera.sh --preview`) the same frames are also
    offered to a loopback MJPEG server for the length of the session, so whoever is
    standing at this machine can see what the camera sees under the skeleton
    (`routine_watch.preview`). It is started here and closed in the `finally` below,
    with the camera: a preview exists only while something is being filmed, is served to
    `127.0.0.1` and nothing else, and is never written down.

    The camera and MediaPipe are opened on the first record and raise `CaptureError`
    there - no camera at that index, no `capture` extra, no task bundles - so a reader
    can tell "there is no camera here" from "the session ended". Both are let go of when
    the stream is closed, which is as soon as the dashboard's socket closes.
    """
    detector = build_detector(weights_path(weights))  # bad weights before MediaPipe starts
    landmarker = MediaPipeLandmarker(pose_model=pose_model, hand_model=hand_model)
    preview = start_preview()  # None unless CAMERA_PREVIEW=1
    records = frame_stream(
        camera_images(index, fps if fps is not None else _env_int("CAPTURE_FPS", DEFAULT_FPS)),
        landmarker=landmarker,
        detector=detector,
        source=CaptureSource.CAMERA,
        session_id=session_id or default_session_id(CaptureSource.CAMERA),
        limit=limit,
        preview=preview.preview if preview is not None else None,
    )
    keep = record if record is not None else (os.environ.get(RECORD_ENV) or None)
    try:
        yield from (recorded(records, Path(keep)) if keep else records)
    finally:
        if preview is not None:
            preview.close()  # the frame is dropped before the camera is released
        landmarker.close()


def run(
    source: int | str | Path,
    out: Path,
    fps: int = DEFAULT_FPS,
    *,
    detector: Detector | None = None,
    landmarker: Landmarker | None = None,
    session_id: str | None = None,
    weights: str | Path | None = None,
    pose_model: str | Path | None = None,
    hand_model: str | Path | None = None,
    limit: int | None = None,
) -> CaptureResult:
    """Capture a session from a camera index or a video file into one JSONL file.

    Everything heavy is built here and injected into `record_stream`: a camera or a
    video file for the frames, `MediaPipeLandmarker` for the landmarks, and the local
    detector if `weights` point at a model (`FakeDetector`, which reports no objects,
    if they do not). Pass `detector` or `landmarker` to swap either out.

    An `int` source is a camera index; anything else is a path to a video file.

    `out` is overwritten: one run, one session, one file.

    With `CAMERA_PREVIEW=1` this process also serves its current frame on loopback while
    it runs, the same preview a live session gets (`routine_watch.preview`). What it
    writes to `out` is the same either way.
    """
    live = isinstance(source, int)
    kind = CaptureSource.CAMERA if live else CaptureSource.VIDEO
    images = camera_images(source, fps) if live else video_images(source, fps)
    # The detector first: bad weights should say so before MediaPipe is started.
    detector = detector or build_detector(weights)
    ours = landmarker is None
    landmarker = landmarker or MediaPipeLandmarker(pose_model=pose_model, hand_model=hand_model)
    preview = start_preview()  # None unless CAMERA_PREVIEW=1
    try:
        return record_stream(
            images,
            Path(out),
            landmarker=landmarker,
            detector=detector,
            source=kind,
            session_id=session_id or default_session_id(kind),
            limit=limit,
            preview=preview.preview if preview is not None else None,
        )
    finally:
        if preview is not None:
            preview.close()
        close = getattr(landmarker, "close", None) if ours else None
        if close is not None:
            close()  # a landmarker we were handed is the caller's to close


# ------------------------------------------------------------------------- the CLI


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m routine_watch.capture",
        description="Camera or video file -> one JSONL record per frame. "
        "Landmarks, object boxes and timestamps only; frames are dropped.",
    )
    where = parser.add_mutually_exclusive_group(required=True)
    where.add_argument("--camera", type=int, metavar="INDEX", help="webcam index, e.g. 0")
    where.add_argument("--video", type=Path, metavar="PATH", help="a recorded video file")
    parser.add_argument(
        "--out", type=Path, required=True, metavar="PATH", help="JSONL file to write (overwritten)"
    )
    parser.add_argument(
        "--fps",
        type=int,
        default=_env_int("CAPTURE_FPS", DEFAULT_FPS),
        help=f"records per second (default: {DEFAULT_FPS}, or CAPTURE_FPS)",
    )
    parser.add_argument("--limit", type=int, default=None, help="stop after this many frames")
    parser.add_argument("--session-id", default=None, help="default: source and start time")
    parser.add_argument(
        "--weights",
        type=Path,
        default=os.environ.get(WEIGHTS_ENV) or None,
        help="local detector weights, e.g. models/detector.onnx (default: "
        f"{WEIGHTS_ENV}; without them no objects are reported)",
    )
    parser.add_argument("--pose-model", type=Path, default=None, help=f"default: {POSE_MODEL_ENV}")
    parser.add_argument("--hand-model", type=Path, default=None, help=f"default: {HAND_MODEL_ENV}")
    parser.add_argument("--json", action="store_true", help="print the summary as JSON")
    args = parser.parse_args(argv)

    try:
        result = run(
            args.video if args.video is not None else args.camera,
            args.out,
            args.fps,
            session_id=args.session_id,
            weights=args.weights,
            pose_model=args.pose_model,
            hand_model=args.hand_model,
            limit=args.limit,
        )
    except (CaptureError, DetectorError) as exc:
        print(f"capture: {exc}", file=sys.stderr)
        return 1

    summary = {
        "session_id": result.session_id,
        "source": str(result.source),
        "out": str(result.out),
        "frames": result.frames,
        "duration_s": result.duration_s,
        "with_people": result.with_people,
        "with_objects": result.with_objects,
    }
    if not result.frames:
        print(f"capture: no frames read from {summary['source']}", file=sys.stderr)
    if args.json:
        print(json.dumps(summary, indent=2))
    else:
        print(
            f"{result.frames} frames in {result.duration_s:.1f}s -> {result.out} "
            f"(session {result.session_id}, people in {result.with_people}, "
            f"objects in {result.with_objects})"
        )
    return 0 if result.frames else 1


if __name__ == "__main__":
    raise SystemExit(main())
