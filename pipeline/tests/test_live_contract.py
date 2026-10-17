"""The live socket's messages, against `contracts/live_message.schema.json`.

The live view crosses the pipeline/web boundary over one WebSocket (SPEC section 16
decision B), so its messages are a shared shape like any other and live in
`contracts/` with the rest: a `oneOf` keyed on `type`, generated from
`routine_watch.contracts.LiveMessage`.

These tests hold both sides to it. One recorded scenario is replayed through
`/ws/live` with fakes only and every message it sends is validated, the `paused`
answer with it, and the schema's branches have to be exactly the messages that turn
up: a message that changes shape, or that only one side knows about, fails here
rather than on stage.
"""

import json
import re
from typing import Any, get_args

import pytest
from fastapi import WebSocketDisconnect
from fastapi.testclient import TestClient
from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError as SchemaValidationError
from pydantic import ValidationError

from routine_watch import live
from routine_watch.api import app
from routine_watch.contracts import LiveMessage, StepStateName, repo_root, schema_name
from routine_watch.demo import DEMO_RESIDENT, demo_residents
from routine_watch.monitoring import get_monitoring_store

CONTRACTS_DIR = repo_root() / "contracts"
SCHEMA_PATH = CONTRACTS_DIR / f"{schema_name(LiveMessage)}.schema.json"

#: The dashboard's own copy of the protocol, hand-written against the same messages.
USE_LIVE_SESSION = repo_root() / "web" / "src" / "live" / "useLiveSession.ts"

#: The demo's bad session (SPEC section 10 beat 4): the one recording that sends every
#: message a session has, errors included.
SCENARIO = "tea_skip_teabag_pour_twice"

#: Every message a session sends (`routine_watch.live`), first one first.
SESSION_MESSAGES = ("session_start", "step_state", "frame", "step", "error", "session_end")

#: And the one the API sends when the room is not being watched (SPEC section 12),
#: in place of the session or of the rest of it.
PAUSED = "paused"

#: mrs-k's room: every `/ws/live` session lands against her (`routine_watch.live`).
MRS_K_ROOM = next(r["room"] for r in demo_residents() if r["id"] == DEMO_RESIDENT)

#: Fast enough that a recorded session plays out inside a test.
FAST = 1000.0

#: The dashboard's union, from `export type LiveMessage =` to the blank line after it.
_TS_UNION = re.compile(r"export type LiveMessage =(.*?)\n\n", re.DOTALL)


@pytest.fixture(autouse=True)
def _every_room_on():
    """Every test starts and ends with monitoring on, so a session plays."""
    get_monitoring_store().reset()
    yield
    get_monitoring_store().reset()


def schema() -> dict[str, Any]:
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


def validator() -> Draft202012Validator:
    """The on-disk schema, checked against the JSON Schema metaschema first."""
    Draft202012Validator.check_schema(schema())
    return Draft202012Validator(schema())


def live_messages(scenario: str = SCENARIO) -> list[dict[str, Any]]:
    """Every message of one live session, as the dashboard receives it."""
    with TestClient(app) as client:
        url = f"/ws/live?scenario={scenario}&speed={FAST}"
        with client.websocket_connect(url) as websocket:
            messages = []
            while True:
                messages.append(websocket.receive_json())
                if messages[-1]["type"] == "session_end":
                    return messages


def paused_message() -> dict[str, Any]:
    """The socket's one message when this resident's room is already on pause."""
    with TestClient(app) as client:
        client.put(f"/rooms/{MRS_K_ROOM}/monitoring", json={"on": False})
        url = f"/ws/live?scenario={SCENARIO}&speed={FAST}"
        with client.websocket_connect(url) as websocket:
            message = websocket.receive_json()
            with pytest.raises(WebSocketDisconnect):  # and nothing else: no session ran
                websocket.receive_json()
    return message


def test_the_schema_has_one_branch_per_message() -> None:
    document = schema()
    Draft202012Validator.check_schema(document)
    branches = document["discriminator"]

    assert branches["propertyName"] == "type"
    assert set(branches["mapping"]) == {*SESSION_MESSAGES, PAUSED}
    assert {option["$ref"] for option in document["oneOf"]} == set(branches["mapping"].values())
    assert len(document["oneOf"]) == len(branches["mapping"])


def test_every_message_of_a_live_session_validates() -> None:
    check = validator()

    messages = live_messages()

    for message in messages:
        check.validate(message)
        LiveMessage.model_validate(message)
    # The session's own six, and no seventh the schema has never been shown.
    assert {message["type"] for message in messages} == set(SESSION_MESSAGES)
    assert [message["type"] for message in messages[:2]] == ["session_start", "step_state"]
    assert messages[-1]["type"] == "session_end"


def test_the_paused_answer_validates() -> None:
    check = validator()

    message = paused_message()

    check.validate(message)
    assert message["type"] == PAUSED
    assert LiveMessage.model_validate(message).root.room == MRS_K_ROOM


def test_a_message_cannot_smuggle_a_field_past_the_schema() -> None:
    check = validator()
    end = live_messages()[-1]

    check.validate(end)

    with pytest.raises(SchemaValidationError):
        check.validate(end | {"frame_jpeg": "iVBORw0KGgo="})


@pytest.mark.parametrize(
    "message",
    [
        pytest.param({"type": "session_paused", "room": MRS_K_ROOM}, id="unknown-type"),
        pytest.param({"type": PAUSED}, id="missing-field"),
        pytest.param(
            {"type": "step_state", "states": {"stir": "skipped"}},
            id="state-the-task-map-cannot-draw",
        ),
        pytest.param(
            {
                "type": "session_end",
                "errors": [],
                "score": -1.0,
                "flag": False,
                "alert_id": None,
                "quality": "ok",
            },
            id="score-below-zero",
        ),
    ],
)
def test_the_schema_rejects(message: dict[str, Any]) -> None:
    with pytest.raises(SchemaValidationError):
        validator().validate(message)

    with pytest.raises(ValidationError):
        LiveMessage.model_validate(message)


def test_the_step_states_match_the_live_module() -> None:
    assert get_args(StepStateName) == get_args(live.StepState)


def test_the_dashboard_lists_the_same_messages() -> None:
    union = _TS_UNION.search(USE_LIVE_SESSION.read_text(encoding="utf-8"))

    assert union is not None
    listed = set(re.findall(r"type: '(\w+)'", union.group(1)))
    assert listed == set(schema()["discriminator"]["mapping"])


def test_the_contracts_readme_lists_the_protocol() -> None:
    assert SCHEMA_PATH.name in (CONTRACTS_DIR / "README.md").read_text(encoding="utf-8")
