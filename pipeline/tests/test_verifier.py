"""The Gemini step verifier (SPEC sections 6.2 and 16, decision A): `resolve` settling
an uncertain event with a `Verifier`'s answer, and `GeminiVerifier` building that answer
over a stubbed HTTP transport. No test here reaches the network - `FakeVerifier` for
`resolve`, and an `httpx2.MockTransport` for everything Gemini-shaped.
"""

from __future__ import annotations

import json
from unittest.mock import Mock

import httpx2
import pytest

from routine_watch.api_cache import LiveApiDisabled
from routine_watch.contracts import ObjectLabel, StepEvent, StepSource
from routine_watch.verifier import (
    MAX_IMAGES,
    FakeVerifier,
    GeminiVerifier,
    VerifierResult,
    get_verifier,
    resolve,
)

SESSION = "session-1"
CANDIDATES = ["fill_kettle", "boil"]


def _event(*, step_id: str = "boil", confidence: float = 0.4) -> StepEvent:
    return StepEvent(
        event_id=f"{SESSION}:{step_id}@0",
        session_id=SESSION,
        step_id=step_id,
        objects=[ObjectLabel.KETTLE],
        t_start=0.0,
        t_end=1.0,
        confidence=confidence,
        source=StepSource.RULE,
        unclear=confidence < 0.6,
    )


# --------------------------------------------------------------------- FakeVerifier


def test_fake_verifier_returns_configured_answer():
    answer = VerifierResult(step_id="fill_kettle", objects=["kettle"], confidence=0.9)
    verifier = FakeVerifier({"fill_kettle,boil": answer})
    assert verifier.verify([b"frame"], CANDIDATES) is answer
    assert verifier.calls == [([b"frame"], CANDIDATES, 3.0)]


def test_fake_verifier_defaults_to_none_for_unconfigured_candidates():
    verifier = FakeVerifier()
    assert verifier.verify([b"frame"], CANDIDATES) is None


def test_fake_verifier_raises_configured_exception():
    verifier = FakeVerifier({"fill_kettle,boil": RuntimeError("network down")})
    with pytest.raises(RuntimeError, match="network down"):
        verifier.verify([b"frame"], CANDIDATES)


# ------------------------------------------------------------------------------ resolve


def test_resolve_confident_answer_switches_source_and_clears_unclear():
    event = _event()
    verifier = FakeVerifier(
        {"fill_kettle,boil": VerifierResult(step_id="boil", objects=["kettle"], confidence=0.88)}
    )
    resolved = resolve(event, verifier, [b"frame"], CANDIDATES)
    assert resolved.step_id == "boil"
    assert resolved.objects == [ObjectLabel.KETTLE]
    assert resolved.confidence == 0.88
    assert resolved.source is StepSource.VERIFIER
    assert resolved.unclear is False


def test_resolve_none_answer_is_unclear():
    event = _event()
    resolved = resolve(event, FakeVerifier(), [b"frame"], CANDIDATES)
    assert resolved.unclear is True
    assert resolved.source is StepSource.RULE
    assert resolved.step_id == event.step_id


def test_resolve_exception_is_unclear():
    event = _event()
    verifier = FakeVerifier({"fill_kettle,boil": TimeoutError("too slow")})
    resolved = resolve(event, verifier, [b"frame"], CANDIDATES)
    assert resolved.unclear is True
    assert resolved.source is StepSource.RULE


def test_resolve_answer_outside_candidates_is_unclear():
    event = _event()
    answer = VerifierResult(step_id="stir", objects=["spoon"], confidence=0.95)
    verifier = FakeVerifier({"fill_kettle,boil": answer})
    resolved = resolve(event, verifier, [b"frame"], CANDIDATES)
    assert resolved.unclear is True
    assert resolved.step_id == event.step_id


def test_resolve_answer_with_unknown_object_is_unclear():
    event = _event()
    answer = VerifierResult(step_id="boil", objects=["microwave"], confidence=0.9)
    verifier = FakeVerifier({"fill_kettle,boil": answer})
    resolved = resolve(event, verifier, [b"frame"], CANDIDATES)
    assert resolved.unclear is True


def test_resolve_null_step_id_answer_is_unclear():
    event = _event()
    answer = VerifierResult(step_id=None, objects=[], confidence=0.1)
    verifier = FakeVerifier({"fill_kettle,boil": answer})
    resolved = resolve(event, verifier, [b"frame"], CANDIDATES)
    assert resolved.unclear is True


# --------------------------------------------------------------------- get_verifier


def test_get_verifier_defaults_to_fake(monkeypatch):
    monkeypatch.delenv("LIVE_API", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    assert isinstance(get_verifier(), FakeVerifier)


def test_get_verifier_without_key_stays_fake_even_if_live(monkeypatch):
    monkeypatch.setenv("LIVE_API", "1")
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    assert isinstance(get_verifier(), FakeVerifier)


def test_get_verifier_uses_gemini_when_live_and_keyed(monkeypatch):
    monkeypatch.setenv("LIVE_API", "1")
    monkeypatch.setenv("GEMINI_API_KEY", "secret")
    monkeypatch.setenv("GEMINI_MODEL", "gemini-test-model")
    verifier = get_verifier()
    assert isinstance(verifier, GeminiVerifier)
    assert verifier._model == "gemini-test-model"


# -------------------------------------------------------------------- GeminiVerifier


def _gemini_response(step_id: str | None, objects: list[str], confidence: float) -> httpx2.Response:
    payload = {"step_id": step_id, "objects": objects, "confidence": confidence}
    body = {"candidates": [{"content": {"parts": [{"text": json.dumps(payload)}]}}]}
    return httpx2.Response(200, json=body)


def test_gemini_verifier_parses_a_confident_answer(tmp_path, monkeypatch):
    monkeypatch.setenv("LIVE_API", "1")
    calls = []

    def handler(request: httpx2.Request) -> httpx2.Response:
        calls.append(request)
        return _gemini_response("boil", ["kettle"], 0.82)

    verifier = GeminiVerifier(
        api_key="secret",
        transport=httpx2.MockTransport(handler),
        cache_dir=tmp_path,
    )
    result = verifier.verify([b"frame-1", b"frame-2"], CANDIDATES)
    assert result == VerifierResult(step_id="boil", objects=["kettle"], confidence=0.82)
    assert len(calls) == 1
    sent = json.loads(calls[0].content)
    assert len(sent["contents"][0]["parts"]) == 3  # two images, one text prompt
    assert "fill_kettle" in sent["contents"][0]["parts"][-1]["text"]


def test_gemini_verifier_caps_images_at_max_images(tmp_path, monkeypatch):
    monkeypatch.setenv("LIVE_API", "1")

    def handler(request: httpx2.Request) -> httpx2.Response:
        sent = json.loads(request.content)
        assert len(sent["contents"][0]["parts"]) == MAX_IMAGES + 1  # + the text prompt
        return _gemini_response("boil", [], 0.7)

    verifier = GeminiVerifier(
        api_key="secret",
        transport=httpx2.MockTransport(handler),
        cache_dir=tmp_path,
    )
    images = [f"frame-{i}".encode() for i in range(MAX_IMAGES + 5)]
    verifier.verify(images, CANDIDATES)


def test_gemini_verifier_caches_so_the_transport_is_called_once(tmp_path, monkeypatch):
    monkeypatch.setenv("LIVE_API", "1")
    calls = []

    def handler(request: httpx2.Request) -> httpx2.Response:
        calls.append(request)
        return _gemini_response("boil", ["kettle"], 0.82)

    verifier = GeminiVerifier(
        api_key="secret", transport=httpx2.MockTransport(handler), cache_dir=tmp_path
    )
    first = verifier.verify([b"frame"], CANDIDATES)
    second = verifier.verify([b"frame"], CANDIDATES)
    assert first == second
    assert len(calls) == 1


def test_gemini_verifier_timeout_is_not_cached_and_propagates(tmp_path, monkeypatch):
    monkeypatch.setenv("LIVE_API", "1")

    def handler(request: httpx2.Request) -> httpx2.Response:
        raise httpx2.TimeoutException("too slow")

    verifier = GeminiVerifier(
        api_key="secret", transport=httpx2.MockTransport(handler), cache_dir=tmp_path
    )
    with pytest.raises(httpx2.TimeoutException):
        verifier.verify([b"frame"], CANDIDATES, timeout_s=0.01)
    assert list(tmp_path.rglob("*.json")) == []


def test_gemini_verifier_timeout_resolves_to_unclear_through_resolve(tmp_path, monkeypatch):
    monkeypatch.setenv("LIVE_API", "1")

    def handler(request: httpx2.Request) -> httpx2.Response:
        raise httpx2.TimeoutException("too slow")

    verifier = GeminiVerifier(
        api_key="secret", transport=httpx2.MockTransport(handler), cache_dir=tmp_path
    )
    event = _event()
    resolved = resolve(event, verifier, [b"frame"], CANDIDATES)
    assert resolved.unclear is True


def test_gemini_verifier_without_live_api_raises_without_calling_transport(tmp_path, monkeypatch):
    monkeypatch.setenv("LIVE_API", "0")
    handler = Mock(side_effect=AssertionError("must not be called"))
    verifier = GeminiVerifier(
        api_key="secret", transport=httpx2.MockTransport(handler), cache_dir=tmp_path
    )
    with pytest.raises(LiveApiDisabled):
        verifier.verify([b"frame"], CANDIDATES)
    handler.assert_not_called()
