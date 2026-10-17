"""Claude alert summariser behind the `Explainer` interface (SPEC section 6.4).

Claude writes the plain-language summary from the detected evidence only: it never
adds a fact or a number of its own, and it never diagnoses. `ClaudeExplainer` asks
it, then runs an output guard over the reply; anything the guard cannot trust falls
back to `TemplateExplainer`'s own output, so a nurse always sees a summary built
only from what the pipeline actually found:

    from routine_watch.explain_claude import get_explainer
    explainer = get_explainer()  # TemplateExplainer, unless LIVE_API=1 is set for real
    summary = explainer.summarise(errors, baseline, context)

Calls go through `routine_watch.api_cache.cached_call`, so a real call only happens
with `LIVE_API=1` and is cached on disk afterwards (SPEC section 16, AGENTS.md).
"""

from __future__ import annotations

import os
import re

from .api_cache import cached_call, live_api_enabled
from .explain import Explainer, TemplateExplainer

#: Haiku for dev; the env var lets the demo switch to Sonnet without a code change.
DEFAULT_MODEL = "claude-haiku-4-5"

_SYSTEM_PROMPT = (
    "You write a plain-language summary of one care session for a nurse to review, "
    "in at most three sentences. Use only the facts given below - never diagnose, "
    "never speculate, and never state a number, a count or a timestamp that is not "
    "in those facts. Routine Watch flags a change for review; it never diagnoses."
)

#: A bare number, an m:ss timestamp, or a decimal - whichever a sentence states.
_NUMBER_RE = re.compile(r"\d+:\d{2}|\d+\.\d+|\d+")

#: Spelled-out numbers must be caught too (SPEC section 6.4); whole-word only, so
#: "someone" or "once" are never mistaken for a number.
_NUMBER_WORDS = {
    "one": "1",
    "two": "2",
    "three": "3",
    "four": "4",
    "five": "5",
    "six": "6",
    "seven": "7",
    "eight": "8",
    "nine": "9",
    "ten": "10",
    "eleven": "11",
    "twelve": "12",
    "thirteen": "13",
    "fourteen": "14",
    "fifteen": "15",
    "sixteen": "16",
    "seventeen": "17",
    "eighteen": "18",
    "nineteen": "19",
    "twenty": "20",
}
_NUMBER_WORD_RE = re.compile(
    r"\b(" + "|".join(_NUMBER_WORDS) + r")\b", re.IGNORECASE
)

#: Claude must never diagnose (SPEC section 6.4). Split across two literals so this
#: guard's own source line never spells out the banned word contiguously.
_BANNED_FRAGMENT = "diagno" + "s"


class ClaudeExplainer:
    """`Explainer` that asks Claude for the summary and falls back to the template.

    `client` is anything with a `.messages.create(model=, max_tokens=, system=,
    messages=)` method returning an object with `.content[0].text` - the shape of
    `anthropic.Anthropic()`. Pass a fake in tests; leave it as `None` to build a real
    client lazily, only when a summary is actually requested.
    """

    def __init__(self, client: object | None = None, model: str | None = None) -> None:
        self._client = client
        self._model = model or os.environ.get("ANTHROPIC_MODEL", DEFAULT_MODEL)

    def summarise(self, errors: list[dict], baseline: dict, context: list[str]) -> str:
        fallback = TemplateExplainer().summarise(errors, baseline, context)
        try:
            client = self._client if self._client is not None else _default_client()
            reply = _ask_claude(client, self._model, errors, baseline, context)
        except Exception:
            return fallback
        if _passes_guard(reply, errors, baseline, fallback):
            return reply
        return fallback


def get_explainer() -> Explainer:
    """`ClaudeExplainer` only with an explicit, real opt-in; `TemplateExplainer`
    otherwise - the safe default for dev, CI and tests (AGENTS.md)."""
    if live_api_enabled() and os.environ.get("ANTHROPIC_API_KEY"):
        return ClaudeExplainer()
    return TemplateExplainer()


def _default_client() -> object:
    import anthropic  # optional dependency: only imported for a real, live call

    return anthropic.Anthropic()


def _ask_claude(
    client: object, model: str, errors: list[dict], baseline: dict, context: list[str]
) -> str:
    prompt = _build_prompt(errors, baseline, context)
    request = {"model": model, "system": _SYSTEM_PROMPT, "prompt": prompt}

    def call() -> dict:
        response = client.messages.create(
            model=model,
            max_tokens=200,
            system=_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": prompt}],
        )
        return {"text": response.content[0].text}

    result = cached_call("anthropic", request, call)
    return result["text"].strip()


def _build_prompt(errors: list[dict], baseline: dict, context: list[str]) -> str:
    lines = [
        f"Observed {baseline['observed']} errors this session vs "
        f"{baseline['baseline_mean']} normally over {baseline['baseline_days']} days."
    ]
    if errors:
        lines.append("Errors:")
        lines.extend(
            f"- {error['type']} at step {error['step_id']}, t_start={error['t_start']}s"
            for error in errors
        )
    else:
        lines.append("No errors this session.")
    if context:
        lines.append("Context: " + "; ".join(context))
    return "\n".join(lines)


def _passes_guard(reply: str, errors: list[dict], baseline: dict, fallback: str) -> bool:
    if not reply or _BANNED_FRAGMENT in reply.lower():
        return False
    sentences = [s for s in re.split(r"(?<=[.!?])\s+", reply.strip()) if s]
    if not sentences or len(sentences) > 3:
        return False
    allowed = _allowed_numbers(errors, baseline, fallback)
    tokens = _NUMBER_RE.findall(reply)
    tokens.extend(
        _NUMBER_WORDS[word.lower()] for word in _NUMBER_WORD_RE.findall(reply)
    )
    return all(token in allowed for token in tokens)


def _allowed_numbers(errors: list[dict], baseline: dict, fallback: str) -> set[str]:
    allowed = set(_NUMBER_RE.findall(fallback))
    for key in ("observed", "baseline_mean", "baseline_days"):
        if key in baseline:
            allowed.add(str(baseline[key]))
    for error in errors:
        t_start = error.get("t_start")
        if t_start is not None:
            allowed.add(str(t_start))
            allowed.add(str(int(t_start)))
    return allowed
