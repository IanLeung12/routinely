"""scripts/kaze_demo.py against a stand-in for the check-in API (SPEC §18).

The runner is the thing under test here: its requests, its waiting on a countdown it
does not own, its transcript and - above all - its checks. So the API it talks to is a
small fake in this file (the subset of T450's routes the runner uses, with the same
payload shapes and the same rules), and the interesting tests are the ones where the
fake is *wrong*: a countdown that never fires, a payload that leaks a location it was
not given, a duress answer the person's screen could tell apart. Each of those must
make the matching scenario fail, which is what says the runner checks the flow rather
than narrating it.

The real state machine and the real routes have their own tests
(`pipeline/tests/test_checkin.py`, `test_api_checkin.py`); the runner against the real
stack is `python3 scripts/kaze_demo.py all` (docs/KAZE.md).

Root `tests/` runs with no project dependencies (`scripts/ci.sh`: `uv run --with
pytest --no-project`), so everything here is the standard library.
"""

import json
import socket
import subprocess
import sys
import threading
import urllib.parse
from datetime import UTC, datetime, timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / "scripts" / "kaze_demo.py"

SCENARIOS = [
    "safe",
    "no-response",
    "duress",
    "disconnect",
    "unacknowledged",
    "false-alarm",
    "privacy",
]

PERSON = "mrs-k"
FIRST = "nurse-ana"
SECOND = "care-line"
SAFETY_PIN = "1234"
DURESS_PIN = "9111"

#: Short enough that a scenario plays out inside a test, long enough that the handful
#: of requests a scenario makes before answering cannot race the window on a loaded
#: machine. (The real API's floor is 5s; nothing here is the real API, and the point is
#: to exercise the runner's waiting rather than its arithmetic.)
WINDOW_S = 1.0


def _iso(when):
    return None if when is None else when.isoformat().replace("+00:00", "Z")


class FakeKaze:
    """The check-in API's rules, small enough to read: one person, two supporters.

    Not the real state machine - that one is pure, injected-clock and tested on its
    own. This is a stand-in with the same payloads, so the runner's HTTP calls and
    checks can be exercised without a stack, and can be broken on purpose.
    """

    def __init__(self, **broken):
        #: Ways to be wrong on purpose. Each one must make a scenario fail.
        self.leak_location = broken.pop("leak_location", False)
        self.no_countdown = broken.pop("no_countdown", False)
        self.duress_tells = broken.pop("duress_tells", False)
        assert not broken, f"unknown option: {broken}"
        self.settings = {
            "person_id": PERSON,
            "name": "Mrs. K",
            "checkin_window_s": WINDOW_S,
            "ack_window_s": WINDOW_S,
            "location": "Room 204, care home",
            "location_simulated": True,
            "supporters": [
                {
                    "id": FIRST,
                    "name": "Nurse Ana",
                    "relationship": "nurse",
                    "share": {"location": True, "alert_details": True, "replay": True},
                },
                {
                    "id": SECOND,
                    "name": "Care line (on call)",
                    "relationship": "carer",
                    "share": {"location": False, "alert_details": False, "replay": False},
                },
            ],
            "safety_pin_set": True,
            "duress_pin_set": True,
        }
        self.checkins = {}
        self.by_alert = {}

    # -- the rules -------------------------------------------------------------

    @property
    def supporters(self):
        return [one["id"] for one in self.settings["supporters"]]

    def share_of(self, supporter):
        found = next((one for one in self.settings["supporters"] if one["id"] == supporter), None)
        return found["share"] if found else {"location": False, "alert_details": False, "replay": False}

    def start(self, person, alert_id):
        if person != PERSON:
            raise Answer(404, "no safety settings for that person")
        if alert_id is not None and alert_id in self.by_alert:
            return self.checkins[self.by_alert[alert_id]]
        now = datetime.now(UTC)
        record = {
            "checkin_id": f"checkin-{person}-{len(self.checkins) + 1}",
            "person_id": person,
            "alert_id": alert_id,
            "state": "pending",
            "started_at": now,
            "deadline": now + timedelta(seconds=self.settings["checkin_window_s"]),
            "duress": False,
            "silent": False,
            "device_online": True,
            "supporter": None,
            "notified": [],
            "acknowledged_by": None,
            "resolved_by": None,
            "resolved_reason": None,
            "events": [],
        }
        self.log(record, "started", "server", detail=alert_id)
        self.checkins[record["checkin_id"]] = record
        if alert_id is not None:
            self.by_alert[alert_id] = record["checkin_id"]
        return record

    def log(self, record, event, actor, detail=None):
        record["events"].append(
            {
                "at": _iso(datetime.now(UTC)),
                "event": event,
                "actor": actor,
                "state": record["state"],
                "detail": detail,
            }
        )

    def advance(self, record):
        """What the server's own countdown does: the question becomes an alarm, and an
        unanswered alarm moves down the list."""
        if self.no_countdown:
            return record
        while record["deadline"] is not None and datetime.now(UTC) >= record["deadline"]:
            at = record["deadline"]
            nxt = next((one for one in self.supporters if one not in record["notified"]), None)
            if nxt is None:
                record["deadline"] = None
                self.log(record, "escalation_exhausted", "server", detail="nobody left to alarm")
                break
            record["state"] = "alarm" if record["state"] == "pending" else "escalated"
            record["supporter"] = nxt
            record["notified"] = [*record["notified"], nxt]
            record["deadline"] = at + timedelta(seconds=self.settings["ack_window_s"])
            self.log(record, "alarmed" if record["state"] == "alarm" else "escalated", "server", nxt)
        return record

    def get(self, checkin_id):
        record = self.checkins.get(checkin_id)
        if record is None:
            raise Answer(404, "no such check-in")
        return self.advance(record)

    def raise_alarm(self, record, event, actor):
        first = self.supporters[0] if self.supporters else None
        record["state"] = "alarm"
        record["supporter"] = first
        record["notified"] = [first] if first else []
        record["deadline"] = (
            datetime.now(UTC) + timedelta(seconds=self.settings["ack_window_s"]) if first else None
        )
        self.log(record, event, actor, detail="duress" if event == "duress" else first)

    # -- what each audience sees -----------------------------------------------

    def person_state(self, record):
        """A duress check-in reads as cancelled on the person's own screen."""
        if record["duress"] and not self.duress_tells:
            return "ok"
        return record["state"]

    def person_view(self, record):
        state = self.person_state(record)
        masked = state != record["state"]
        return {
            "checkin_id": record["checkin_id"],
            "person_id": record["person_id"],
            "state": state,
            "ask": "Can you check in?",
            "started_at": _iso(record["started_at"]),
            "deadline": None if masked else _iso(record["deadline"]),
            "seconds_left": None if masked else self.seconds_left(record),
            "device_online": record["device_online"],
            "resolved_reason": None if masked else record["resolved_reason"],
        }

    def seconds_left(self, record):
        if record["deadline"] is None:
            return None
        return max(0.0, round((record["deadline"] - datetime.now(UTC)).total_seconds(), 3))

    def supporter_view(self, record, supporter):
        share = self.share_of(supporter)
        view = {
            "checkin_id": record["checkin_id"],
            "person_id": record["person_id"],
            "person_name": self.settings["name"],
            "state": record["state"],
            "ask": "Is everyone okay?",
            "duress": record["duress"],
            "silent": record["silent"],
            "started_at": _iso(record["started_at"]),
            "deadline": _iso(record["deadline"]),
            "seconds_left": self.seconds_left(record),
            "for_supporter": supporter,
            "supporter": record["supporter"],
            "notified": list(record["notified"]),
            "acknowledged_by": record["acknowledged_by"],
            "resolved_by": record["resolved_by"],
            "resolved_reason": record["resolved_reason"],
            "device_online": record["device_online"],
        }
        if share["location"] or self.leak_location:
            view["location"] = self.settings["location"]
            view["location_simulated"] = True
        if share["alert_details"]:
            view["alert_id"] = record["alert_id"]
            view["events"] = list(record["events"])
        if share["replay"]:
            view["replays_url"] = f"/people/{record['person_id']}/replays"
        return view

    def active(self):
        return [self.advance(record) for record in self.checkins.values()]

    # -- the routes ------------------------------------------------------------

    def route(self, method, path, query, body):
        parts = [part for part in path.split("/") if part]
        if method == "GET" and parts == ["checkins", "active"]:
            return self.list_active(query)
        if method == "POST" and parts == ["checkins", "demo"]:
            record = self.start(body.get("person", PERSON), body.get("alert_id"))
            return {"checkin": self.person_view(record)}
        if method == "POST" and len(parts) == 3 and parts[0] == "checkins":
            return self.act(parts[1], parts[2], body)
        if len(parts) == 3 and parts[0] == "people" and parts[2] == "safety":
            if parts[1] != PERSON:
                raise Answer(404, "no safety settings for that person")
            if method == "PUT":
                for key, value in body.items():
                    self.settings[key] = value
            return dict(self.settings)
        raise Answer(404, f"no route for {method} {path}")

    def list_active(self, query):
        person, supporter = query.get("person", [""])[0], query.get("supporter", [""])[0]
        if bool(person) == bool(supporter):
            raise Answer(422, "say who is asking: ?person= or ?supporter=, not both")
        if person:
            if person != PERSON:
                raise Answer(404, "no safety settings for that person")
            return {
                "checkins": [
                    self.person_view(record)
                    for record in self.active()
                    if self.person_state(record) not in ("ok", "resolved")
                ]
            }
        return {
            "checkins": [
                self.supporter_view(record, supporter)
                for record in self.active()
                if supporter in record["notified"] and record["state"] not in ("ok", "resolved")
            ]
        }

    def act(self, checkin_id, action, body):
        record = self.get(checkin_id)
        if action == "respond":
            if body.get("pin") not in (SAFETY_PIN, DURESS_PIN):
                raise Answer(401, "that is not the check-in PIN")
            if record["state"] != "pending":
                raise Answer(409, "this check-in is not waiting for an answer any more")
            if body["pin"] == SAFETY_PIN:
                record["state"], record["deadline"] = "ok", None
                self.log(record, "checked_in", "person")
            else:
                record["duress"] = record["silent"] = True
                self.raise_alarm(record, "duress", "person")
            return {"checkin": self.person_view(record)}
        if action == "ack":
            supporter = body["supporter"]
            if supporter not in self.supporters:
                raise Answer(404, "this supporter is not on that person's list")
            if record["state"] not in ("alarm", "escalated"):
                raise Answer(409, "this check-in is not waiting to be acknowledged")
            record.update(
                state="acknowledged", deadline=None, supporter=supporter, acknowledged_by=supporter
            )
            self.log(record, "acknowledged", supporter)
            return {"checkin": self.supporter_view(record, supporter)}
        if action == "resolve":
            by = body["by"]
            if by != "person" and by not in self.supporters:
                raise Answer(404, "this supporter is not on that person's list")
            if record["state"] in ("ok", "resolved"):
                raise Answer(409, "this check-in is already closed")
            record.update(
                state="resolved", deadline=None, resolved_by=by, resolved_reason=body["reason"]
            )
            self.log(record, "resolved", by, detail=body["reason"])
            view = self.person_view(record) if by == "person" else self.supporter_view(record, by)
            return {"checkin": view}
        if action == "simulate":
            record["device_online"] = body["event"] == "reconnect"
            self.log(record, "reconnected" if record["device_online"] else "disconnected", "person")
            return {"checkin": self.person_view(record)}
        raise Answer(404, f"no such action: {action}")


class Answer(Exception):
    """An HTTP status the fake means to send."""

    def __init__(self, status, detail):
        super().__init__(detail)
        self.status = status
        self.detail = detail


def serve(fake):
    """`fake` on a loopback port of its own. Returns (url, shutdown)."""

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            self.answer("GET")

        def do_POST(self):
            self.answer("POST")

        def do_PUT(self):
            self.answer("PUT")

        def answer(self, method):
            length = int(self.headers.get("Content-Length") or 0)
            raw = self.rfile.read(length) if length else b""
            parsed = urllib.parse.urlparse(self.path)
            try:
                body = json.loads(raw) if raw else {}
                payload = fake.route(method, parsed.path, urllib.parse.parse_qs(parsed.query), body)
                status = 200
            except Answer as answer:
                status, payload = answer.status, {"detail": answer.detail}
            except Exception as exc:  # a broken fake must read as a 500, not a hang
                status, payload = 500, {"detail": f"{type(exc).__name__}: {exc}"}
            encoded = json.dumps(payload).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(encoded)))
            self.end_headers()
            self.wfile.write(encoded)

        def log_message(self, *_args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()

    def close():
        server.shutdown()
        server.server_close()

    return f"http://127.0.0.1:{server.server_port}", close


@pytest.fixture
def stack():
    """A fake stack, and the fake behind it, for the length of one test."""

    made = []

    def start(**broken):
        fake = FakeKaze(**broken)
        url, shutdown = serve(fake)
        made.append(shutdown)
        return url, fake

    yield start
    for shutdown in made:
        shutdown()


def a_closed_port():
    """A port nothing is listening on: bound to find a free one, then let go."""
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def run_demo(*args, cwd=REPO):
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        capture_output=True,
        text=True,
        cwd=cwd,
        timeout=180,
    )


# ------------------------------------------------------------------------- the CLI


def test_help_works_and_names_every_scenario():
    done = run_demo("--help")

    assert done.returncode == 0, done.stderr
    for name in SCENARIOS:
        assert name in done.stdout, f"--help never mentions {name}"


def test_list_says_what_each_scenario_is_for():
    done = run_demo("--list")

    assert done.returncode == 0, done.stderr
    lines = [line for line in done.stdout.splitlines() if line.strip()]
    assert [line.split()[0] for line in lines] == SCENARIOS
    assert all(len(line.split(maxsplit=1)[1]) > 10 for line in lines)


def test_naming_no_scenario_at_all_is_a_usage_error():
    done = run_demo()

    assert done.returncode == 2
    assert "which scenario" in done.stderr


def test_an_unknown_scenario_is_a_usage_error():
    done = run_demo("not-a-scenario")

    assert done.returncode == 2
    assert "not-a-scenario" in done.stderr


def test_a_stack_that_is_not_there_says_how_to_start_one():
    done = run_demo("safe", "--api-url", f"http://127.0.0.1:{a_closed_port()}")

    assert done.returncode == 1
    assert "scripts/dev.sh up" in done.stderr


# ------------------------------------------------------- the seven, end to end


@pytest.mark.parametrize("name", SCENARIOS)
def test_every_scenario_plays_out_and_exits_zero(stack, name):
    url, fake = stack()

    done = run_demo(name, "--api-url", url)

    assert done.returncode == 0, done.stdout + done.stderr
    assert f"OK {name}" in done.stdout
    assert "1 of 1 scenario(s) OK" in done.stdout
    # Nothing is left ringing for whoever runs the next one.
    assert [record for record in fake.checkins.values() if record["state"] in ("alarm", "escalated")] == []


def test_all_runs_every_scenario_in_order(stack):
    url, _fake = stack()

    done = run_demo("all", "--api-url", url)

    assert done.returncode == 0, done.stdout + done.stderr
    assert "7 of 7 scenario(s) OK" in done.stdout
    assert [line.split()[1] for line in done.stdout.splitlines() if line.startswith("OK ")] == SCENARIOS


def test_a_run_prints_every_state_change_with_the_time_it_happened(stack):
    url, _fake = stack()

    done = run_demo("unacknowledged", "--api-url", url)

    assert done.returncode == 0, done.stdout + done.stderr
    states = [line for line in done.stdout.splitlines() if "s  " in line]
    for state in ("pending", "alarm", "escalated", "acknowledged", "resolved"):
        assert any(state in line for line in states), f"no line about {state}"
    assert f"waiting on {FIRST}" in done.stdout
    assert f"alarmed {FIRST}, {SECOND}" in done.stdout


def test_the_windows_it_shortened_are_put_back(stack):
    url, fake = stack()
    before = (fake.settings["checkin_window_s"], fake.settings["ack_window_s"])

    done = run_demo("safe", "--api-url", url, "--checkin-window", "1.5", "--ack-window", "1.5")

    assert done.returncode == 0, done.stdout + done.stderr
    assert "1.5" in done.stdout  # it said what it changed
    assert (fake.settings["checkin_window_s"], fake.settings["ack_window_s"]) == before


def test_sharing_it_switched_off_is_put_back(stack):
    url, fake = stack()
    before = json.dumps(fake.settings["supporters"], sort_keys=True)

    done = run_demo("privacy", "--api-url", url)

    assert done.returncode == 0, done.stdout + done.stderr
    assert json.dumps(fake.settings["supporters"], sort_keys=True) == before


# ------------------------------------------- a stack that is wrong must fail


def test_a_countdown_that_never_fires_fails_the_no_response_scenario(stack):
    url, _fake = stack(no_countdown=True)

    done = run_demo("no-response", "--api-url", url)

    assert done.returncode == 1
    assert "FAILED no-response" in done.stderr
    assert "countdown" in done.stderr


def test_a_leaked_location_fails_the_privacy_scenario(stack):
    url, _fake = stack(leak_location=True)

    done = run_demo("privacy", "--api-url", url)

    assert done.returncode == 1
    assert "FAILED privacy" in done.stderr
    assert "location" in done.stderr


def test_a_duress_answer_the_person_could_tell_apart_fails_the_duress_scenario(stack):
    url, _fake = stack(duress_tells=True)

    done = run_demo("duress", "--api-url", url)

    assert done.returncode == 1
    assert "FAILED duress" in done.stderr


def test_one_failure_does_not_stop_the_others_and_the_run_still_fails(stack):
    url, _fake = stack(leak_location=True)

    done = run_demo("all", "--api-url", url)

    assert done.returncode == 1
    assert "1 of 7 scenario(s) failed: privacy" in done.stderr
    assert "OK safe" in done.stdout and "OK no-response" in done.stdout
