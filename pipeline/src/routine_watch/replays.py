"""Kept skeleton replays of the sessions that went wrong (SPEC sections 17 and 8).

A person and their supervisors should be able to look back at a failed attempt and
judge it for themselves, instead of taking a summary's word for it. So every session
with at least one error keeps its skeleton - poses, hand landmarks, object boxes and
timestamps, thinned to about ten a second - and one clean session is kept beside them
as the comparison SPEC section 17 asks for ("compare with the person's normal")::

    store = get_replay_store()
    store.save(session, frames, errors)        # -> Replay, or the person's new normal
    store.list("mrs-k", error_type="omission") # -> [ReplaySummary], newest first
    store.get(session_id)                      # -> Replay (markers + frames)
    store.delete(session_id)                   # the person can delete any of them

**Never video.** What is kept is what the pipeline already works from
(`contracts.CaptureFrame`): landmarks, boxes and times. There is no field for an
image anywhere in the record, the store writes contracts and not dictionaries, and
`pipeline/tests/test_replays.py` holds the stored shape to that.

Two implementations, the same interface. `MemoryReplayStore` is the default and is
what tests, CI and an offline demo get: a dictionary in this process, gone when it
exits. `JsonlReplayStore` keeps one gzipped JSONL file per session under `REPLAY_DIR`
(default `.data/replays/`), a header line and then a frame per line, so a library
survives a restart without a database. `get_replay_store()` picks the second only
when `REPLAY_DIR` is set, so nothing writes to disk unless somebody asked for it.

**Retention is read off the sessions, not the wall clock.** A replay older than
`REPLAY_RETENTION_DAYS` (default 30) is pruned on every save, and "older" is measured
against the newest session the store holds rather than against today: the demo's
sessions are stamped on its own fixed clock (`demo.DEMO_NOW`, 2026-01-01), so a wall
clock would throw the whole library away the first time anything was saved. The
person's normal session ages out with the rest - keeping nothing beyond the window is
the promise, and a comparison is not an exception to it.
"""

from __future__ import annotations

import gzip
import json
import os
from abc import ABC, abstractmethod
from collections.abc import Iterable, Sequence
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import quote

from pydantic import ValidationError

from .contracts import (
    CaptureFrame,
    ErrorType,
    Replay,
    ReplayMarker,
    ReplaySummary,
    Session,
    TaskError,
)

STAGE = "replays"

#: Frames are kept no faster than this, in frames per second of session time: the
#: rate the live socket sends at (`live.MAX_FRAME_FPS`) and the evidence view replays
#: at (`evidence.MAX_REPLAY_FPS`), which is enough for a smooth skeleton and little
#: enough that a session is kilobytes rather than megabytes.
REPLAY_FPS = 10.0

#: How long a replay is kept, in days, unless `REPLAY_RETENTION_DAYS` says otherwise
#: (SPEC section 17: "kept 30 days by default").
DEFAULT_RETENTION_DAYS = 30.0

#: Where `JsonlReplayStore` keeps its files unless `REPLAY_DIR` says otherwise.
DEFAULT_REPLAY_DIR = Path(".data/replays")

#: One replay's file: a header line (the summary and its markers) then a frame a line.
_SUFFIX = ".jsonl.gz"


def markers_of(errors: Iterable[TaskError]) -> list[ReplayMarker]:
    """One marker per error, oldest first: where a viewer jumps to in the frames.

    Self-corrected slips are kept, flagged as what they are. They are not counted in
    the session's score (SPEC section 7) but they are exactly the kind of moment
    somebody looking back at their own routine wants to see.
    """
    return [
        ReplayMarker(
            error_id=error.error_id,
            type=error.type,
            step_id=error.step_id,
            t_start=error.t_start,
            t_end=error.t_end,
            self_corrected=error.self_corrected,
        )
        for error in sorted(errors, key=lambda error: (error.t_start, error.t_end))
    ]


def downsampled(frames: Sequence[CaptureFrame], fps: float = REPLAY_FPS) -> list[CaptureFrame]:
    """The frames worth keeping: the first, then one every `1 / fps` seconds.

    A recording slower than `fps` is kept whole. Same rule as `live._downsampled` and
    `evidence._downsample`, so a replay plays at the rate the live view ran at.
    """
    gap = 1.0 / (fps if fps > 0 else REPLAY_FPS)
    kept: list[CaptureFrame] = []
    last: float | None = None
    for frame in sorted(frames, key=lambda frame: (frame.t, frame.seq)):
        if last is None or frame.t - last >= gap - 1e-9:
            kept.append(frame)
            last = frame.t
    return kept


def build_replay(
    session: Session,
    frames: Sequence[CaptureFrame],
    errors: Sequence[TaskError] = (),
    fps: float = REPLAY_FPS,
) -> Replay:
    """The replay one finished session leaves behind. Pure: it stores nothing.

    `session` says whose it was and when (its `resident_id` is the replay's
    `person_id`), `frames` is what was captured, at whatever rate it was captured,
    and `errors` is the finished session's list - the authoritative one, the same
    `TaskError`s the alert and the live screen show, so the markers land on the
    moments a nurse was already told about.

    A session with no errors comes back `normal`: it is not an attempt to review, it
    is the comparison to review the others against (SPEC section 17).
    """
    kept = downsampled(frames, fps)
    duration = _duration_s(session, kept)
    return Replay(
        session_id=session.session_id,
        person_id=session.resident_id,
        task_id=session.task_id,
        started_at=session.started_at,
        duration_s=duration,
        error_count=len(errors),
        error_types=list(dict.fromkeys(error.type for error in errors)),
        normal=not errors,
        markers=markers_of(errors),
        frames=kept,
    )


def _duration_s(session: Session, frames: Sequence[CaptureFrame]) -> float:
    """How long the attempt took: the session's own two timestamps where it has both,
    otherwise how far into it the last kept frame was. Never negative."""
    if session.ended_at is not None:
        return max((session.ended_at - session.started_at).total_seconds(), 0.0)
    return max((frames[-1].t if frames else 0.0), 0.0)


def _newest_first(summary: ReplaySummary) -> tuple[datetime, str]:
    """Sort key for a library: by when the session was, then by its id, so two
    sessions stamped the same instant still come back in a fixed order."""
    return (summary.started_at, summary.session_id)


def _summary_of(replay: Replay) -> ReplaySummary:
    """One replay as its library row: everything but the markers and the frames."""
    fields = {name: getattr(replay, name) for name in ReplaySummary.model_fields}
    return ReplaySummary(**fields)


class ReplayStore(ABC):
    """Where a person's replays are kept.

    Subclasses answer five questions about storage - put one, read one, delete one,
    list them all, forget everything - and everything a caller actually asks for is
    written once, here: what counts as a replay worth keeping, which clean session is
    the comparison, the filters the library view offers, and when a replay has aged
    out.
    """

    def __init__(self, retention_days: float | None = None) -> None:
        self.retention_days = (
            _retention_days_from_env() if retention_days is None else float(retention_days)
        )

    # ------------------------------------------------------------ storage

    @abstractmethod
    def _put(self, replay: Replay) -> None:
        """Store one replay, replacing any replay of the same session."""

    @abstractmethod
    def get(self, session_id: str) -> Replay | None:
        """One replay in full - markers and frames - or None if it is not kept."""

    @abstractmethod
    def delete(self, session_id: str) -> bool:
        """Forget one replay. True if there was one to forget (SPEC section 17: the
        person can delete any of theirs)."""

    @abstractmethod
    def summaries(self) -> list[ReplaySummary]:
        """Every replay kept, as library rows, in no particular order."""

    @abstractmethod
    def reset(self) -> None:
        """Forget every replay: an empty library."""

    # ------------------------------------------------------------ the library

    def save(
        self,
        session: Session,
        frames: Sequence[CaptureFrame],
        errors: Sequence[TaskError] = (),
    ) -> Replay:
        """Keep this finished session's skeleton, and prune whatever has aged out.

        A session with errors is kept as one of this person's replays. A session with
        none is kept as their comparison instead: SPEC section 17 wants the most
        recent normal session beside the bad ones, and keeping every clean session
        would be keeping everything, so the person is left with exactly one - the
        newest, whichever order they arrived in.

        Saving the same session twice replaces it rather than keeping two copies, the
        way `session_log.record` does: a replayed recording is one session.
        """
        replay = build_replay(session, frames, errors)
        self._put(replay)
        if replay.normal:
            self._keep_one_normal(replay.person_id)
        self.prune()
        return replay

    def _keep_one_normal(self, person_id: str) -> None:
        """Leave this person with only their newest clean session (see `save`)."""
        kept = self.normal_for(person_id)
        for summary in self.summaries():
            if summary.normal and summary.person_id == person_id:
                if kept is None or summary.session_id != kept.session_id:
                    self.delete(summary.session_id)

    def list(
        self,
        person_id: str,
        since: datetime | None = None,
        error_type: ErrorType | str | None = None,
    ) -> list[ReplaySummary]:
        """This person's kept attempts, newest first (SPEC section 17).

        `since` keeps the ones that started at or after it, and `error_type` keeps
        the ones that had an error of that kind, which is how the library view's
        filters are answered. The comparison session is not one of the attempts, so
        it is never in this list; `normal_for` is where it lives.
        """
        wanted = None if error_type is None else ErrorType(error_type)
        rows = [
            summary
            for summary in self.summaries()
            if summary.person_id == person_id
            and not summary.normal
            and (since is None or summary.started_at >= since)
            and (wanted is None or wanted in summary.error_types)
        ]
        return sorted(rows, key=_newest_first, reverse=True)

    def normal_for(self, person_id: str) -> ReplaySummary | None:
        """This person's most recent session with no errors, or None if they have had
        none inside the retention window: what their attempts are compared against."""
        normals = [
            summary
            for summary in self.summaries()
            if summary.person_id == person_id and summary.normal
        ]
        return max(normals, key=lambda summary: summary.started_at, default=None)

    # ------------------------------------------------------------ retention

    def prune(self, now: datetime | None = None) -> list[str]:
        """Delete every replay older than `retention_days`, and say which went.

        `now` is the clock the window is measured back from; by default it is the
        newest session the store holds, which is the one that has just been saved.
        Replays carry the time of the session they are of, and the demo's sessions
        are on its own fixed clock (`demo.DEMO_NOW`), so measuring against today
        would delete a perfectly good demo library the moment anything was saved.
        """
        summaries = self.summaries()
        if not summaries or self.retention_days <= 0:
            return []
        latest = now or max(summary.started_at for summary in summaries)
        cutoff = latest - timedelta(days=self.retention_days)
        gone = [summary.session_id for summary in summaries if summary.started_at < cutoff]
        for session_id in gone:
            self.delete(session_id)
        return gone


class MemoryReplayStore(ReplayStore):
    """Replays in this process, gone when it exits: the default (and every test's).

    No file, no database, no network - the same shape as `JsonlReplayStore`, so the
    demo stack can point at either without anything upstream of it changing.
    """

    def __init__(self, retention_days: float | None = None) -> None:
        super().__init__(retention_days)
        self._replays: dict[str, Replay] = {}

    def _put(self, replay: Replay) -> None:
        self._replays[replay.session_id] = replay

    def get(self, session_id: str) -> Replay | None:
        return self._replays.get(session_id)

    def delete(self, session_id: str) -> bool:
        return self._replays.pop(session_id, None) is not None

    def summaries(self) -> list[ReplaySummary]:
        return [_summary_of(replay) for replay in self._replays.values()]

    def reset(self) -> None:
        self._replays.clear()


class JsonlReplayStore(ReplayStore):
    """Replays as one gzipped JSONL file per session, under `directory`.

    The file is the summary and its markers on the first line, then one
    `CaptureFrame` a line, which is the format every other recording in this repo is
    written in (`tests/scenarios/*/frames.jsonl`, `contracts/examples/capture.jsonl`)
    and the reason listing a library does not have to read a single frame: one line
    per file answers it.

    Files are written whole and then moved into place, so a library is never read
    half-written, and a file that is not a replay - truncated, hand-edited, left over
    from an older shape - is skipped rather than breaking the library it is in.
    """

    def __init__(self, directory: Path | str | None = None, retention_days: float | None = None):
        super().__init__(retention_days)
        self.directory = Path(directory) if directory is not None else _replay_dir_from_env()

    def _path(self, session_id: str) -> Path:
        """One session's file. The id is a client's string - it reaches this from a
        URL - so it is percent-encoded into a single flat name rather than trusted as
        a path: nothing it can contain escapes `directory`."""
        return self.directory / (quote(session_id, safe="") + _SUFFIX)

    def _put(self, replay: Replay) -> None:
        self.directory.mkdir(parents=True, exist_ok=True)
        path = self._path(replay.session_id)
        partial = path.with_suffix(".part")
        header = replay.model_dump(mode="json", exclude={"frames"})
        lines = [header, *(frame.model_dump(mode="json") for frame in replay.frames)]
        with gzip.open(partial, "wt", encoding="utf-8") as out:
            out.writelines(json.dumps(line) + "\n" for line in lines)
        partial.replace(path)

    def get(self, session_id: str) -> Replay | None:
        return self._read(self._path(session_id))

    def delete(self, session_id: str) -> bool:
        path = self._path(session_id)
        if not path.is_file():
            return False
        path.unlink()
        return True

    def summaries(self) -> list[ReplaySummary]:
        return [
            summary
            for path in sorted(self.directory.glob("*" + _SUFFIX))
            if (summary := self._read_summary(path)) is not None
        ]

    def reset(self) -> None:
        for path in sorted(self.directory.glob("*" + _SUFFIX)):
            path.unlink()

    def _read_summary(self, path: Path) -> ReplaySummary | None:
        """One file's header line, read without touching its frames.

        The header is a whole replay bar the frames, so it is validated as one (with
        no frames) rather than as a summary: a file carrying a field no contract has
        is not a replay, here as much as in `get`.
        """
        try:
            with gzip.open(path, "rt", encoding="utf-8") as lines:
                header = json.loads(next(lines))
                return _summary_of(Replay.model_validate(header | {"frames": []}))
        except (OSError, StopIteration, TypeError, ValueError, ValidationError):
            return None  # not a replay file, or not a readable one

    def _read(self, path: Path) -> Replay | None:
        try:
            with gzip.open(path, "rt", encoding="utf-8") as lines:
                header = json.loads(next(lines))
                frames = [json.loads(line) for line in lines if line.strip()]
                return Replay.model_validate(header | {"frames": frames})
        except (OSError, StopIteration, ValueError, ValidationError):
            return None


def _retention_days_from_env() -> float:
    """`REPLAY_RETENTION_DAYS`, or `DEFAULT_RETENTION_DAYS`. A value that is not a
    number is the default too: a typo in a deployment's environment must not quietly
    turn retention off, or into forever."""
    raw = os.environ.get("REPLAY_RETENTION_DAYS", "").strip()
    try:
        return float(raw) if raw else DEFAULT_RETENTION_DAYS
    except ValueError:
        return DEFAULT_RETENTION_DAYS


def _replay_dir_from_env() -> Path:
    """`REPLAY_DIR`, or `DEFAULT_REPLAY_DIR`."""
    return Path(os.environ.get("REPLAY_DIR", "").strip() or DEFAULT_REPLAY_DIR)


#: The one store this process uses, built on first use so `REPLAY_DIR` is read then
#: rather than at import time (`store.get_store` building a fresh one per call is
#: what this must not do: a library nobody can add to).
_store: ReplayStore | None = None


def get_replay_store() -> ReplayStore:
    """The shared `ReplayStore` for this process.

    On disk when `REPLAY_DIR` names a directory to keep replays in, in memory
    otherwise - so a dev stack, CI and the tester keep a library for as long as the
    API is up and write nothing anywhere unless they were asked to.
    """
    global _store
    if _store is None:
        on_disk = bool(os.environ.get("REPLAY_DIR", "").strip())
        _store = JsonlReplayStore() if on_disk else MemoryReplayStore()
    return _store


def use_replay_store(store: ReplayStore | None) -> None:
    """Point this process at `store` (or, with None, at a store built fresh on the
    next call). The seam tests and `/demo/reset` use; nothing else should need it."""
    global _store
    _store = store
