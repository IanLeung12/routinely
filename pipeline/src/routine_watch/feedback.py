"""Nurse feedback threshold tuning (SPEC MVP 7).

A one-tap "confirmed" or "false alarm" on an alert nudges that resident's
threshold: a false alarm raises it (be less sensitive), a confirmed alert
lowers it (stay sensitive). Pure in-memory bookkeeping; the API route that
calls this lives in a later task.

    store = FeedbackStore()
    store.record(alert_id, resident_id, AlertFeedback(...))
    store.threshold(resident_id, base=0.5)
"""

from __future__ import annotations

from .contracts import AlertFeedback, FeedbackVerdict

#: Each false alarm raises the threshold by this fraction.
FALSE_ALARM_STEP = 0.1

#: Each confirmed alert lowers the threshold by this fraction.
CONFIRMED_STEP = 0.05

#: The threshold can never drop below this multiple of the base.
MIN_FACTOR = 0.8

#: The threshold can never rise above this multiple of the base.
MAX_FACTOR = 1.5


class FeedbackStore:
    """Logged nurse feedback, and the per-resident threshold it implies."""

    def __init__(self) -> None:
        self._by_alert: dict[str, tuple[str, AlertFeedback]] = {}

    def record(self, alert_id: str, resident_id: str, feedback: AlertFeedback) -> None:
        """Log feedback for an alert. Re-recording the same alert_id replaces it."""
        self._by_alert[alert_id] = (resident_id, feedback)

    def get(self, alert_id: str) -> AlertFeedback | None:
        """The stored feedback for an alert, or None if it has none."""
        entry = self._by_alert.get(alert_id)
        return entry[1] if entry else None

    def threshold(self, resident_id: str, base: float) -> float:
        """This resident's threshold, tuned by their logged feedback.

        Counts are read fresh from the current state of every alert's feedback, so
        replacing an alert's verdict never double counts its earlier verdict.
        """
        n_false_alarms = 0
        n_confirmed = 0
        for owner, feedback in self._by_alert.values():
            if owner != resident_id:
                continue
            if feedback.verdict == FeedbackVerdict.FALSE_ALARM:
                n_false_alarms += 1
            elif feedback.verdict == FeedbackVerdict.CONFIRMED:
                n_confirmed += 1

        value = (
            base
            * (1 + FALSE_ALARM_STEP) ** n_false_alarms
            * (1 - CONFIRMED_STEP) ** n_confirmed
        )
        return min(max(value, base * MIN_FACTOR), base * MAX_FACTOR)
