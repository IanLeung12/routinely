"""The push alert notifier (SPEC Nice-to-have 3, section 10 step 4): `FakeNotifier`
for tests and the default path, `SupabaseNotifier` building the real insert over a
stubbed HTTP transport. No test here reaches the network.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime

import httpx2

from routine_watch.notify import FakeNotifier, Notifier, SupabaseNotifier, get_notifier

ALERT = {
    "alert_id": "alert-1",
    "resident_id": "resident-1",
    "summary": "Two errors this session, above her normal.",
    "created_at": "2026-10-17T06:00:00+00:00",
    "errors": [{"type": "skipped_step"}],  # extra fields must never reach the payload
}


# -------------------------------------------------------------------- FakeNotifier


def test_fake_notifier_records_sent_alerts():
    notifier = FakeNotifier()
    notifier.send(ALERT)
    assert notifier.sent == [ALERT]


def test_fake_notifier_satisfies_notifier_protocol():
    notifier: Notifier = FakeNotifier()
    notifier.send(ALERT)


# -------------------------------------------------------------------- get_notifier


def test_get_notifier_defaults_to_fake(monkeypatch):
    monkeypatch.delenv("LIVE_API", raising=False)
    monkeypatch.delenv("SUPABASE_URL", raising=False)
    monkeypatch.delenv("SUPABASE_SERVICE_ROLE_KEY", raising=False)
    assert isinstance(get_notifier(), FakeNotifier)


def test_get_notifier_without_keys_stays_fake_even_if_live(monkeypatch):
    monkeypatch.setenv("LIVE_API", "1")
    monkeypatch.delenv("SUPABASE_URL", raising=False)
    monkeypatch.delenv("SUPABASE_SERVICE_ROLE_KEY", raising=False)
    assert isinstance(get_notifier(), FakeNotifier)


def test_get_notifier_not_live_stays_fake_even_with_keys(monkeypatch):
    monkeypatch.delenv("LIVE_API", raising=False)
    monkeypatch.setenv("SUPABASE_URL", "https://example.supabase.co")
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "secret")
    assert isinstance(get_notifier(), FakeNotifier)


def test_get_notifier_uses_supabase_when_live_and_keyed(monkeypatch):
    monkeypatch.setenv("LIVE_API", "1")
    monkeypatch.setenv("SUPABASE_URL", "https://example.supabase.co")
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "secret")
    notifier = get_notifier()
    assert isinstance(notifier, SupabaseNotifier)
    assert notifier._url == "https://example.supabase.co"
    assert notifier._key == "secret"


# ------------------------------------------------------------------ SupabaseNotifier


def test_supabase_notifier_posts_expected_url_headers_and_body():
    calls = []

    def handler(request: httpx2.Request) -> httpx2.Response:
        calls.append(request)
        return httpx2.Response(201)

    notifier = SupabaseNotifier(
        "https://example.supabase.co", "secret-key", transport=httpx2.MockTransport(handler)
    )
    notifier.send(ALERT)

    assert len(calls) == 1
    request = calls[0]
    assert request.url == "https://example.supabase.co/rest/v1/alerts_feed"
    assert request.headers["apikey"] == "secret-key"
    assert request.headers["authorization"] == "Bearer secret-key"
    body = json.loads(request.content)
    assert body == {
        "alert_id": "alert-1",
        "resident_id": "resident-1",
        "summary": "Two errors this session, above her normal.",
        "created_at": "2026-10-17T06:00:00+00:00",
    }


def test_supabase_notifier_strips_trailing_slash_from_url():
    calls = []

    def handler(request: httpx2.Request) -> httpx2.Response:
        calls.append(request)
        return httpx2.Response(201)

    notifier = SupabaseNotifier(
        "https://example.supabase.co/", "secret-key", transport=httpx2.MockTransport(handler)
    )
    notifier.send(ALERT)
    assert calls[0].url == "https://example.supabase.co/rest/v1/alerts_feed"


def test_supabase_notifier_serialises_datetime_created_at():
    calls = []

    def handler(request: httpx2.Request) -> httpx2.Response:
        calls.append(request)
        return httpx2.Response(201)

    notifier = SupabaseNotifier(
        "https://example.supabase.co", "secret-key", transport=httpx2.MockTransport(handler)
    )
    alert = dict(ALERT, created_at=datetime(2026, 10, 17, 6, 0, tzinfo=UTC))
    notifier.send(alert)
    body = json.loads(calls[0].content)
    assert body["created_at"] == "2026-10-17T06:00:00+00:00"


def test_supabase_notifier_network_failure_is_logged_and_swallowed(caplog):
    def handler(request: httpx2.Request) -> httpx2.Response:
        raise httpx2.ConnectError("connection refused")

    notifier = SupabaseNotifier(
        "https://example.supabase.co", "secret-key", transport=httpx2.MockTransport(handler)
    )
    notifier.send(ALERT)  # must not raise
    assert "alert-1" in caplog.text


def test_supabase_notifier_http_error_is_logged_and_swallowed(caplog):
    def handler(request: httpx2.Request) -> httpx2.Response:
        return httpx2.Response(500, json={"message": "server error"})

    notifier = SupabaseNotifier(
        "https://example.supabase.co", "secret-key", transport=httpx2.MockTransport(handler)
    )
    notifier.send(ALERT)  # must not raise
    assert "alert-1" in caplog.text
