"""Errors by time of day: the evidence behind an evening-only worsening (SPEC §7.5).

`patterns.py` already scores "errors concentrated in late-day sessions, mornings
normal" and the alert says so in words. These tests cover the strip of numbers the
alert shows underneath it (`api_alerts.errors_by_time_of_day`): one bucket per part
of a day over the fortnight behind the alert, read off the resident's own sessions,
and carried on the payload the dashboard validates against
`contracts/alert_detail.schema.json`.

Offline like the rest: the demo residents are the synthetic generators' output and
the one live session played here is a recording replayed through the pipeline.
"""

import json
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from jsonschema import Draft202012Validator

from routine_watch.api import app
from routine_watch.api_alerts import (
    TIME_OF_DAY_DAYS,
    errors_by_time_of_day,
)
from routine_watch.contracts import AlertDetail, TimeOfDay, repo_root, schema_name
from routine_watch.demo import DEMO_NOW, DEMO_RESIDENT, demo_residents

#: The resident the pattern library calls evening-only worsening (`demo._RESIDENTS`).
EVENING_RESIDENT = "mr-nguyen"

#: The alert mrs-k's live session raises (`routine_watch.alerts`).
MRS_K_ALERT = f"alert-{DEMO_RESIDENT}"


@pytest.fixture
def client():
    with TestClient(app) as client:
        yield client


def resident(resident_id: str) -> dict:
    """One demo resident as the API has them right now, live sessions included."""
    return next(person for person in demo_residents() if person["id"] == resident_id)


def session_at(ts: str, errors: dict[str, int] | None = None, assisted: bool = False) -> dict:
    """One session record in the shape `demo.demo_residents` serves them."""
    return {
        "resident_id": "resident-a",
        "ts": ts,
        "task": "tea",
        "errors": errors or {},
        "self_corrected": 0,
        "duration_s": 180.0,
        "assisted": assisted,
    }


def errors_in(sessions: list[dict]) -> int:
    return sum(sum(session["errors"].values()) for session in sessions)


def buckets_of(payload: dict) -> dict[str, dict]:
    return {bucket["bucket"]: bucket for bucket in payload["errors_by_time_of_day"]}


def detail_schema() -> Draft202012Validator:
    path = repo_root() / "contracts" / f"{schema_name(AlertDetail)}.schema.json"
    schema = json.loads(path.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema)


def test_the_strip_is_the_three_parts_of_a_day_in_that_order() -> None:
    """Morning, afternoon, evening, always all three: the dashboard draws one bar
    each, and a part of the day she never makes tea in is a real answer."""
    strip = errors_by_time_of_day(resident(DEMO_RESIDENT)["sessions"], DEMO_NOW)

    assert [bucket.bucket for bucket in strip] == list(TimeOfDay)


def test_mrs_ks_buckets_add_up_to_her_fortnight() -> None:
    """Her whole history is inside the window (14 days of it, `demo.DEMO_DAYS`), so
    the strip accounts for every session and every error of it, not a subset."""
    mrs_k = resident(DEMO_RESIDENT)

    strip = errors_by_time_of_day(mrs_k["sessions"], DEMO_NOW)

    assert sum(bucket.sessions for bucket in strip) == len(mrs_k["sessions"])
    assert sum(bucket.errors for bucket in strip) == errors_in(mrs_k["sessions"])


def test_mrs_k_makes_tea_morning_and_evening_and_never_in_between() -> None:
    """The shape of her day, which is what makes the strip worth showing: the
    synthetic history runs an 08:00 and an 18:00 session (`synth.history`), so two
    buckets carry her sessions and the afternoon one is empty rather than missing."""
    strip = {bucket.bucket: bucket for bucket in errors_by_time_of_day(
        resident(DEMO_RESIDENT)["sessions"], DEMO_NOW
    )}

    assert strip[TimeOfDay.MORNING].sessions > 0
    assert strip[TimeOfDay.EVENING].sessions > 0
    assert strip[TimeOfDay.AFTERNOON].sessions == 0
    assert strip[TimeOfDay.AFTERNOON].errors == 0


def test_the_evening_resident_is_visibly_worse_late_in_the_day() -> None:
    """The point of the whole strip (SPEC §7.5): the resident the library names
    evening-only worsening for has mornings as clean as anybody's and the errors all
    land in her late sessions, which a nurse can now see rather than take on trust."""
    nguyen = resident(EVENING_RESIDENT)
    assert nguyen["top_pattern"]["pattern_id"] == "evening_worsening"

    strip = {bucket.bucket: bucket for bucket in errors_by_time_of_day(
        nguyen["sessions"], DEMO_NOW
    )}
    morning = strip[TimeOfDay.MORNING]
    evening = strip[TimeOfDay.EVENING]

    assert morning.sessions > 0 and evening.sessions > 0
    assert evening.errors / evening.sessions > morning.errors / morning.sessions
    assert evening.errors > morning.errors


@pytest.mark.parametrize(
    ("hour", "bucket"),
    [
        (0, TimeOfDay.MORNING),
        (8, TimeOfDay.MORNING),
        (11, TimeOfDay.MORNING),
        (12, TimeOfDay.AFTERNOON),
        (16, TimeOfDay.AFTERNOON),
        (17, TimeOfDay.EVENING),
        (18, TimeOfDay.EVENING),
        (23, TimeOfDay.EVENING),
    ],
)
def test_the_day_splits_at_noon_and_at_five(hour: int, bucket: TimeOfDay) -> None:
    now = datetime(2026, 1, 2, tzinfo=UTC)
    session = session_at(datetime(2026, 1, 1, hour, 30, tzinfo=UTC).isoformat(), {"omission": 1})

    strip = {counted.bucket: counted for counted in errors_by_time_of_day([session], now)}

    assert strip[bucket].sessions == 1
    assert strip[bucket].errors == 1
    assert sum(counted.sessions for counted in strip.values()) == 1


def test_a_sessions_own_timestamp_decides_its_bucket() -> None:
    """The hour the session carries, not this machine's clock: 20:30 where the
    resident lives is her evening even when the same instant is 15:30 UTC, and a
    worker in another timezone reads the same strip off the same recording."""
    now = datetime(2026, 1, 2, tzinfo=UTC)
    session = session_at("2026-01-01T20:30:00+05:00", {"omission": 1})

    strip = {counted.bucket: counted for counted in errors_by_time_of_day([session], now)}

    assert strip[TimeOfDay.EVENING].sessions == 1
    assert strip[TimeOfDay.MORNING].sessions == 0
    assert strip[TimeOfDay.AFTERNOON].sessions == 0


def test_only_the_window_counts() -> None:
    """A fortnight of her own days (`TIME_OF_DAY_DAYS`), ending at the alert: an
    older session is what she used to be like, which is the baseline's job."""
    now = datetime(2026, 1, 15, tzinfo=UTC)
    inside = session_at((now - timedelta(days=1)).isoformat(), {"omission": 1})
    older = session_at((now - timedelta(days=TIME_OF_DAY_DAYS + 1)).isoformat(), {"omission": 5})
    later = session_at((now + timedelta(hours=2)).isoformat(), {"omission": 7})

    strip = errors_by_time_of_day([older, inside, later], now)

    assert sum(bucket.sessions for bucket in strip) == 1
    assert sum(bucket.errors for bucket in strip) == 1


def test_an_assisted_session_is_left_out() -> None:
    """Somebody else's hands as much as hers (SPEC §7), so it is not evidence about
    her evenings - the same sessions the score and her baseline leave out."""
    now = datetime(2026, 1, 15, tzinfo=UTC)
    hers = session_at((now - timedelta(days=1, hours=4)).isoformat(), {"omission": 1})
    assisted = session_at(
        (now - timedelta(days=1)).isoformat(), {"omission": 4}, assisted=True
    )

    strip = errors_by_time_of_day([hers, assisted], now)

    assert sum(bucket.sessions for bucket in strip) == 1
    assert sum(bucket.errors for bucket in strip) == 1


def test_no_sessions_in_the_window_means_no_strip() -> None:
    """Nothing to show, said as nothing: the dashboard hides the strip rather than
    drawing three empty bars that read as three good parts of a day."""
    now = datetime(2026, 1, 15, tzinfo=UTC)
    older = session_at((now - timedelta(days=TIME_OF_DAY_DAYS + 2)).isoformat())

    assert errors_by_time_of_day([], now) is None
    assert errors_by_time_of_day([older], now) is None
    assert errors_by_time_of_day([session_at(now.isoformat(), assisted=True)], now) is None


def test_the_alert_payload_carries_the_strip_and_validates(
    client: TestClient, mrs_k_flagged: None
) -> None:
    """`GET /alerts/{id}` and every row of `GET /alerts` answer with it, inside the
    schema the dashboard reads (`contracts/alert_detail.schema.json`)."""
    schema = detail_schema()
    mrs_k = resident(DEMO_RESIDENT)

    detail = client.get(f"/alerts/{MRS_K_ALERT}").json()
    rows = client.get("/alerts").json()

    schema.validate(detail)
    AlertDetail.model_validate(detail)
    assert [bucket["bucket"] for bucket in detail["errors_by_time_of_day"]] == [
        bucket.value for bucket in TimeOfDay
    ]
    assert sum(bucket["errors"] for bucket in detail["errors_by_time_of_day"]) == errors_in(
        mrs_k["sessions"]
    )
    for row in rows:
        schema.validate(row)
        assert row["errors_by_time_of_day"] == detail["errors_by_time_of_day"]


def test_the_session_a_nurse_just_watched_is_in_the_strip(
    client: TestClient, mrs_k_flagged: None
) -> None:
    """A live session is stamped inside the demo's own clock (`live.py`, ending at
    `DEMO_NOW`), so the bad session the alert is about is one of the evenings the
    strip counts - not a session the evidence quietly leaves out."""
    seeded = errors_by_time_of_day(
        [s for s in resident(DEMO_RESIDENT)["sessions"] if "session_id" not in s], DEMO_NOW
    )
    seeded_evening = next(b for b in seeded if b.bucket is TimeOfDay.EVENING)

    served = buckets_of(client.get(f"/alerts/{MRS_K_ALERT}").json())

    assert served["evening"]["sessions"] == seeded_evening.sessions + 1
    assert served["evening"]["errors"] > seeded_evening.errors


def test_feedback_answers_with_the_strip_too(client: TestClient, mrs_k_flagged: None) -> None:
    """The POST answers with the whole alert (SPEC MVP 7), so the strip survives a
    nurse's verdict instead of vanishing from the screen she is looking at."""
    before = client.get(f"/alerts/{MRS_K_ALERT}").json()["errors_by_time_of_day"]

    answered = client.post(
        f"/alerts/{MRS_K_ALERT}/feedback", json={"verdict": "confirmed"}
    ).json()

    detail_schema().validate(answered)
    assert answered["errors_by_time_of_day"] == before
