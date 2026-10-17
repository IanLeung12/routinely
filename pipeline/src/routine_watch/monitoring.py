"""Per-room monitoring on/paused store (SPEC §12 - monitoring can be turned off per room).

A nurse can pause monitoring for a room (say, during a sponge bath) without
touching any other room. Pure in-memory bookkeeping; the API route and the UI
toggle that call this live in other tasks::

    store = MonitoringStore()
    store.is_on("room-3")          # -> True, unknown rooms default to on
    store.set("room-3", False)     # pause it
    store.paused_rooms()           # -> ["room-3"]
    store.reset()                  # back to every room on
"""

from __future__ import annotations


class MonitoringStore:
    """Whether monitoring is on or paused, per room. Unknown rooms default to on."""

    def __init__(self) -> None:
        self._paused: set[str] = set()

    def is_on(self, room: str) -> bool:
        """Whether `room` is being monitored. Defaults to True for unknown rooms."""
        return room not in self._paused

    def set(self, room: str, on: bool) -> None:
        """Turn monitoring on or off for `room`."""
        if on:
            self._paused.discard(room)
        else:
            self._paused.add(room)

    def paused_rooms(self) -> list[str]:
        """Every room currently paused, sorted."""
        return sorted(self._paused)

    def reset(self) -> None:
        """Forget every pause: every room is back to on."""
        self._paused.clear()


_store = MonitoringStore()


def get_monitoring_store() -> MonitoringStore:
    """The one shared `MonitoringStore` instance for this process."""
    return _store
