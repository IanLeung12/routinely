"""`session_end` says when a session was too unclear to score (SPEC section 12, T343).

An unclear session is already neither scored nor counted towards a flag (T342): too
little of the capture can be trusted - a walker, a blocked view, a dim kitchen - so
`replay.score_session` scores it 0.0 and leaves it out of the resident's history. What
was missing is that nobody is told. A score of 0.0 means "nothing went wrong" for a
clean session and "we could not read it" for an unclear one, and the live screen had no
way to tell those two apart, so it showed the second as the first. `session_end` now
carries `quality`, and these tests are what hold it to the one rule
(`quality.session_quality`) on both paths a session can arrive by.

The pairs below are the point: in each one the two sessions end on the *same* score, the
same errors and the same task map, and only `quality` says that one of them could not be
read. `test_live_camera.py` already compares the two paths message for message over
every recording in the repo, so its helpers drive the sessions here too - a quality the
camera and the fallback disagreed about would fail there as well as here.
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import pytest
from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError as SchemaValidationError
from test_live_camera import RECORDINGS, as_scenario, camera, load_frames, replayed

from routine_watch.contracts import CaptureFrame, LiveMessage, repo_root, schema_name
from routine_watch.live import as_json, scenario_path

#: The live socket's own contract, which `quality` is now a required field of.
SCHEMA_PATH = repo_root() / "contracts" / f"{schema_name(LiveMessage)}.schema.json"

#: A pair of recorded scenarios: the demo's bad session, and the same steps and errors
#: with most of the capture barely seen (`tests/scenarios/*/expected.yaml` pins the
#: quality each one replays to, which is where these two came from).
CLEAR_SCENARIO = "tea_skip_teabag_pour_twice"
UNCLEAR_SCENARIOS = ("tea_session_unclear_no_flag", "meds_session_unclear_no_flag")

#: The one recording written at frame level with a whole task in it: seven steps of
#: making tea, every one of them confidently seen. A camera session can only be played
#: from frames, so this is the clip the camera half of each pair reads.
CLEAR_CLIP = "make_tea"

#: A clip with a single step in it, which is under `session_quality`'s floor of three:
#: a session can be unclear for having barely happened as well as for being badly lit.
THIN_CLIP = "fill_kettle"

#: How sure the detector is of every box once the kitchen is dim, as a share of how sure
#: it was: enough to put every step under `recogniser.MIN_STEP_CONFIDENCE` without
#: changing which steps are there (`dimmed`).
DIM = 0.6


def dimmed(frames: Sequence[CaptureFrame], factor: float = DIM) -> list[CaptureFrame]:
    """The same recording with the detector only `factor` as sure of every box.

    What bad lighting does to a capture stream: the kettle and the cup are still in the
    same places, so the same steps are read off the same frames, but no reading of them
    clears `recogniser.MIN_STEP_CONFIDENCE` any more. Every box is dimmed by the same
    share, because the recogniser picks between two boxes of one class by confidence
    (`recogniser._scenes`) and a session that swapped a box for another would be a
    different recording rather than the same one read badly.
    """
    return [
        frame.model_copy(
            update={
                "objects": [
                    found.model_copy(update={"confidence": round(found.confidence * factor, 3)})
                    for found in frame.objects
                ]
            }
        )
        for frame in frames
    ]


def end_of(messages: Sequence[dict[str, Any]]) -> dict[str, Any]:
    """One session's `session_end`, which is always its last message."""
    assert messages[-1]["type"] == "session_end"
    return messages[-1]


def validator() -> Draft202012Validator:
    """The on-disk schema, checked against the JSON Schema metaschema first."""
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema)


# ------------------------------------------------------- the recorded fallback's path


@pytest.mark.parametrize("name", UNCLEAR_SCENARIOS)
def test_a_replayed_session_the_pipeline_could_not_read_ends_unclear(name: str) -> None:
    end = end_of(replayed(scenario_path(name)))

    assert end["quality"] == "unclear"
    assert end["score"] == 0.0  # never scored, which is the reason for the field


def test_a_replayed_session_that_was_read_clearly_ends_ok() -> None:
    """The demo's bad session (SPEC section 10 beat 4): badly made, clearly seen. The
    score is the session's own, and the screen goes on showing it."""
    end = end_of(replayed(scenario_path(CLEAR_SCENARIO)))

    assert end["quality"] == "ok"
    assert end["score"] > 0.0


def test_the_unclear_replay_ends_on_the_same_errors_as_the_clear_one() -> None:
    """`tea_session_unclear_no_flag` is `tea_skip_teabag_pour_twice`'s steps and errors
    read badly, so the two sessions differ in `quality` and in nothing else a nurse is
    shown: the teabag omission and the second pour are both still there, and only
    `quality` says the capture behind them cannot be trusted."""
    unclear = end_of(replayed(scenario_path("tea_session_unclear_no_flag")))
    clear = end_of(replayed(scenario_path(CLEAR_SCENARIO)))

    def errors(end: dict[str, Any]) -> set[tuple[str, str | None]]:
        return {(error.type.value, error.step_id) for error in end["errors"]}

    assert errors(unclear) == errors(clear)
    assert (unclear["quality"], clear["quality"]) == ("unclear", "ok")


# ------------------------------------------------------------------- the camera's path


def test_a_camera_session_the_detector_could_barely_see_ends_unclear() -> None:
    """One recording, read twice: as filmed, and as a dim kitchen would have it. The
    same seven steps either way - so what the session *did* is not in question - and the
    whole of `session_end` is the same but for `quality`, which is the field's point: a
    nurse looking at the score alone cannot tell the two apart."""
    frames = load_frames(RECORDINGS[CLEAR_CLIP])

    clear = end_of(camera(frames))
    unclear = end_of(camera(dimmed(frames)))

    assert clear["quality"] == "ok"
    assert unclear["quality"] == "unclear"
    assert unclear | {"quality": "ok"} == clear  # 0.0, no errors, nothing flagged: both


def test_a_camera_session_with_barely_a_step_in_it_ends_unclear() -> None:
    """The other half of the rule (`quality.session_quality`): a session can be too thin
    to read as well as too dim. One clear step is not a session to score."""
    end = end_of(camera(load_frames(RECORDINGS[THIN_CLIP])))

    assert end["quality"] == "unclear"


def test_the_camera_and_the_fallback_agree_about_an_unclear_recording(tmp_path: Path) -> None:
    """The acceptance case of `test_live_camera.py`, on the recording this task is
    about: the dashboard cannot tell a camera session from a replay of it, so the two
    paths have to read the same capture as the same quality."""
    frames = dimmed(load_frames(RECORDINGS[CLEAR_CLIP]))

    live_camera_end = end_of(camera(frames))
    fallback_end = end_of(replayed(as_scenario(frames, tmp_path / "dim_kitchen")))

    assert live_camera_end["quality"] == fallback_end["quality"] == "unclear"
    assert live_camera_end == fallback_end


# ----------------------------------------------------------------- against the contract


@pytest.mark.parametrize("quality", ["ok", "unclear"])
def test_every_message_of_a_session_validates_either_way(quality: str) -> None:
    frames = load_frames(RECORDINGS[CLEAR_CLIP])
    check = validator()

    session = camera(frames if quality == "ok" else dimmed(frames))
    messages = [as_json(message) for message in session]

    for message in messages:
        check.validate(message)
        LiveMessage.model_validate(message)
    assert end_of(messages)["quality"] == quality


def test_the_schema_requires_a_quality() -> None:
    """Required, not optional with a default: a `session_end` that left it out would be
    a session nobody can say was readable, which is the state this task removed."""
    end = as_json(end_of(camera(load_frames(RECORDINGS[CLEAR_CLIP]))))

    validator().validate(end)

    with pytest.raises(SchemaValidationError):
        validator().validate({key: value for key, value in end.items() if key != "quality"})
