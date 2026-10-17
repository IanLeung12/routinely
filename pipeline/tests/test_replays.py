"""Kept skeleton replays of the sessions that went wrong (SPEC sections 17 and 8).

SPEC section 17 is the promise under test: every session with at least one error keeps
a replay, the person's most recent normal session is kept beside them to compare
against, it is landmarks and boxes and never video, it is kept 30 days, and the person
can delete any of it. So these tests are about what is kept and what is not - both
store implementations, the two live paths that save, the generated demo library and
the routes that serve it - and the privacy case is explicit: nothing that goes into a
replay has anywhere to put an image.

The store is process-global like the session log, so `_empty_library` puts a fresh
in-memory one in place around every test here and forgets the generated demo libraries
with it: a test that lists somebody's replays must not be reading the one before it.
"""

from __future__ import annotations

import asyncio
import gzip
import json
import re
from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from test_contracts import BANNED_FIELD_WORDS

from routine_watch.api import app
from routine_watch.contracts import (
    CaptureFrame,
    ErrorType,
    EvidenceRef,
    Replay,
    ReplaySummary,
    Session,
    TaskError,
)
from routine_watch.demo import DEMO_NOW, DEMO_RESIDENT
from routine_watch.evidence import (
    DEMO_REPLAYS_PER_PERSON,
    ensure_demo_replays,
    generated_frames,
    person_of,
    reset_demo_replays,
)
from routine_watch.live import scenario_path, session_messages
from routine_watch.live_camera import camera_session_messages
from routine_watch.replay import SCENARIOS_DIR, load_scenario
from routine_watch.replays import (
    DEFAULT_RETENTION_DAYS,
    REPLAY_FPS,
    JsonlReplayStore,
    MemoryReplayStore,
    ReplayStore,
    build_replay,
    get_replay_store,
    use_replay_store,
)

#: A quiet resident's day, on the demo's own clock (`demo.DEMO_NOW`), which is what
#: every session in this repo is timed against.
WHEN = DEMO_NOW - timedelta(hours=3)

#: Fast enough that a recorded session plays out inside a test.
FAST = 1000.0

#: The demo's bad session: skip the teabag, pour twice (SPEC section 10, beat 4).
BAD_SCENARIO = "tea_skip_teabag_pour_twice"

#: A session that goes right, and one the capture could not be trusted to read.
CLEAN_SCENARIO = "tea_normal"
UNCLEAR_SCENARIO = "tea_session_unclear_no_flag"

#: The one scenario written at frame level with an error in it: a camera stream.
CAMERA_SCENARIO = "tea_no_kettle"

#: A long run of base64-ish characters is what an image smuggled into a JSONL line
#: would look like (`pipeline/tests/test_privacy.py` sweeps every other recording in
#: the repo for the same thing).
BASE64_RUN = re.compile(r"[A-Za-z0-9+/=]{200,}")


# --------------------------------------------------------------- fixtures


@pytest.fixture(autouse=True)
def _empty_library():
    """Every test starts with an empty library and no demo library generated yet."""
    use_replay_store(MemoryReplayStore())
    reset_demo_replays()
    yield
    use_replay_store(None)
    reset_demo_replays()


@pytest.fixture(params=["memory", "jsonl"])
def store(request: pytest.FixtureRequest, tmp_path: Path) -> ReplayStore:
    """Both implementations, behind the one interface: the on-disk one is what a
    dev stack keeps a library in, the in-memory one is what everything else uses."""
    if request.param == "memory":
        return MemoryReplayStore()
    return JsonlReplayStore(tmp_path / "replays")


def a_session(
    session_id: str = "s1",
    person_id: str = DEMO_RESIDENT,
    started_at: datetime = WHEN,
    duration_s: float = 120.0,
) -> Session:
    return Session(
        session_id=session_id,
        resident_id=person_id,
        task_id="make_tea",
        started_at=started_at,
        ended_at=started_at + timedelta(seconds=duration_s),
    )


def an_error(
    error_id: str = "e1",
    session_id: str = "s1",
    error_type: ErrorType = ErrorType.OMISSION,
    step_id: str | None = "teabag_in_cup",
    t_start: float = 42.0,
    t_end: float = 48.5,
    self_corrected: bool = False,
) -> TaskError:
    return TaskError(
        error_id=error_id,
        session_id=session_id,
        type=error_type,
        step_id=step_id,
        t_start=t_start,
        t_end=t_end,
        evidence=[EvidenceRef(kind="skeleton_replay", t_start=t_start, t_end=t_end)],
        self_corrected=self_corrected,
    )


def some_frames(
    session_id: str = "s1", count: int = 12, gap: float = 0.5, source: str = "camera"
) -> list[CaptureFrame]:
    """A stand-in capture stream: no landmarks, which is all these tests need of it."""
    return [
        CaptureFrame(
            session_id=session_id,
            seq=index,
            t=round(index * gap, 3),
            source=source,
            poses=[],
            hands=[],
            objects=[],
        )
        for index in range(count)
    ]


def play(scenario: str, resident_id: str = DEMO_RESIDENT) -> list[dict[str, Any]]:
    """One recorded scenario played through the live pipeline, as its messages."""

    async def run() -> list[dict[str, Any]]:
        return [
            message
            async for message in session_messages(
                scenario_path(scenario), speed=FAST, resident_id=resident_id
            )
        ]

    return asyncio.run(run())


# -------------------------------------------------- what is kept, and what is not


def test_a_session_with_an_error_is_kept_and_listed(store: ReplayStore) -> None:
    saved = store.save(a_session(), some_frames(), [an_error()])

    [row] = store.list(DEMO_RESIDENT)

    assert (row.session_id, row.person_id) == ("s1", DEMO_RESIDENT)
    assert (row.error_count, row.error_types) == (1, [ErrorType.OMISSION])
    assert row.duration_s == pytest.approx(120.0)
    assert not row.normal
    assert store.get("s1") == saved


def test_a_clean_session_is_not_listed_but_is_the_comparison(store: ReplayStore) -> None:
    """SPEC section 17: the attempts to review are the ones that went wrong, and the
    person's most recent normal session is what they are compared against. It is kept,
    so there is something to compare with, and it is not one of the attempts."""
    store.save(a_session("clean"), some_frames("clean"), [])

    assert store.list(DEMO_RESIDENT) == []
    assert store.normal_for(DEMO_RESIDENT).session_id == "clean"
    assert store.get("clean").normal
    assert store.get("clean").markers == []


def test_only_the_most_recent_clean_session_is_kept(store: ReplayStore) -> None:
    """Every clean session kept would be everything kept. One is the comparison."""
    store.save(a_session("clean-1", started_at=WHEN - timedelta(days=2)), some_frames(), [])
    store.save(a_session("clean-2", started_at=WHEN), some_frames(), [])

    assert store.normal_for(DEMO_RESIDENT).session_id == "clean-2"
    assert store.get("clean-1") is None
    assert [summary.session_id for summary in store.summaries()] == ["clean-2"]


def test_an_older_clean_session_does_not_replace_the_comparison(store: ReplayStore) -> None:
    """The comparison is the person's most recent normal session, not the last one
    somebody happened to play: a recording from last week is not today's normal."""
    store.save(a_session("clean-now"), some_frames(), [])

    store.save(a_session("clean-then", started_at=WHEN - timedelta(days=4)), some_frames(), [])

    assert store.normal_for(DEMO_RESIDENT).session_id == "clean-now"
    assert store.get("clean-then") is None


def test_markers_line_up_with_the_errors_timestamps(store: ReplayStore) -> None:
    """A marker is where the viewer jumps to, so it has to be the error's own moment
    - the same window, step and type the alert and the live screen were told about."""
    errors = [
        an_error(
            "e2",
            error_type=ErrorType.PERSEVERATION,
            step_id="pour",
            t_start=90.0,
            t_end=96.5,
        ),
        an_error("e1", t_start=42.0, t_end=48.5),
    ]

    replay = store.save(a_session(), some_frames(), errors)

    assert [(marker.t_start, marker.t_end) for marker in replay.markers] == [
        (42.0, 48.5),
        (90.0, 96.5),
    ]
    assert [marker.error_id for marker in replay.markers] == ["e1", "e2"]
    assert [str(marker.type) for marker in replay.markers] == ["omission", "perseveration"]
    assert [marker.step_id for marker in replay.markers] == ["teabag_in_cup", "pour"]


def test_a_self_corrected_slip_is_marked_as_one(store: ReplayStore) -> None:
    """It is not counted in the score (SPEC section 7) and it is exactly the kind of
    moment somebody looking back at their own routine wants to find."""
    replay = store.save(a_session(), some_frames(), [an_error(self_corrected=True)])

    assert [marker.self_corrected for marker in replay.markers] == [True]
    assert [row.session_id for row in store.list(DEMO_RESIDENT)] == ["s1"]


def test_frames_are_thinned_to_about_ten_a_second(store: ReplayStore) -> None:
    """A replay is a skeleton to watch, not a capture file: SPEC's "downsampled"."""
    replay = store.save(a_session(), some_frames(count=90, gap=1 / 30), [an_error()])

    gaps = [b.t - a.t for a, b in zip(replay.frames, replay.frames[1:], strict=False)]

    assert gaps and min(gaps) >= 1 / REPLAY_FPS - 1e-9
    assert len(replay.frames) < 90


def test_a_recording_slower_than_that_is_kept_whole(store: ReplayStore) -> None:
    frames = some_frames(count=10, gap=0.5)

    replay = store.save(a_session(), frames, [an_error()])

    assert [frame.t for frame in replay.frames] == [frame.t for frame in frames]


def test_a_library_is_one_persons(store: ReplayStore) -> None:
    store.save(a_session("mine"), some_frames(), [an_error()])
    store.save(a_session("theirs", person_id="mr-chen"), some_frames(), [an_error()])

    assert [row.session_id for row in store.list(DEMO_RESIDENT)] == ["mine"]
    assert [row.session_id for row in store.list("mr-chen")] == ["theirs"]
    assert store.normal_for("mr-chen") is None


def test_the_library_is_newest_first(store: ReplayStore) -> None:
    for days, name in ((3, "older"), (1, "newest"), (2, "middle")):
        store.save(
            a_session(name, started_at=WHEN - timedelta(days=days)), some_frames(), [an_error()]
        )

    assert [row.session_id for row in store.list(DEMO_RESIDENT)] == [
        "newest",
        "middle",
        "older",
    ]


def test_listing_filters_by_error_type_and_by_when(store: ReplayStore) -> None:
    """The two filters the library view offers (`GET /people/{id}/replays`)."""
    store.save(
        a_session("old", started_at=WHEN - timedelta(days=5)),
        some_frames(),
        [an_error(error_type=ErrorType.HESITATION)],
    )
    store.save(a_session("new"), some_frames(), [an_error(error_type=ErrorType.OMISSION)])

    assert [row.session_id for row in store.list(DEMO_RESIDENT, error_type="omission")] == ["new"]
    assert [row.session_id for row in store.list(DEMO_RESIDENT, error_type="hesitation")] == ["old"]
    assert store.list(DEMO_RESIDENT, error_type=ErrorType.SEQUENCE) == []
    since = WHEN - timedelta(days=1)
    assert [row.session_id for row in store.list(DEMO_RESIDENT, since=since)] == ["new"]


def test_the_same_session_saved_twice_is_one_replay(store: ReplayStore) -> None:
    """A recording replayed twice is one session, the way `session_log.record` has
    it: two copies would be two attempts to review that never happened."""
    store.save(a_session(), some_frames(), [an_error()])
    store.save(a_session(), some_frames(count=20), [an_error(), an_error("e2")])

    [row] = store.list(DEMO_RESIDENT)

    assert row.error_count == 2
    assert len(store.summaries()) == 1


def test_delete_forgets_one_replay(store: ReplayStore) -> None:
    """SPEC section 17: the person sees the same replays and can delete any of them."""
    store.save(a_session(), some_frames(), [an_error()])

    assert store.delete("s1") is True
    assert store.get("s1") is None
    assert store.list(DEMO_RESIDENT) == []
    assert store.delete("s1") is False


def test_reset_empties_the_library(store: ReplayStore) -> None:
    store.save(a_session(), some_frames(), [an_error()])
    store.save(a_session("clean"), some_frames(), [])

    store.reset()

    assert store.summaries() == []


# ------------------------------------------------------------------ retention


def test_retention_prunes_what_has_aged_out(store: ReplayStore) -> None:
    """Kept 30 days by default (SPEC section 17), pruned whenever anything is saved."""
    long_ago = WHEN - timedelta(days=DEFAULT_RETENTION_DAYS + 1)
    store.save(a_session("ancient", started_at=long_ago), some_frames(), [an_error()])
    assert [row.session_id for row in store.list(DEMO_RESIDENT)] == ["ancient"]

    store.save(a_session("today"), some_frames(), [an_error()])

    assert [row.session_id for row in store.list(DEMO_RESIDENT)] == ["today"]
    assert store.get("ancient") is None


def test_an_aged_out_comparison_goes_too(store: ReplayStore) -> None:
    """Keeping nothing past the window is the promise; a comparison is not an
    exception to it."""
    long_ago = WHEN - timedelta(days=DEFAULT_RETENTION_DAYS + 1)
    store.save(a_session("old-normal", started_at=long_ago), some_frames(), [])

    store.save(a_session("today"), some_frames(), [an_error()])

    assert store.normal_for(DEMO_RESIDENT) is None


def test_what_is_inside_the_window_stays(store: ReplayStore) -> None:
    recent = WHEN - timedelta(days=DEFAULT_RETENTION_DAYS - 1)
    store.save(a_session("recent", started_at=recent), some_frames(), [an_error()])

    store.save(a_session("today"), some_frames(), [an_error()])

    assert [row.session_id for row in store.list(DEMO_RESIDENT)] == ["today", "recent"]


def test_retention_is_read_off_the_sessions_not_the_wall_clock(store: ReplayStore) -> None:
    """The demo's sessions are stamped on its own fixed today (`demo.DEMO_NOW`), which
    is not this machine's: measuring the window back from the wall clock would throw
    the whole demo library away the first time anything was saved."""
    assert DEMO_NOW < datetime.now(UTC) - timedelta(days=DEFAULT_RETENTION_DAYS)

    store.save(a_session(), some_frames(), [an_error()])

    assert [row.session_id for row in store.list(DEMO_RESIDENT)] == ["s1"]


def test_the_window_comes_from_the_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("REPLAY_RETENTION_DAYS", "2")
    store = MemoryReplayStore()
    store.save(a_session("old", started_at=WHEN - timedelta(days=3)), some_frames(), [an_error()])

    store.save(a_session("today"), some_frames(), [an_error()])

    assert store.retention_days == 2
    assert [row.session_id for row in store.list(DEMO_RESIDENT)] == ["today"]


def test_a_nonsense_retention_setting_is_the_default(monkeypatch: pytest.MonkeyPatch) -> None:
    """A typo in a deployment's environment must not quietly turn retention off."""
    monkeypatch.setenv("REPLAY_RETENTION_DAYS", "thirty")

    assert MemoryReplayStore().retention_days == DEFAULT_RETENTION_DAYS


# -------------------------------------------------------------------- privacy


def test_no_image_or_video_field_can_be_stored() -> None:
    """SPEC section 8, the storage boundary: a replay is skeletons, boxes and
    timestamps, and every shape it is made of forbids a field it has never heard of,
    so there is nowhere for an image to be smuggled in - not in the replay, not in a
    marker, not in a frame."""
    replay = build_replay(a_session(), some_frames(), [an_error()])
    payload = replay.model_dump(mode="json")

    for smuggled in ("frame_jpeg", "image", "video_url", "thumbnail_png", "clip"):
        with pytest.raises(ValidationError):
            Replay.model_validate(payload | {smuggled: "iVBORw0KGgo="})
        with pytest.raises(ValidationError):
            ReplaySummary.model_validate(
                {key: value for key, value in payload.items() if key in ReplaySummary.model_fields}
                | {smuggled: "iVBORw0KGgo="}
            )

    frame = payload["frames"][0]
    with pytest.raises(ValidationError):
        CaptureFrame.model_validate(frame | {"image": "iVBORw0KGgo="})
    with pytest.raises(ValidationError):
        Replay.model_validate(
            payload | {"frames": [frame | {"image": "iVBORw0KGgo="}]}
        )


def test_a_replay_names_no_field_that_sounds_like_video() -> None:
    """The field names themselves, so a later field called `thumbnail` is caught
    here and not in review. The list is `test_contracts.BANNED_FIELD_WORDS`, the one
    every other contract is held to, so there is one answer to what sounds like
    video and not two."""
    named = (
        set(Replay.model_fields)
        | set(ReplaySummary.model_fields)
        | set(CaptureFrame.model_fields)
    )

    offenders = {
        field for field in named if any(word in field for word in BANNED_FIELD_WORDS)
    }

    assert offenders == {"frames"}, "only the list of CaptureFrames may say 'frame'"


def test_what_reaches_the_disk_is_skeletons_and_numbers(tmp_path: Path) -> None:
    """The on-disk library, read as bytes: no image data, no long base64-ish run, and
    every line small enough that nothing could be hiding in it
    (`tests/test_privacy.py` holds every other recording in the repo to the same)."""
    store = JsonlReplayStore(tmp_path)
    store.save(a_session(), load_scenario(SCENARIOS_DIR / CAMERA_SCENARIO).frames, [an_error()])

    [path] = sorted(tmp_path.glob("*.jsonl.gz"))
    lines = gzip.decompress(path.read_bytes()).decode().splitlines()

    assert len(lines) > 1
    for line in lines:
        assert len(line) < 20_000
        assert "data:image" not in line.lower()
        assert not BASE64_RUN.search(line)
    keys = {key for line in lines[1:] for key in json.loads(line)}
    assert keys <= set(CaptureFrame.model_fields)


def test_a_file_carrying_an_unknown_field_is_not_a_replay(tmp_path: Path) -> None:
    """Reading is held to the same shape as writing: a hand-edited file with a field
    no contract has is skipped, not loaded."""
    store = JsonlReplayStore(tmp_path)
    store.save(a_session(), some_frames(), [an_error()])
    path = tmp_path / "s1.jsonl.gz"
    lines = gzip.decompress(path.read_bytes()).decode().splitlines()
    header = json.loads(lines[0]) | {"frame_jpeg": "iVBORw0KGgo="}
    with gzip.open(path, "wt", encoding="utf-8") as out:
        out.write("\n".join([json.dumps(header), *lines[1:]]) + "\n")

    assert store.get("s1") is None
    assert store.summaries() == []


# ------------------------------------------------------------- the on-disk store


def test_a_library_survives_the_process_that_wrote_it(tmp_path: Path) -> None:
    JsonlReplayStore(tmp_path).save(a_session(), some_frames(), [an_error()])

    reopened = JsonlReplayStore(tmp_path)

    [row] = reopened.list(DEMO_RESIDENT)
    assert row.session_id == "s1"
    assert len(reopened.get("s1").frames) == len(some_frames())


def test_one_file_per_session_with_a_header_and_a_frame_a_line(tmp_path: Path) -> None:
    store = JsonlReplayStore(tmp_path)
    store.save(a_session(), some_frames(count=4), [an_error()])

    [path] = sorted(tmp_path.glob("*"))
    lines = gzip.decompress(path.read_bytes()).decode().splitlines()

    assert path.name == "s1.jsonl.gz"
    assert len(lines) == 5
    assert json.loads(lines[0])["markers"][0]["error_id"] == "e1"
    assert [json.loads(line)["seq"] for line in lines[1:]] == [0, 1, 2, 3]


def test_a_file_that_is_not_a_replay_is_skipped(tmp_path: Path) -> None:
    """A truncated or half-written file must not break the library it is in."""
    store = JsonlReplayStore(tmp_path)
    store.save(a_session(), some_frames(), [an_error()])
    (tmp_path / "rubbish.jsonl.gz").write_bytes(b"not gzip at all")

    assert [row.session_id for row in store.summaries()] == ["s1"]


def test_a_session_id_off_a_url_cannot_escape_the_directory(tmp_path: Path) -> None:
    """Ids reach the store from a route path, so one is a flat file name and nothing
    more: `DELETE /replays/..%2F..%2Fetc%2Fpasswd` has nowhere to go."""
    store = JsonlReplayStore(tmp_path / "library")
    nasty = "../../escape"

    store.save(a_session(nasty), some_frames(), [an_error()])

    assert store.get(nasty) is not None
    assert [path.parent for path in (tmp_path / "library").glob("*.jsonl.gz")] == [
        tmp_path / "library"
    ]
    assert not (tmp_path / "escape.jsonl.gz").exists()


def test_the_store_is_on_disk_only_when_asked(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    """Nothing writes a replay anywhere unless `REPLAY_DIR` says where (AGENTS.md:
    tests, CI and the tester keep to themselves)."""
    use_replay_store(None)
    assert isinstance(get_replay_store(), MemoryReplayStore)

    use_replay_store(None)
    monkeypatch.setenv("REPLAY_DIR", str(tmp_path / "kept"))

    store = get_replay_store()
    assert isinstance(store, JsonlReplayStore)
    assert store.directory == tmp_path / "kept"


# --------------------------------------------------------------- the live paths


def test_a_live_session_with_errors_keeps_its_replay() -> None:
    """The demo's bad session on stage (SPEC section 10, beat 4): what the dashboard
    just watched is there to watch again afterwards."""
    messages = play(BAD_SCENARIO)
    [end] = [message for message in messages if message["type"] == "session_end"]

    [row] = get_replay_store().list(DEMO_RESIDENT)
    replay = get_replay_store().get(row.session_id)

    assert row.error_count == len(end["errors"])
    assert [marker.error_id for marker in replay.markers] == [
        error.error_id for error in sorted(end["errors"], key=lambda e: (e.t_start, e.t_end))
    ]
    assert replay.frames
    assert row.task_id == "make_tea"


def test_a_clean_live_session_becomes_the_comparison() -> None:
    play(CLEAN_SCENARIO)

    store = get_replay_store()

    assert store.list(DEMO_RESIDENT) == []
    assert store.normal_for(DEMO_RESIDENT) is not None


def test_an_unclear_session_keeps_nothing() -> None:
    """Too little of its capture can be trusted to call anything in it an error
    (SPEC section 12), so there is nothing in it to mark up or look back at."""
    messages = play(UNCLEAR_SCENARIO)
    [end] = [message for message in messages if message["type"] == "session_end"]

    assert end["quality"] == "unclear"
    assert get_replay_store().summaries() == []


def test_a_cut_short_session_keeps_nothing() -> None:
    """The socket closing mid-session is not a finished attempt, so - like the
    session log - it leaves nothing behind."""

    async def run() -> None:
        messages = session_messages(scenario_path(BAD_SCENARIO), speed=FAST)
        async for message in messages:
            if message["type"] == "error":
                break
        await messages.aclose()

    asyncio.run(run())

    assert get_replay_store().summaries() == []


def test_a_camera_session_keeps_a_replay_of_what_it_saw() -> None:
    """A camera has no history to be flagged against, and still leaves an attempt
    worth looking at - these are real capture records, not a stand-in."""
    recorded = load_scenario(SCENARIOS_DIR / CAMERA_SCENARIO).frames

    async def run() -> list[dict[str, Any]]:
        async def stream() -> AsyncIterator[CaptureFrame]:
            for frame in recorded:
                yield frame

        return [message async for message in camera_session_messages(stream())]

    messages = asyncio.run(run())
    [end] = [message for message in messages if message["type"] == "session_end"]

    [row] = get_replay_store().list(DEMO_RESIDENT)
    replay = get_replay_store().get(row.session_id)

    assert end["errors"] and row.error_count == len(end["errors"])
    assert [frame.t for frame in replay.frames] == [frame.t for frame in recorded]
    assert replay.frames[0].source == recorded[0].source


# ----------------------------------------------------------- the demo's library


def test_the_demo_people_have_a_library_to_look_through() -> None:
    """Nobody has ever filmed a demo person's fortnight of history, so without this
    the demo's replay library is empty on stage (SPEC section 17)."""
    store = get_replay_store()

    ensure_demo_replays(DEMO_RESIDENT, store)

    rows = store.list(DEMO_RESIDENT)
    assert 0 < len(rows) <= DEMO_REPLAYS_PER_PERSON
    assert all(row.error_count > 0 for row in rows)
    assert store.normal_for(DEMO_RESIDENT) is not None


def test_a_generated_replay_runs_the_length_of_the_session() -> None:
    store = get_replay_store()
    ensure_demo_replays(DEMO_RESIDENT, store)

    row = store.list(DEMO_RESIDENT)[0]
    replay = store.get(row.session_id)

    assert replay.frames[0].t == 0.0
    assert replay.duration_s - replay.frames[-1].t < 1.0
    assert all(frame.poses and frame.hands for frame in replay.frames)
    assert all(marker.t_start <= replay.duration_s for marker in replay.markers)


def test_a_generated_replays_markers_are_the_alerts_errors() -> None:
    """A supervisor reads the alert and opens the replay: both have to name the same
    moments, which is why both come from `alerts.task_errors`."""
    from routine_watch.alerts import task_errors
    from routine_watch.demo import demo_residents

    store = get_replay_store()
    ensure_demo_replays(DEMO_RESIDENT, store)
    row = store.list(DEMO_RESIDENT)[0]
    resident = next(one for one in demo_residents() if one["id"] == DEMO_RESIDENT)
    index = int(row.session_id.rsplit("-", 1)[1])

    expected = task_errors(row.session_id, resident["sessions"][index])

    assert [marker.t_start for marker in store.get(row.session_id).markers] == [
        error.t_start for error in expected
    ]


def test_a_deleted_replay_is_not_generated_again() -> None:
    """Deleting is deleting (SPEC section 17), even for a generated one."""
    store = get_replay_store()
    ensure_demo_replays(DEMO_RESIDENT, store)
    gone = store.list(DEMO_RESIDENT)[0].session_id

    store.delete(gone)
    ensure_demo_replays(DEMO_RESIDENT, store)

    assert gone not in {row.session_id for row in store.list(DEMO_RESIDENT)}


def test_a_session_this_process_watched_is_not_generated_over() -> None:
    """A live session brought its own frames; a stand-in must never replace them."""
    play(BAD_SCENARIO)
    store = get_replay_store()
    [live_row] = store.list(DEMO_RESIDENT)
    before = store.get(live_row.session_id)

    ensure_demo_replays(DEMO_RESIDENT, store)

    assert store.get(live_row.session_id) == before


def test_only_the_demo_people_get_a_generated_library() -> None:
    store = get_replay_store()

    ensure_demo_replays("somebody-else", store)

    assert store.summaries() == []
    assert person_of("mrs-k-3") == "mrs-k"
    assert person_of("nobody-3") is None
    assert person_of("tea-session") is None


def test_generated_frames_cover_a_session_and_stop() -> None:
    frames = generated_frames("mrs-k-4", duration_s=40.0)

    assert frames[0].t == 0.0
    assert frames[-1].t <= 40.0
    assert all(frame.session_id == "mrs-k-4" for frame in frames)
    assert [frame.seq for frame in frames] == list(range(len(frames)))
    assert generated_frames("mrs-k-4", duration_s=0.0) == []


# ------------------------------------------------------------------- the routes


@pytest.fixture
def client() -> TestClient:
    with TestClient(app) as client:
        yield client


def test_the_route_lists_a_persons_replays_and_their_normal(client: TestClient) -> None:
    body = client.get(f"/people/{DEMO_RESIDENT}/replays").json()

    assert body["person_id"] == DEMO_RESIDENT
    assert body["replays"] and all(row["error_count"] > 0 for row in body["replays"])
    assert body["normal"]["normal"] is True
    assert all("frames" not in row for row in body["replays"])


def test_the_route_filters_by_type_and_since(client: TestClient) -> None:
    rows = client.get(f"/people/{DEMO_RESIDENT}/replays").json()["replays"]
    wanted = rows[0]["error_types"][0]

    filtered = client.get(
        f"/people/{DEMO_RESIDENT}/replays", params={"type": wanted}
    ).json()["replays"]
    since = client.get(
        f"/people/{DEMO_RESIDENT}/replays", params={"since": rows[0]["started_at"]}
    ).json()["replays"]

    assert filtered and all(wanted in row["error_types"] for row in filtered)
    assert [row["session_id"] for row in since] == [rows[0]["session_id"]]
    assert client.get(
        f"/people/{DEMO_RESIDENT}/replays", params={"type": "not-an-error-type"}
    ).status_code == 422


def test_a_person_with_nothing_kept_has_an_empty_library(client: TestClient) -> None:
    body = client.get("/people/sam/replays").json()

    assert body == {"person_id": "sam", "replays": [], "normal": None}


def test_the_route_serves_one_replay_with_its_markers(client: TestClient) -> None:
    row = client.get(f"/people/{DEMO_RESIDENT}/replays").json()["replays"][0]

    body = client.get(f"/replays/{row['session_id']}").json()

    assert body["session_id"] == row["session_id"]
    assert len(body["markers"]) == row["error_count"]
    assert body["frames"] and body["frames"][0]["t"] == 0.0


def test_a_replay_can_be_asked_for_one_errors_window(client: TestClient) -> None:
    """The window `GET /sessions/{id}/replay` serves out of a stand-in recording, out
    of the real one this time - and the markers come with it either way."""
    row = client.get(f"/people/{DEMO_RESIDENT}/replays").json()["replays"][0]
    marker = client.get(f"/replays/{row['session_id']}").json()["markers"][0]
    window = {"t_start": marker["t_start"], "t_end": marker["t_end"] + 5.0, "fps": 1.0}

    body = client.get(f"/replays/{row['session_id']}", params=window).json()

    times = [frame["t"] for frame in body["frames"]]
    assert times and min(times) >= window["t_start"] and max(times) <= window["t_end"]
    assert all(b - a >= 1.0 - 1e-9 for a, b in zip(times, times[1:], strict=False))
    assert len(body["markers"]) == row["error_count"]


def test_the_person_can_delete_a_replay(client: TestClient) -> None:
    """SPEC section 17: the person sees the same replays and can delete any of them."""
    row = client.get(f"/people/{DEMO_RESIDENT}/replays").json()["replays"][0]

    deleted = client.delete(f"/replays/{row['session_id']}")

    assert deleted.json() == {"session_id": row["session_id"], "deleted": True}
    assert client.get(f"/replays/{row['session_id']}").status_code == 404
    assert client.delete(f"/replays/{row['session_id']}").status_code == 404
    left = client.get(f"/people/{DEMO_RESIDENT}/replays").json()["replays"]
    assert row["session_id"] not in {other["session_id"] for other in left}


def test_an_unknown_replay_is_a_404(client: TestClient) -> None:
    assert client.get("/replays/nobody-at-all").status_code == 404


def test_the_older_evidence_route_still_works(client: TestClient) -> None:
    """The alert's own window (SPEC section 8) is unchanged: the library supersedes
    it as the way to look back at a session, not as the way to open an alert."""
    body = client.get(
        f"/sessions/{DEMO_RESIDENT}-22/replay", params={"t_start": 4.0, "t_end": 5.0}
    )

    assert body.status_code == 200
    assert body.json()["frames"]


def test_demo_reset_empties_the_library(client: TestClient, monkeypatch) -> None:
    monkeypatch.setenv("DEMO_RESET", "1")
    client.get(f"/people/{DEMO_RESIDENT}/replays")
    assert get_replay_store().summaries()

    assert client.post("/demo/reset").json() == {"ok": True}

    assert get_replay_store().summaries() == []
