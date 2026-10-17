"""Skeleton replay for alert evidence (SPEC section 8): never video.

The dashboard's "open evidence" backs an alert with the skeleton frames around the
moment an error happened, plus a ghost layer of a normal session to compare it
against. The demo residents (`routine_watch.demo`) have no camera and so no recorded
frames of their own, so every alert replays off `tests/scenarios/tea_no_kettle` and
every ghost layer off `tests/scenarios/tea_normal` - the two frames-level scenarios -
until a frames recording exists for the demo's actual bad session
(`tea_skip_teabag_pour_twice`, written at step level today).

    from routine_watch.evidence import replay_frames
    replay_frames("mrs-k-22", t_start=10.0, t_end=14.0, fps=10)

A session id is a demo resident id and that resident's session index, `mrs-k-22`,
the same shape `routine_watch.alerts` builds a `TaskError.session_id` from.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from functools import lru_cache

from .contracts import CaptureFrame
from .demo import demo_residents
from .replay import SCENARIOS_DIR, load_scenario

#: No recorded frames are faster than this, live camera included (`routine_watch.live`).
MAX_REPLAY_FPS = 10.0

#: A requested window is widened by this much on each side before it is clipped to
#: the session, so the evidence shows a moment settling in and out, not a jump cut.
PAD_S = 2.0

#: Stand-in sources for every replay until a frames recording exists per scenario
#: (see the module docstring): the two scenarios written at frame level.
_ALERT_SCENARIO = "tea_no_kettle"
_NORMAL_SCENARIO = "tea_normal"


class EvidenceError(ValueError):
    """No such session or resident."""


def replay_frames(
    session_id: str, t_start: float, t_end: float, fps: float = MAX_REPLAY_FPS
) -> list[CaptureFrame]:
    """Skeleton frames around one window of one session, downsampled to `fps`.

    The window is padded by `PAD_S` on each side and then clipped to the session, so
    it never asks for a time the session does not have. Raises :class:`EvidenceError`
    if `session_id` is not a demo session.
    """
    if not known_session(session_id):
        raise EvidenceError(f"no such session: {session_id!r}")
    return _windowed(_scenario_frames(_ALERT_SCENARIO), t_start, t_end, fps, session_id=session_id)


def normal_replay_frames(
    resident_id: str, t_start: float, t_end: float, fps: float = MAX_REPLAY_FPS
) -> list[CaptureFrame]:
    """Skeleton frames from a normal session, for the ghost layer next to `replay_frames`.

    Raises :class:`EvidenceError` if `resident_id` is not a demo resident.
    """
    if not known_resident(resident_id):
        raise EvidenceError(f"no such resident: {resident_id!r}")
    session_id = f"{resident_id}-normal"
    return _windowed(_scenario_frames(_NORMAL_SCENARIO), t_start, t_end, fps, session_id=session_id)


def known_resident(resident_id: str) -> bool:
    """Whether `resident_id` is one of the demo residents."""
    return any(resident["id"] == resident_id for resident in demo_residents())


def known_session(session_id: str) -> bool:
    """Whether `session_id` is a real index into a demo resident's sessions."""
    parsed = _parse_session_id(session_id)
    if parsed is None:
        return False
    resident_id, index = parsed
    for resident in demo_residents():
        if resident["id"] == resident_id:
            return 0 <= index < len(resident["sessions"])
    return False


def _parse_session_id(session_id: str) -> tuple[str, int] | None:
    """``"mrs-k-22"`` -> ``("mrs-k", 22)``; anything else is not a session id."""
    resident_id, sep, index = session_id.rpartition("-")
    if not sep or not index.isdigit():
        return None
    return resident_id, int(index)


@lru_cache
def _scenario_frames(name: str) -> tuple[CaptureFrame, ...]:
    return load_scenario(SCENARIOS_DIR / name).frames


def _windowed(
    frames: Sequence[CaptureFrame],
    t_start: float,
    t_end: float,
    fps: float,
    *,
    session_id: str,
) -> list[CaptureFrame]:
    if not frames:
        return []
    capped_fps = min(fps, MAX_REPLAY_FPS) if fps > 0 else MAX_REPLAY_FPS
    session_lo, session_hi = frames[0].t, frames[-1].t
    padded_lo, padded_hi = t_start - PAD_S, t_end + PAD_S
    if padded_lo <= session_hi and padded_hi >= session_lo:
        lo = max(session_lo, padded_lo)
        hi = min(session_hi, padded_hi)
        in_window = [frame for frame in frames if lo <= frame.t <= hi]
    else:
        # The requested window (e.g. an alert's real error window) sits entirely
        # outside the stand-in recording's own timestamps: tile the recording,
        # one copy every `session_hi - session_lo`, so the window still gets
        # frames, with `t` landing inside the requested window rather than the
        # recording's native range.
        in_window = _tiled(frames, session_lo, session_hi, padded_lo, padded_hi)
    sampled = _downsample(in_window, capped_fps)
    return [frame.model_copy(update={"session_id": session_id}) for frame in sampled]


def _tiled(
    frames: Sequence[CaptureFrame],
    session_lo: float,
    session_hi: float,
    lo: float,
    hi: float,
) -> list[CaptureFrame]:
    period = session_hi - session_lo
    if period <= 0:
        return []
    first_cycle = math.floor((lo - session_lo) / period)
    last_cycle = math.floor((hi - session_lo) / period)
    tiled: list[CaptureFrame] = []
    for cycle in range(first_cycle, last_cycle + 1):
        shift = cycle * period
        for frame in frames:
            t = frame.t + shift
            if lo <= t <= hi:
                tiled.append(frame.model_copy(update={"t": t}))
    tiled.sort(key=lambda frame: frame.t)
    return tiled


def _downsample(frames: Sequence[CaptureFrame], fps: float) -> list[CaptureFrame]:
    """The first frame, then one every `1 / fps` seconds. Frames are already in order."""
    gap = 1.0 / fps
    kept: list[CaptureFrame] = []
    last: float | None = None
    for frame in frames:
        if last is None or frame.t - last >= gap - 1e-9:
            kept.append(frame)
            last = frame.t
    return kept
