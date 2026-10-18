"""Safety check-ins, scenario by scenario, on a clock the test owns (SPEC §18).

Project KAZE's seven scenarios, as the state machine sees them: somebody who checks
in, somebody who does not, the duress PIN, a device that drops off after the question
was asked, an alarm nobody acknowledges, a false alarm closed by a supporter and by
the person, and a supporter who was never shown where the person is.

No sleeping and no wall clock anywhere: `CheckinStore(clock=...)` is handed a clock
the test moves, which is also why one tick a second and one jump of ten minutes have
to leave the same record (`test_a_clock_jump_lands_where_ticking_would_have`).
"""

import json
import logging
from datetime import UTC, datetime, timedelta

import pytest

from routine_watch.checkin import (
    DEMO_ACK_WINDOW_S,
    DEMO_CHECKIN_WINDOW_S,
    DEMO_DURESS_PIN,
    DEMO_SAFETY_PIN,
    PERSON_ASK,
    SUPPORTER_ASK,
    CheckinState,
    CheckinStore,
    NotWaiting,
    ResolveReason,
    Sharing,
    Supporter,
    UnknownCheckin,
    UnknownPerson,
    UnknownSupporter,
    WrongPin,
    hash_pin,
    person_sees_open,
    person_view,
    pin_kind,
    settings_payload,
    supporter_view,
)

#: The demo's own clock (`demo.DEMO_NOW`), so a check-in in a test is stamped the same
#: way a check-in during the demo is.
BASE = datetime(2026, 1, 1, tzinfo=UTC)

#: Mrs. K's seeded supporters, in the order they are alarmed (SPEC §17's links).
FIRST = "nurse-ana"
SECOND = "care-line"


class FakeClock:
    """A clock the test moves by hand."""

    def __init__(self, now: datetime = BASE):
        self.now = now

    def __call__(self) -> datetime:
        return self.now

    def advance(self, seconds: float) -> datetime:
        self.now += timedelta(seconds=seconds)
        return self.now


@pytest.fixture
def clock() -> FakeClock:
    return FakeClock()


@pytest.fixture
def store(clock, tmp_path) -> CheckinStore:
    """A store on the test's clock, writing settings into the test's own directory."""
    return CheckinStore(clock=clock, directory=tmp_path / "safety")


def events_of(record) -> list[tuple[str, str]]:
    """The check-in's log as (event, actor) pairs, in order."""
    return [(event.event, event.actor) for event in record.events]


# ------------------------------------------------------------------ 1. safe


def test_a_person_who_checks_in_is_safe(store, clock):
    record = store.start("mrs-k")
    assert record.state is CheckinState.PENDING
    assert record.deadline == BASE + timedelta(seconds=DEMO_CHECKIN_WINDOW_S)

    clock.advance(5)
    answered, kind = store.respond(record.checkin_id, DEMO_SAFETY_PIN)

    assert kind == "safety"
    assert answered.state is CheckinState.OK
    assert answered.deadline is None
    assert answered.notified == ()  # nobody was alarmed
    assert events_of(answered) == [("started", "server"), ("checked_in", "person")]
    assert store.active("mrs-k") == []

    clock.advance(DEMO_CHECKIN_WINDOW_S * 10)
    assert store.get(record.checkin_id).state is CheckinState.OK  # and stays safe


def test_the_person_is_asked_in_plain_words(store):
    record = store.start("mrs-k")
    settings = store.settings_of("mrs-k")

    assert person_view(record, store.now())["ask"] == PERSON_ASK
    assert supporter_view(record, settings, FIRST, store.now())["ask"] == SUPPORTER_ASK


# ------------------------------------------------- 2. no response -> alarm


def test_no_answer_alarms_the_first_supporter(store, clock):
    record = store.start("mrs-k")

    clock.advance(DEMO_CHECKIN_WINDOW_S)
    alarmed = store.get(record.checkin_id)

    assert alarmed.state is CheckinState.ALARM
    assert alarmed.supporter == FIRST
    assert alarmed.notified == (FIRST,)
    # Stamped with the deadline it missed, not with whenever somebody looked.
    assert alarmed.events[-1].at == BASE + timedelta(seconds=DEMO_CHECKIN_WINDOW_S)
    assert alarmed.deadline == alarmed.events[-1].at + timedelta(seconds=DEMO_ACK_WINDOW_S)


def test_the_countdown_runs_out_once_and_not_a_second_early(store, clock):
    record = store.start("mrs-k")

    clock.advance(DEMO_CHECKIN_WINDOW_S - 1)
    assert store.get(record.checkin_id).state is CheckinState.PENDING

    clock.advance(1)
    assert store.get(record.checkin_id).state is CheckinState.ALARM


def test_a_person_with_nobody_linked_still_reaches_the_alarm(store, clock):
    """Self-monitoring is a supported state (SPEC §17): there is simply nobody to
    pass it to, and the log says so rather than the check-in going quiet."""
    record = store.start("sam")

    clock.advance(DEMO_CHECKIN_WINDOW_S)
    alarmed = store.get(record.checkin_id)

    assert alarmed.state is CheckinState.ALARM
    assert alarmed.supporter is None
    assert alarmed.notified == ()
    assert alarmed.deadline is None  # nothing left to escalate to
    assert alarmed.events[-1].detail == "nobody linked"


# --------------------------------------------------------------- 3. duress


def test_the_duress_pin_looks_exactly_like_checking_in(clock, tmp_path):
    """The whole duress promise (SPEC §18): the person's own screen cannot tell the
    two apart, so neither can anyone standing over them.

    The same person on the same clock in two stores, so the two records differ in
    nothing but which PIN was entered - and their screens still say the same thing.
    """
    safely = CheckinStore(clock=clock, directory=tmp_path / "safely")
    coerced = CheckinStore(clock=clock, directory=tmp_path / "coerced")

    checked_in, safe_kind = safely.respond(safely.start("mrs-k").checkin_id, DEMO_SAFETY_PIN)
    forced, duress_kind = coerced.respond(coerced.start("mrs-k").checkin_id, DEMO_DURESS_PIN)

    assert (safe_kind, duress_kind) == ("safety", "duress")
    safe_view = person_view(checked_in, safely.now())
    duress_view = person_view(forced, coerced.now())
    assert duress_view == safe_view
    assert json.dumps(duress_view) == json.dumps(safe_view)  # byte for byte
    assert duress_view["state"] == "ok"
    assert "duress" not in json.dumps(duress_view)
    assert not person_sees_open(forced)  # their screen shows no countdown either


def test_the_duress_pin_alarms_the_supporters_silently(store):
    record = store.start("mrs-k")

    coerced, _ = store.respond(record.checkin_id, DEMO_DURESS_PIN)

    assert coerced.state is CheckinState.ALARM
    assert coerced.duress and coerced.silent
    assert coerced.supporter == FIRST
    view = supporter_view(coerced, store.settings_of("mrs-k"), FIRST, store.now())
    assert view["duress"] is True
    assert view["silent"] is True
    assert events_of(coerced) == [("started", "server"), ("duress", "person")]


def test_what_happens_after_a_duress_alarm_never_shows_on_the_person_screen(store, clock):
    record = store.start("mrs-k")
    coerced, _ = store.respond(record.checkin_id, DEMO_DURESS_PIN)
    before = person_view(coerced, store.now())

    clock.advance(DEMO_ACK_WINDOW_S)
    store.acknowledge(record.checkin_id, SECOND)
    helped = store.resolve(record.checkin_id, SECOND, ResolveReason.HELPED)

    assert person_view(helped, store.now()) == before


# ----------------------------------------- 4. the device drops off the net


def test_a_device_that_drops_off_after_the_start_still_alarms(store, clock):
    """KAZE's connectivity failure: the countdown is the server's, so losing the
    person's device loses nothing."""
    record = store.start("mrs-k")

    clock.advance(2)
    offline = store.simulate(record.checkin_id, "disconnect")
    assert offline.device_online is False
    assert offline.deadline == record.deadline  # the countdown was not restarted

    clock.advance(DEMO_CHECKIN_WINDOW_S)
    alarmed = store.get(record.checkin_id)

    assert alarmed.state is CheckinState.ALARM
    assert alarmed.supporter == FIRST
    assert alarmed.device_online is False
    assert supporter_view(alarmed, store.settings_of("mrs-k"), FIRST, store.now())[
        "device_online"
    ] is False
    assert events_of(alarmed) == [
        ("started", "server"),
        ("disconnected", "person"),
        ("alarmed", "server"),
    ]


def test_a_device_that_comes_back_is_logged(store, clock):
    record = store.start("mrs-k")
    store.simulate(record.checkin_id, "disconnect")

    clock.advance(1)
    back = store.simulate(record.checkin_id, "reconnect")

    assert back.device_online is True
    assert back.state is CheckinState.PENDING  # still their question to answer


# ------------------------------------------------------- 5. escalation


def test_an_unacknowledged_alarm_escalates_to_the_second_supporter(store, clock):
    record = store.start("mrs-k")

    clock.advance(DEMO_CHECKIN_WINDOW_S + DEMO_ACK_WINDOW_S)
    escalated = store.get(record.checkin_id)

    assert escalated.state is CheckinState.ESCALATED
    assert escalated.supporter == SECOND
    assert escalated.notified == (FIRST, SECOND)
    assert [event for event, _ in events_of(escalated)] == ["started", "alarmed", "escalated"]


def test_escalation_stops_when_the_list_runs_out(store, clock):
    record = store.start("mrs-k")

    clock.advance(DEMO_CHECKIN_WINDOW_S + DEMO_ACK_WINDOW_S * 10)
    out_of_supporters = store.get(record.checkin_id)

    assert out_of_supporters.state is CheckinState.ESCALATED
    assert out_of_supporters.supporter == SECOND
    assert out_of_supporters.deadline is None
    assert out_of_supporters.events[-1].event == "escalation_exhausted"


def test_a_supporter_who_is_on_it_stops_the_escalation(store, clock):
    record = store.start("mrs-k")
    clock.advance(DEMO_CHECKIN_WINDOW_S)

    taken = store.acknowledge(record.checkin_id, FIRST)

    assert taken.state is CheckinState.ACKNOWLEDGED
    assert taken.acknowledged_by == FIRST
    assert taken.deadline is None

    clock.advance(DEMO_ACK_WINDOW_S * 10)
    assert store.get(record.checkin_id).notified == (FIRST,)  # nobody else was woken


def test_only_a_supporter_on_the_list_can_take_it(store, clock):
    record = store.start("mrs-k")
    clock.advance(DEMO_CHECKIN_WINDOW_S)

    with pytest.raises(UnknownSupporter):
        store.acknowledge(record.checkin_id, "lena")  # Mr. D's daughter, not Mrs. K's


def test_a_pending_checkin_cannot_be_acknowledged(store):
    record = store.start("mrs-k")

    with pytest.raises(NotWaiting):
        store.acknowledge(record.checkin_id, FIRST)


# ---------------------------------------------------------- 6. false alarm


def test_a_supporter_resolves_a_false_alarm(store, clock):
    record = store.start("mrs-k")
    clock.advance(DEMO_CHECKIN_WINDOW_S)
    store.acknowledge(record.checkin_id, FIRST)

    clock.advance(30)
    closed = store.resolve(record.checkin_id, FIRST, ResolveReason.FALSE_ALARM)

    assert closed.state is CheckinState.RESOLVED
    assert closed.resolved_by == FIRST
    assert closed.resolved_reason is ResolveReason.FALSE_ALARM
    assert closed.events[-1].detail == "false_alarm"
    assert store.active("mrs-k") == []


def test_the_person_resolves_a_false_alarm_themselves(store, clock):
    record = store.start("mrs-k")
    clock.advance(DEMO_CHECKIN_WINDOW_S)

    closed = store.resolve(record.checkin_id, "person", ResolveReason.FALSE_ALARM)

    assert closed.state is CheckinState.RESOLVED
    assert closed.resolved_by == "person"
    assert events_of(closed)[-1] == ("resolved", "person")


def test_a_closed_checkin_stays_closed(store, clock):
    record = store.start("mrs-k")
    clock.advance(DEMO_CHECKIN_WINDOW_S)
    store.resolve(record.checkin_id, FIRST, ResolveReason.HELPED)

    with pytest.raises(NotWaiting):
        store.resolve(record.checkin_id, "person", ResolveReason.FALSE_ALARM)


def test_a_safety_pin_is_too_late_once_the_alarm_is_out(store, clock):
    """After the alarm, taking it back is a `resolve` with a reason rather than a PIN
    somebody could be made to enter (SPEC §18)."""
    record = store.start("mrs-k")
    clock.advance(DEMO_CHECKIN_WINDOW_S)

    with pytest.raises(NotWaiting):
        store.respond(record.checkin_id, DEMO_SAFETY_PIN)
    with pytest.raises(NotWaiting):
        store.respond(record.checkin_id, DEMO_DURESS_PIN)


# --------------------------------------------------------- 7. permissions


def test_a_supporter_without_location_never_gets_it(store, clock):
    """The on-call care line hears the alarm and nothing else (SPEC §18): what the
    person did not share is absent from the payload, not blanked in it."""
    record = store.start("mrs-k")
    clock.advance(DEMO_CHECKIN_WINDOW_S + DEMO_ACK_WINDOW_S)
    escalated = store.get(record.checkin_id)
    settings = store.settings_of("mrs-k")

    allowed = supporter_view(escalated, settings, FIRST, store.now())
    not_allowed = supporter_view(escalated, settings, SECOND, store.now())

    assert allowed["location"] == settings.location
    assert allowed["location_simulated"] is True
    assert "location" not in not_allowed
    assert settings.location not in json.dumps(not_allowed)


def test_a_supporter_without_alert_details_gets_no_alert_and_no_log(store, clock):
    record = store.start("mrs-k", alert_id="alert-mrs-k")
    clock.advance(DEMO_CHECKIN_WINDOW_S + DEMO_ACK_WINDOW_S)
    escalated = store.get(record.checkin_id)
    settings = store.settings_of("mrs-k")

    allowed = supporter_view(escalated, settings, FIRST, store.now())
    not_allowed = supporter_view(escalated, settings, SECOND, store.now())

    assert allowed["alert_id"] == "alert-mrs-k"
    assert [event["event"] for event in allowed["events"]] == ["started", "alarmed", "escalated"]
    assert "alert_id" not in not_allowed
    assert "events" not in not_allowed
    assert "alert-mrs-k" not in json.dumps(not_allowed)


def test_only_a_supporter_with_replay_is_pointed_at_the_replays(store, clock):
    record = store.start("mr-d")
    clock.advance(DEMO_CHECKIN_WINDOW_S)
    alarmed = store.get(record.checkin_id)
    settings = store.settings_of("mr-d")

    daughter = supporter_view(alarmed, settings, "lena", store.now())

    assert daughter["location"] == settings.location  # she would drive over
    assert daughter["alert_id"] is None  # this one was started by hand
    assert "replays_url" not in daughter  # but not her father's skeletons
    assert "replays_url" in supporter_view(alarmed, store.settings_of("mrs-k"), FIRST, store.now())


def test_somebody_who_is_not_a_supporter_is_shown_nothing_extra(store, clock):
    record = store.start("mrs-k")
    clock.advance(DEMO_CHECKIN_WINDOW_S)
    alarmed = store.get(record.checkin_id)

    stranger = supporter_view(alarmed, store.settings_of("mrs-k"), "somebody-else", store.now())

    assert "location" not in stranger
    assert "alert_id" not in stranger
    assert "replays_url" not in stranger


# ------------------------------------------------------------------- PINs


def test_a_wrong_pin_changes_nothing_and_the_countdown_carries_on(store, clock):
    record = store.start("mrs-k")

    clock.advance(5)
    with pytest.raises(WrongPin):
        store.respond(record.checkin_id, "0000")

    still_waiting = store.get(record.checkin_id)
    assert still_waiting.state is CheckinState.PENDING
    assert still_waiting.deadline == record.deadline
    assert events_of(still_waiting) == [("started", "server")]

    clock.advance(DEMO_CHECKIN_WINDOW_S)
    assert store.get(record.checkin_id).state is CheckinState.ALARM


def test_a_pin_is_never_in_a_payload_a_log_or_a_file(store, clock, caplog):
    caplog.set_level(logging.DEBUG)
    store.update_settings("mrs-k", {"safety_pin": "8426", "duress_pin": "1357"})
    record = store.start("mrs-k")
    store.respond(record.checkin_id, "1357")
    clock.advance(1)
    settings = store.settings_of("mrs-k")

    payloads = json.dumps(
        [
            settings_payload(settings),
            person_view(store.get(record.checkin_id), store.now()),
            supporter_view(store.get(record.checkin_id), settings, FIRST, store.now()),
            [event.model_dump(mode="json") for event in store.get(record.checkin_id).events],
        ]
    )
    kept = (store.directory / "mrs-k.json").read_text(encoding="utf-8")

    for pin in ("8426", "1357", DEMO_SAFETY_PIN, DEMO_DURESS_PIN):
        assert pin not in payloads
        assert pin not in caplog.text
        assert pin not in kept
    assert settings_payload(settings)["safety_pin_set"] is True
    assert "hash" not in settings_payload(settings)


def test_a_pin_is_kept_as_a_salted_hash(store):
    first = hash_pin("4242")
    second = hash_pin("4242")

    assert first.salt != second.salt  # a different salt every time
    assert first.hash != second.hash
    assert "4242" not in first.hash
    settings = store.settings_of("mrs-k")
    assert pin_kind(settings, DEMO_SAFETY_PIN) == "safety"
    assert pin_kind(settings, DEMO_DURESS_PIN) == "duress"
    assert pin_kind(settings, "0000") is None


def test_a_person_with_no_pin_set_cannot_be_checked_in(store):
    store.update_settings("mrs-k", {})
    settings = store.settings_of("mrs-k").model_copy(
        update={"safety_pin": None, "duress_pin": None}
    )

    assert pin_kind(settings, DEMO_SAFETY_PIN) is None
    assert pin_kind(settings, "") is None


# ------------------------------------------------ the server owns the time


def test_a_clock_jump_lands_where_ticking_would_have(clock, tmp_path):
    """One tick a second and one jump of ten minutes leave the same record, which is
    what lets the tests above move time in one go."""
    ticked = CheckinStore(clock=clock, directory=tmp_path / "ticked")
    record = ticked.start("mrs-k")
    for _ in range(600):
        clock.advance(1)
        ticked.tick()
    ticking = ticked.get(record.checkin_id)

    jumped_clock = FakeClock()
    jumped = CheckinStore(clock=jumped_clock, directory=tmp_path / "jumped")
    same = jumped.start("mrs-k")
    jumped_clock.advance(600)
    in_one_go = jumped.get(same.checkin_id)

    assert ticking == in_one_go


def test_a_tick_only_mentions_what_changed(store, clock):
    record = store.start("mrs-k")

    assert store.tick() == []  # nothing is due yet

    clock.advance(DEMO_CHECKIN_WINDOW_S)
    changed = store.tick()

    assert [one.checkin_id for one in changed] == [record.checkin_id]
    assert changed[0].state is CheckinState.ALARM
    assert store.tick() == []  # and not again


def test_one_checkin_per_alert(store, clock):
    first = store.start("mrs-k", alert_id="alert-mrs-k")

    clock.advance(DEMO_CHECKIN_WINDOW_S + 1)
    again = store.start("mrs-k", alert_id="alert-mrs-k")

    assert again.checkin_id == first.checkin_id
    assert store.checkin_for_alert("alert-mrs-k").checkin_id == first.checkin_id
    assert store.checkin_for_alert("alert-nobody") is None
    assert len(store.active()) == 1


def test_two_checkins_in_the_same_second_get_their_own_ids(store):
    """`_new_id`'s counter: somebody who checks in and is asked again inside the same
    second gets a second id rather than overwriting the first."""
    first = store.start("mrs-k")
    store.respond(first.checkin_id, DEMO_SAFETY_PIN)
    second = store.start("mrs-k")

    assert first.checkin_id != second.checkin_id
    assert [one.checkin_id for one in store.active()] == [second.checkin_id]


def test_one_open_question_per_person(store, clock):
    """A question nobody has answered yet is never asked twice (T460): a second flag -
    or the demo's button pressed again - joins the countdown already running, instead
    of leaving a stale check-in on the person's screen."""
    first = store.start("mrs-k")

    clock.advance(5)
    again = store.start("mrs-k")
    for_a_flag = store.start("mrs-k", alert_id="alert-later")

    assert again.checkin_id == first.checkin_id
    assert for_a_flag.checkin_id == first.checkin_id
    assert again.state is CheckinState.PENDING
    assert again.deadline == first.deadline  # the countdown carries on, it is not reset
    assert events_of(again) == [("started", "server")]  # and nothing was logged twice
    assert [one.checkin_id for one in store.active("mrs-k")] == [first.checkin_id]
    # The later flag is answered by the question already out, so once that one closes
    # it does not come back and ask again.
    assert store.checkin_for_alert("alert-later").checkin_id == first.checkin_id
    store.respond(first.checkin_id, DEMO_SAFETY_PIN)
    assert store.start("mrs-k", alert_id="alert-later").checkin_id == first.checkin_id
    assert store.active("mrs-k") == []


def test_an_alarm_already_out_does_not_block_the_next_question(store, clock):
    """Once the window has run out the record belongs to the supporters, so the next
    flag asks a new question (T460) rather than handing back a countdown at 0:00 that
    the person can no longer answer."""
    first = store.start("mrs-k")
    clock.advance(DEMO_CHECKIN_WINDOW_S)
    assert store.get(first.checkin_id).state is CheckinState.ALARM

    second = store.start("mrs-k")

    assert second.checkin_id != first.checkin_id
    assert second.state is CheckinState.PENDING
    assert [one.state for one in store.active("mrs-k")] == [
        CheckinState.ALARM,
        CheckinState.PENDING,
    ]


def test_active_is_only_what_somebody_is_still_waiting_for(store, clock):
    answered = store.start("mrs-k")
    store.respond(answered.checkin_id, DEMO_SAFETY_PIN)
    waiting = store.start("mr-d")

    clock.advance(1)

    assert [one.checkin_id for one in store.active()] == [waiting.checkin_id]
    assert store.active("mrs-k") == []
    assert [one.person_id for one in store.active("mr-d")] == ["mr-d"]


def test_an_unknown_checkin_or_person_says_so(store):
    with pytest.raises(UnknownCheckin):
        store.get("checkin-nobody")
    with pytest.raises(UnknownPerson):
        store.start("nobody")
    with pytest.raises(UnknownPerson):
        store.settings_of("nobody")


# ----------------------------------------------------------- the settings


def test_settings_are_kept_and_read_back(store, clock, tmp_path):
    store.update_settings(
        "mr-d",
        {
            "checkin_window_s": 45.0,
            "ack_window_s": 30.0,
            "location": "14 Rowan Avenue, flat 2 (back door key with Lena)",
            "supporters": (
                Supporter(id="lena", name="Lena", relationship="family", share=Sharing()),
            ),
            "safety_pin": "7391",
        },
    )

    reopened = CheckinStore(clock=clock, directory=store.directory)
    settings = reopened.settings_of("mr-d")

    assert settings.checkin_window_s == 45.0
    assert settings.ack_window_s == 30.0
    assert [one.id for one in settings.supporters] == ["lena"]
    assert settings.supporters[0].share == Sharing()  # everything switched off
    assert pin_kind(settings, "7391") == "safety"
    assert pin_kind(settings, DEMO_DURESS_PIN) == "duress"  # untouched by this change
    assert reopened.settings_of("mrs-k").checkin_window_s == DEMO_CHECKIN_WINDOW_S


def test_a_file_that_is_not_settings_is_skipped(store, clock, tmp_path):
    directory = tmp_path / "safety"
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "mrs-k.json").write_text("{not json", encoding="utf-8")
    (directory / "stray.json").write_text(json.dumps({"hello": "world"}), encoding="utf-8")

    reopened = CheckinStore(clock=clock, directory=directory)

    assert reopened.settings_of("mrs-k").checkin_window_s == DEMO_CHECKIN_WINDOW_S
    assert reopened.people() == ["mr-d", "mrs-k", "sam"]


def test_reset_forgets_check_ins_and_settings(store, clock):
    store.update_settings("mrs-k", {"checkin_window_s": 600.0})
    record = store.start("mrs-k", alert_id="alert-mrs-k")

    store.reset()

    assert store.active() == []
    assert store.checkin_for_alert("alert-mrs-k") is None
    assert store.settings_of("mrs-k").checkin_window_s == DEMO_CHECKIN_WINDOW_S
    assert not list(store.directory.glob("*.json"))
    with pytest.raises(UnknownCheckin):
        store.get(record.checkin_id)


def test_the_demo_people_are_set_up_for_the_demo(store):
    """The seeded people are SPEC §17's three cases, with the demo's short windows so
    a check-in plays out on stage (SPEC §10)."""
    assert store.people() == ["mr-d", "mrs-k", "sam"]
    for person_id in store.people():
        settings = store.settings_of(person_id)
        assert settings.checkin_window_s == DEMO_CHECKIN_WINDOW_S
        assert settings.ack_window_s == DEMO_ACK_WINDOW_S
        assert settings.safety_pin is not None and settings.duress_pin is not None
        assert len({one.id for one in settings.supporters}) == len(settings.supporters)
    assert [one.id for one in store.settings_of("mrs-k").supporters] == [FIRST, SECOND]
    assert [one.id for one in store.settings_of("mr-d").supporters] == ["lena", SECOND]
    assert store.settings_of("sam").supporters == ()
