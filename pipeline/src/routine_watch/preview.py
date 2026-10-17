"""The optional local camera preview (SPEC sections 12 and 16).

The dashboard draws skeletons, because that is all a capture record holds (SPEC
section 8). Standing in the kitchen while you frame the camera, that is not quite
enough: you cannot tell whether the kettle is in shot, or whether the person is lit
well enough for MediaPipe to see their hands. So the capture machine may show *itself*
its own camera picture, with the skeleton drawn over it:

    CAMERA_PREVIEW=1 scripts/camera.sh --preview
    # -> PREVIEW_URL=http://127.0.0.1:8765/preview.mjpg

**It never leaves the machine the camera is on, and it is never stored.** The server
binds `127.0.0.1` and nothing else, refuses any client that is not this machine talking
to itself, holds exactly one JPEG - the frame being shown right now - in memory, and has
no path to a file: `Preview` has one `bytes` field, which the next frame overwrites and
closing drops. Nothing here writes, and nothing here is reachable from the API, the
store, a replay or a supervisor's browser; the records those keep are landmarks, boxes
and timestamps, exactly as before.

Off unless somebody asked for it: `CAMERA_PREVIEW=1` (`scripts/camera.sh --preview`), on
`PREVIEW_PORT`, default 8765.

**One camera handle.** The frames come from the capture loop that is already running
(`capture.frame_stream`), not from a second reader - Windows cannot open a webcam twice,
and a second reader would see different frames from the ones the skeleton was read off.
The loop hands each frame over as it has it (`Preview.offer`), which downscales it to
`MAX_SIDE` and encodes a JPEG, at most `MAX_FPS` of them a second; the frame itself is
dropped by the loop a line later, as it always was.

Three pieces, so the HTTP part is testable without a socket and the whole module
imports with none of the capture extra installed:

`response_for`
    The pure bit: a path and who asked, in; the reply, out. Non-loopback clients get
    403 here, which is what `tests/test_preview.py` holds the server to.
`Preview`
    The current frame as JPEG bytes, shared between the capture loop that offers them
    and the browser threads that wait for them.
`PreviewServer`
    A `ThreadingHTTPServer` on loopback, started and stopped with the camera.
"""

from __future__ import annotations

import ipaddress
import json
import logging
import os
import threading
from collections.abc import Callable
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

STAGE = "preview"

logger = logging.getLogger(__name__)

#: Set to 1 for a local preview. Anything else - unset, 0, empty - and no socket is
#: opened at all (`scripts/camera.sh --preview` is what sets it).
PREVIEW_ENV = "CAMERA_PREVIEW"

#: Which loopback port the preview listens on, when it is on.
PORT_ENV = "PREVIEW_PORT"
DEFAULT_PORT = 8765

#: Loopback and nothing else. Not configurable on purpose: a preview reachable from
#: the network is a different product with a different privacy promise.
HOST = "127.0.0.1"

#: Longest side of a preview frame, in pixels. Enough to frame a kitchen on, small
#: enough that encoding one is cheaper than the two models that just read it.
MAX_SIDE = 640

#: Frames a second handed to the browser, at most, measured in session time: a
#: preview is for aiming a camera, and the capture loop's own rate is for the pipeline.
MAX_FPS = 10.0

#: JPEG quality for a preview frame. Not an archive; nothing keeps it.
JPEG_QUALITY = 70

HEALTH_PATH = "/health"
STREAM_PATH = "/preview.mjpg"

#: The multipart boundary an MJPEG stream separates its frames with.
BOUNDARY = "routine-watch-frame"

#: How long a connected browser waits for the next frame before the stream is ended.
#: A camera that has stopped should close the tab's connection rather than hold it.
IDLE_TIMEOUT_S = 5.0

#: The dashboard is served from another port (5173), so its `fetch` of `/health` is
#: cross-origin. The preview is loopback-only, so "any origin" here still means "any
#: page on this machine".
_CORS = (("Access-Control-Allow-Origin", "*"),)

_JSON = "application/json"
_TEXT = "text/plain; charset=utf-8"
_MJPEG = f"multipart/x-mixed-replace; boundary={BOUNDARY}"


# ----------------------------------------------------------------- who may ask


def is_loopback(host: str) -> bool:
    """Is `host` this machine talking to itself?

    `127.0.0.0/8`, `::1`, an IPv4-mapped loopback address (`::ffff:127.0.0.1`, which is
    what a dual-stack socket reports) and the literal name `localhost`. Anything else,
    including a name that would have to be resolved to find out, is not.
    """
    name = host.strip().strip("[]")
    if name.lower() == "localhost":
        return True
    try:
        address = ipaddress.ip_address(name)
    except ValueError:
        return False
    mapped = getattr(address, "ipv4_mapped", None)
    return (mapped or address).is_loopback


def host_name(header: str) -> str:
    """The host out of a `Host:` header, without its port (`[::1]:8765` included)."""
    value = header.strip()
    if value.startswith("["):
        return value.partition("]")[0] + "]"
    return value.rpartition(":")[0] if value.count(":") == 1 else value


@dataclass(frozen=True)
class Response:
    """One reply. `stream` means "and then frames, until somebody goes away"."""

    status: int
    content_type: str
    body: bytes = b""
    stream: bool = False


def response_for(path: str, client: str, host: str = "") -> Response:
    """The reply to one `GET`: the whole of what this server will answer.

    `client` is the address the request came from and `host` the `Host:` header it
    carried. Both must be loopback: the socket is bound to `127.0.0.1`, so the first is
    belt and braces, and the second is what stops a page on the internet pointing a
    name that resolves to `127.0.0.1` at this port and reading the frames through the
    browser of whoever opens it.
    """
    if not is_loopback(client):
        return Response(403, _TEXT, b"the camera preview is for this device only\n")
    if host and not is_loopback(host_name(host)):
        return Response(403, _TEXT, b"the camera preview answers on 127.0.0.1 only\n")
    route = path.partition("?")[0].rstrip("/") or "/"
    if route == HEALTH_PATH:
        return Response(200, _JSON, json.dumps({"ok": True}).encode("utf-8"))
    if route == STREAM_PATH:
        return Response(200, _MJPEG, stream=True)
    return Response(404, _TEXT, b"the camera preview serves /preview.mjpg and /health\n")


# ------------------------------------------------------------- the current frame


def jpeg_encoder(
    max_side: int = MAX_SIDE, quality: int = JPEG_QUALITY
) -> Callable[[Any], bytes | None]:
    """One capture frame as a small JPEG, in memory.

    opencv is imported on the first frame rather than here, the way the rest of capture
    imports it, so this module stays importable - and testable, with an encoder of the
    test's own - with none of the capture extra installed.
    """

    def encode(image: Any) -> bytes | None:
        import cv2

        height, width = image.shape[:2]
        side = max(height, width)
        if side > max_side:
            scale = max_side / side
            image = cv2.resize(
                image,
                (max(1, round(width * scale)), max(1, round(height * scale))),
                interpolation=cv2.INTER_AREA,
            )
        ok, buffer = cv2.imencode(".jpg", image, [int(cv2.IMWRITE_JPEG_QUALITY), int(quality)])
        return bytes(buffer) if ok else None

    return encode


class Preview:
    """The frame being shown right now, as JPEG bytes, and nothing else.

    The capture loop offers frames (`offer`, on the capture thread) and the browser
    threads wait for them (`frame`). One `bytes` field: a new frame replaces the one
    before it, and `close` drops it, so what this holds is never more than the current
    frame and after the camera has gone it is nothing.
    """

    def __init__(
        self,
        encode: Callable[[Any], bytes | None] | None = None,
        *,
        max_fps: float = MAX_FPS,
    ) -> None:
        self._encode = encode if encode is not None else jpeg_encoder()
        self._period = 1.0 / max_fps if max_fps > 0 else 0.0
        self._ready = threading.Condition()
        self._jpeg: bytes | None = None
        self._seq = 0
        self._last_t: float | None = None
        self._closed = False
        #: How many frames have been encoded for a browser. For tests and the log.
        self.published = 0

    def offer(self, image: Any, t: float) -> None:
        """Hand the capture loop's current frame over, if it is time for one.

        `t` is session time, so the rate is read off the frames rather than the clock,
        and the loop keeps its own frame rate whatever the preview does with it.

        Never raises. A preview that cannot encode - no opencv, a frame opencv will not
        take - turns itself off and says so once; it is a convenience for whoever is
        standing at the camera, and it does not get to stop a capture.
        """
        if self._closed:
            return
        since = None if self._last_t is None else t - self._last_t
        if since is not None and 0.0 <= since < self._period - 1e-9:
            return
        self._last_t = t
        try:
            jpeg = self._encode(image)
        except Exception as exc:  # whatever it is, the capture carries on without it
            logger.warning("camera preview off: this frame could not be encoded (%s)", exc)
            self.close()
            return
        if not jpeg:
            return
        with self._ready:
            self._jpeg = jpeg
            self._seq += 1
            self.published += 1
            self._ready.notify_all()

    def frame(self, after: int = 0, timeout: float = IDLE_TIMEOUT_S) -> tuple[int, bytes] | None:
        """The first frame newer than sequence `after`, or `None`.

        `None` means there is nothing more to send: the camera has gone, or no frame
        arrived within `timeout`, which for a browser holding the stream open is the
        same thing.
        """
        with self._ready:
            if not self._ready.wait_for(lambda: self._closed or self._seq > after, timeout):
                return None
            if self._closed or self._jpeg is None:
                return None
            return self._seq, self._jpeg

    def latest(self) -> bytes | None:
        """The current frame, if there is one. `None` once the camera has gone."""
        with self._ready:
            return self._jpeg

    @property
    def closed(self) -> bool:
        return self._closed

    def close(self) -> None:
        """The camera has gone: drop the frame and let every reader go."""
        with self._ready:
            self._closed = True
            self._jpeg = None  # nothing of the session is left in this process
            self._ready.notify_all()


# ------------------------------------------------------------------ the server


class _Server(ThreadingHTTPServer):
    """A `ThreadingHTTPServer` that knows which `Preview` it is serving."""

    daemon_threads = True  # a browser blocked on a frame cannot hold the process open
    preview: Preview


class _Handler(BaseHTTPRequestHandler):
    """`response_for`, over a socket."""

    protocol_version = "HTTP/1.1"
    server_version = "RoutineWatchPreview/1.0"
    sys_version = ""

    def do_GET(self) -> None:  # BaseHTTPRequestHandler's spelling
        reply = response_for(self.path, self.client_address[0], self.headers.get("Host", ""))
        if not self._reply(reply):
            return
        if reply.stream:
            self._frames()

    def _reply(self, reply: Response) -> bool:
        try:
            self.send_response(reply.status)
            self.send_header("Content-Type", reply.content_type)
            for name, value in _CORS:
                self.send_header(name, value)
            self.send_header("Cache-Control", "no-store")
            if reply.stream:
                # No length to give: the stream ends when the camera or the tab does.
                self.send_header("Connection", "close")
                self.close_connection = True
            else:
                self.send_header("Content-Length", str(len(reply.body)))
            self.end_headers()
            if reply.body:
                self.wfile.write(reply.body)
        except OSError:
            return False  # the client went away mid-handshake
        return True

    def _frames(self) -> None:
        """The current frame, again and again, as multipart JPEG parts."""
        seq = 0
        while True:
            nxt = self.server.preview.frame(after=seq)  # type: ignore[attr-defined]
            if nxt is None:
                return  # the camera stopped, or this tab is no longer being fed
            seq, jpeg = nxt
            part = b"".join(
                (
                    f"--{BOUNDARY}\r\n".encode(),
                    b"Content-Type: image/jpeg\r\n",
                    f"Content-Length: {len(jpeg)}\r\n\r\n".encode(),
                    jpeg,
                    b"\r\n",
                )
            )
            try:
                self.wfile.write(part)
            except OSError:
                return  # the tab was closed; nothing is being sent anywhere any more

    def log_message(self, format: str, *args: Any) -> None:
        """Not an access log: the API's own log says the preview is up, once."""
        logger.debug("preview: " + format, *args)


class PreviewServer:
    """The loopback MJPEG server, and the frame it is serving.

    Started with the camera and stopped with it (`capture.camera_frames`), so a preview
    exists for exactly as long as something is being filmed.
    """

    def __init__(self, preview: Preview, port: int = DEFAULT_PORT) -> None:
        self.preview = preview
        self._http = _Server((HOST, port), _Handler)
        self._http.preview = preview
        self.port = self._http.server_address[1]
        self.url = f"http://{HOST}:{self.port}{STREAM_PATH}"
        self._thread = threading.Thread(
            target=self._http.serve_forever, name="routine-watch-preview", daemon=True
        )
        self._thread.start()

    def close(self) -> None:
        """Drop the frame, then the socket. Safe to call twice."""
        self.preview.close()  # readers let go before the listener does
        self._http.shutdown()
        self._http.server_close()
        self._thread.join(timeout=2.0)

    def __enter__(self) -> PreviewServer:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()


# ------------------------------------------------------------- on, or (by default) off


def preview_enabled(env: dict[str, str] | None = None) -> bool:
    """Did somebody ask for a preview? `CAMERA_PREVIEW=1`, and nothing else by default."""
    value = (os.environ if env is None else env).get(PREVIEW_ENV, "")
    return value.strip().lower() in {"1", "true", "yes", "on"}


def preview_port(env: dict[str, str] | None = None) -> int:
    """`PREVIEW_PORT`, or `DEFAULT_PORT`, ignoring anything that is not a port."""
    try:
        port = int((os.environ if env is None else env)[PORT_ENV])
    except (KeyError, ValueError):
        return DEFAULT_PORT
    return port if 0 <= port <= 65535 else DEFAULT_PORT


def start_preview(
    *, encode: Callable[[Any], bytes | None] | None = None, port: int | None = None
) -> PreviewServer | None:
    """A running `PreviewServer`, or `None` if nobody asked for one.

    `None` is also the answer when the port is taken or the socket will not bind: the
    capture carries on without a preview, which is the normal way everything runs.
    """
    if not preview_enabled():
        return None
    wanted = preview_port() if port is None else port
    try:
        server = PreviewServer(Preview(encode=encode), wanted)
    except OSError as exc:
        logger.warning("no camera preview on port %s: %s", wanted, exc)
        return None
    logger.info("camera preview at %s - this device only, nothing stored", server.url)
    return server
