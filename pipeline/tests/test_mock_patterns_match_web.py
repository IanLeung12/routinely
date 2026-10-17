import re
from pathlib import Path

from routine_watch.patterns_library import LIBRARY

WEB_MOCK_PATTERNS_PATH = (
    Path(__file__).resolve().parents[2] / "web" / "src" / "patterns" / "mockPatterns.ts"
)

_PATTERN_ID_RE = re.compile(r"pattern_id:\s*'([^']+)'")
_URGENCY_RE = re.compile(r"urgency:\s*'([^']+)'")
_CHECKS_RE = re.compile(r"checks:\s*\[([^\]]*)\]")
_STRING_RE = re.compile(r"'([^']*)'")


def _web_patterns() -> dict[str, dict]:
    text = WEB_MOCK_PATTERNS_PATH.read_text()
    starts = [match.start() for match in _PATTERN_ID_RE.finditer(text)]
    ids = [match.group(1) for match in _PATTERN_ID_RE.finditer(text)]
    blocks = [
        text[start : starts[index + 1] if index + 1 < len(starts) else len(text)]
        for index, start in enumerate(starts)
    ]
    return {
        pattern_id: {
            "urgency": _URGENCY_RE.search(block).group(1),
            "checks": _STRING_RE.findall(_CHECKS_RE.search(block).group(1)),
        }
        for pattern_id, block in zip(ids, blocks, strict=True)
    }


def test_web_mock_pattern_ids_match_python_library():
    assert set(_web_patterns()) == {pattern.pattern_id for pattern in LIBRARY}


def test_web_mock_patterns_match_python_urgency_and_checks():
    web_patterns = _web_patterns()
    for pattern in LIBRARY:
        web = web_patterns[pattern.pattern_id]
        assert web["urgency"] == pattern.urgency.value, pattern.pattern_id
        assert web["checks"] == [str(check) for check in pattern.checks], pattern.pattern_id
