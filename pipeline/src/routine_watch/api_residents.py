"""Resident, drift, pattern-library and replay routes (SPEC sections 8, 9 and 17).

Split out of `api.py`: `GET /residents`, `GET /residents/{id}`,
`GET /residents/{id}/drift`, `GET /residents/{id}/feedback`, `GET /patterns`,
`GET /sessions/{id}/replay` and `GET /residents/{id}/normal_replay` share these
helpers, kept together here.

The replay library (`GET /people/{id}/replays`, `GET /replays/{id}` and its
`DELETE`) lives here too, with the two older replay routes. It is the same subject
from the other end: those two answer "show me the window behind this error in this
alert" out of a stand-in recording (`routine_watch.evidence`), and these answer "let
me look through the attempts that went wrong" out of what was really captured and
kept (`routine_watch.replays`, SPEC section 17).

The feedback-tuned status/threshold helpers (`_tuned`, `_SUMMARY_FIELDS`) live
on `api_state.py`, imported here at module load time instead of reached back
into for on every call, so a reset there is visible to these routes without
either module rebinding the other's state.
"""

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query

from . import api_state
from .contracts import CaptureFrame, ErrorType, ReplaySummary, SuggestedCheck
from .demo import demo_residents
from .drift import daily_scores, drift
from .evidence import (
    EvidenceError,
    ensure_demo_replays,
    normal_replay_frames,
    person_of,
    replay_frames,
)
from .patterns_library import BY_ID as PATTERNS_BY_ID
from .patterns_library import LIBRARY as PATTERN_LIBRARY
from .patterns_library import Pattern, TimeProfile
from .replays import ReplayStore, downsampled, get_replay_store

router = APIRouter()


@router.get("/residents")
def list_residents() -> list[dict]:
    """Unit overview (SPEC section 9): status chip and sparkline per resident."""
    return [
        {field: resident[field] for field in api_state._SUMMARY_FIELDS}
        for resident in (api_state._tuned(resident) for resident in demo_residents())
    ]


def _resident_or_404(resident_id: str) -> dict:
    """The demo resident with this id, or a 404 (SPEC section 9)."""
    for resident in demo_residents():
        if resident["id"] == resident_id:
            return resident
    raise HTTPException(status_code=404, detail="resident not found")


@router.get("/residents/{resident_id}")
def get_resident(resident_id: str) -> dict:
    """Resident detail (SPEC section 9): sessions, care records and baseline."""
    return api_state._tuned(_resident_or_404(resident_id))


@router.get("/residents/{resident_id}/drift")
def resident_drift(resident_id: str) -> dict:
    """Daily score trend (SPEC section 8): backs the drift card with one point per day."""
    resident = _resident_or_404(resident_id)
    result = drift(daily_scores(resident["scores"]))
    return {
        "resident_id": resident_id,
        "slope_per_day": result.slope_per_day,
        "days": result.days,
        "trending": result.trending,
    }


@router.get("/residents/{resident_id}/feedback")
def resident_feedback(resident_id: str) -> dict:
    """What this resident's nurses answered, and the ranking those answers changed.

    The feedback loop (SPEC Nice to have 8) re-weights this resident's patterns from
    her own nurses' answers, which until now only showed up in how her next alert was
    ranked. This serves the record behind it: every answer newest first
    (`{alert_id, verdict, cause, at}`), the weights they add up to, and the name each
    pattern id is shown under, so the card reading this never has to keep its own copy
    of the library. A pattern nobody has answered about has no weight here and is read
    as 1.0; `"other"` is a real answer with no pattern to name.
    """
    _resident_or_404(resident_id)
    answers = api_state._feedback_store.history(resident_id)
    weights = api_state._feedback_store.pattern_weights(resident_id)
    named = {row["cause"] for row in answers if row["cause"]} | set(weights)
    return {
        "resident_id": resident_id,
        "answers": answers,
        "pattern_weights": weights,
        "pattern_names": {
            pattern_id: PATTERNS_BY_ID[pattern_id].name
            for pattern_id in sorted(named)
            if pattern_id in PATTERNS_BY_ID
        },
    }


def _time_profile_payload(time_profile: TimeProfile) -> dict:
    return {
        "onset_days": list(time_profile.onset_days),
        "tolerance_days": time_profile.tolerance_days,
        "note": time_profile.note,
    }


def _pattern_payload(pattern: Pattern) -> dict:
    """One library entry as JSON: signals, time profile, checks and source, so a
    reader can see exactly what the rule looks for, never a verdict on a resident.
    """
    return {
        "pattern_id": pattern.pattern_id,
        "name": pattern.name,
        "signals": dict(pattern.signals),
        "time_profile": _time_profile_payload(pattern.time_profile),
        "checks": [
            check.value if isinstance(check, SuggestedCheck) else check
            for check in pattern.checks
        ],
        "urgency": pattern.urgency.value,
        "source": pattern.source,
    }


@router.get("/patterns")
def list_patterns() -> list[dict]:
    """The pattern library (SPEC §7.5): every pattern's signals, time profile, checks
    and source, read-only and separate from the demo path - a cited rules library,
    not a model guess.
    """
    return [_pattern_payload(pattern) for pattern in PATTERN_LIBRARY]


@router.get("/sessions/{session_id}/replay")
def session_replay(
    session_id: str,
    t_start: Annotated[float, Query(ge=0.0)],
    t_end: Annotated[float, Query(ge=0.0)],
    fps: Annotated[float, Query(gt=0)] = 10.0,
) -> dict:
    """Skeleton-frame evidence for one window of one session (SPEC section 8)."""
    try:
        frames = replay_frames(session_id, t_start, t_end, fps=fps)
    except EvidenceError:
        raise HTTPException(status_code=404, detail="session not found") from None
    return {
        "session_id": session_id,
        "frames": [frame.model_dump(mode="json") for frame in frames],
    }


@router.get("/residents/{resident_id}/normal_replay")
def resident_normal_replay(
    resident_id: str,
    t_start: Annotated[float, Query(ge=0.0)],
    t_end: Annotated[float, Query(ge=0.0)],
) -> dict:
    """A normal session's skeleton frames, for the evidence view's ghost layer."""
    try:
        frames = normal_replay_frames(resident_id, t_start, t_end)
    except EvidenceError:
        raise HTTPException(status_code=404, detail="resident not found") from None
    return {
        "resident_id": resident_id,
        "frames": [frame.model_dump(mode="json") for frame in frames],
    }


@router.get("/people/{person_id}/replays")
def person_replays(
    person_id: str,
    error_type: Annotated[ErrorType | None, Query(alias="type")] = None,
    since: datetime | None = None,
) -> dict:
    """One person's kept replays, newest first (SPEC section 17).

    Every session of theirs that had an error and is still inside the retention
    window, as rows with no frames in them, plus the one clean session kept as the
    comparison. `?type=` keeps the attempts that had an error of that kind and
    `?since=` the ones from an ISO 8601 instant onwards; neither touches the
    comparison, which is what all of them are looked at against.

    A person with nothing kept gets an empty library rather than a 404: who this unit
    knows is not a question for a route that answers to a person id off a URL, and
    somebody who has never gone wrong in front of a camera has an empty library in
    exactly the same way.
    """
    store = get_replay_store()
    ensure_demo_replays(person_id, store)
    return {
        "person_id": person_id,
        "replays": [
            summary.model_dump(mode="json")
            for summary in store.list(person_id, since=since, error_type=error_type)
        ],
        "normal": _dumped(store.normal_for(person_id)),
    }


@router.get("/replays/{session_id}")
def session_replay_record(
    session_id: str,
    t_start: Annotated[float | None, Query(ge=0.0)] = None,
    t_end: Annotated[float | None, Query(ge=0.0)] = None,
    fps: Annotated[float | None, Query(gt=0)] = None,
) -> dict:
    """One kept replay: its frames and a marker on each of its errors (SPEC §17, §8).

    The whole session by default, which is what a player opening an attempt wants.
    `?t_start=`, `?t_end=` and `?fps=` trim it to one error's moment and thin it
    further, the way `GET /sessions/{id}/replay` does for an alert - except that
    these are the frames the session really left behind rather than a stand-in for
    them, and the markers come with it either way, so the player can jump between
    errors without asking again. 404s for a session nothing was kept for.
    """
    store = get_replay_store()
    _seed_for(session_id, store)
    replay = store.get(session_id)
    if replay is None:
        raise HTTPException(status_code=404, detail="replay not found")
    frames = _window(replay.frames, t_start, t_end, fps)
    return replay.model_copy(update={"frames": frames}).model_dump(mode="json")


@router.delete("/replays/{session_id}")
def delete_replay(session_id: str) -> dict:
    """Delete one kept replay (SPEC section 17: the person can delete any of theirs).

    Deleting is deleting: the frames and the markers go, and nothing regenerates
    them. 404s for a session nothing was kept for, so a second delete says so rather
    than claiming to have deleted something twice.
    """
    store = get_replay_store()
    _seed_for(session_id, store)
    if not store.delete(session_id):
        raise HTTPException(status_code=404, detail="replay not found")
    return {"session_id": session_id, "deleted": True}


def _seed_for(session_id: str, store: ReplayStore) -> None:
    """Build the demo library this session would be part of, if it is a demo
    person's: their history was never in front of a camera, so their replays are
    generated the first time anybody asks for one (`routine_watch.evidence`)."""
    person_id = person_of(session_id)
    if person_id is not None:
        ensure_demo_replays(person_id, store)


def _dumped(summary: ReplaySummary | None) -> dict | None:
    """One library row as JSON, or null where there is no row to send."""
    return None if summary is None else summary.model_dump(mode="json")


def _window(
    frames: list[CaptureFrame],
    t_start: float | None,
    t_end: float | None,
    fps: float | None,
) -> list[CaptureFrame]:
    """The frames inside the window asked for, thinned to `fps` if one was asked for.

    Both ends are inclusive and both are optional: asking for neither is asking for
    the session. The replay was already thinned when it was kept
    (`replays.REPLAY_FPS`), so `fps` only ever takes frames away.
    """
    kept = [
        frame
        for frame in frames
        if (t_start is None or frame.t >= t_start) and (t_end is None or frame.t <= t_end)
    ]
    return downsampled(kept, fps) if fps else kept
