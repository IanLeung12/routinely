"""The local object detector (SPEC sections 6.1 and 16).

Finds the task objects in one frame - kettle, cup, teabag, spoon, milk, sugar, shaker,
protein tub, scoop, and optionally hands and "pouring" - and reports them as boxes
normalised to the frame.

The detector **always runs locally from downloaded weights**. Roboflow's hosted
inference is never called, from code, tests or CI: the credits are scarce and the demo
has to work offline (SPEC section 16). Three implementations sit behind one interface:

``FakeDetector``
    The default. No weights, no boxes, no network. Tests, CI and the scenario replay
    use this one, so nothing in them can reach a paid API by accident.
``LocalDetector``
    An exported Roboflow/YOLO model run on this machine: ``.onnx`` through
    onnxruntime, other formats through ultralytics. Both imports are lazy, so this
    module is importable without either installed.

Weights are not in git. Export the trained model from Roboflow, save it as
``models/detector.onnx`` or set ``DETECTOR_WEIGHTS``, and pass it to
``python -m routine_watch.capture --weights``. Until then capture runs with
``FakeDetector`` and reports no objects: the rest of the pipeline still works, it just
sees no objects to build steps from.

Nothing here keeps a frame. An image goes in, boxes and labels come out (SPEC
section 8).
"""

from __future__ import annotations

import ast
import json
import re
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

from .contracts import BoundingBox, ObjectDetection, ObjectLabel

#: One frame as the detector takes it: an OpenCV BGR array, usually. Deliberately
#: untyped so this module never has to import numpy.
Image = Any

#: Keep a box below this and it is noise rather than an object.
DEFAULT_CONFIDENCE = 0.25

#: Two boxes overlapping more than this are the same object seen twice.
DEFAULT_IOU = 0.45

#: What an exported YOLO model wants its input letterboxed to, when it does not say.
DEFAULT_INPUT_SIZE = 640

#: Box corners are stored to this many decimals: millimetre-ish on a kitchen counter,
#: and it keeps the JSONL small.
BOX_DIGITS = 4

#: Detector class names that mean one of the contract's labels under another word.
#: A model trained on "mug" still reports a cup to the rest of the pipeline.
LABEL_ALIASES: dict[str, ObjectLabel] = {
    "mug": ObjectLabel.CUP,
    "tea_cup": ObjectLabel.CUP,
    "tea_bag": ObjectLabel.TEABAG,
    "tea_bag_in_cup": ObjectLabel.TEABAG,
    "teaspoon": ObjectLabel.SPOON,
    "spoon_in_cup": ObjectLabel.SPOON,
    "milk_jug": ObjectLabel.MILK,
    "milk_carton": ObjectLabel.MILK,
    "sugar_bowl": ObjectLabel.SUGAR,
    "sugar_jar": ObjectLabel.SUGAR,
    "shaker_bottle": ObjectLabel.SHAKER,
    "blender_bottle": ObjectLabel.SHAKER,
    "protein_powder": ObjectLabel.PROTEIN_TUB,
    "protein_tub_closed": ObjectLabel.PROTEIN_TUB,
    "scoop_spoon": ObjectLabel.SCOOP,
    "pour": ObjectLabel.POURING,
    "pouring_water": ObjectLabel.POURING,
    "hands": ObjectLabel.HAND,
}

_BY_NAME: dict[str, ObjectLabel] = {label.value: label for label in ObjectLabel} | LABEL_ALIASES

#: Model formats ultralytics loads for us, decoding and NMS included.
_ULTRALYTICS_SUFFIXES = (".pt", ".engine", ".torchscript", ".tflite", ".mlpackage")


class DetectorError(RuntimeError):
    """The weights are missing, unreadable, or not a detector we can run locally."""


class Detector(Protocol):
    """Finds the task objects in one frame. Local only; never hosted inference."""

    def detect(self, image: Image) -> list[ObjectDetection]:
        """The objects in this frame, as boxes normalised to it."""
        ...


class FakeDetector:
    """The default detector: whatever it was handed, and nothing by default.

    Used everywhere a real model would cost money or need hardware - tests, CI, the
    scenario replay - and while the trained weights do not exist yet. Pass canned
    detections to stand in for a model that found something.
    """

    def __init__(self, detections: Sequence[ObjectDetection] = ()) -> None:
        self._detections = tuple(detections)

    def detect(self, image: Image) -> list[ObjectDetection]:
        return list(self._detections)


# -------------------------------------------------------------- labels and boxes


def label_for(name: str) -> ObjectLabel | None:
    """One detector class name as a contract label, or None if it is not one of ours.

    Case, spaces and dashes do not matter, and `LABEL_ALIASES` covers the obvious
    synonyms. An unknown class is dropped rather than guessed at: a model trained with
    extra classes must not push labels the rest of the pipeline cannot read.
    """
    key = re.sub(r"[^a-z0-9]+", "_", name.strip().lower()).strip("_")
    return _BY_NAME.get(key)


def parse_names(raw: str) -> list[str]:
    """Class names as exporters write them, in class-index order.

    ultralytics puts ``{0: 'cup', 1: 'kettle'}`` in the ONNX metadata, other tools
    write a JSON list, and a sibling ``labels.txt`` is one name per line.
    """
    text = raw.strip()
    if text.startswith("{"):
        mapping = ast.literal_eval(text)
        return [str(mapping[key]) for key in sorted(mapping, key=lambda k: int(k))]
    if text.startswith("["):
        return [str(name) for name in json.loads(text)]
    return [line.strip() for line in text.splitlines() if line.strip()]


def normalised_box(
    x1: float, y1: float, x2: float, y2: float, width: float, height: float
) -> BoundingBox:
    """Pixel corners as the contract's 0..1 box: clamped to the frame and ordered.

    A model happily predicts a corner just off the edge of the frame; the contract
    does not allow one, and a box that has left the frame is still the object.
    """
    if width <= 0 or height <= 0:
        raise ValueError(f"frame must have a positive size, got {width}x{height}")
    left, right = sorted((x1 / width, x2 / width))
    top, bottom = sorted((y1 / height, y2 / height))
    return BoundingBox(
        x1=_unit(left), y1=_unit(top), x2=_unit(right), y2=_unit(bottom)
    )


def iou(a: tuple[float, float, float, float], b: tuple[float, float, float, float]) -> float:
    """Intersection over union of two ``(x1, y1, x2, y2)`` boxes."""
    overlap_w = min(a[2], b[2]) - max(a[0], b[0])
    overlap_h = min(a[3], b[3]) - max(a[1], b[1])
    if overlap_w <= 0 or overlap_h <= 0:
        return 0.0
    overlap = overlap_w * overlap_h
    union = _area(a) + _area(b) - overlap
    return overlap / union if union > 0 else 0.0


def non_max_suppression(
    boxes: Sequence[tuple[float, float, float, float]],
    scores: Sequence[float],
    iou_threshold: float = DEFAULT_IOU,
) -> list[int]:
    """Which boxes to keep, best first: the strongest, then anything not covered by it.

    Per class, so a hand resting on the cup does not suppress the cup.
    """
    order = sorted(range(len(boxes)), key=lambda i: scores[i], reverse=True)
    kept: list[int] = []
    for index in order:
        if all(iou(boxes[index], boxes[other]) <= iou_threshold for other in kept):
            kept.append(index)
    return kept


# ------------------------------------------------------------------- letterboxing


@dataclass(frozen=True)
class Letterbox:
    """How a frame was fitted into the model's square input: scaled, then padded."""

    scale: float
    pad_x: float
    pad_y: float

    def to_frame(
        self, cx: float, cy: float, w: float, h: float
    ) -> tuple[float, float, float, float]:
        """One ``(centre, size)`` prediction back in frame pixels, as corners."""
        x1 = (cx - w / 2 - self.pad_x) / self.scale
        y1 = (cy - h / 2 - self.pad_y) / self.scale
        return x1, y1, x1 + w / self.scale, y1 + h / self.scale


def letterbox(src_w: int, src_h: int, dst_w: int, dst_h: int) -> Letterbox:
    """Fit a ``src_w`` x ``src_h`` frame into the model's input without distorting it."""
    if min(src_w, src_h, dst_w, dst_h) <= 0:
        raise ValueError("letterbox sizes must be positive")
    scale = min(dst_w / src_w, dst_h / src_h)
    return Letterbox(
        scale=scale,
        pad_x=(dst_w - src_w * scale) / 2,
        pad_y=(dst_h - src_h * scale) / 2,
    )


# ------------------------------------------------------------------ output decoding


def decode_rows(
    rows: Iterable[Sequence[float]],
    names: Sequence[str],
    *,
    box: Letterbox,
    width: int,
    height: int,
    confidence: float = DEFAULT_CONFIDENCE,
    iou_threshold: float = DEFAULT_IOU,
) -> list[ObjectDetection]:
    """Raw YOLO rows as detections: ``[cx, cy, w, h, score per class]`` in input pixels.

    Everything shape-specific has already happened by here, which is what makes this
    the testable half of `LocalDetector`: rows of plain numbers in, contract objects
    out, no model and no numpy. Rows below `confidence`, and classes the contract has
    no label for, are dropped; the rest go through per-class non-max suppression.
    """
    candidates: dict[ObjectLabel, list[tuple[tuple[float, float, float, float], float]]] = {}
    for row in rows:
        scores = row[4:]
        if not scores:
            raise ValueError("a detector row needs a box and at least one class score")
        best = max(range(len(scores)), key=lambda i: scores[i])
        score = float(scores[best])
        if score < confidence:
            continue
        if best >= len(names):
            raise ValueError(f"class {best} is outside the model's {len(names)} names")
        label = label_for(names[best])
        if label is None:
            continue
        corners = box.to_frame(float(row[0]), float(row[1]), float(row[2]), float(row[3]))
        candidates.setdefault(label, []).append((corners, score))

    detections: list[ObjectDetection] = []
    for label, found in candidates.items():
        boxes = [corners for corners, _ in found]
        scores = [score for _, score in found]
        for index in non_max_suppression(boxes, scores, iou_threshold):
            detections.append(
                ObjectDetection(
                    label=label,
                    confidence=_unit(scores[index]),
                    box=normalised_box(*boxes[index], width, height),
                )
            )
    return sorted(detections, key=lambda d: (-d.confidence, str(d.label)))


# ------------------------------------------------------------------- local weights


class LocalDetector:
    """A trained detector run on this machine, from weights on disk.

    ``.onnx`` weights go through onnxruntime (in the ``capture`` extra) and are decoded
    here; ``.pt`` and the other ultralytics formats are handed to ultralytics, which
    decodes them itself. Either way the weights are local files: no hosted inference,
    no API key, no credits (SPEC section 16).

        detector = LocalDetector(Path("models/detector.onnx"))
        boxes = detector.detect(frame)

    The ONNX path expects a YOLOv8-style head: one output shaped
    ``(1, 4 + classes, boxes)`` (or its transpose) holding a centre, a size and one
    score per class. That is what Roboflow and ultralytics export. Anything else
    raises `DetectorError` rather than quietly reporting nonsense.
    """

    def __init__(
        self,
        weights_path: str | Path,
        *,
        labels: Sequence[str] | None = None,
        confidence: float = DEFAULT_CONFIDENCE,
        iou_threshold: float = DEFAULT_IOU,
        input_size: int | None = None,
    ) -> None:
        self.weights_path = Path(weights_path)
        if not self.weights_path.is_file():
            raise DetectorError(
                f"no detector weights at {self.weights_path}. Export the trained model "
                "from Roboflow (ONNX) and pass --weights, or run without them and "
                "capture reports no objects."
            )
        self.confidence = confidence
        self.iou_threshold = iou_threshold
        self._onnx = self.weights_path.suffix.lower() == ".onnx"
        if self._onnx:
            self._session = _onnx_session(self.weights_path)
            self._names = list(labels) if labels else _onnx_names(self._session, self.weights_path)
            self._size = input_size or _onnx_input_size(self._session)
        elif self.weights_path.suffix.lower() in _ULTRALYTICS_SUFFIXES:
            self._model = _ultralytics_model(self.weights_path)
            self._names = list(labels) if labels else _ultralytics_names(self._model)
            self._size = input_size or DEFAULT_INPUT_SIZE
        else:
            raise DetectorError(
                f"{self.weights_path.name}: unsupported weights. Use .onnx, or one of "
                f"{', '.join(_ULTRALYTICS_SUFFIXES)} with ultralytics installed."
            )

    @property
    def names(self) -> list[str]:
        """The model's class names, in class-index order."""
        return list(self._names)

    def detect(self, image: Image) -> list[ObjectDetection]:
        """The objects in one BGR frame. The frame is read, never kept."""
        return self._detect_onnx(image) if self._onnx else self._detect_ultralytics(image)

    def _detect_onnx(self, image: Image) -> list[ObjectDetection]:
        import numpy as np

        height, width = image.shape[:2]
        box = letterbox(width, height, self._size, self._size)
        tensor = _letterboxed_tensor(image, box, self._size)
        name = self._session.get_inputs()[0].name
        raw = np.asarray(self._session.run(None, {name: tensor})[0])
        rows = _candidate_rows(raw, len(self._names), self.confidence)
        return decode_rows(
            rows,
            self._names,
            box=box,
            width=width,
            height=height,
            confidence=self.confidence,
            iou_threshold=self.iou_threshold,
        )

    def _detect_ultralytics(self, image: Image) -> list[ObjectDetection]:
        height, width = image.shape[:2]
        results = self._model.predict(
            image, conf=self.confidence, iou=self.iou_threshold, imgsz=self._size, verbose=False
        )
        detections: list[ObjectDetection] = []
        for result in results:
            for row in result.boxes:
                label = label_for(self._names[int(row.cls[0])])
                if label is None:
                    continue
                x1, y1, x2, y2 = (float(value) for value in row.xyxy[0])
                detections.append(
                    ObjectDetection(
                        label=label,
                        confidence=_unit(float(row.conf[0])),
                        box=normalised_box(x1, y1, x2, y2, width, height),
                    )
                )
        return sorted(detections, key=lambda d: (-d.confidence, str(d.label)))


def build_detector(
    weights_path: str | Path | None, *, confidence: float = DEFAULT_CONFIDENCE
) -> Detector:
    """`LocalDetector` when there are weights, `FakeDetector` when there are not.

    The fallback is the point: capture runs with no detector at all, and the pipeline
    sees a session with no objects rather than failing to start.
    """
    if weights_path is None:
        return FakeDetector()
    return LocalDetector(weights_path, confidence=confidence)


# ------------------------------------------------------- the lazily imported half


def _onnx_session(path: Path) -> Any:
    try:
        import onnxruntime
    except ImportError as exc:  # pragma: no cover - needs the capture extra
        raise DetectorError(
            "onnxruntime is not installed. Install the capture extra: "
            "`cd pipeline && uv sync --extra capture`."
        ) from exc
    try:
        return onnxruntime.InferenceSession(str(path), providers=["CPUExecutionProvider"])
    except Exception as exc:  # pragma: no cover - needs weights on disk
        raise DetectorError(f"{path.name}: could not load the ONNX model: {exc}") from exc


def _onnx_names(session: Any, path: Path) -> list[str]:
    """Class names from the model's own metadata, or a sibling ``labels.txt``."""
    raw = session.get_modelmeta().custom_metadata_map.get("names", "")
    if not raw:
        sibling = path.with_suffix(".labels.txt")
        if sibling.is_file():
            raw = sibling.read_text(encoding="utf-8")
    if not raw:
        raise DetectorError(
            f"{path.name}: no class names in the model metadata. Write them next to the "
            f"weights as {path.with_suffix('.labels.txt').name}, one per line, in class order."
        )
    return parse_names(raw)


def _onnx_input_size(session: Any) -> int:
    """The square input the model was exported with, falling back to 640."""
    shape = session.get_inputs()[0].shape
    sizes = [value for value in shape[-2:] if isinstance(value, int) and value > 0]
    return min(sizes) if len(sizes) == 2 else DEFAULT_INPUT_SIZE


def _letterboxed_tensor(image: Image, box: Letterbox, size: int) -> Any:
    """One BGR frame as the model's input: RGB, letterboxed, 0..1, NCHW."""
    import cv2
    import numpy as np

    height, width = image.shape[:2]
    resized = cv2.resize(
        image, (max(1, round(width * box.scale)), max(1, round(height * box.scale)))
    )
    canvas = np.full((size, size, 3), 114, dtype=np.uint8)
    top, left = int(box.pad_y), int(box.pad_x)
    canvas[top : top + resized.shape[0], left : left + resized.shape[1]] = resized
    rgb = cv2.cvtColor(canvas, cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0
    return np.ascontiguousarray(rgb.transpose(2, 0, 1)[None])


def _candidate_rows(raw: Any, class_count: int, confidence: float) -> list[list[float]]:
    """The rows worth decoding, as plain floats.

    numpy does the cheap part - find each box's best class and throw away the 8000-odd
    that scored nothing - and only the survivors become Python numbers for
    `decode_rows`. Keeps the per-frame cost in numpy and the arithmetic testable.
    """
    import numpy as np

    array = np.squeeze(raw)
    if array.ndim != 2:
        raise DetectorError(f"expected a 2-D detector output, got shape {tuple(np.shape(raw))}")
    expected = 4 + class_count
    if array.shape[0] == expected:
        array = array.T
    elif array.shape[1] != expected:
        raise DetectorError(
            f"detector output {array.shape} matches neither (4 + {class_count}, boxes) "
            "nor its transpose; is this a YOLOv8-style detection model?"
        )
    best = array[:, 4:].max(axis=1)
    return [[float(value) for value in row] for row in array[best >= confidence]]


def _ultralytics_model(path: Path) -> Any:
    try:
        from ultralytics import YOLO
    except ImportError as exc:  # pragma: no cover - ultralytics is not in any extra
        raise DetectorError(
            f"{path.name} needs ultralytics, which is not installed (it pulls in torch). "
            "Export the model to ONNX, or install it yourself: `uv pip install ultralytics`."
        ) from exc
    try:
        return YOLO(str(path))
    except Exception as exc:  # pragma: no cover - needs weights on disk
        raise DetectorError(f"{path.name}: could not load the model: {exc}") from exc


def _ultralytics_names(model: Any) -> list[str]:
    names = model.names
    if isinstance(names, dict):
        return [str(names[key]) for key in sorted(names, key=lambda k: int(k))]
    return [str(name) for name in names]


# ------------------------------------------------------------------------ helpers


def _unit(value: float) -> float:
    """A number the contract wants in 0..1, rounded and clamped into it."""
    return round(min(1.0, max(0.0, float(value))), BOX_DIGITS)


def _area(box: tuple[float, float, float, float]) -> float:
    return max(0.0, box[2] - box[0]) * max(0.0, box[3] - box[1])
