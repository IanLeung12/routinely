#!/usr/bin/env python3
"""Project KAZE's seven safety check-in scenarios, against a running stack (SPEC §18).

Drives a local stack (`scripts/dev.sh up`) through one scenario at a time over HTTP,
using nothing but the safety check-in API: `POST /checkins/demo`,
`GET /checkins/active`, `POST /checkins/{id}/respond|ack|resolve|simulate` and
`GET/PUT /people/{id}/safety`. It prints every state change as the server makes it and
exits non-zero if the flow does not play out the way SPEC §18 says it must, so this is
a live check of the flow rather than a narration of it.

    python3 scripts/kaze_demo.py --list        # the seven scenarios, one line each
    python3 scripts/kaze_demo.py safe          # one of them
    python3 scripts/kaze_demo.py all           # all seven, demo timings (20s / 15s)
    python3 scripts/kaze_demo.py all --fast    # the same in a third of the time

The waiting is real: the check-in window and each ack window are the server's
countdown, so a scenario that alarms takes as long as that person's windows say. The
demo people are seeded with the short pair (SPEC §18); `--fast` shortens them to the
API's 5s floor for the length of the run and puts them back afterwards.

Nothing here calls, texts or pages anybody - an alarm is a payload a screen shows.
What this demonstrates, what is simulated and what still needs validating: docs/KAZE.md.
"""

from __future__ import annotations

import argparse
import json
import os
import secrets
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field

#: The person the demo opens on (SPEC §17's care-home case: Mrs. K, supported by
#: Nurse Ana and then the on-call care line).
DEFAULT_PERSON = "mrs-k"

#: The demo's seeded PINs (SPEC §18). Not secrets: they are written down in the spec
#: and overwritable with `PUT /people/{id}/safety`.
DEMO_SAFETY_PIN = "1234"
DEMO_DURESS_PIN = "9111"

#: `--fast`: the shortest window the API accepts (`checkin.MIN_WINDOW_S`).
FAST_WINDOW_S = 5.0

#: How often this polls `GET /checkins/active` while waiting for the server's
#: countdown. The server ticks once a second and every route advances before it
#: answers, so twice a second sees a transition as soon as it exists.
POLL_S = 0.5

#: How long after a deadline a transition may still arrive before this calls it a
#: failure: one server tick, plus room for a slow laptop.
SLACK_S = 5.0

HTTP_TIMEOUT_S = 10.0

#: The states in which somebody is still being waited for (`checkin.OPEN_STATES`).
OPEN_STATES = ("pending", "alarm", "escalated", "acknowledged")

PERSON_ASK = "Can you check in?"
SUPPORTER_ASK = "Is everyone okay?"


class DemoError(RuntimeError):
    """The stack did not answer, or a scenario did not play out as SPEC §18 says."""


def default_api_url() -> str:
    """The stack `scripts/dev.sh up` prints, unless `--api-url` says otherwise."""
    return os.environ.get("API_URL", "").strip() or f"http://localhost:{os.environ.get('API_PORT', '8000')}"


# ------------------------------------------------------------------- the HTTP client


@dataclass
class Api:
    """The safety check-in API of a running stack, over plain HTTP.

    Deliberately tiny and dependency-free: this script has to run from a bare
    `python3` on a demo machine, with no venv and nothing installed.
    """

    base_url: str
    timeout: float = HTTP_TIMEOUT_S

    def call(
        self,
        method: str,
        path: str,
        body: dict | None = None,
        *,
        params: dict[str, str] | None = None,
        expect: int = 200,
    ) -> dict:
        """One request, as JSON in and JSON out. Any status but `expect` is a failure."""
        url = self.base_url.rstrip("/") + path
        if params:
            url = f"{url}?{urllib.parse.urlencode(params)}"
        data = None if body is None else json.dumps(body).encode("utf-8")
        headers = {"Content-Type": "application/json"} if data is not None else {}
        request = urllib.request.Request(url, data=data, method=method, headers=headers)
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as answer:
                status, payload = answer.status, answer.read()
        except urllib.error.HTTPError as exc:  # a status is an answer, not a crash
            status, payload = exc.code, exc.read()
        except urllib.error.URLError as exc:
            raise DemoError(
                f"{method} {path}: no answer from {self.base_url} ({exc.reason}). "
                "Is `scripts/dev.sh up` running?"
            ) from exc
        if status != expect:
            detail = payload.decode("utf-8", "replace")[:300]
            raise DemoError(f"{method} {path}: expected HTTP {expect}, got {status}: {detail}")
        if not payload:
            return {}
        try:
            return json.loads(payload)
        except ValueError as exc:
            raise DemoError(f"{method} {path}: answer was not JSON: {payload[:200]!r}") from exc


# ----------------------------------------------------------------- one scenario's run


def _state_key(view: dict) -> tuple:
    """Everything a transcript line says about a check-in, so repeating a poll that
    changed nothing says nothing."""
    return (
        view["state"],
        view.get("supporter"),
        tuple(view.get("notified") or ()),
        view.get("acknowledged_by"),
        view.get("resolved_reason"),
        view.get("device_online"),
        "location" in view,
    )


#: Every key a sharing permission can add to a supporter's payload (SPEC §18), and
#: the permission that puts it there.
SHARED_KEYS = {
    "location": "location",
    "location_simulated": "location",
    "alert_id": "alert_details",
    "events": "alert_details",
    "replays_url": "replay",
}


def _shared_line(view: dict) -> str:
    """Which sharing-gated keys this payload carries, and which are simply not there."""
    has = [key for key in SHARED_KEYS if key in view]
    missing = [key for key in SHARED_KEYS if key not in view]
    parts = [f"carries {', '.join(has)}" if has else "carries nothing beyond the alarm"]
    if missing:
        parts.append(f"no {', '.join(missing)}")
    if "location" in view:
        parts.append(f"location: {view['location']} (simulated)")
    if "events" in view:
        parts.append(f"{len(view['events'])} events logged")
    return "   ".join(parts)


def _state_line(label: str, view: dict) -> str:
    """One state change, as a line somebody watching the demo can follow."""
    parts = [f"{label:<11}", f"{view['state']:<13}", f'"{view["ask"]}"']
    left = view.get("seconds_left")
    if left is not None:
        parts.append(f"{left:.0f}s left")
    if view.get("duress"):
        parts.append("duress, silent" if view.get("silent") else "duress")
    if view.get("supporter") and view["state"] in ("alarm", "escalated"):
        parts.append(f"waiting on {view['supporter']}")
    if view.get("notified"):
        parts.append(f"alarmed {', '.join(view['notified'])}")
    if view.get("acknowledged_by"):
        parts.append(f"on it: {view['acknowledged_by']}")
    if view.get("resolved_reason"):
        closed = f"closed: {view['resolved_reason']}"
        if view.get("resolved_by"):
            closed += f" by {view['resolved_by']}"
        parts.append(closed)
    if view.get("device_online") is False:
        parts.append("device offline")
    if "location" in view:
        parts.append(f"location: {view['location']} (simulated)")
    return "   ".join(parts)


@dataclass
class Demo:
    """One scenario's run: the API, the person it is about, and what has been said.

    Every method either prints something or checks something. `check` is what makes
    this a test: a scenario that does not play out as SPEC §18 says raises `DemoError`
    and the script exits non-zero.
    """

    api: Api
    person: str
    scenario: str
    safety_pin: str = DEMO_SAFETY_PIN
    duress_pin: str = DEMO_DURESS_PIN
    settings: dict = field(default_factory=dict)
    started_at: float = field(default_factory=time.monotonic)
    #: Every check-in this run started, so the cleanup can close the ones it left open.
    opened: list[str] = field(default_factory=list)
    #: The last line printed about one check-in on one audience's screen, so a poll
    #: that changed nothing says nothing.
    said: dict[tuple[str, str], tuple] = field(default_factory=dict)

    # -- talking ---------------------------------------------------------------

    def say(self, text: str) -> None:
        print(f"{time.monotonic() - self.started_at:6.1f}s  {text}", flush=True)

    def note(self, label: str, view: dict) -> None:
        """Print `view` as `label`'s screen would read it, if it has changed."""
        seen = (label, view["checkin_id"])
        key = _state_key(view)
        if self.said.get(seen) == key:
            return
        self.said[seen] = key
        self.say(_state_line(label, view))

    def note_closed(self, label: str, checkin_id: str) -> None:
        """Print that a check-in has left this audience's screen, once."""
        if self.said.get((label, checkin_id)) == ("gone",):
            return
        self.said[(label, checkin_id)] = ("gone",)
        self.say(f"{label:<11}   (nothing to answer: off their screen)")

    def check(self, condition: object, message: str) -> None:
        if not condition:
            raise DemoError(message)

    # -- the API ---------------------------------------------------------------

    def call(self, method: str, path: str, body: dict | None = None, **kwargs) -> dict:
        shown = f" {json.dumps(body)}" if body else ""
        self.say(f"→ {method} {path}{shown}")
        return self.api.call(method, path, body, **kwargs)

    def load_settings(self) -> dict:
        """This person's check-in settings: windows, supporters, what each may see."""
        self.settings = self.api.call("GET", f"/people/{self.person}/safety")
        return self.settings

    @property
    def supporters(self) -> list[dict]:
        return list(self.settings.get("supporters") or ())

    @property
    def checkin_window_s(self) -> float:
        return float(self.settings["checkin_window_s"])

    @property
    def ack_window_s(self) -> float:
        return float(self.settings["ack_window_s"])

    def supporter_at(self, index: int) -> str:
        """The id of supporter #index+1 on this person's list."""
        self.check(
            len(self.supporters) > index,
            f"{self.person} has {len(self.supporters)} supporter(s) linked; this scenario "
            f"needs at least {index + 1}. Try --person mrs-k.",
        )
        return str(self.supporters[index]["id"])

    def start(self, suffix: str = "") -> dict:
        """Ask this person to check in, the way a flagged change does (SPEC §18).

        The alert id is made up and unique per run: `POST /checkins/demo` is idempotent
        per alert, and in the product the id is the alert a flagged session produced.
        """
        alert_id = f"kaze-demo-{self.scenario}{suffix}-{secrets.token_hex(3)}"
        answer = self.call("POST", "/checkins/demo", {"person": self.person, "alert_id": alert_id})
        view = answer["checkin"]
        view["alert_id"] = alert_id  # the person's own payload never carries it
        self.opened.append(view["checkin_id"])
        self.note("person", view)
        self.check(view["state"] == "pending", f"a new check-in should be pending, got {view['state']}")
        self.check(view["ask"] == PERSON_ASK, f"the person should be asked {PERSON_ASK!r}")
        return view

    def respond(self, checkin_id: str, pin: str, *, expect: int = 200) -> dict:
        """The person answering with a PIN. Both PINs answer the same (SPEC §18)."""
        masked = json.dumps({"pin": "*" * len(pin)})
        self.say(f"→ POST /checkins/{checkin_id}/respond {masked}")
        answer = self.api.call("POST", f"/checkins/{checkin_id}/respond", {"pin": pin}, expect=expect)
        if expect == 200:
            self.note("person", answer["checkin"])
            return answer["checkin"]
        return answer

    def ack(self, checkin_id: str, supporter: str) -> dict:
        """A supporter tapping "I'm on it"."""
        answer = self.call("POST", f"/checkins/{checkin_id}/ack", {"supporter": supporter})
        self.note(supporter, answer["checkin"])
        return answer["checkin"]

    def resolve(self, checkin_id: str, by: str, reason: str) -> dict:
        """A supporter or the person closing it, with a reason."""
        answer = self.call("POST", f"/checkins/{checkin_id}/resolve", {"by": by, "reason": reason})
        self.note(by, answer["checkin"])
        return answer["checkin"]

    def simulate(self, checkin_id: str, event: str) -> dict:
        """The person's device dropping off the network, or coming back."""
        answer = self.call("POST", f"/checkins/{checkin_id}/simulate", {"event": event})
        self.note("person", answer["checkin"])
        return answer["checkin"]

    # -- what each audience can see --------------------------------------------

    def person_sees(self, checkin_id: str) -> dict | None:
        """This check-in as it is on the person's own screen, or None if it has left
        it (they checked in, somebody closed it - or they used the duress PIN)."""
        answer = self.api.call("GET", "/checkins/active", params={"person": self.person})
        return next((one for one in answer["checkins"] if one["checkin_id"] == checkin_id), None)

    def supporter_sees(self, checkin_id: str, supporter: str) -> dict | None:
        """This check-in as it reached one supporter, or None if it never did."""
        answer = self.api.call("GET", "/checkins/active", params={"supporter": supporter})
        return next((one for one in answer["checkins"] if one["checkin_id"] == checkin_id), None)

    def nobody_was_woken(self, checkin_id: str) -> None:
        """Check that this check-in is on no supporter's screen at all."""
        for supporter in self.supporters:
            seen = self.supporter_sees(checkin_id, str(supporter["id"]))
            self.check(seen is None, f"{supporter['id']} was alarmed and should not have been")
        self.say(f"{'supporters':<11}   (nobody woken: every supporter's list is empty)")

    # -- waiting for the server's countdown ------------------------------------

    def wait_for(
        self,
        checkin_id: str,
        state: str,
        *,
        supporter: str | None = None,
        seconds: float | None = None,
    ) -> dict:
        """Poll until this check-in reaches `state`, printing every change on the way.

        `supporter` reads a supporter's screen (`?supporter=`), otherwise the person's
        own (`?person=`). The timeout is the window being waited out plus one tick, so
        a countdown that does not fire is a failure rather than a hang.
        """
        label = supporter or "person"
        limit = (seconds if seconds is not None else self.checkin_window_s) + SLACK_S
        until = time.monotonic() + limit
        last: dict | None = None
        while True:
            if supporter is None:
                view = self.person_sees(checkin_id)
            else:
                view = self.supporter_sees(checkin_id, supporter)
            if view is not None:
                last = view
                self.note(label, view)
                if view["state"] == state:
                    return view
            elif last is not None:
                self.note_closed(label, checkin_id)
            if time.monotonic() >= until:
                seen = "nothing" if last is None else f"{last['state']!r}"
                raise DemoError(
                    f"waited {limit:.0f}s for {label} to see {state!r} and saw {seen}. "
                    "The server owns the countdown (SPEC §18): is the API's background "
                    "tick running?"
                )
            time.sleep(POLL_S)

    # -- settings --------------------------------------------------------------

    @contextmanager
    def sharing(self, supporter: str, key: str, on: bool) -> Iterator[None]:
        """Turn one sharing permission on or off for one supporter, then put it back.

        The person decides what each supporter may see (SPEC §18), and this is that
        switch: `PUT /people/{id}/safety` with the list as it is, one flag flipped.
        """
        before = [dict(one) for one in self.supporters]
        after = [
            {**one, "share": {**one["share"], key: on}} if one["id"] == supporter else dict(one)
            for one in before
        ]
        self.call("PUT", f"/people/{self.person}/safety", {"supporters": after})
        try:
            yield
        finally:
            self.say(f"→ PUT /people/{self.person}/safety (putting {supporter}'s sharing back)")
            self.settings = self.api.call(
                "PUT", f"/people/{self.person}/safety", {"supporters": before}
            )

    def close_what_is_left(self) -> None:
        """Close every check-in this run started and left open.

        A scenario that failed half way through must not leave an alarm ringing for
        whoever runs the next one.
        """
        for checkin_id in reversed(self.opened):
            open_now = self.person_sees(checkin_id) or next(
                (
                    seen
                    for supporter in self.supporters
                    if (seen := self.supporter_sees(checkin_id, str(supporter["id"]))) is not None
                ),
                None,
            )
            if open_now is None:
                continue
            self.say(f"cleanup: closing {checkin_id} ({open_now['state']})")
            try:
                self.resolve(checkin_id, "person", "other")
            except DemoError as exc:  # never hide the scenario's own failure behind this
                print(f"warning: could not close {checkin_id}: {exc}", file=sys.stderr)


# ------------------------------------------------------------------- the 7 scenarios


def scenario_safe(demo: Demo) -> None:
    """1. The person checks in, and nobody is woken."""
    started = demo.start()
    checkin_id = started["checkin_id"]
    demo.check(
        started["seconds_left"] is not None and started["seconds_left"] > 0,
        "a pending check-in should be counting down",
    )
    demo.nobody_was_woken(checkin_id)

    # A wrong PIN is a 401 and changes nothing: whoever is counting carries on.
    wrong = next(pin for pin in ("0000", "1111", "4321") if pin not in (demo.safety_pin, demo.duress_pin))
    demo.respond(checkin_id, wrong, expect=401)
    still = demo.person_sees(checkin_id)
    demo.check(still is not None and still["state"] == "pending", "a wrong PIN must change nothing")
    demo.say(f"{'person':<11}   (wrong PIN refused, 401; the countdown carries on)")

    answered = demo.respond(checkin_id, demo.safety_pin)

    demo.check(answered["state"] == "ok", f"the safety PIN should answer ok, got {answered['state']}")
    demo.check(answered["seconds_left"] is None, "nothing should still be counting")
    demo.check(demo.person_sees(checkin_id) is None, "their own screen should be clear")
    demo.nobody_was_woken(checkin_id)


def scenario_no_response(demo: Demo) -> None:
    """2. Nobody answers the question, so supporter #1 is alarmed."""
    first = demo.supporter_at(0)
    started = demo.start()
    checkin_id = started["checkin_id"]
    demo.check(demo.supporter_sees(checkin_id, first) is None, f"{first} was woken too early")

    alarmed = demo.wait_for(checkin_id, "alarm", supporter=first)

    demo.check(alarmed["ask"] == SUPPORTER_ASK, f"a supporter should be asked {SUPPORTER_ASK!r}")
    demo.check(alarmed["supporter"] == first, f"supporter #1 ({first}) should be the one asked")
    demo.check(alarmed["notified"] == [first], f"only {first} should have been alarmed, got {alarmed['notified']}")
    demo.check(
        alarmed["seconds_left"] is not None and alarmed["seconds_left"] > 0,
        "their ack window should be counting down",
    )

    taken = demo.ack(checkin_id, first)

    demo.check(taken["state"] == "acknowledged", f"\"I'm on it\" should acknowledge, got {taken['state']}")
    demo.check(taken["acknowledged_by"] == first, "the acknowledgement should name who took it")
    demo.check(taken["seconds_left"] is None, "nothing should still be counting: escalation stopped")
    demo.resolve(checkin_id, first, "helped")


def scenario_duress(demo: Demo) -> None:
    """3. The duress PIN alarms, and the person's own screen cannot tell."""
    first = demo.supporter_at(0)
    safely = demo.start("-safety")
    safe_answer = demo.respond(safely["checkin_id"], demo.safety_pin)

    coerced = demo.start("-duress")
    duress_answer = demo.respond(coerced["checkin_id"], demo.duress_pin)

    # Two different check-ins, so the id and the start differ; everything the person's
    # screen actually reads is the same. (`test_api_checkin.py` holds the stronger
    # version: same check-in, same clock, byte-for-byte identical responses.)
    drop = {"checkin_id", "started_at"}
    same = {key: value for key, value in safe_answer.items() if key not in drop}
    also = {key: value for key, value in duress_answer.items() if key not in drop}
    demo.say(f"{'person':<11}   safety PIN → {json.dumps(same, sort_keys=True)}")
    demo.say(f"{'person':<11}   duress PIN → {json.dumps(also, sort_keys=True)}")
    demo.check(same == also, "the duress answer must read exactly like checking in")
    demo.check("duress" not in json.dumps(duress_answer), "the person's payload must never say duress")
    demo.check(demo.person_sees(coerced["checkin_id"]) is None, "their own screen should read as cancelled")

    alarm = demo.supporter_sees(coerced["checkin_id"], first)

    demo.check(alarm is not None, f"{first} should have a silent duress alarm")
    demo.note(first, alarm)
    demo.check(alarm["state"] == "alarm", f"the duress alarm should be out, got {alarm['state']}")
    demo.check(alarm["duress"] is True, "the supporter's payload should say it was duress")
    demo.check(alarm["silent"] is True, "a duress alarm must be silent on the person's side")
    demo.check(
        demo.supporter_sees(safely["checkin_id"], first) is None,
        "checking in with the safety PIN must not alarm anybody",
    )
    demo.resolve(coerced["checkin_id"], first, "helped")


def scenario_disconnect(demo: Demo) -> None:
    """4. The device drops off the network, and the alarm still fires."""
    first = demo.supporter_at(0)
    started = demo.start()
    checkin_id = started["checkin_id"]

    gone = demo.simulate(checkin_id, "disconnect")

    demo.check(gone["device_online"] is False, "the device should read as offline")
    demo.check(
        gone["deadline"] == started["deadline"],
        "the deadline must not move when a device drops: the countdown is the server's",
    )
    demo.say(f"{'person':<11}   (deadline unchanged at {gone['deadline']}: the server owns the countdown)")

    alarmed = demo.wait_for(checkin_id, "alarm", supporter=first)

    demo.check(alarmed["device_online"] is False, "the supporter should be told the device was offline")
    back = demo.simulate(checkin_id, "reconnect")
    demo.check(back["device_online"] is True, "the device should read as back")
    demo.ack(checkin_id, first)
    demo.resolve(checkin_id, first, "helped")


def scenario_unacknowledged(demo: Demo) -> None:
    """5. Nobody acknowledges, so it escalates to supporter #2."""
    first, second = demo.supporter_at(0), demo.supporter_at(1)
    started = demo.start()
    checkin_id = started["checkin_id"]

    demo.wait_for(checkin_id, "alarm", supporter=first)
    demo.say(f"{first:<11}   (not answering: their ack window is {demo.ack_window_s:.0f}s)")
    escalated = demo.wait_for(checkin_id, "escalated", supporter=second, seconds=demo.ack_window_s)

    demo.check(escalated["supporter"] == second, f"it should have passed to {second}, got {escalated['supporter']}")
    demo.check(
        escalated["notified"] == [first, second],
        f"both supporters should have been alarmed, in order; got {escalated['notified']}",
    )

    taken = demo.ack(checkin_id, second)

    demo.check(taken["acknowledged_by"] == second, f"{second} should be the one on it")
    demo.check(taken["seconds_left"] is None, "nothing should still be counting: escalation stopped")
    demo.resolve(checkin_id, second, "helped")


def scenario_false_alarm(demo: Demo) -> None:
    """6. A false alarm, closed by a supporter - and one closed by the person."""
    first = demo.supporter_at(0)

    by_supporter = demo.start("-supporter")
    demo.wait_for(by_supporter["checkin_id"], "alarm", supporter=first)
    closed = demo.resolve(by_supporter["checkin_id"], first, "false_alarm")

    demo.check(closed["state"] == "resolved", f"it should be resolved, got {closed['state']}")
    demo.check(closed["resolved_reason"] == "false_alarm", "the reason should be the one given")
    demo.check(closed["resolved_by"] == first, f"{first} should be on record as closing it")
    demo.check(demo.supporter_sees(by_supporter["checkin_id"], first) is None, "it should be off their screen")
    demo.check(demo.person_sees(by_supporter["checkin_id"]) is None, "it should be off the person's screen")

    by_person = demo.start("-person")
    demo.wait_for(by_person["checkin_id"], "alarm", supporter=first)
    closed = demo.resolve(by_person["checkin_id"], "person", "false_alarm")

    demo.check(closed["state"] == "resolved", f"the person should be able to close it, got {closed['state']}")
    demo.check(closed["resolved_reason"] == "false_alarm", "the reason should be the one given")
    demo.check(demo.person_sees(by_person["checkin_id"]) is None, "it should be off their screen")
    demo.check(
        demo.supporter_sees(by_person["checkin_id"], first) is None,
        "closing it must take it off the supporter's screen too",
    )


def scenario_privacy(demo: Demo) -> None:
    """7. Each supporter is told only what this person shared with them."""
    first, second = demo.supporter_at(0), demo.supporter_at(1)
    started = demo.start()
    checkin_id, alert_id = started["checkin_id"], started["alert_id"]

    demo.wait_for(checkin_id, "alarm", supporter=first)
    escalated = demo.wait_for(checkin_id, "escalated", supporter=second, seconds=demo.ack_window_s)
    demo.check(escalated["notified"] == [first, second], "both supporters should have been alarmed")

    #: What each sharing permission puts in a supporter's payload (SPEC §18). What is
    #: switched off is absent, not blanked.
    keys = {"location": ("location",), "alert_details": ("alert_id", "events"), "replay": ("replays_url",)}
    for supporter in demo.supporters:
        supporter_id = str(supporter["id"])
        view = demo.supporter_sees(checkin_id, supporter_id)
        demo.check(view is not None, f"{supporter_id} should have been alarmed by now")
        shared = [name for name, on in supporter["share"].items() if on] or ["nothing"]
        demo.say(f"{supporter_id:<11}   shared with them: {', '.join(shared)}")
        demo.say(f"{supporter_id:<11}   {_shared_line(view)}")
        for permission, payload_keys in keys.items():
            for key in payload_keys:
                if supporter["share"][permission]:
                    demo.check(key in view, f"{supporter_id} has {permission} on but no {key!r}")
                else:
                    demo.check(key not in view, f"{supporter_id} has {permission} off but was sent {key!r}")
        if supporter["share"]["location"]:
            demo.check(
                view["location"] == demo.settings["location"],
                "a shared location should be the one the person typed",
            )
            demo.check(view.get("location_simulated") is True, "the location must say it is simulated")
        if supporter["share"]["alert_details"]:
            demo.check(view["alert_id"] == alert_id, "alert details should carry the alert behind it")
            demo.check(view["events"], "alert details should carry the event log")

    # And the person can take it back: location off, and it is gone from the payload.
    sharing = next((one for one in demo.supporters if one["share"]["location"]), None)
    demo.say("the person can take it back: location sharing off, and it leaves the payload")
    if sharing is None:
        demo.say(f"{'person':<11}   (nobody has location sharing on; nothing to switch off)")
    else:
        with demo.sharing(str(sharing["id"]), "location", False):
            narrowed = demo.supporter_sees(checkin_id, str(sharing["id"]))
            demo.check(narrowed is not None, "the alarm should still be theirs")
            demo.check("location" not in narrowed, "location sharing was off and it was still sent")
            demo.say(f"{sharing['id']:<11}   {_shared_line(narrowed)}")
        restored = demo.supporter_sees(checkin_id, str(sharing["id"]))
        demo.check(
            restored is not None and restored.get("location") == demo.settings["location"],
            "the run should leave this person's sharing exactly as it found it",
        )

    demo.resolve(checkin_id, second, "helped")


# --------------------------------------------------------------------- the scenarios


@dataclass(frozen=True)
class Scenario:
    """One of SPEC §18's seven, and the function that drives it."""

    name: str
    summary: str
    run: Callable[[Demo], None]


SCENARIOS: dict[str, Scenario] = {
    scenario.name: scenario
    for scenario in (
        Scenario("safe", "the person checks in; nobody is woken", scenario_safe),
        Scenario("no-response", "the window runs out, so supporter #1 is alarmed", scenario_no_response),
        Scenario("duress", "the duress PIN alarms silently; their own screen says they checked in", scenario_duress),
        Scenario("disconnect", "the device drops off the net and the alarm still fires", scenario_disconnect),
        Scenario("unacknowledged", "nobody says \"I'm on it\", so it escalates to supporter #2", scenario_unacknowledged),
        Scenario("false-alarm", "a false alarm closed by a supporter, and one closed by the person", scenario_false_alarm),
        Scenario("privacy", "each supporter is told only what this person shared with them", scenario_privacy),
    )
}


# ----------------------------------------------------------------------------- the CLI


@contextmanager
def shortened(demo: Demo, checkin_window: float | None, ack_window: float | None) -> Iterator[None]:
    """Run with shorter windows than this person has, then put theirs back.

    `PUT /people/{id}/safety` is how a person sets their own windows, so this is the
    demo using the same route a screen would - including on the way out, so a run
    leaves nothing behind.
    """
    body = {}
    if checkin_window is not None:
        body["checkin_window_s"] = checkin_window
    if ack_window is not None:
        body["ack_window_s"] = ack_window
    if not body:
        yield
        return
    before = {
        "checkin_window_s": demo.checkin_window_s,
        "ack_window_s": demo.ack_window_s,
    }
    demo.settings = demo.call("PUT", f"/people/{demo.person}/safety", body)
    try:
        yield
    finally:
        demo.say(f"→ PUT /people/{demo.person}/safety {json.dumps(before)} (putting the windows back)")
        demo.settings = demo.api.call("PUT", f"/people/{demo.person}/safety", before)


def run_scenario(scenario: Scenario, args: argparse.Namespace) -> bool:
    """Drive one scenario. True if it played out as SPEC §18 says it must."""
    api = Api(args.api_url, timeout=args.timeout)
    demo = Demo(
        api=api,
        person=args.person,
        scenario=scenario.name,
        safety_pin=args.safety_pin,
        duress_pin=args.duress_pin,
    )
    print(f"\n== {scenario.name}: {scenario.summary}")
    try:
        settings = demo.load_settings()
        supporters = ", ".join(
            f"{one['name']} (#{index + 1}, {one['id']})"
            for index, one in enumerate(settings.get("supporters") or ())
        )
        print(f"   {settings['name'] or demo.person} ({demo.person}) at {api.base_url}")
        print(f"   supporters: {supporters or '(nobody linked)'}")
        with shortened(demo, args.checkin_window, args.ack_window):
            print(
                f"   windows: {demo.checkin_window_s:.0f}s to check in, "
                f"{demo.ack_window_s:.0f}s per supporter to answer"
            )
            try:
                scenario.run(demo)
            finally:
                demo.close_what_is_left()
    except DemoError as exc:
        print(f"FAILED {scenario.name}: {exc}", file=sys.stderr)
        return False
    print(f"OK {scenario.name} ({time.monotonic() - demo.started_at:.1f}s)")
    return True


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="scripts/kaze_demo.py",
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "scenario",
        nargs="?",
        choices=[*SCENARIOS, "all"],
        help="one of SPEC §18's seven scenarios, or `all` for every one in order",
    )
    parser.add_argument("--list", action="store_true", help="print the scenarios and exit")
    parser.add_argument("--api-url", default=default_api_url(), help="default: %(default)s")
    parser.add_argument("--person", default=DEFAULT_PERSON, help="default: %(default)s")
    parser.add_argument(
        "--fast",
        action="store_true",
        help=f"shorten both windows to {FAST_WINDOW_S:.0f}s (the API's floor) for this run",
    )
    parser.add_argument("--checkin-window", type=float, help="seconds the person has to check in")
    parser.add_argument("--ack-window", type=float, help="seconds each supporter has to answer")
    parser.add_argument("--safety-pin", default=DEMO_SAFETY_PIN, help="default: the demo's seeded PIN")
    parser.add_argument("--duress-pin", default=DEMO_DURESS_PIN, help="default: the demo's seeded PIN")
    parser.add_argument("--timeout", type=float, default=HTTP_TIMEOUT_S, help="HTTP timeout, seconds")
    args = parser.parse_args(argv)

    if args.list:
        for scenario in SCENARIOS.values():
            print(f"{scenario.name:<15} {scenario.summary}")
        return 0
    if args.scenario is None:
        parser.error("say which scenario to run (one of the seven, or `all`, or --list)")
    if args.fast:
        if args.checkin_window is None:
            args.checkin_window = FAST_WINDOW_S
        if args.ack_window is None:
            args.ack_window = FAST_WINDOW_S

    names = list(SCENARIOS) if args.scenario == "all" else [args.scenario]
    failed = [name for name in names if not run_scenario(SCENARIOS[name], args)]

    if failed:
        print(f"\n{len(failed)} of {len(names)} scenario(s) failed: {', '.join(failed)}", file=sys.stderr)
        return 1
    print(f"\n{len(names)} of {len(names)} scenario(s) OK: {', '.join(names)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
