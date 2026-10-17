"""Per-room monitoring on/paused store (SPEC §12 - monitoring can be turned off per room).

A nurse can pause monitoring for a room (say, during a sponge bath) without
touching any other room. Every change is logged with who made it and when, so a
camera going quiet is accountable rather than silent (SPEC §12: consent is per room
and can be turned off). Pure in-memory bookkeeping; the API routes and the UI
toggle that call this live elsewhere (`routine_watch.api_live`)::

    store = MonitoringStore()
    store.is_on("room-3")          # -> True, unknown rooms default to on
    store.set("room-3", False)     # pause it; "by" defaults to "nurse"
    store.paused_rooms()           # -> ["room-3"]
    store.history("room-3")        # -> [{"on": False, "by": "nurse", "at": "..."}]
    store.reset()                  # back to every room on, with nothing logged
"""

from __future__ import annotations

from datetime import UTC, datetime

#: Who a change is logged under when the caller doesn't say. The MVP has no nurse
#: logins yet (same as `api._FEEDBACK_BY`), so every tap is one anonymous nurse.
DEFAULT_BY = "nurse"

#: How many changes one room keeps: a shift's worth of taps, not an audit database
#: (there is no DB yet, and this is memory). Older changes fall off the end.
MAX_HISTORY = 20


class MonitoringStore:
    """Whether monitoring is on or paused per room, and who changed it when.

    Unknown rooms default to on, with nothing logged against them.
    """

    def __init__(self) -> None:
        self._paused: set[str] = set()
        self._history: dict[str, list[dict]] = {}

    def is_on(self, room: str) -> bool:
        """Whether `room` is being monitored. Defaults to True for unknown rooms."""
        return room not in self._paused

    def set(
        self,
        room: str,
        on: bool,
        by: str = DEFAULT_BY,
        at: datetime | None = None,
    ) -> None:
        """Turn monitoring on or off for `room`, and log who did it and when.

        `by` is whoever made the change and `at` is when (default: now, in UTC - a
        nurse's tap has no recorded timestamp to take one from, unlike a frame).

        A call that leaves the room as it already was changes nothing and logs
        nothing: the trail is the pauses and resumes that happened, so a second tap
        on an already-paused room is not a second pause to answer for.
        """
        if on == self.is_on(room):
            return
        if on:
            self._paused.discard(room)
        else:
            self._paused.add(room)
        when = datetime.now(UTC) if at is None else at
        changes = self._history.setdefault(room, [])
        changes.append({"on": on, "by": by, "at": when.isoformat()})
        del changes[:-MAX_HISTORY]

    def history(self, room: str) -> list[dict]:
        """Monitoring changes for `room`, newest first, at most `MAX_HISTORY` of them.

        Each change is `{"on": bool, "by": str, "at": ISO 8601 str}`: `on` False is a
        pause and True a resume. Copies, so reading the trail can't edit it.
        """
        return [dict(change) for change in reversed(self._history.get(room, ()))]

    def paused_rooms(self) -> list[str]:
        """Every room currently paused, sorted."""
        return sorted(self._paused)

    def reset(self) -> None:
        """Forget every pause and every logged change: every room is back to on."""
        self._paused.clear()
        self._history.clear()


_store = MonitoringStore()


def get_monitoring_store() -> MonitoringStore:
    """The one shared `MonitoringStore` instance for this process."""
    return _store
