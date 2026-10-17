"""Nurse feedback threshold tuning (SPEC MVP 7) and pattern weights (Nice to have 8).

A one-tap "confirmed" or "false alarm" on an alert nudges that resident's
threshold: a false alarm raises it (be less sensitive), a confirmed alert
lowers it (stay sensitive). The answer to "what was it?" nudges that pattern's
weight for the same resident, so her next alerts rank the patterns her last
alerts actually turned out to be. Pure in-memory bookkeeping; the API route that
calls this lives in `routine_watch.api`.

    store = FeedbackStore()
    store.record(alert_id, resident_id, AlertFeedback(...), cause="slow_drift")
    store.threshold(resident_id, base=0.5)
    store.pattern_weights(resident_id)      # {"slow_drift": 1.1}
"""

from __future__ import annotations

from dataclasses import dataclass

from .contracts import AlertFeedback, FeedbackVerdict
from .patterns_library import BY_ID as PATTERNS_BY_ID

#: Each false alarm raises the threshold by this fraction.
FALSE_ALARM_STEP = 0.1

#: Each confirmed alert lowers the threshold by this fraction.
CONFIRMED_STEP = 0.05

#: The threshold can never drop below this multiple of the base.
MIN_FACTOR = 0.8

#: The threshold can never rise above this multiple of the base.
MAX_FACTOR = 1.5

#: What one nurse answer is worth to a pattern's weight: a confirmed cause moves it
#: up by this much, a false alarm on the pattern an alert led with moves it down.
#: Answers are counted, not weighted by age - the demo's history is days long.
PATTERN_STEP = 0.1

#: A pattern's weight never leaves this band, however many answers pile up
#: (SPEC Nice to have 8). Three answers reach the edge of it, so one answer alone
#: can only reorder patterns that were already within a tenth of each other: the
#: ranking stays rules over features, nudged by feedback rather than driven by it.
MIN_PATTERN_WEIGHT = 0.7
MAX_PATTERN_WEIGHT = 1.3


@dataclass(frozen=True)
class _Answer:
    """One alert's logged feedback, as the store keeps it."""

    resident_id: str
    feedback: AlertFeedback
    #: The answer to "what was it?": a pattern id, "other", or None if nobody said.
    cause: str | None = None
    #: The pattern the alert led with when the nurse answered, if the caller knew it.
    #: A false alarm is evidence against that pattern for this resident.
    top_pattern: str | None = None


class FeedbackStore:
    """Logged nurse feedback, and the per-resident tuning it implies."""

    def __init__(self) -> None:
        self._by_alert: dict[str, _Answer] = {}

    def record(
        self,
        alert_id: str,
        resident_id: str,
        feedback: AlertFeedback,
        cause: str | None = None,
        top_pattern: str | None = None,
    ) -> None:
        """Log feedback for an alert. Re-recording the same alert_id replaces it.

        `top_pattern` is the pattern the alert ranked first when the nurse answered:
        what a "false alarm" is a false alarm *on* (`pattern_weights`).
        """
        self._by_alert[alert_id] = _Answer(resident_id, feedback, cause, top_pattern)

    def get(self, alert_id: str) -> AlertFeedback | None:
        """The stored feedback for an alert, or None if it has none."""
        answer = self._by_alert.get(alert_id)
        return answer.feedback if answer else None

    def reset(self) -> None:
        """Forget every logged answer: thresholds and pattern weights back to base."""
        self._by_alert.clear()

    def cause_of(self, alert_id: str) -> str | None:
        """The stored cause for an alert, or None if it has none."""
        answer = self._by_alert.get(alert_id)
        return answer.cause if answer else None

    def _answers_for(self, resident_id: str) -> list[_Answer]:
        """Every alert's current answer for one resident.

        Read fresh from the current state of every alert, so replacing an alert's
        verdict or cause never double counts the earlier one.
        """
        return [answer for answer in self._by_alert.values() if answer.resident_id == resident_id]

    def cause_counts(self, resident_id: str) -> dict[str, int]:
        """How many confirmed alerts this resident has per cause id.

        Only ``confirmed`` alerts count; false alarms never contribute, since a
        cause on a dismissed alert isn't evidence the pattern matched.
        """
        counts: dict[str, int] = {}
        for answer in self._answers_for(resident_id):
            if answer.cause is None:
                continue
            if answer.feedback.verdict != FeedbackVerdict.CONFIRMED:
                continue
            counts[answer.cause] = counts.get(answer.cause, 0) + 1
        return counts

    def _pattern_tally(self, resident_id: str) -> dict[str, tuple[int, int]]:
        """Per pattern id, how many answers push it up and how many push it down.

        Up: a confirmed alert whose cause was this pattern - the change really was
        the kind of thing this pattern describes. Down: a false alarm on an alert
        this pattern led - it was ranked first and there was nothing to see.

        Causes the pattern library has no pattern for ("other", or a stale id from an
        older client) weigh nothing: there is no pattern to weigh.
        """
        tally: dict[str, tuple[int, int]] = {}
        for answer in self._answers_for(resident_id):
            if answer.feedback.verdict == FeedbackVerdict.CONFIRMED:
                pattern_id, step = answer.cause, (1, 0)
            else:
                pattern_id, step = answer.top_pattern, (0, 1)
            if pattern_id not in PATTERNS_BY_ID:
                continue
            up, down = tally.get(pattern_id, (0, 0))
            tally[pattern_id] = (up + step[0], down + step[1])
        return tally

    def pattern_weights(self, resident_id: str) -> dict[str, float]:
        """This resident's pattern confidence multipliers (SPEC Nice to have 8).

        One entry per pattern her nurses have answered about; every other pattern is
        unweighted, so callers read this with a default of 1.0. Clamped to
        `MIN_PATTERN_WEIGHT`..`MAX_PATTERN_WEIGHT`, and a pattern confirmed as often
        as it was dismissed comes back to exactly 1.0.
        """
        weights = {}
        for pattern_id, (up, down) in self._pattern_tally(resident_id).items():
            weight = 1.0 + PATTERN_STEP * (up - down)
            weights[pattern_id] = round(
                min(max(weight, MIN_PATTERN_WEIGHT), MAX_PATTERN_WEIGHT), 3
            )
        return weights

    def pattern_answers(self, resident_id: str) -> dict[str, int]:
        """How many nurse answers stand behind each of `pattern_weights`' entries.

        Both directions count: it is how many answers a weight is read from, which is
        what the alert's evidence line tells the nurse.
        """
        return {
            pattern_id: up + down
            for pattern_id, (up, down) in self._pattern_tally(resident_id).items()
        }

    def threshold(self, resident_id: str, base: float) -> float:
        """This resident's threshold, tuned by their logged feedback.

        Counts are read fresh from the current state of every alert's feedback, so
        replacing an alert's verdict never double counts its earlier verdict.
        """
        n_false_alarms = 0
        n_confirmed = 0
        for answer in self._answers_for(resident_id):
            if answer.feedback.verdict == FeedbackVerdict.FALSE_ALARM:
                n_false_alarms += 1
            elif answer.feedback.verdict == FeedbackVerdict.CONFIRMED:
                n_confirmed += 1

        value = (
            base
            * (1 + FALSE_ALARM_STEP) ** n_false_alarms
            * (1 - CONFIRMED_STEP) ** n_confirmed
        )
        return min(max(value, base * MIN_FACTOR), base * MAX_FACTOR)
