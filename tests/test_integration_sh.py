"""scripts/integration.sh's page checks: text that is there must never read as
a failure.

`echo "$dom" | grep -q X` under `set -o pipefail` reports 141 about half the
time on a 60 KB DOM: grep -q exits at its first match, echo is killed by SIGPIPE
with the rest of the DOM unwritten, and pipefail hands the pipeline echo's 141.
That is how the integration check reported "dashboard did not render" against a
dashboard that rendered perfectly well (T367). The script searches captured text
with contains()/contains_any_ci() instead, which have no pipeline to lose.
"""

import os
import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / "scripts" / "integration.sh"


def bash_function(name):
    """The named function, copied out of scripts/integration.sh."""
    text = SCRIPT.read_text()
    start = text.find(f"\n{name}() {{\n")
    assert start != -1, f"expected a multi-line {name}() in {SCRIPT.name}"
    end = text.index("\n}\n", start)
    return text[start : end + 3]


# A quarter of a megabyte, built in the shell: far more than a 64 KB pipe can
# hold, and too long to pass as an argument or an environment variable.
PAD = 'pad=x; while [ ${#pad} -lt 200000 ]; do pad="$pad$pad"; done'

# The phrases integration.sh treats as "the app blew up".
ERROR_PHRASES = '"something went wrong" "uncaught" "cannot read prop"'


def run_with_helpers(body):
    """Run `body` with integration.sh's own helpers and its own shell options."""
    script = "\n".join(
        ["set -uo pipefail", bash_function("contains"), bash_function("contains_any_ci"), body]
    )
    return subprocess.run(
        ["bash", "-c", script],
        capture_output=True,
        text=True,
        cwd=REPO,
        env=dict(os.environ),
        timeout=60,
    )


def test_a_match_near_the_start_of_a_huge_dom_always_succeeds():
    """The failing case: needle first, then far more text than a pipe can hold."""
    body = f"""{PAD}
    dom="<title>Routinely</title>$pad"
    for _ in $(seq 1 25); do contains "$dom" "Routinely"; printf "%s " "$?"; done"""

    done = run_with_helpers(body)

    assert done.returncode == 0, done.stderr
    assert set(done.stdout.split()) == {"0"}, f"contains() reported {done.stdout.strip()}"


def test_a_dom_without_the_app_title_still_fails():
    done = run_with_helpers('contains "<html><body></body></html>" "Routinely"')

    assert done.returncode == 1, done.stdout + done.stderr


def test_the_error_phrases_are_matched_whatever_the_case_and_however_long_the_dom():
    body = f"""{PAD}
    dom="$pad<p>Something Went Wrong</p>"
    contains_any_ci "$dom" {ERROR_PHRASES}
    """

    done = run_with_helpers(body)

    assert done.returncode == 0, done.stdout + done.stderr


def test_a_healthy_dom_matches_none_of_the_error_phrases():
    body = f'contains_any_ci "<h1>Routinely</h1>" {ERROR_PHRASES}'

    done = run_with_helpers(body)

    assert done.returncode == 1, done.stdout + done.stderr


def test_no_check_pipes_captured_text_into_grep_q():
    """The regression itself: one such pipeline is one flaky check."""
    code = [
        line
        for line in SCRIPT.read_text().splitlines()
        if not line.lstrip().startswith("#") and "| grep -" in line
    ]

    assert code == [], f"pipes into grep under pipefail (SIGPIPE 141 on a match): {code}"


def test_the_render_check_still_looks_for_the_app_title_and_still_fails_loudly():
    text = SCRIPT.read_text()

    assert 'contains "$body" "Routinely"' in text
    assert "dashboard did not render" in text


def test_a_title_only_dom_does_not_satisfy_the_render_check():
    """index.html's static <title>Routinely</title> sits in <head> whether
    or not React ever mounted; a DOM dump with an empty <body> must still read
    as "did not render" (T426), not pass on the head's title alone."""
    body = """
    dom="<html><head><title>Routinely</title></head><body></body></html>"
    body=${dom#*<body}
    contains "$body" "Routinely"
    """

    done = run_with_helpers(body)

    assert done.returncode == 1, done.stdout + done.stderr


def test_a_rendered_body_satisfies_the_render_check():
    body = """
    dom="<html><head><title>Routinely</title></head><body><h1>Routinely</h1></body></html>"
    body=${dom#*<body}
    contains "$body" "Routinely"
    """

    done = run_with_helpers(body)

    assert done.returncode == 0, done.stdout + done.stderr
