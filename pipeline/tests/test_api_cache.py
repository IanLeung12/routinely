import hashlib
import json
from unittest.mock import Mock

import pytest

from routine_watch.api_cache import (
    LiveApiDisabled,
    cached_call,
    live_api_enabled,
    request_key,
)


@pytest.mark.parametrize("value", [None, "0", "true", "yes", "", "1"])
def test_live_api_requires_exact_opt_in(monkeypatch, value):
    if value is None:
        monkeypatch.delenv("LIVE_API", raising=False)
    else:
        monkeypatch.setenv("LIVE_API", value)
    assert live_api_enabled() is (value == "1")


def test_key_is_stable_and_matches_specification():
    request = {"z": [1, 2], "a": {"b": "hello"}}
    expected = hashlib.sha256(
        ("gemini" + json.dumps(request, sort_keys=True, separators=(",", ":"))).encode()
    ).hexdigest()
    assert request_key("gemini", request) == expected
    assert request_key("gemini", {"a": {"b": "hello"}, "z": [1, 2]}) == expected
    assert request_key("claude", request) != expected


def test_cache_hit_does_not_call_api_when_disabled(tmp_path, monkeypatch):
    monkeypatch.setenv("LIVE_API", "0")
    path = tmp_path / "gemini" / f"{request_key('gemini', {})}.json"
    path.parent.mkdir()
    path.write_text('{"answer": "cached"}', encoding="utf-8")
    fn = Mock(side_effect=AssertionError("API must not be called"))
    assert cached_call("gemini", {}, fn, tmp_path) == {"answer": "cached"}
    fn.assert_not_called()


def test_miss_raises_without_live_api(tmp_path, monkeypatch):
    monkeypatch.setenv("LIVE_API", "0")
    fn = Mock()
    with pytest.raises(LiveApiDisabled):
        cached_call("gemini", {}, fn, tmp_path)
    fn.assert_not_called()
    assert list(tmp_path.iterdir()) == []


def test_live_miss_is_cached_and_namespaces_are_separate(tmp_path, monkeypatch):
    monkeypatch.setenv("LIVE_API", "1")
    fn = Mock(return_value={"answer": "fresh"})
    assert cached_call("gemini", {}, fn, tmp_path) == {"answer": "fresh"}
    assert cached_call("gemini", {}, fn, tmp_path) == {"answer": "fresh"}
    fn.assert_called_once_with()
    other = Mock(return_value={"answer": "other"})
    assert cached_call("claude", {}, other, tmp_path) == {"answer": "other"}
    other.assert_called_once_with()
    assert len(list(tmp_path.rglob("*.json"))) == 2
    assert not list(tmp_path.rglob("*.tmp"))


def test_cache_directory_environment_override(tmp_path, monkeypatch):
    monkeypatch.setenv("API_CACHE_DIR", str(tmp_path))
    monkeypatch.setenv("LIVE_API", "1")
    assert cached_call("gemini", {}, lambda: {"ok": True}) == {"ok": True}
    assert (tmp_path / "gemini" / f"{request_key('gemini', {})}.json").is_file()


def test_failed_api_call_does_not_write_cache(tmp_path, monkeypatch):
    monkeypatch.setenv("LIVE_API", "1")
    with pytest.raises(RuntimeError, match="unavailable"):
        cached_call("gemini", {}, Mock(side_effect=RuntimeError("unavailable")), tmp_path)
    assert not list(tmp_path.rglob("*"))
