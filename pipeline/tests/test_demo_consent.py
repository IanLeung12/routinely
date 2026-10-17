"""Every demo resident carries a seeded consent record (SPEC §12): the resident or
their substitute decision-maker opts in per room before it is monitored."""

from datetime import date, datetime

from fastapi.testclient import TestClient

from routine_watch.api import app
from routine_watch.demo import demo_residents


def test_every_resident_has_a_consent_record() -> None:
    for resident in demo_residents():
        consent = resident["consent"]
        assert consent["given_by"]
        first_session_date = datetime.fromisoformat(
            resident["sessions"][0]["ts"]
        ).date()
        assert date.fromisoformat(consent["on"]) < first_session_date


def test_get_resident_detail_includes_consent() -> None:
    with TestClient(app) as client:
        response = client.get("/residents/mrs-k")

    assert response.status_code == 200
    body = response.json()
    assert body["consent"]["given_by"]
    assert date.fromisoformat(body["consent"]["on"])
