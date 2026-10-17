"""Skeleton replay for alert evidence (SPEC section 8): frames, never video."""

import json
from itertools import pairwise

import pytest
from fastapi.testclient import TestClient
from jsonschema import Draft202012Validator

from routine_watch import evidence
from routine_watch.api import app
from routine_watch.contracts import CaptureFrame, ObjectLabel, repo_root
from routine_watch.demo import demo_residents
from routine_watch.evidence import (
    MAX_REPLAY_FPS,
    PAD_S,
    EvidenceError,
    known_resident,
    known_session,
    normal_replay_frames,
    replay_frames,
)
from routine_watch.recogniser import recognise
from routine_watch.replay import SCENARIOS_DIR, load_scenario

MRS_K = "mrs-k"
#: The flagged resident's latest session (`routine_watch.alerts._qualifying_sessions`).
LATEST_SESSION = f"{MRS_K}-22"

#: `tests/scenarios/tea_no_kettle`: 25 frames, t=0.0 .. t=12.0, 0.5s apart.
SESSION_T_START, SESSION_T_END = 0.0, 12.0

CAPTURE_FRAME_SCHEMA = json.loads(
    (repo_root() / "contracts" / "capture_frame.schema.json").read_text()
)


def _frame_validator() -> Draft202012Validator:
    Draft202012Validator.check_schema(CAPTURE_FRAME_SCHEMA)
    return Draft202012Validator(CAPTURE_FRAME_SCHEMA)


def test_latest_session_is_known() -> None:
    assert known_session(LATEST_SESSION)
    assert known_resident(MRS_K)


def test_unknown_session_and_resident_are_not_known() -> None:
    assert not known_session("does-not-exist-0")
    assert not known_session(MRS_K)  # no trailing index
    assert not known_resident("does-not-exist")


def test_replay_frames_rejects_an_unknown_session() -> None:
    with pytest.raises(EvidenceError):
        replay_frames("does-not-exist-0", t_start=0.0, t_end=1.0)


def test_normal_replay_frames_rejects_an_unknown_resident() -> None:
    with pytest.raises(EvidenceError):
        normal_replay_frames("does-not-exist", t_start=0.0, t_end=1.0)


def test_frames_are_padded_by_two_seconds_either_side() -> None:
    frames = replay_frames(LATEST_SESSION, t_start=4.0, t_end=5.0)

    times = [frame.t for frame in frames]
    assert min(times) == pytest.approx(2.0)
    assert max(times) == pytest.approx(7.0)


def test_padded_window_is_clipped_to_the_session() -> None:
    frames = replay_frames(LATEST_SESSION, t_start=-5.0, t_end=20.0)

    assert min(frame.t for frame in frames) == pytest.approx(SESSION_T_START)
    assert max(frame.t for frame in frames) == pytest.approx(SESSION_T_END)


def test_fps_cap_is_honoured_even_for_a_very_high_request() -> None:
    frames = replay_frames(LATEST_SESSION, t_start=0.0, t_end=12.0, fps=1_000.0)

    min_gap = 1.0 / MAX_REPLAY_FPS
    for earlier, later in pairwise(frames):
        assert later.t - earlier.t >= min_gap - 1e-9


def test_a_low_fps_downsamples_below_the_native_rate() -> None:
    frames = replay_frames(LATEST_SESSION, t_start=0.0, t_end=12.0, fps=1.0)

    for earlier, later in pairwise(frames):
        assert later.t - earlier.t >= 1.0 - 1e-9
    assert len(frames) < 25


def test_replayed_frames_carry_the_requested_session_id() -> None:
    frames = replay_frames(LATEST_SESSION, t_start=0.0, t_end=1.0)

    assert frames
    assert {frame.session_id for frame in frames} == {LATEST_SESSION}


def test_replayed_frames_validate_against_the_capture_frame_schema() -> None:
    validator = _frame_validator()
    frames = replay_frames(LATEST_SESSION, t_start=0.0, t_end=12.0)

    assert frames
    for frame in frames:
        payload = frame.model_dump(mode="json")
        validator.validate(payload)
        assert not any("image" in key or "byte" in key for key in payload)


def test_normal_replay_frames_come_from_a_different_session_id() -> None:
    frames = normal_replay_frames(MRS_K, t_start=0.0, t_end=1.0)

    assert frames
    assert {frame.session_id for frame in frames} == {f"{MRS_K}-normal"}


def test_normal_replay_frames_are_not_just_the_alert_replay_with_a_new_id() -> None:
    """The ghost overlay must show a different session, not today's traced over
    (regression for the bug where both scenarios were `tea_no_kettle`)."""
    window = {"t_start": 0.0, "t_end": SESSION_T_END}
    alert_frames = replay_frames(LATEST_SESSION, **window)
    normal_frames = normal_replay_frames(MRS_K, **window)

    def landmarks(frames: list) -> list:
        return [
            [obj.model_dump(exclude={"confidence"}) for obj in frame.objects]
            for frame in frames
        ]

    assert landmarks(alert_frames) != landmarks(normal_frames)


def test_replay_frames_window_past_the_stand_in_length_is_not_empty() -> None:
    """Regression for T154: real alert error windows (e.g. 33-107s, since T121) sit
    well past tea_no_kettle's 0-12s recording; the window must still get frames."""
    frames = replay_frames(LATEST_SESSION, t_start=102.1, t_end=107.1)

    assert frames
    for frame in frames:
        assert 102.1 - PAD_S <= frame.t <= 107.1 + PAD_S


def test_normal_replay_frames_window_past_the_stand_in_length_is_not_empty() -> None:
    frames = normal_replay_frames(MRS_K, t_start=102.1, t_end=107.1)

    assert frames
    for frame in frames:
        assert 102.1 - PAD_S <= frame.t <= 107.1 + PAD_S


def test_every_demo_resident_has_a_known_latest_session() -> None:
    for resident in demo_residents():
        session_id = f"{resident['id']}-{len(resident['sessions']) - 1}"
        assert known_session(session_id)


# ----------------------------------------------------------------------- the API


def test_session_replay_route_returns_frames() -> None:
    with TestClient(app) as client:
        response = client.get(
            f"/sessions/{LATEST_SESSION}/replay", params={"t_start": 4.0, "t_end": 5.0}
        )

    assert response.status_code == 200
    body = response.json()
    assert body["session_id"] == LATEST_SESSION
    assert body["frames"]
    assert all(frame["session_id"] == LATEST_SESSION for frame in body["frames"])


def test_session_replay_route_honours_the_fps_query_param() -> None:
    with TestClient(app) as client:
        response = client.get(
            f"/sessions/{LATEST_SESSION}/replay",
            params={"t_start": 0.0, "t_end": 12.0, "fps": 1.0},
        )

    assert response.status_code == 200
    times = [frame["t"] for frame in response.json()["frames"]]
    for earlier, later in pairwise(times):
        assert later - earlier >= 1.0 - 1e-9


def test_session_replay_route_404s_for_an_unknown_session() -> None:
    with TestClient(app) as client:
        response = client.get(
            "/sessions/does-not-exist-0/replay", params={"t_start": 0.0, "t_end": 1.0}
        )

    assert response.status_code == 404


def test_normal_replay_route_returns_frames() -> None:
    with TestClient(app) as client:
        response = client.get(
            f"/residents/{MRS_K}/normal_replay", params={"t_start": 0.0, "t_end": 1.0}
        )

    assert response.status_code == 200
    body = response.json()
    assert body["resident_id"] == MRS_K
    assert body["frames"]


def test_normal_replay_route_404s_for_an_unknown_resident() -> None:
    with TestClient(app) as client:
        response = client.get(
            "/residents/does-not-exist/normal_replay", params={"t_start": 0.0, "t_end": 1.0}
        )

    assert response.status_code == 404


# ------------------------------------------------------------------ the skeleton


@pytest.mark.parametrize("layer", ["today", "usual"])
def test_replayed_frames_carry_a_skeleton_and_not_just_boxes(layer: str) -> None:
    """Regression for T207: both stand-in recordings were written as object boxes with
    no landmarks, so the evidence view replayed boxes and the ghost layer - which draws
    poses and nothing else - drew nothing at all."""
    frames = (
        replay_frames(LATEST_SESSION, t_start=0.0, t_end=SESSION_T_END)
        if layer == "today"
        else normal_replay_frames(MRS_K, t_start=0.0, t_end=SESSION_T_END)
    )

    assert frames
    for frame in frames:
        assert len(frame.poses) == 1
        assert len(frame.hands) == 1
        for landmark in [*frame.poses[0].landmarks, *frame.hands[0].landmarks]:
            assert 0.0 <= landmark.x <= 1.0
            assert 0.0 <= landmark.y <= 1.0


def test_the_skeleton_moves_through_the_replay() -> None:
    frames = replay_frames(LATEST_SESSION, t_start=0.0, t_end=SESSION_T_END)

    wrists = {(frame.hands[0].landmarks[0].x, frame.hands[0].landmarks[0].y) for frame in frames}
    assert len(wrists) > 1


def test_the_ghost_layer_is_a_different_skeleton_from_todays() -> None:
    """The point of the ghost replay (SPEC nice-to-have 1) is the difference between
    the two, so the usual session's body must not trace today's."""
    window = {"t_start": 0.0, "t_end": SESSION_T_END}

    def skeletons(frames: list[CaptureFrame]) -> list[list[tuple[float, float]]]:
        return [
            [(landmark.x, landmark.y) for landmark in frame.poses[0].landmarks]
            for frame in frames
        ]

    assert skeletons(replay_frames(LATEST_SESSION, **window)) != skeletons(
        normal_replay_frames(MRS_K, **window)
    )


def test_the_hand_lands_in_the_hand_box_the_recording_tracks() -> None:
    """The skeleton is laid into the recording's own hand box, not next to it, so the
    figure reaches for whatever the recording says the hand was on."""
    for frame in replay_frames(LATEST_SESSION, t_start=0.0, t_end=SESSION_T_END):
        box = next(found.box for found in frame.objects if found.label is ObjectLabel.HAND)
        for landmark in frame.hands[0].landmarks:
            assert box.x1 <= landmark.x <= box.x2
            assert box.y1 <= landmark.y <= box.y2


@pytest.mark.parametrize("scenario", ["tea_no_kettle", "tea_normal"])
def test_the_skeleton_does_not_change_what_the_recogniser_reads(scenario: str) -> None:
    """The stand-in frames are the recogniser's own fixtures (`scripts/e2e.sh` replays
    them), and it reads hand landmarks as well as hand boxes, so adding a skeleton must
    leave every step event exactly where it was."""
    recorded = load_scenario(SCENARIOS_DIR / scenario)
    with_skeleton = evidence._scenario_frames(scenario)

    before = recognise(recorded.frames, recorded.graph, session_id="before")
    after = recognise(with_skeleton, recorded.graph, session_id="before")
    assert after == before
