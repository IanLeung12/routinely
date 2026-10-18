#!/usr/bin/env bash
# One command to watch your own camera on the dashboard (SPEC section 10, section 16
# decision B). For a laptop with a webcam; everything else about the demo runs offline.
#
#   scripts/camera.sh                      # the built-in camera on the Live screen
#   scripts/camera.sh --camera 1           # a different device
#   scripts/camera.sh --record out.jsonl   # keep the capture records too (never video)
#   scripts/camera.sh --preview            # show the camera picture under the skeleton
#
# In order: install the capture extra (MediaPipe + OpenCV), download the two MediaPipe
# task bundles if they are not here yet, check the camera opens, restart the local stack
# with the camera settings in its environment, and print the dashboard URL with the Live
# screen pointed at the camera (`/ws/live?source=camera`, `routine_watch.live_camera`).
#
# `--preview` adds the real camera picture under the skeleton on the Live screen, served
# by the capture process on 127.0.0.1 only: this device only, one frame at a time in
# memory, never stored and never sent anywhere (PREVIEW_PORT, default 8765).
#
# Stop it again with `scripts/dev.sh down`. docs/DEMO.md has the walk-through, including
# the macOS camera permission and what the screen shows without detector weights.
set -euo pipefail

CALLED_FROM=$PWD
cd "$(git rev-parse --show-toplevel)"

CAMERA=0
RECORD=""
PREVIEW=0

# The header comment above is the usage message: printed without its hashes, down to
# the first line that is not a comment.
usage() {
  awk 'NR > 1 && /^#/ { sub(/^# ?/, ""); print; next } NR > 1 { exit }' "$0"
}

while [ $# -gt 0 ]; do
  case "$1" in
    --camera)
      CAMERA=${2:?--camera needs an index, e.g. --camera 0}
      shift 2
      ;;
    --record)
      RECORD=${2:?--record needs a file, e.g. --record out.jsonl}
      shift 2
      ;;
    --preview)
      PREVIEW=1
      shift
      ;;
    -h | --help)
      usage
      exit 0
      ;;
    *)
      echo "$0: unknown argument $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

case "$CAMERA" in
  '' | *[!0-9]*)
    echo "$0: --camera takes a device index, not '$CAMERA'" >&2
    exit 2
    ;;
esac

# MediaPipe, OpenCV and the ONNX runtime: big, platform-specific, and needed only when
# there is a camera involved, which is why they are an extra and imported lazily.
# `scripts/dev.sh up` syncs every extra below, so this is only ever the first run's wait.
echo "== capture extra (mediapipe, opencv, onnxruntime)"
command -v uv >/dev/null || python3 -m pip install -q uv
(cd pipeline && uv sync -q --extra capture)

# The two task bundles MediaPipe needs on disk: free downloads, no key, no credits, not
# in git. `capture.missing_models()` is what knows where they belong and where they come
# from, so this downloads exactly the ones this machine has not got.
echo "== MediaPipe task bundles"
missing=$(cd pipeline && uv run python - <<'PY'
from routine_watch.capture import missing_models
from routine_watch.contracts import repo_root

root = repo_root()
for path, url in missing_models().items():
    print(path if path.is_absolute() else root / path, url, sep="\t")
PY
)
if [ -z "$missing" ]; then
  echo "both bundles are already here"
else
  while IFS=$'\t' read -r path url; do
    [ -n "$path" ] || continue
    echo "downloading $(basename "$path")"
    curl -fL --progress-bar --create-dirs -o "$path" "$url"
  done <<<"$missing"
fi

# Open the camera once before the dashboard does, so "no camera at that index" or a
# permission that was never granted is a line in this terminal rather than a Live screen
# that quietly falls back to the recorded demo. One record, written to a temporary file
# and deleted: landmarks and timestamps, never a frame (SPEC section 8).
echo "== camera $CAMERA"
probe=$(mktemp -t routine-watch-camera.XXXXXX)
probe_err="$probe.err"
if (cd pipeline && uv run python -m routine_watch.capture \
  --camera "$CAMERA" --out "$probe" --limit 1 --json) >/dev/null 2>"$probe_err"; then
  echo "camera $CAMERA answers"
else
  echo "warning: camera $CAMERA did not give us a frame:" >&2
  # The capture process says what is wrong on its last line ("capture: ..."); everything
  # above it is MediaPipe and OpenCV talking to themselves.
  { grep '^capture: ' "$probe_err" || tail -3 "$probe_err"; } | sed 's/^/  /' >&2
  echo "  the Live screen will show the recorded demo (Mock data) until this works." >&2
  echo "  on macOS, grant this terminal camera access: System Settings > Privacy &" >&2
  echo "  Security > Camera. On Linux/Windows, try another --camera index." >&2
fi
rm -f "$probe" "$probe_err"

# The local object detector is what turns hands near objects into steps. Without weights
# capture runs with the fake detector: skeleton and hands still stream live, and the Live
# screen says it is waiting for the object detector instead of looking stuck.
if [ -n "${DETECTOR_WEIGHTS:-}" ]; then
  # a relative path means relative to where you ran this script, not to pipeline/
  case "$DETECTOR_WEIGHTS" in
    /*|[A-Za-z]:*) ;;
    *) DETECTOR_WEIGHTS="$CALLED_FROM/$DETECTOR_WEIGHTS" ;;
  esac
  export DETECTOR_WEIGHTS
  echo "== object detector: $DETECTOR_WEIGHTS"
else
  echo "== object detector: none (export DETECTOR_WEIGHTS=models/detector.onnx to add one)"
  echo "   skeleton and hands stream live; steps show as waiting for the object detector"
fi

# The optional local preview: the capture process serves its current frame as MJPEG on
# loopback while the camera is open, and the Live screen offers a toggle to show it under
# the skeleton (`routine_watch.preview`, `web/src/live/CameraPreview.tsx`). Exported after
# the probe above, so the one-frame check never takes the port the stack is about to use.
# 127.0.0.1 only, one frame at a time in memory, never written down (SPEC section 12).
PREVIEW_PORT=${PREVIEW_PORT:-8765}
if [ "$PREVIEW" = 1 ]; then
  export CAMERA_PREVIEW=1
  export PREVIEW_PORT
  export VITE_PREVIEW_PORT=$PREVIEW_PORT  # the dashboard looks at the same port
  echo "== camera preview on 127.0.0.1:$PREVIEW_PORT (this device only, never stored)"
else
  export CAMERA_PREVIEW=0
  echo "== camera preview: off (add --preview to see the camera picture on this device)"
fi

# Where the records are kept, if they are: the API reads this when it opens the camera,
# and what it writes is the JSONL a replay reads, so a session filmed now can be played
# back offline later (`scripts/e2e.sh`, `routine_watch.replay`). Records, never video.
if [ -n "$RECORD" ]; then
  case "$RECORD" in
    /*) ;;
    *) RECORD="$CALLED_FROM/$RECORD" ;;
  esac
  export CAMERA_RECORD="$RECORD"
  echo "== keeping the capture records in $CAMERA_RECORD (landmarks and boxes, no video)"
fi

# The API reads the camera settings when it starts, so the stack is restarted rather
# than reused: an API already up was started without them.
echo "== stack"
scripts/dev.sh down >/dev/null
up=$(scripts/dev.sh up)
echo "$up"

dashboard=$(printf '%s\n' "$up" | sed -n 's/^DASHBOARD_URL=//p')
echo "LIVE_URL=${dashboard}/?source=camera&camera=${CAMERA}"
if [ "$PREVIEW" = 1 ]; then
  echo "PREVIEW_URL=http://127.0.0.1:${PREVIEW_PORT}/preview.mjpg"
fi
echo
echo "Open LIVE_URL. The Live session card is your camera: the skeleton view on the left,"
echo "the task map filling in on the right, errors as they are classified. Pick the"
echo "routine to watch above it; stop everything with scripts/dev.sh down."
if [ "$PREVIEW" = 1 ]; then
  echo
  echo "Press \"Show camera preview (this device only)\" on the skeleton view for the real"
  echo "picture under it. It is served from this machine to this machine, is not recorded,"
  echo "and reaches neither the API nor anybody you share your routines with."
fi
