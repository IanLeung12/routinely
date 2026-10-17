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

Both recordings were written as object boxes with no landmarks, so each frame served
from here is given a stand-in body reaching into the hand box the recording already
tracks (`routine_watch.stick_figure`): made up like the frames around it, and the only
way the ghost layer has a skeleton to lay over anything.

A session id is a demo resident id and that resident's session index, `mrs-k-22`, the
shape `routine_watch.alerts` builds a `TaskError.session_id` from - or, for a session
played live this run, the id it was recorded with (`routine_watch.session_log`), which
it keeps into the alert and so into the replay asked for here.

The same stand-in recording fills the demo's **replay library** (SPEC section 17,
`routine_watch.replays`): a demo person's history is a fortnight of sessions nobody
filmed, so `ensure_demo_replays` generates a replay for the most recent of their
sessions that had errors - the frames tiled out of that recording to the length the
session says it ran for, the markers from the same placeholder errors the alert shows
(`alerts.task_errors`) - plus their most recent clean session as the comparison. A
session this process really watched is never generated over: it brought its own
frames, and those are the ones its replay keeps.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from datetime import datetime, timedelta
from functools import lru_cache

from .alerts import session_id_for, task_errors
from .contracts import CaptureFrame, ObjectLabel, Session, TaskError
from .demo import demo_residents
from .replay import SCENARIOS_DIR, load_scenario
from .replays import ReplayStore, get_replay_store
from .stick_figure import REST, reaching_for, reaching_into

#: No recorded frames are faster than this, live camera included (`routine_watch.live`).
MAX_REPLAY_FPS = 10.0

#: How many of a demo person's sessions with errors get a generated replay, newest
#: first: enough that their library is worth opening in the demo, few enough that
#: building it is a handful of milliseconds (SPEC section 17).
DEMO_REPLAYS_PER_PERSON = 4

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
    """Whether `session_id` is one of a demo resident's sessions.

    Either shape counts: the `resident-index` id the synthetic history is given
    (`alerts.session_id_for`), or the id a live session was recorded with, which it
    keeps all the way into its alert's evidence (T155) and which is nobody's index.
    """
    residents = demo_residents()
    if any(
        session.get("session_id") == session_id
        for resident in residents
        for session in resident["sessions"]
    ):
        return True
    parsed = _parse_session_id(session_id)
    if parsed is None:
        return False
    resident_id, index = parsed
    for resident in residents:
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
    return tuple(_with_skeleton(frame) for frame in load_scenario(SCENARIOS_DIR / name).frames)


def _with_skeleton(frame: CaptureFrame) -> CaptureFrame:
    """The frame with a stand-in body skeleton in it, if it has none of its own.

    The frame-level scenarios were written as object boxes only - they are what the
    recogniser is tested against, and it reads boxes - so the evidence view had no
    skeleton to replay and the ghost layer, which draws poses and nothing else, drew
    nothing at all (T207). The figure reaches into the frame's own `hand` box, the
    hand the recording already tracks, so the skeleton moves with the recorded hand
    instead of inventing a second one somewhere else, and its landmarks stay inside
    that box: a frame read by the recogniser still says exactly what it did before.
    """
    if frame.poses or frame.hands:
        return frame  # a real recording brings its own landmarks
    hand_box = next(
        (found.box for found in frame.objects if found.label is ObjectLabel.HAND), None
    )
    pose, hand = reaching_into(hand_box) if hand_box else reaching_for(REST)
    return frame.model_copy(update={"poses": [pose], "hands": [hand]})


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


# ------------------------------------------------- the demo's replay library


#: Which demo people have had their generated replays built this run, so a library
#: is built once rather than on every request - and so a replay somebody deleted
#: stays deleted (SPEC section 17: the person can delete any of theirs).
_seeded: set[str] = set()


def person_of(session_id: str) -> str | None:
    """The demo person a session id belongs to, or None if it is nobody's.

    Either shape `known_session` takes: the `person-index` id the synthetic history
    is given, or the id a session played live was recorded with, which is whichever
    recording it was played out of and so names no person at all.
    """
    parsed = _parse_session_id(session_id)
    if parsed is None:
        return None
    person_id, _index = parsed
    return person_id if known_resident(person_id) else None


def ensure_demo_replays(person_id: str, store: ReplayStore | None = None) -> None:
    """Build this demo person's replay library, once, if they are a demo person.

    Their history is synthetic (`routine_watch.demo`), so nothing has ever captured
    a frame of it and their library would be empty on a stand with nobody making tea
    (SPEC section 17). This fills it with the generated replays below. A real session
    - one this process watched, which saved its own replay with its own frames - is
    left exactly as it is.
    """
    kept = store or get_replay_store()
    if person_id in _seeded or not known_resident(person_id):
        return
    _seeded.add(person_id)
    for session, frames, errors in demo_replays(person_id):
        if kept.get(session.session_id) is None:
            kept.save(session, frames, errors)


def reset_demo_replays(store: ReplayStore | None = None) -> None:
    """Empty the replay library and forget which demo people have had one built, so
    the next ask builds it again: what `/demo/reset` calls between rehearsals."""
    (store or get_replay_store()).reset()
    _seeded.clear()


def demo_replays(person_id: str) -> list[tuple[Session, list[CaptureFrame], list[TaskError]]]:
    """What to keep for one demo person: their recent bad sessions, then a clean one.

    The bad ones are the `DEMO_REPLAYS_PER_PERSON` most recent sessions of theirs
    that had an error, newest last; the clean one is their most recent session with
    none, which the store keeps as the comparison. Each comes with the frames
    `generated_frames` makes for it and the errors `alerts.task_errors` reads off it,
    which are the same placeholder step-and-time ones their alert lists, so a marker
    here and an error there name the same moment.
    """
    resident = next((one for one in demo_residents() if one["id"] == person_id), None)
    if resident is None:
        return []
    bad: list[tuple[Session, list[CaptureFrame], list[TaskError]]] = []
    clean: tuple[Session, list[CaptureFrame], list[TaskError]] | None = None
    for index, session in enumerate(resident["sessions"]):
        built = _demo_session(person_id, index, session)
        if sum(session["errors"].values()):
            bad.append(built)
        else:
            clean = built
    return [*bad[-DEMO_REPLAYS_PER_PERSON:], *([clean] if clean else [])]


def _demo_session(
    person_id: str, index: int, session: dict
) -> tuple[Session, list[CaptureFrame], list[TaskError]]:
    """One session of a demo person's history as a replay's three parts."""
    session_id = session_id_for(person_id, index, session)
    started_at = datetime.fromisoformat(session["ts"])
    duration_s = float(session["duration_s"])
    record = Session(
        session_id=session_id,
        resident_id=person_id,
        task_id=session["task"],
        started_at=started_at,
        ended_at=started_at + timedelta(seconds=duration_s),
        assisted=session["assisted"],
    )
    return record, generated_frames(session_id, duration_s), task_errors(session_id, session)


def generated_frames(session_id: str, duration_s: float) -> list[CaptureFrame]:
    """Made-up frames for a whole session nobody filmed, from t=0 to `duration_s`.

    The stand-in recording (`_ALERT_SCENARIO`, with the stand-in body every frame
    served from here gets) laid end to end until the session is covered, so a
    four-minute attempt plays for four minutes instead of stopping when the
    twelve-second recording runs out. Its own rate is what the frames keep - two a
    second, the rate the frame-level recordings were written at and the one
    `live._synthetic_frames` makes its frames up at - which is inside the ten a
    second a replay is thinned to (`replays.REPLAY_FPS`).
    """
    source = _scenario_frames(_ALERT_SCENARIO)
    if duration_s <= 0 or len(source) < 2:
        return []
    start = source[0].t
    period = source[-1].t - start
    step = period / (len(source) - 1)
    frames: list[CaptureFrame] = []
    offset = 0.0
    while offset <= duration_s:
        for frame in source:
            t = round(offset + frame.t - start, 3)
            if t > duration_s:
                return frames
            frames.append(
                frame.model_copy(
                    update={"session_id": session_id, "seq": len(frames), "t": t}
                )
            )
        offset += period + step
    return frames
