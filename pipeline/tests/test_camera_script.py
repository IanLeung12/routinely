"""scripts/camera.sh argument handling (T356): only the parts that run before any
pip install, MediaPipe download or camera probe (SPEC section 10, decision B).
These must never shell out to uv sync, the capture process or scripts/dev.sh."""

import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / "scripts" / "camera.sh"

#: The first thing the script does once argument parsing is done: its
#: presence means a test let the script reach the pip install / download / camera
#: steps it must never touch.
_NEVER_REACHED = "== capture extra"


def run_camera(*args):
    done = subprocess.run(
        ["bash", str(SCRIPT), *args],
        capture_output=True,
        text=True,
        cwd=REPO,
        timeout=5,
    )
    assert _NEVER_REACHED not in (done.stdout + done.stderr)
    return done


def test_help_prints_header_usage_and_exits_zero():
    done = run_camera("--help")

    assert done.returncode == 0, done.stderr
    assert "scripts/camera.sh" in done.stdout
    assert "the built-in camera on the Live screen" in done.stdout


def test_short_help_flag_also_works():
    done = run_camera("-h")

    assert done.returncode == 0, done.stderr
    assert "scripts/camera.sh" in done.stdout


def test_unknown_argument_exits_2_with_message():
    done = run_camera("--bogus")

    assert done.returncode == 2
    assert "unknown argument --bogus" in done.stderr


@pytest.mark.parametrize("camera", ["abc", "-1", "1.5"])
def test_non_numeric_camera_exits_2_with_message(camera):
    done = run_camera("--camera", camera)

    assert done.returncode == 2
    assert "--camera" in done.stderr
    assert camera in done.stderr


@pytest.mark.parametrize("flag", ["--camera", "--record"])
def test_missing_value_fails(flag):
    done = run_camera(flag)

    assert done.returncode != 0
    assert flag in done.stderr


@pytest.mark.parametrize("flag", ["--camera", "--record"])
def test_empty_value_fails(flag):
    done = run_camera(flag, "")

    assert done.returncode != 0
    assert flag in done.stderr


def test_missing_value_as_last_argument_also_fails():
    """`--camera` with nothing after it is an unset $2, not an empty string."""
    done = run_camera("--record", "out.jsonl", "--camera")

    assert done.returncode != 0
