"""Push alert notifier behind the `Notifier` interface (SPEC Nice-to-have 3, section 10
step 4: "her sparkline spikes ... and the nurse's phone or dashboard alerts").

`FakeNotifier` is what every test, CI and the offline/dashboard-only path use.
`SupabaseNotifier` inserts one row per alert into a `alerts_feed` table (columns:
`alert_id`, `resident_id`, `summary`, `created_at`) over Supabase's PostgREST endpoint,
with plain HTTP - no Supabase SDK. A client subscribed to that table over Supabase
Realtime is how a phone would actually get pushed to; wiring a route to call `send` is
a separate task.

    from routine_watch.notify import get_notifier
    notifier = get_notifier()  # FakeNotifier, unless LIVE_API=1 and Supabase env vars
    notifier.send({"alert_id": ..., "resident_id": ..., "summary": ..., "created_at": ...})

A network failure is logged and swallowed: a push alert is a bonus, never a reason to
break the pipeline (AGENTS.md).
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from datetime import datetime
from typing import Protocol

import httpx2

from .api_cache import live_api_enabled

logger = logging.getLogger(__name__)


class Notifier(Protocol):
    def send(self, alert: dict) -> None:
        """Push `alert` out. Must never raise: a failed push is logged and dropped."""
        ...


@dataclass
class FakeNotifier:
    """A notifier for tests and the default path: no network, just records calls."""

    sent: list[dict] = field(default_factory=list)

    def send(self, alert: dict) -> None:
        self.sent.append(dict(alert))


class SupabaseNotifier:
    """The real notifier: one REST insert into `alerts_feed` per alert.

    `transport` is the one seam tests use: an `httpx2.MockTransport` stands in for the
    network, so no test ever makes a real call.
    """

    def __init__(
        self,
        url: str,
        key: str,
        *,
        transport: httpx2.BaseTransport | None = None,
        timeout_s: float = 3.0,
    ) -> None:
        self._url = url.rstrip("/")
        self._key = key
        self._transport = transport
        self._timeout_s = timeout_s

    def send(self, alert: dict) -> None:
        body = _payload(alert)
        try:
            with httpx2.Client(transport=self._transport, timeout=self._timeout_s) as client:
                response = client.post(
                    f"{self._url}/rest/v1/alerts_feed",
                    json=body,
                    headers={
                        "apikey": self._key,
                        "Authorization": f"Bearer {self._key}",
                        "Content-Type": "application/json",
                        "Prefer": "return=minimal",
                    },
                )
                response.raise_for_status()
        except Exception:
            logger.warning(
                "alerts_feed push failed for alert %s", body.get("alert_id"), exc_info=True
            )


def _payload(alert: dict) -> dict:
    created_at = alert.get("created_at")
    if isinstance(created_at, datetime):
        created_at = created_at.isoformat()
    return {
        "alert_id": alert.get("alert_id"),
        "resident_id": alert.get("resident_id"),
        "summary": alert.get("summary"),
        "created_at": created_at,
    }


def get_notifier() -> Notifier:
    """The notifier the rest of the pipeline should use.

    `FakeNotifier` unless `LIVE_API=1` and both `SUPABASE_URL` and
    `SUPABASE_SERVICE_ROLE_KEY` are set (AGENTS.md: no paid/real call is ever a side
    effect of running tests, CI, replay or the tester)."""
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    if live_api_enabled() and url and key:
        return SupabaseNotifier(url, key)
    return FakeNotifier()
