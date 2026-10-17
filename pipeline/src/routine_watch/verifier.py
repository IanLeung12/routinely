"""Gemini step verifier (SPEC sections 6.2 and 16, decision A).

`routine_watch.recogniser.needs_verifier` picks out step events too weak to stand on
their own: a frame or two of weak support, or none at all. This module is what answers
them: a handful of low-res JPEG frames from the capture ring buffer, cropped to the
counter, go to a vision LLM alongside the task's candidate steps, and it says which one
happened and with what objects - or it does not, and the event stays `unclear`.

`FakeVerifier` is what every test and the offline/CI path use; nothing here reaches the
network unless `LIVE_API=1` and a key is configured (`get_verifier`). `GeminiVerifier`
talks to Gemini over plain REST (no SDK dependency beyond the HTTP client already in
this project) and never writes a frame to disk: `routine_watch.api_cache.cached_call`
keys its cache on a hash of the images, not their bytes, so only Gemini's JSON answer
is ever persisted.
"""

from __future__ import annotations

import base64
import hashlib
import json
import os
from dataclasses import dataclass, field
from typing import Protocol

import httpx2

from .api_cache import cached_call, live_api_enabled
from .contracts import ObjectLabel, StepEvent, StepSource

#: SPEC section 16, decision A: 4-8 frames is the budget for one verifier call.
MAX_IMAGES = 8

#: Cheapest model that works for this task (SPEC section 16); overridden by GEMINI_MODEL.
DEFAULT_GEMINI_MODEL = "gemini-2.5-flash-lite"

_GEMINI_API_BASE = "https://generativelanguage.googleapis.com/v1beta"

_PROMPT = (
    "You are watching a kitchenette from above during a tea-making task. The images "
    "are consecutive frames from one short, uncertain moment. Decide which of these "
    "steps the person is doing: {candidates}. Respond with only a JSON object, no "
    "other text: "
    '{{"step_id": one of the listed steps or null if none fits, '
    '"objects": a list of the object names actually involved, '
    '"confidence": your confidence from 0 to 1}}.'
)


@dataclass(frozen=True)
class VerifierResult:
    """Gemini's answer for one uncertain moment: which step, with what, how sure."""

    step_id: str | None
    objects: list[str]
    confidence: float


class Verifier(Protocol):
    def verify(
        self, images: list[bytes], candidates: list[str], timeout_s: float = 3.0
    ) -> VerifierResult | None:
        """Which of `candidates` these JPEG `images` show, or None if unclear."""
        ...


@dataclass
class FakeVerifier:
    """A verifier for tests and the offline path: no network, canned answers only.

    `answers` maps a comma-joined `candidates` list to what `verify` should do: a
    `VerifierResult` to answer confidently, `None` to come back unclear, or an
    `Exception` instance to raise it (so a caller's error handling can be tested without
    a real network failure). Candidates not in `answers` come back `None`.
    """

    answers: dict[str, VerifierResult | None | Exception] | None = None
    calls: list[tuple[list[bytes], list[str], float]] = field(default_factory=list, init=False)

    def verify(
        self, images: list[bytes], candidates: list[str], timeout_s: float = 3.0
    ) -> VerifierResult | None:
        self.calls.append((list(images), list(candidates), timeout_s))
        answer = (self.answers or {}).get(",".join(candidates))
        if isinstance(answer, Exception):
            raise answer
        return answer


class GeminiVerifier:
    """The real verifier: REST to Gemini's `generateContent`, cached and capped.

    `transport` is the one seam tests use: an `httpx2.MockTransport` stands in for the
    network, so no test ever makes a real call. A live cache miss goes through
    `routine_watch.api_cache.cached_call`, which raises `LiveApiDisabled` unless
    `LIVE_API=1` - that propagates out of `verify` like any other failure.
    """

    def __init__(
        self,
        api_key: str,
        model: str = DEFAULT_GEMINI_MODEL,
        *,
        transport: httpx2.BaseTransport | None = None,
        cache_dir=None,
    ) -> None:
        self._api_key = api_key
        self._model = model
        self._transport = transport
        self._cache_dir = cache_dir

    def verify(
        self, images: list[bytes], candidates: list[str], timeout_s: float = 3.0
    ) -> VerifierResult | None:
        images = images[-MAX_IMAGES:]
        request = {
            "model": self._model,
            "candidates": list(candidates),
            # Only a hash of each frame goes into the cache key; the bytes never do.
            "images": [hashlib.sha256(image).hexdigest() for image in images],
        }
        response = cached_call(
            "gemini", request, lambda: self._call(images, candidates, timeout_s), self._cache_dir
        )
        return _parse_response(response, candidates)

    def _call(self, images: list[bytes], candidates: list[str], timeout_s: float) -> dict:
        parts = [
            {"inline_data": {"mime_type": "image/jpeg", "data": base64.b64encode(image).decode()}}
            for image in images
        ]
        parts.append({"text": _PROMPT.format(candidates=", ".join(candidates))})
        body = {
            "contents": [{"parts": parts}],
            "generationConfig": {"response_mime_type": "application/json"},
        }
        # Left to propagate, not caught: a timeout or network failure must not be
        # cached as if it were Gemini's answer. `resolve` treats any exception from
        # `verify` as unclear, same as a clean None.
        with httpx2.Client(transport=self._transport, timeout=timeout_s) as client:
            reply = client.post(
                f"{_GEMINI_API_BASE}/models/{self._model}:generateContent",
                json=body,
                headers={"x-goog-api-key": self._api_key},
            )
            reply.raise_for_status()
        return reply.json()


def _parse_response(response: dict, candidates: list[str]) -> VerifierResult | None:
    """Gemini's reply, read back into a `VerifierResult`, or None if it never answered."""
    candidate_list = response.get("candidates")
    if not candidate_list:
        return VerifierResult(step_id=None, objects=[], confidence=0.0)
    text = candidate_list[0]["content"]["parts"][0]["text"]
    answer = json.loads(text)
    return VerifierResult(
        step_id=answer.get("step_id"),
        objects=list(answer.get("objects", [])),
        confidence=float(answer.get("confidence", 0.0)),
    )


def get_verifier() -> Verifier:
    """The verifier the rest of the pipeline should use.

    `FakeVerifier` unless `LIVE_API=1` and `GEMINI_API_KEY` is set (SPEC section 16,
    decision A keeps this opt-in: no paid call is ever a side effect of running tests,
    CI, replay or the tester).
    """
    api_key = os.environ.get("GEMINI_API_KEY")
    if live_api_enabled() and api_key:
        model = os.environ.get("GEMINI_MODEL", DEFAULT_GEMINI_MODEL)
        return GeminiVerifier(api_key=api_key, model=model)
    return FakeVerifier()


def resolve(
    event: StepEvent, verifier: Verifier, images: list[bytes], candidates: list[str]
) -> StepEvent:
    """`event`, settled by `verifier`: confident -> `source="verifier"`; otherwise
    `unclear=True` and `event` is returned unchanged (None, timeout, exception, or an
    answer outside `candidates` all land here - a verifier that cannot help is no
    different from one that was never asked, SPEC section 7)."""
    try:
        result = verifier.verify(images, candidates)
    except Exception:
        return event.model_copy(update={"unclear": True})
    if result is None or result.step_id is None or result.step_id not in candidates:
        return event.model_copy(update={"unclear": True})
    try:
        objects = [ObjectLabel(label) for label in result.objects]
    except ValueError:
        return event.model_copy(update={"unclear": True})
    return event.model_copy(
        update={
            "step_id": result.step_id,
            "objects": objects,
            "confidence": result.confidence,
            "source": StepSource.VERIFIER,
            "unclear": False,
        }
    )
