import pytest

from routine_watch import explain_claude
from routine_watch.explain import TemplateExplainer
from routine_watch.explain_claude import ClaudeExplainer, get_explainer

ERRORS = [{"type": "omission", "step_id": "teabag_in_cup", "t_start": 42}]
BASELINE = {"observed": 1, "baseline_mean": 0.2, "baseline_days": 14}
CONTEXT: list[str] = []


class _Content:
    def __init__(self, text: str) -> None:
        self.text = text


class _Message:
    def __init__(self, text: str) -> None:
        self.content = [_Content(text)]


class FakeMessages:
    def __init__(self, text: str | None = None, error: Exception | None = None) -> None:
        self._text = text
        self._error = error
        self.calls: list[dict] = []

    def create(self, **kwargs: object) -> _Message:
        self.calls.append(kwargs)
        if self._error is not None:
            raise self._error
        return _Message(self._text or "")


class FakeClient:
    def __init__(self, text: str | None = None, error: Exception | None = None) -> None:
        self.messages = FakeMessages(text=text, error=error)


@pytest.fixture(autouse=True)
def _bypass_cache(monkeypatch):
    """Call straight through to the fake client: the cache itself is already covered
    by test_api_cache.py, and tests must never set LIVE_API (AGENTS.md lessons)."""
    monkeypatch.setattr(
        explain_claude, "cached_call", lambda namespace, request, fn, cache_dir=None: fn()
    )


def test_good_reply_is_used():
    client = FakeClient(
        text="Flagged for review: 1 error this session (skipped teabag in cup at 0:42) "
        "vs 0.2 normally."
    )
    result = ClaudeExplainer(client=client).summarise(ERRORS, BASELINE, CONTEXT)
    assert result == client.messages._text


def test_diagnosed_reply_is_rejected():
    client = FakeClient(text="This session suggests the resident should be diagnosed with a UTI.")
    result = ClaudeExplainer(client=client).summarise(ERRORS, BASELINE, CONTEXT)
    assert result == TemplateExplainer().summarise(ERRORS, BASELINE, CONTEXT)


def test_invented_timestamp_is_rejected():
    client = FakeClient(
        text="Flagged for review: an error happened at 3:17, unlike the usual pattern."
    )
    result = ClaudeExplainer(client=client).summarise(ERRORS, BASELINE, CONTEXT)
    assert result == TemplateExplainer().summarise(ERRORS, BASELINE, CONTEXT)


def test_too_many_sentences_is_rejected():
    client = FakeClient(
        text="One sentence. Two sentences. Three sentences. Four sentences is too many."
    )
    result = ClaudeExplainer(client=client).summarise(ERRORS, BASELINE, CONTEXT)
    assert result == TemplateExplainer().summarise(ERRORS, BASELINE, CONTEXT)


def test_exception_falls_back_to_template():
    client = FakeClient(error=RuntimeError("timeout"))
    result = ClaudeExplainer(client=client).summarise(ERRORS, BASELINE, CONTEXT)
    assert result == TemplateExplainer().summarise(ERRORS, BASELINE, CONTEXT)


def test_model_defaults_to_env_or_constant(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_MODEL", raising=False)
    client = FakeClient(text="No errors this session vs 0.2 normally over 14 days.")
    ClaudeExplainer(client=client).summarise(ERRORS, BASELINE, CONTEXT)
    assert client.messages.calls[0]["model"] == "claude-haiku-4-5"

    monkeypatch.setenv("ANTHROPIC_MODEL", "claude-sonnet-4-5")
    client = FakeClient(text="No errors this session vs 0.2 normally over 14 days.")
    ClaudeExplainer(client=client).summarise(ERRORS, BASELINE, CONTEXT)
    assert client.messages.calls[0]["model"] == "claude-sonnet-4-5"


def test_get_explainer_default_is_template(monkeypatch):
    monkeypatch.delenv("LIVE_API", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    assert isinstance(get_explainer(), TemplateExplainer)


def test_get_explainer_live_with_key_is_claude(monkeypatch):
    monkeypatch.setenv("LIVE_API", "1")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    assert isinstance(get_explainer(), ClaudeExplainer)


def test_get_explainer_live_without_key_is_template(monkeypatch):
    monkeypatch.setenv("LIVE_API", "1")
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    assert isinstance(get_explainer(), TemplateExplainer)
