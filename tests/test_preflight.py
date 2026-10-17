"""scripts/preflight.sh --dry-run: lists every step, never runs for real, and
refuses outright if LIVE_API=1 (it must never call a paid API, SPEC §13)."""

import os
import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / "scripts" / "preflight.sh"

STEPS = [
    "LIVE_API unset and OFFLINE_MODE=true",
    "scripts/dev.sh up",
    "scripts/smoke.sh",
    "scripts/e2e.sh",
    "POST /demo/reset",
    "GET /residents",
]


def run_preflight(*args, env=None):
    full_env = dict(os.environ)
    if env:
        full_env.update(env)
    return subprocess.run(
        ["bash", str(SCRIPT), *args],
        capture_output=True,
        text=True,
        cwd=REPO,
        env=full_env,
        timeout=30,
    )


def test_dry_run_lists_every_step():
    done = run_preflight("--dry-run", env={"LIVE_API": "0"})

    assert done.returncode == 0, done.stderr
    output = done.stdout + done.stderr
    for step in STEPS:
        assert step in output, f"{step!r} missing from preflight --dry-run output"


def test_dry_run_never_shells_out_to_dev_or_smoke_or_e2e():
    """A dry run must not actually bring the stack up or hit the network."""
    done = run_preflight("--dry-run", env={"LIVE_API": "0"})

    assert done.returncode == 0, done.stderr
    assert "ready to demo" not in done.stdout


def test_refuses_to_run_when_live_api_is_set():
    done = run_preflight("--dry-run", env={"LIVE_API": "1"})

    assert done.returncode != 0
    assert "✗" in done.stdout + done.stderr
    assert "LIVE_API" in done.stdout + done.stderr


def test_refuses_for_real_run_too_when_live_api_is_set():
    done = run_preflight(env={"LIVE_API": "1"})

    assert done.returncode != 0
    assert "LIVE_API" in done.stdout + done.stderr
    # Must fail before touching dev.sh/smoke.sh/e2e.sh.
    assert "ready to demo" not in done.stdout
