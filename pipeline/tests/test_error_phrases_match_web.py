import re
from pathlib import Path

from routine_watch.explain import _PHRASES

WEB_ERROR_TYPES_PATH = (
    Path(__file__).resolve().parents[2] / "web" / "src" / "ui" / "errorTypes.ts"
)

_ENTRY_RE = re.compile(r"(\w+):\s*\(step\)\s*=>\s*`([^`]*)`,")


def _web_phrases() -> dict[str, str]:
    text = WEB_ERROR_TYPES_PATH.read_text()
    phrases_block = text.split("const PHRASES", 1)[1]
    return {
        error_type: template.replace("${step}", "{step}")
        for error_type, template in _ENTRY_RE.findall(phrases_block)
    }


def test_web_phrases_have_same_error_types_as_python():
    assert set(_web_phrases()) == set(_PHRASES)


def test_web_phrases_match_python_wording():
    web_phrases = _web_phrases()
    for error_type, python_template in _PHRASES.items():
        assert web_phrases[error_type] == python_template, error_type
