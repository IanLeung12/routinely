"""Resident, drift, pattern-library and replay routes (SPEC sections 8 and 9).

Split out of `api.py`: `GET /residents`, `GET /residents/{id}`,
`GET /residents/{id}/drift`, `GET /patterns`, `GET /sessions/{id}/replay` and
`GET /residents/{id}/normal_replay` share these helpers, kept together here.
The feedback-tuned status/threshold helpers (`_tuned`, `_SUMMARY_FIELDS`) live
on `api_state.py`, imported here at module load time instead of reached back
into for on every call, so a reset there is visible to these routes without
either module rebinding the other's state.
"""

from typing import Annotated

from fastapi import APIRouter, HTTPException, Query

from . import api_state
from .contracts import SuggestedCheck
from .demo import demo_residents
from .drift import daily_scores, drift
from .evidence import EvidenceError, normal_replay_frames, replay_frames
from .patterns_library import LIBRARY as PATTERN_LIBRARY
from .patterns_library import Pattern, TimeProfile

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
