"""Every demo resident carries a seeded consent record (SPEC §12): the resident or
their substitute decision-maker opts in per room before it is monitored."""

from datetime import date, datetime

import pytest
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


def _assert_every_resident_has_consent(client: TestClient, resident_ids: list[str]) -> None:
    for resident_id in resident_ids:
        consent = client.get(f"/residents/{resident_id}").json()["consent"]
        assert consent["given_by"]
        assert date.fromisoformat(consent["on"])


def test_every_resident_consent_survives_demo_reset(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Consent is seeded config (`demo._RESIDENTS`), not recorded session state, so
    `/demo/reset` - which forgets live sessions and feedback (T144) - must leave it
    untouched for every resident listed by `/residents`, not just mrs-k (T254)."""
    monkeypatch.setenv("DEMO_RESET", "1")
    with TestClient(app) as client:
        resident_ids = [resident["id"] for resident in client.get("/residents").json()]
        assert resident_ids == [resident["id"] for resident in demo_residents()]

        _assert_every_resident_has_consent(client, resident_ids)

        response = client.post("/demo/reset")
        assert response.status_code == 200

        _assert_every_resident_has_consent(client, resident_ids)
