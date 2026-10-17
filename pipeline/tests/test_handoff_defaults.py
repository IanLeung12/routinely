"""T292 made `Handoff.paused` and `HandoffResident.monitoring_paused` optional with
defaults (SPEC section 12 predates `paused` in both). This locks that in so an older
or trimmed payload - one of those two fields missing - still validates rather than
breaking the shift handoff (T311).
"""

from routine_watch.contracts import Handoff, HandoffResident


def _resident(**overrides: object) -> dict:
    base = {
        "resident_id": "mrs-k",
        "name": "Mrs. K",
        "room": "204",
        "flags": 0,
        "pending_review": 0,
        "trending": False,
    }
    base.update(overrides)
    return base


def test_resident_without_monitoring_paused_defaults_to_false() -> None:
    resident = HandoffResident.model_validate(_resident())

    assert resident.monitoring_paused is False


def test_handoff_without_paused_defaults_to_an_empty_list() -> None:
    handoff = Handoff.model_validate(
        {
            "window_hours": 12,
            "residents": [_resident()],
            "summary": "Nothing to review.",
        }
    )

    assert handoff.paused == []


def test_handoff_missing_both_fields_round_trips_through_model_dump() -> None:
    handoff = Handoff.model_validate(
        {
            "window_hours": 12,
            "residents": [_resident()],
            "summary": "Nothing to review.",
        }
    )

    dumped = handoff.model_dump()

    assert dumped["paused"] == []
    assert dumped["residents"][0]["monitoring_paused"] is False

    # The defaulted payload validates again on its own, same as a payload that
    # named the fields explicitly (a trimmed or older payload round-trips cleanly).
    assert Handoff.model_validate(dumped) == handoff
