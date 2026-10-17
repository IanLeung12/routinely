"""The optional local camera preview: who may see it, and that nothing keeps it.

The preview is the one place in the system that has a picture of the kitchen in it, so
these tests are mostly about its two promises: it answers this machine only, and a
session run with it on writes exactly what the same session writes with it off - no
image anywhere under the repo, the capture record or the replay store.

Nothing here needs a camera, mediapipe or opencv: the frames are stand-ins, the encoder
is a function the test wrote, and the HTTP part is checked both as a pure function and
over a real loopback socket (`urllib`, 127.0.0.1, no network).
"""

from __future__ import annotations

import asyncio
import gc
import json
import re
import subprocess
import sys
import types
import urllib.error
import urllib.request
import weakref
from datetime import timedelta
from pathlib import Path

import pytest

from routine_watch.capture import (
    DEFAULT_FPS,
    FakeLandmarker,
    Landmarks,
    camera_frames,
    frame_stream,
    record_stream,
    recorded,
)
from routine_watch.contracts import Session
from routine_watch.demo import DEMO_NOW, DEMO_RESIDENT
from routine_watch.detector import FakeDetector
from routine_watch.live_camera import camera_session_messages
from routine_watch.preview import (
    BOUNDARY,
    DEFAULT_PORT,
    HEALTH_PATH,
    PORT_ENV,
    PREVIEW_ENV,
    STREAM_PATH,
    Preview,
    PreviewServer,
    host_name,
    is_loopback,
    jpeg_encoder,
    preview_enabled,
    preview_port,
    response_for,
    start_preview,
)
from routine_watch.replays import get_replay_store

REPO = Path(__file__).resolve().parents[2]
CAMERA_SCRIPT = REPO / "scripts" / "camera.sh"

#: File magic for the formats a preview frame could be written as. Four bytes each, so
#: a compressed replay cannot match one by accident.
IMAGE_MAGIC = (b"\xff\xd8\xff\xe0", b"\x89PNG", b"GIF89a", b"GIF87a")
BASE64_RUN = re.compile(rb"[A-Za-z0-9+/=]{200,}")

#: What the test's own encoder puts in every preview frame. Nothing else in the repo
#: has it, so finding it in a file means a preview frame was written down.
PREVIEW_MARKER = b"preview-bytes"


class FakeImage:
    """A stand-in for a decoded frame: a shape, weak-referenceable, nothing else."""

    shape = (480, 640, 3)


def fake_images(count: int, *, refs: list | None = None, fps: int = DEFAULT_FPS):
    """`(t, image)` pairs the way a camera hands them over."""
    for index in range(count):
        image = FakeImage()
        if refs is not None:
            refs.append(weakref.ref(image))
        yield index / fps, image


def fake_jpeg(image: object = None) -> bytes:
    """An encoder that produces something unmistakably image-shaped.

    Real JPEG magic and a marker of its own, so the privacy sweep below finds it if
    anything ever writes a preview frame down, and no opencv needed to make one.
    """
    return b"\xff\xd8\xff\xe0" + PREVIEW_MARKER * 64 + b"\xff\xd9"


def one_part(jpeg: bytes) -> bytes:
    """One MJPEG part, exactly as the server sends it."""
    return b"".join(
        (
            f"--{BOUNDARY}\r\n".encode(),
            b"Content-Type: image/jpeg\r\n",
            f"Content-Length: {len(jpeg)}\r\n\r\n".encode(),
            jpeg,
            b"\r\n",
        )
    )


def image_offenders(root: Path) -> list[str]:
    """Every file under `root` that holds, or looks like it holds, an image."""
    offenders = []
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        data = path.read_bytes()
        where = path.relative_to(root)
        if any(magic in data for magic in IMAGE_MAGIC):
            offenders.append(f"{where}: image file magic")
        if PREVIEW_MARKER in data:
            offenders.append(f"{where}: a preview frame was written here")
        if b"data:image" in data.lower() or BASE64_RUN.search(data):
            offenders.append(f"{where}: inline image data or a long base64-like run")
    return offenders


# ----------------------------------------------------------------- who may ask


@pytest.mark.parametrize(
    "client", ["127.0.0.1", "127.0.1.1", "::1", "::ffff:127.0.0.1", "localhost"]
)
def test_this_machine_may_watch_its_own_camera(client):
    assert is_loopback(client)
    assert response_for(STREAM_PATH, client).status == 200


@pytest.mark.parametrize(
    "client",
    ["10.0.0.4", "192.168.1.20", "203.0.113.7", "2001:db8::1", "kitchen.local", "", "0.0.0.0"],
)
def test_the_preview_refuses_a_client_that_is_not_this_machine(client):
    assert not is_loopback(client)
    for path in (STREAM_PATH, HEALTH_PATH):
        refused = response_for(path, client)
        assert refused.status == 403
        assert not refused.stream
        assert b"this device only" in refused.body


def test_health_says_ok_as_json():
    reply = response_for(HEALTH_PATH, "127.0.0.1")

    assert reply.status == 200
    assert reply.content_type == "application/json"
    assert json.loads(reply.body) == {"ok": True}
    assert not reply.stream


def test_the_stream_is_multipart_jpeg():
    reply = response_for(STREAM_PATH, "127.0.0.1")

    assert reply.status == 200
    assert reply.content_type == f"multipart/x-mixed-replace; boundary={BOUNDARY}"
    assert reply.stream
    assert reply.body == b""


def test_a_query_string_and_a_trailing_slash_still_find_the_stream():
    assert response_for(f"{STREAM_PATH}?t=12", "127.0.0.1").stream
    assert response_for(HEALTH_PATH + "/", "127.0.0.1").status == 200


def test_anything_else_is_a_404():
    for path in ("/", "/index.html", "/preview.mjpg/extra", "/../etc/passwd"):
        assert response_for(path, "127.0.0.1").status == 404


def test_a_host_header_that_is_not_loopback_is_refused():
    """A page on the internet cannot point a name at 127.0.0.1 and read the frames."""
    refused = response_for(STREAM_PATH, "127.0.0.1", "preview.evil.example")

    assert refused.status == 403
    assert not refused.stream


@pytest.mark.parametrize("host", ["127.0.0.1", "127.0.0.1:8765", "localhost:8765", "[::1]:8765"])
def test_the_dashboards_own_host_header_is_allowed(host):
    assert response_for(STREAM_PATH, "127.0.0.1", host).status == 200


def test_host_name_drops_the_port_and_keeps_the_address():
    assert host_name("127.0.0.1:8765") == "127.0.0.1"
    assert host_name("[::1]:8765") == "[::1]"
    assert host_name("localhost") == "localhost"


# ------------------------------------------------------------- the current frame


def test_the_preview_holds_the_current_frame_and_nothing_older():
    preview = Preview(fake_jpeg, max_fps=0)

    preview.offer(FakeImage(), 0.0)
    first = preview.frame(after=0)
    preview.offer(FakeImage(), 1.0)
    second = preview.frame(after=1)

    assert first is not None and second is not None
    assert (first[0], second[0]) == (1, 2)
    assert preview.published == 2
    assert preview.latest() == second[1]


def test_closing_the_preview_drops_the_frame_and_lets_readers_go():
    preview = Preview(fake_jpeg, max_fps=0)
    preview.offer(FakeImage(), 0.0)
    assert preview.latest() is not None

    preview.close()

    assert preview.latest() is None  # nothing of the session is left in this process
    assert preview.closed
    assert preview.frame(after=0, timeout=0.1) is None
    preview.offer(FakeImage(), 1.0)  # and nothing can put one back
    assert preview.latest() is None


def test_a_reader_waiting_for_a_frame_gives_up_rather_than_waiting_forever():
    preview = Preview(fake_jpeg, max_fps=0)

    assert preview.frame(after=0, timeout=0.05) is None


def test_the_preview_keeps_to_its_own_frame_rate_in_session_time():
    preview = Preview(fake_jpeg, max_fps=10.0)

    for index in range(15):  # 15 fps of capture: every other frame at most
        preview.offer(FakeImage(), index / 15)

    assert preview.published == 8


def test_a_frame_that_cannot_be_encoded_turns_the_preview_off_instead_of_raising():
    def broken(image: object) -> bytes:
        raise RuntimeError("no opencv here")

    preview = Preview(broken, max_fps=0)

    preview.offer(FakeImage(), 0.0)  # must not raise: capture carries on without it

    assert preview.closed
    assert preview.latest() is None


def test_an_encoder_that_declines_a_frame_publishes_nothing():
    preview = Preview(lambda image: None, max_fps=0)

    preview.offer(FakeImage(), 0.0)

    assert preview.published == 0
    assert preview.latest() is None


def fake_cv2(resized: list):
    """Just enough of opencv for `jpeg_encoder`, so the sizing rule can be pinned
    without the capture extra installed."""

    def resize(image, size, interpolation):
        resized.append(size)
        return types.SimpleNamespace(shape=(size[1], size[0], 3))

    return types.SimpleNamespace(
        INTER_AREA=3,
        IMWRITE_JPEG_QUALITY=1,
        resize=resize,
        imencode=lambda suffix, image, params: (True, bytearray(f"{suffix}{params}".encode())),
    )


def test_jpeg_encoder_downscales_a_big_frame_to_at_most_max_side(monkeypatch):
    resized: list = []
    monkeypatch.setitem(sys.modules, "cv2", fake_cv2(resized))

    class Hd:
        shape = (1080, 1920, 3)

    jpeg = jpeg_encoder(max_side=640, quality=70)(Hd())

    assert resized == [(640, 360)]  # 1920x1080 -> 640 on the long side, same shape
    assert jpeg == b".jpg[1, 70]"  # the suffix and the quality it was given


def test_jpeg_encoder_leaves_a_small_frame_alone(monkeypatch):
    resized: list = []
    monkeypatch.setitem(sys.modules, "cv2", fake_cv2(resized))

    assert jpeg_encoder(max_side=640)(FakeImage())  # 640x480: already small enough
    assert resized == []


def test_jpeg_encoder_is_built_without_opencv():
    """Importable and built with none of the capture extra: cv2 arrives with a frame."""
    assert callable(jpeg_encoder())


# -------------------------------------------------------------- over a real socket


@pytest.fixture
def server():
    """A preview server on a port the OS picked, stopped however the test ends."""
    running = PreviewServer(Preview(fake_jpeg, max_fps=0), port=0)
    try:
        yield running
    finally:
        running.close()


def get(url: str, timeout: float = 5.0):
    """A GET of our own loopback server. No network is involved anywhere here."""
    return urllib.request.urlopen(url, timeout=timeout)


def test_the_server_is_on_loopback_and_answers_health(server):
    assert server.url == f"http://127.0.0.1:{server.port}{STREAM_PATH}"

    with get(f"http://127.0.0.1:{server.port}{HEALTH_PATH}") as answer:
        assert answer.status == 200
        assert answer.headers["Access-Control-Allow-Origin"] == "*"
        assert json.loads(answer.read()) == {"ok": True}


def test_the_server_streams_the_current_frame_as_multipart_jpeg(server):
    server.preview.offer(FakeImage(), 0.0)
    expected = one_part(fake_jpeg())

    with get(server.url) as answer:
        assert answer.status == 200
        assert answer.headers["Content-Type"] == f"multipart/x-mixed-replace; boundary={BOUNDARY}"
        assert answer.headers["Access-Control-Allow-Origin"] == "*"
        assert answer.headers["Cache-Control"] == "no-store"
        assert answer.read(len(expected)) == expected


def test_the_server_404s_anything_that_is_not_the_preview(server):
    with pytest.raises(urllib.error.HTTPError) as refused:
        get(f"http://127.0.0.1:{server.port}/secrets")

    assert refused.value.code == 404


def test_the_stream_ends_when_the_camera_does(server):
    """A tab left open on a finished session is let go of, not fed and not held."""
    server.preview.offer(FakeImage(), 0.0)
    answer = get(server.url)
    assert answer.read(len(one_part(fake_jpeg()))) == one_part(fake_jpeg())

    server.preview.close()

    assert answer.read() == b""  # the stream is over, with no frame left behind
    answer.close()


def test_closing_the_server_frees_the_port(server):
    port = server.port

    server.close()
    server.close()  # idempotent: the session can end more than one way

    replacement = PreviewServer(Preview(fake_jpeg, max_fps=0), port=port)
    try:
        assert replacement.port == port
    finally:
        replacement.close()


# --------------------------------------------------------------- off by default


def test_the_preview_is_off_unless_somebody_asked_for_it(monkeypatch):
    monkeypatch.delenv(PREVIEW_ENV, raising=False)
    assert not preview_enabled()
    assert start_preview() is None

    for value in ("", "0", "no", "false"):
        monkeypatch.setenv(PREVIEW_ENV, value)
        assert not preview_enabled()
        assert start_preview() is None


def test_camera_preview_1_turns_it_on_and_closes_it_again(monkeypatch):
    monkeypatch.setenv(PREVIEW_ENV, "1")
    monkeypatch.setenv(PORT_ENV, "0")  # a port the OS picked: tests share a machine

    running = start_preview(encode=fake_jpeg)

    assert running is not None
    try:
        with get(f"http://127.0.0.1:{running.port}{HEALTH_PATH}") as answer:
            assert json.loads(answer.read()) == {"ok": True}
    finally:
        running.close()
    assert running.preview.latest() is None


def test_the_port_comes_from_the_environment_or_the_default(monkeypatch):
    monkeypatch.delenv(PORT_ENV, raising=False)
    assert preview_port() == DEFAULT_PORT

    monkeypatch.setenv(PORT_ENV, "9001")
    assert preview_port() == 9001

    for nonsense in ("", "八", "-1", "70000"):
        monkeypatch.setenv(PORT_ENV, nonsense)
        assert preview_port() == DEFAULT_PORT


def test_a_port_already_taken_leaves_the_capture_without_a_preview(monkeypatch):
    """Never a reason for a session not to run: the capture is the product."""
    taken = PreviewServer(Preview(fake_jpeg, max_fps=0), port=0)
    try:
        monkeypatch.setenv(PREVIEW_ENV, "1")
        monkeypatch.setenv(PORT_ENV, str(taken.port))

        assert start_preview(encode=fake_jpeg) is None
    finally:
        taken.close()


# ------------------------------------------------- the capture is unchanged by it


def test_capture_writes_the_same_jsonl_with_the_preview_on_or_off(tmp_path):
    def session(out: Path, preview: Preview | None) -> None:
        record_stream(
            fake_images(6),
            out,
            landmarker=FakeLandmarker(Landmarks()),
            detector=FakeDetector(),
            source="camera",
            session_id="tea-preview",
            preview=preview,
        )

    preview = Preview(fake_jpeg, max_fps=0)
    session(tmp_path / "with.jsonl", preview)
    session(tmp_path / "without.jsonl", None)

    assert preview.published == 6  # the preview really did see every frame
    assert (tmp_path / "with.jsonl").read_bytes() == (tmp_path / "without.jsonl").read_bytes()


def test_capture_still_drops_every_frame_it_was_given_with_the_preview_on(tmp_path):
    """SPEC section 8: the preview keeps a JPEG of the current frame, never the frame."""
    refs: list[weakref.ref] = []
    preview = Preview(fake_jpeg, max_fps=0)

    record_stream(
        fake_images(3, refs=refs),
        tmp_path / "session.jsonl",
        landmarker=FakeLandmarker(Landmarks()),
        detector=FakeDetector(),
        source="camera",
        session_id="tea-preview",
        preview=preview,
    )

    gc.collect()
    assert len(refs) == 3
    assert [ref() for ref in refs] == [None, None, None]


def test_a_session_with_the_preview_on_writes_no_image_anywhere(tmp_path, monkeypatch):
    """The whole privacy promise, end to end.

    A camera session played through the pipeline with the preview on, keeping both the
    things a session can keep - the capture records (`CAMERA_RECORD`) and the skeleton
    replay (`REPLAY_DIR`) - with every relative path pointed inside `tmp_path`, so
    anything written anywhere lands where this test can see it. The preview encodes a
    frame with real JPEG magic and a marker of its own in it, and not one byte of that
    may be in any of them.
    """
    monkeypatch.chdir(tmp_path)  # catches a relative default (replays' .data/replays)
    monkeypatch.setenv("REPLAY_DIR", str(tmp_path / "replays"))
    monkeypatch.setattr("routine_watch.replays._store", None, raising=False)
    record = tmp_path / "records" / "session.jsonl"
    preview = Preview(fake_jpeg, max_fps=0)

    frames = frame_stream(
        fake_images(40),
        landmarker=FakeLandmarker(Landmarks()),
        detector=FakeDetector(),
        source="camera",
        session_id="tea-preview",
        preview=preview,
    )
    kept: list = []

    async def watch() -> list[dict]:
        stream = recorded(frames, record)  # CAMERA_RECORD: the JSONL a replay reads
        return [
            message
            async for message in camera_session_messages(_keeping(stream, kept))
        ]

    messages = asyncio.run(watch())

    # An empty session keeps no replay of its own (`live_camera`: unclear sessions are
    # not kept), so its records go into the store the way a session with an error's
    # would - the one other place a session is written down.
    get_replay_store().save(_finished_session(kept), kept)
    written = [path for path in (tmp_path / "replays").rglob("*") if path.is_file()]
    assert written, "the replay store should have written the session's skeleton"

    assert messages[-1]["type"] == "session_end"
    assert preview.published == 40  # the preview was on for the whole session
    assert record.is_file() and record.read_bytes()  # and the records were kept
    assert image_offenders(tmp_path) == []


def _keeping(stream, kept: list):
    """`stream`, with every record also kept for the replay store below."""
    for frame in stream:
        kept.append(frame)
        yield frame


def _finished_session(frames) -> Session:
    """The session those records came off, as the replay store takes it."""
    seconds = frames[-1].t if frames else 0.0
    return Session(
        session_id=frames[0].session_id,
        resident_id=DEMO_RESIDENT,
        task_id="tea",
        started_at=DEMO_NOW - timedelta(seconds=seconds),
        ended_at=DEMO_NOW,
        assisted=False,
        score=1.0,
    )


class FakeMediaPipe:
    """`MediaPipeLandmarker` without MediaPipe: sees nobody, and can be closed."""

    def __init__(self, **kwargs):
        self.closed = False

    def landmark(self, image, t):
        return Landmarks()

    def close(self):
        self.closed = True


def stub_camera(monkeypatch, frames: int):
    """`camera_frames` with the camera and MediaPipe taken out from under it."""
    landmarker = FakeMediaPipe()
    monkeypatch.setattr("routine_watch.capture.MediaPipeLandmarker", lambda **kw: landmarker)
    monkeypatch.setattr(
        "routine_watch.capture.camera_images", lambda index, fps: fake_images(frames)
    )
    return landmarker


def test_a_camera_session_offers_its_frames_to_the_preview_and_closes_it_after(monkeypatch):
    """`camera_frames` is what the dashboard opens: one camera handle, one preview,
    and the preview goes when the camera does."""
    stub_camera(monkeypatch, 5)
    server = PreviewServer(Preview(fake_jpeg, max_fps=0), port=0)
    monkeypatch.setattr("routine_watch.capture.start_preview", lambda **kwargs: server)

    records = list(camera_frames(0))

    assert [record.seq for record in records] == [0, 1, 2, 3, 4]
    assert server.preview.published == 5  # the same frames the records were read off
    assert server.preview.closed  # and nothing is left once the session is over
    assert server.preview.latest() is None


def test_a_camera_session_without_a_preview_is_the_same_session(monkeypatch):
    monkeypatch.delenv(PREVIEW_ENV, raising=False)
    stub_camera(monkeypatch, 5)

    records = list(camera_frames(0))

    assert [record.seq for record in records] == [0, 1, 2, 3, 4]


# ----------------------------------------------------------- scripts/camera.sh


def test_camera_sh_documents_the_preview_flag():
    done = subprocess.run(
        ["bash", str(CAMERA_SCRIPT), "--help"],
        capture_output=True,
        text=True,
        cwd=REPO,
        timeout=10,
    )

    assert done.returncode == 0, done.stderr
    assert "--preview" in done.stdout
    assert "this device only" in done.stdout


def test_camera_sh_turns_the_preview_on_for_the_stack_it_starts():
    """The script's own wiring: `--preview` sets the environment the API reads, and the
    dashboard is pointed at the same port (`VITE_PREVIEW_PORT`)."""
    text = CAMERA_SCRIPT.read_text(encoding="utf-8")

    assert f"export {PREVIEW_ENV}=1" in text
    for name in (PORT_ENV, "VITE_PREVIEW_PORT"):
        assert re.search(rf"export {name}\b", text), f"camera.sh should export {name}"
