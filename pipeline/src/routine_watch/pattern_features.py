"""From session history to the features `patterns.score_patterns` weighs (SPEC §7.5).

    features = extract_features(resident["sessions"], baseline, resident["care_records"])
    patterns = score_patterns(features)   # top 3 above the threshold, best first

A resident's own session history and care records become the feature list in
SPEC §7.5 - error counts by type, durations and gaps against their own baseline,
onset in days or weeks, time of day, movement speed, which hand, self-corrected
slips, care-record context. Pure: the same sessions and care records always give
the same features.

Features the pipeline does not record yet (gaps between steps, movement speed from
the skeleton, per-hand step shares) are left as `None` rather than guessed. Callers
that do have those numbers can pass them to `Features` and `patterns.score_patterns`
scores immediately.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from .change_detection import Baseline
from .drift import Drift, drift
from .errors import ERROR_TYPES
from .patterns_library import SEDATING_MEDICATIONS
from .scoring import session_score

#: The window "what just changed" is read from: the same 24-48 h as the flag itself
#: (`change_detection.flag_change`, `alerts.FLAG_WINDOW_H`).
CHANGE_WINDOW_H = 48.0

#: Days of recent history a time-of-day pattern is read from. A recurring daily
#: pattern needs more than the flag window: two sessions cannot show "every evening".
TIME_OF_DAY_DAYS = 7

#: Sessions starting at or after this hour are late-day; before noon is morning.
EVENING_HOUR = 16
MORNING_END_HOUR = 12

#: How far above baseline an error type has to be before `risen_error_types` counts
#: it as one of the types that is up (`patterns.BREADTH_FULL` is how many of those
#: count as "across error types" at full strength).
BREADTH_MIN = 0.25

#: Floor on the gap between a resident's mean score and their threshold, so a
#: resident with a very tight baseline does not get a huge change strength from noise.
MIN_HEADROOM = 0.5

#: Care-record lookbacks. The vitals thresholds are the ones `checks.suggest_checks`
#: uses; a medication change stays relevant for longer than a temperature reading
#: because motor slowing after a new sedative takes days to show up.
VITALS_LOOKBACK_H = 72.0
NEW_MEDICATION_H = 72.0
MEDICATION_LOOKBACK_H = 14 * 24.0
FEVER_C = 37.8
LOW_FLUID_ML = 1000


def _clamp(value: float) -> float:
    return max(0.0, min(1.0, value))


@dataclass(frozen=True)
class Features:
    """What the scorer looks at: one resident, their own history (SPEC §7.5).

    Rates are errors per session. "Recent" is the flag window, "baseline" is the same
    resident before it, so every feature is this resident against themselves.

    `gap_ratio`, `movement_speed_ratio` and `hand_share_drop` are `None` unless a
    caller supplies them: `extract_features` reads session records, which carry error
    counts and durations but not per-step gaps, skeleton speed or per-hand shares.
    """

    recent_sessions: int = 0
    baseline_sessions: int = 0
    #: The highest-scoring session in the window: the one the flag is about.
    recent_score_peak: float = 0.0
    baseline_score_mean: float = 0.0
    threshold: float = 0.0
    error_rates: Mapping[str, float] = field(default_factory=dict)
    baseline_error_rates: Mapping[str, float] = field(default_factory=dict)
    #: How long the change has been building, in days: the length of the current run
    #: of sessions above threshold, or the span of a drift that `drift.drift` calls a
    #: trend. `None` when nothing is above threshold and nothing is trending.
    change_days: float | None = None
    drift_slope_per_day: float = 0.0
    drift_days: int = 0
    drift_trending: bool = False
    duration_ratio: float | None = None
    gap_ratio: float | None = None
    movement_speed_ratio: float | None = None
    evening_error_rate: float | None = None
    morning_error_rate: float | None = None
    baseline_morning_error_rate: float | None = None
    #: Days in the recent window with both a morning and a late-day session, and how
    #: many of those had more errors late in the day. "Recurring daily" (SPEC §7.5)
    #: means most of them, not one bad evening.
    compared_days: int = 0
    evening_worse_days: int = 0
    hand_share_drop: float | None = None
    self_corrected_rate: float = 0.0
    baseline_self_corrected_rate: float = 0.0
    #: Care-record flags from `patterns_library.CONTEXT_FLAGS`, and one line of
    #: plain-language evidence per flag.
    context: tuple[str, ...] = ()
    context_notes: Mapping[str, str] = field(default_factory=dict)

    @property
    def change_strength(self) -> float:
        """How far past their own threshold this resident has moved, 0..1.

        The scorer is only ever asked after a flag, and this is what keeps it quiet
        anyway when the recent sessions are ordinary: nothing changed, so nothing is
        consistent with anything.

        Read from the worst session in the window rather than the mean. The mean is
        diluted by the resident's good sessions in the same window - which is exactly
        what an evening-only pattern looks like - and the flag is about the sessions
        that crossed the threshold, not about their average.
        """
        if self.recent_sessions == 0:
            return 0.0
        headroom = max(self.threshold - self.baseline_score_mean, MIN_HEADROOM)
        return _clamp((self.recent_score_peak - self.baseline_score_mean) / headroom)

    def rate(self, error_type: str) -> float:
        """Errors of one type per recent session."""
        return self.error_rates.get(error_type, 0.0)

    def baseline_rate(self, error_type: str) -> float:
        """Errors of one type per session, before the window."""
        return self.baseline_error_rates.get(error_type, 0.0)

    @property
    def total_error_rate(self) -> float:
        return sum(self.error_rates.values())

    @property
    def baseline_total_error_rate(self) -> float:
        return sum(self.baseline_error_rates.values())

    @property
    def evening_recurrence(self) -> float | None:
        """Share of the window's days that were worse late in the day."""
        if self.compared_days == 0:
            return None
        return self.evening_worse_days / self.compared_days

    def risen_error_types(self) -> tuple[str, ...]:
        """Error types clearly more common than this resident's own baseline."""
        return tuple(
            error_type
            for error_type in ERROR_TYPES
            if self.rate(error_type) - self.baseline_rate(error_type) >= BREADTH_MIN
        )


def _score(session: Mapping) -> float:
    return session_score(
        session.get("errors", {}),
        session.get("self_corrected", 0),
        session.get("assisted", False),
    )


def _mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def _rates(sessions: list[dict]) -> dict[str, float]:
    """Errors per session, by type, over a set of sessions."""
    if not sessions:
        return {}
    return {
        error_type: _mean(
            [float(session.get("errors", {}).get(error_type, 0)) for session in sessions]
        )
        for error_type in ERROR_TYPES
    }


def _error_count(session: Mapping) -> float:
    return float(sum(session.get("errors", {}).values()))


def _run_days(
    scored: list[tuple[datetime, dict, float]], threshold: float, now: datetime
) -> float | None:
    """Days since the start of the current run of sessions above threshold."""
    above = [index for index, (_, _, score) in enumerate(scored) if score > threshold]
    if not above:
        return None
    start = above[-1]
    while start - 1 in above:
        start -= 1
    return (now - scored[start][0]).total_seconds() / 86400.0


def _trend(scored: list[tuple[datetime, dict, float]]) -> Drift:
    """`drift.drift` over one point per day: the mean score that day."""
    by_day: dict[object, list[float]] = {}
    for ts, _, score in scored:
        by_day.setdefault(ts.date(), []).append(score)
    daily = sorted((day, _mean(scores)) for day, scores in by_day.items())
    return drift(daily)


def _evening_days(
    scored: list[tuple[datetime, dict, float]], day_start: datetime
) -> tuple[int, int]:
    """Days with both a morning and a late-day session, and how many were worse late.

    This is what separates a recurring daily pattern from one bad evening (SPEC §7.5).
    """
    by_day: dict[object, dict[str, list[float]]] = {}
    for ts, session, _ in scored:
        if ts <= day_start:
            continue
        if ts.hour >= EVENING_HOUR:
            slot = "late"
        elif ts.hour < MORNING_END_HOUR:
            slot = "early"
        else:
            continue
        day = by_day.setdefault(ts.date(), {"late": [], "early": []})
        day[slot].append(_error_count(session))
    compared = [slots for slots in by_day.values() if slots["late"] and slots["early"]]
    worse = [slots for slots in compared if _mean(slots["late"]) > _mean(slots["early"])]
    return len(compared), len(worse)


def _sedating(record: Mapping) -> bool:
    text = f"{record.get('value', '')} {record.get('note', '')}".lower()
    return any(medication in text for medication in SEDATING_MEDICATIONS)


def _ago(age_h: float) -> str:
    days = int(age_h // 24)
    if days == 0:
        return "today"
    if days == 1:
        return "yesterday"
    return f"{days} days ago"


def _context(care_records: list[dict], now: datetime) -> tuple[tuple[str, ...], dict[str, str]]:
    """Care-record context: which flags are set, and one line of evidence each.

    Normal observations are flags too. They lower a pattern that would explain a
    change by infection or dehydration, and never rule it out (SPEC §7.5).
    """
    notes: dict[str, str] = {}
    seen_temperature = False
    seen_fluids = False

    for record in sorted(care_records, key=lambda record: record["ts"], reverse=True):
        ts = datetime.fromisoformat(record["ts"])
        if ts > now:
            continue
        age_h = (now - ts).total_seconds() / 3600.0
        kind = record.get("kind")
        value = record.get("value")

        if kind == "med_change" and age_h <= MEDICATION_LOOKBACK_H:
            note = record.get("note") or f"medication change ({value})"
            line = f"{note}, {_ago(age_h)}"
            notes.setdefault("recent_medication_change", line)
            if age_h <= NEW_MEDICATION_H:
                notes.setdefault("new_medication", line)
            if _sedating(record):
                notes.setdefault("new_sedating_medication", line)
        elif kind == "temperature" and age_h <= VITALS_LOOKBACK_H:
            seen_temperature = True
            if float(value) >= FEVER_C:
                notes.setdefault("fever", f"temperature {float(value):.1f} C, {_ago(age_h)}")
        elif kind == "fluid_intake" and age_h <= VITALS_LOOKBACK_H:
            seen_fluids = True
            if float(value) < LOW_FLUID_ML:
                notes.setdefault(
                    "low_fluids", f"fluid intake {round(float(value))} ml, {_ago(age_h)}"
                )

    if seen_temperature and "fever" not in notes:
        notes["normal_temperature"] = "temperature normal in the last few days"
    if seen_fluids and "low_fluids" not in notes:
        notes["normal_fluids"] = "fluid intake normal in the last few days"

    return tuple(sorted(notes)), notes


def extract_features(
    sessions: list[dict],
    baseline: Baseline,
    care_records: list[dict] | None = None,
    now: datetime | None = None,
    window_h: float = CHANGE_WINDOW_H,
) -> Features:
    """One resident's features, from their own sessions and care records (SPEC §7.5).

    `sessions` are session records as `synth.history` writes them and `demo.py` and
    `session_log` pass them on: a timestamp, per-type error counts, self-corrected
    slips, a duration and whether somebody was assisting. Assisted sessions are
    dropped before anything is measured (SPEC §7).

    `now` defaults to the newest session, never the wall clock, so a recording and the
    live camera produce the same features.
    """
    scored = sorted(
        (
            (datetime.fromisoformat(session["ts"]), session, _score(session))
            for session in sessions
            if not session.get("assisted", False)
        ),
        key=lambda item: item[0],
    )
    if not scored:
        return Features(threshold=baseline.threshold, baseline_score_mean=baseline.mean)

    now = now or scored[-1][0]
    scored = [item for item in scored if item[0] <= now]
    window_start = now - timedelta(hours=window_h)
    recent = [item for item in scored if item[0] > window_start]
    before = [item for item in scored if item[0] <= window_start]

    trend = _trend(scored)
    change_days = (
        float(trend.days)
        if trend.trending
        else _run_days(scored, baseline.threshold, now)
    )

    day_start = now - timedelta(days=TIME_OF_DAY_DAYS)
    late = [item for item in scored if item[0] > day_start and item[0].hour >= EVENING_HOUR]
    early = [item for item in scored if item[0] > day_start and item[0].hour < MORNING_END_HOUR]
    early_before = [
        item for item in scored if item[0] <= day_start and item[0].hour < MORNING_END_HOUR
    ]
    compared_days, evening_worse_days = _evening_days(scored, day_start)

    recent_durations = [float(s.get("duration_s") or 0.0) for _, s, _ in recent]
    before_durations = [float(s.get("duration_s") or 0.0) for _, s, _ in before]
    recent_duration = _mean([d for d in recent_durations if d > 0.0])
    before_duration = _mean([d for d in before_durations if d > 0.0])

    context, notes = _context(care_records or [], now)

    return Features(
        recent_sessions=len(recent),
        baseline_sessions=len(before),
        recent_score_peak=max((score for _, _, score in recent), default=0.0),
        baseline_score_mean=baseline.mean,
        threshold=baseline.threshold,
        error_rates=_rates([session for _, session, _ in recent]),
        baseline_error_rates=_rates([session for _, session, _ in before]),
        change_days=change_days,
        drift_slope_per_day=trend.slope_per_day,
        drift_days=trend.days,
        drift_trending=trend.trending,
        duration_ratio=(
            recent_duration / before_duration if recent_duration and before_duration else None
        ),
        evening_error_rate=_mean([_error_count(s) for _, s, _ in late]) if late else None,
        morning_error_rate=_mean([_error_count(s) for _, s, _ in early]) if early else None,
        baseline_morning_error_rate=(
            _mean([_error_count(s) for _, s, _ in early_before]) if early_before else None
        ),
        compared_days=compared_days,
        evening_worse_days=evening_worse_days,
        self_corrected_rate=_mean([float(s.get("self_corrected", 0)) for _, s, _ in recent]),
        baseline_self_corrected_rate=_mean(
            [float(s.get("self_corrected", 0)) for _, s, _ in before]
        ),
        context=context,
        context_notes=notes,
    )
