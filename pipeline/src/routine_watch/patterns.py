"""From a flag to likely patterns (SPEC §7.5).

A flag says *something changed*. This module says what kind of change it is
consistent with, so a nurse knows what to rule out first::

    features = extract_features(resident["sessions"], baseline, resident["care_records"])
    patterns = score_patterns(features)   # top 3 above the threshold, best first

Two stages, both pure:

* `extract_features` turns a resident's own session history and care records into the
  feature list in SPEC §7.5 - error counts by type, durations and gaps against their
  own baseline, onset in days or weeks, time of day, movement speed, which hand,
  self-corrected slips, care-record context.
* `score_patterns` scores every pattern in `routine_watch.patterns_library` against
  those features. Each pattern's confidence is the weighted mean of its signals,
  narrowed by how well the onset matches its time profile, nudged by care-record
  context, and scaled by how far the resident has moved past their own threshold.

It is rules over features, never a guess: the same features always give the same
patterns, and the library is data, so the LLM summariser never adds a pattern. An
empty result is a real answer - "a change was detected, with no clear pattern" - and
the wording is always "consistent with ... - rule out ...".

Features the pipeline does not record yet (gaps between steps, movement speed from
the skeleton, per-hand step shares) are left as `None` rather than guessed. A pattern
whose signals are mostly unmeasurable is not scored at all, which is why the one-sided
change pattern stays out of the demo until per-hand shares are stored: callers that do
have those numbers can pass them to `Features` and it scores immediately.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from .change_detection import Baseline
from .contracts import PatternMatch
from .drift import Drift, drift
from .errors import ERROR_TYPES
from .patterns_library import LIBRARY, SEDATING_MEDICATIONS, Pattern, TimeProfile
from .scoring import session_score

STAGE = "patterns"

#: Confidence a pattern needs before it is worth showing (SPEC §7.5: the top 1-3
#: above a threshold, and "no clear pattern" rather than the least bad guess).
PATTERN_THRESHOLD = 0.35

#: How many patterns a nurse is shown at once (SPEC §7.5).
MAX_PATTERNS = 3

#: A pattern is skipped unless signals carrying at least this share of its weight can
#: actually be measured. Half keeps a pattern alive when one of its signals is not
#: recorded yet, and drops one that is mostly guesswork.
MIN_COVERAGE = 0.5

#: The window "what just changed" is read from: the same 24-48 h as the flag itself
#: (`change_detection.flag_change`, `alerts.FLAG_WINDOW_H`).
CHANGE_WINDOW_H = 48.0

#: Days of recent history a time-of-day pattern is read from. A recurring daily
#: pattern needs more than the flag window: two sessions cannot show "every evening".
TIME_OF_DAY_DAYS = 7

#: Sessions starting at or after this hour are late-day; before noon is morning.
EVENING_HOUR = 16
MORNING_END_HOUR = 12

# Normalisation: what counts as a signal at full strength. All signals are 0..1, so
# the weights in the library are the only thing that says which signal matters more.

#: One extra error of a given type per session.
RATE_FULL = 1.0

#: One and a half extra errors per session, counting every type.
TOTAL_RATE_FULL = 1.5

#: Error types up at once for "across error types" to be at full strength, and how
#: far above baseline a type has to be before it counts as one of them.
BREADTH_FULL = 3
BREADTH_MIN = 0.25

#: 40 % longer, slower, or more time between steps.
RATIO_FULL = 0.4

#: Session score rising this much a day, on top of `drift.drift` calling it a trend.
SLOPE_FULL = 0.3

#: Half of the steps a hand normally does moving to the other hand.
HAND_DROP_FULL = 0.5

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

#: How far up a signal has to be to count as present at all: the bar a pattern's
#: `requires` signals have to clear, and the bar for a signal to be worth a line of
#: evidence.
SIGNAL_PRESENT = 0.25

#: At most this many signal lines and context lines per pattern, on top of the line
#: about its time course: a nurse reads the pattern in seconds (SPEC §9).
MAX_SIGNAL_LINES = 3
MAX_CONTEXT_LINES = 2


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


# ------------------------------------------------------------------- the signals


def _clamp(value: float) -> float:
    return max(0.0, min(1.0, value))


def _comparable(features: Features) -> bool:
    """There is history on both sides of the window, so "up" means something."""
    return features.recent_sessions > 0 and features.baseline_sessions > 0


def _type_up(features: Features, error_type: str) -> float | None:
    if not _comparable(features):
        return None
    return _clamp((features.rate(error_type) - features.baseline_rate(error_type)) / RATE_FULL)


def _errors_up(features: Features) -> float | None:
    if not _comparable(features):
        return None
    rise = features.total_error_rate - features.baseline_total_error_rate
    return _clamp(rise / TOTAL_RATE_FULL)


def _error_types_broad(features: Features) -> float | None:
    if not _comparable(features):
        return None
    return _clamp(len(features.risen_error_types()) / BREADTH_FULL)


def _steady_rise(features: Features) -> float:
    """A sustained rise over weeks, as `drift.drift` measures it.

    Zero, not unknown, when the history is too short to show one: a fortnight of
    hesitation is not evidence of a slow decline.
    """
    if not features.drift_trending:
        return 0.0
    return _clamp(features.drift_slope_per_day / SLOPE_FULL)


def _evening_concentrated(features: Features) -> float | None:
    """Errors concentrated late in the day, and recurring rather than one-off.

    A sudden change that happens to land on an evening session is not a daily
    pattern, so the gap between late-day and morning errors is scaled by how many of
    the window's days actually show it.
    """
    recurrence = features.evening_recurrence
    if (
        recurrence is None
        or features.evening_error_rate is None
        or features.morning_error_rate is None
    ):
        return None
    gap = (features.evening_error_rate - features.morning_error_rate) / RATE_FULL
    return _clamp(gap) * recurrence


def _mornings_normal(features: Features) -> float | None:
    if features.morning_error_rate is None or features.baseline_morning_error_rate is None:
        return None
    rise = features.morning_error_rate - features.baseline_morning_error_rate
    return _clamp(1.0 - rise / RATE_FULL)


def _ratio_up(ratio: float | None) -> float | None:
    if ratio is None:
        return None
    return _clamp((ratio - 1.0) / RATIO_FULL)


def _movement_slower(features: Features) -> float | None:
    if features.movement_speed_ratio is None:
        return None
    return _clamp((1.0 - features.movement_speed_ratio) / RATIO_FULL)


def _sequencing_intact(features: Features) -> float | None:
    """The order of the steps is still right: what tells slowing from disorder."""
    sequence_up = _type_up(features, "sequence")
    if sequence_up is None:
        return None
    return 1.0 - sequence_up


def _hand_use_dropped(features: Features) -> float | None:
    if features.hand_share_drop is None:
        return None
    return _clamp(features.hand_share_drop / HAND_DROP_FULL)


def _self_corrected_up(features: Features) -> float | None:
    if not _comparable(features):
        return None
    rise = features.self_corrected_rate - features.baseline_self_corrected_rate
    return _clamp(rise / RATE_FULL)


#: Every signal a pattern may weigh, each 0..1, or `None` when the pipeline cannot
#: measure it for this resident yet. A couple (`substitutions_up`,
#: `self_corrected_up`) are computed with no pattern in the library weighing them:
#: SPEC §7.5 lists both as features, so a new library entry can pick them up without
#: touching this module.
SIGNALS: Mapping[str, Callable[[Features], float | None]] = {
    "omissions_up": lambda f: _type_up(f, "omission"),
    "sequence_errors_up": lambda f: _type_up(f, "sequence"),
    "perseveration_up": lambda f: _type_up(f, "perseveration"),
    "substitutions_up": lambda f: _type_up(f, "substitution"),
    "hesitation_up": lambda f: _type_up(f, "hesitation"),
    "errors_up": _errors_up,
    "error_types_broad": _error_types_broad,
    "steady_rise": _steady_rise,
    "evening_concentrated": _evening_concentrated,
    "mornings_normal": _mornings_normal,
    "durations_up": lambda f: _ratio_up(f.duration_ratio),
    "gaps_up": lambda f: _ratio_up(f.gap_ratio),
    "movement_slower": _movement_slower,
    "sequencing_intact": _sequencing_intact,
    "hand_use_dropped": _hand_use_dropped,
    "self_corrected_up": _self_corrected_up,
}

assert {name for pattern in LIBRARY for name in pattern.signals} <= set(SIGNALS), (
    "the pattern library weighs a signal this module does not compute"
)


def signals(features: Features) -> dict[str, float | None]:
    """Every signal, by name: 0..1, or `None` where the data is not there."""
    return {name: signal(features) for name, signal in SIGNALS.items()}


# ------------------------------------------------------------------ the wording


def _pct(ratio: float) -> int:
    return round(abs(ratio - 1.0) * 100)


def _rate_line(label: str, features: Features, error_type: str) -> str:
    return (
        f"{label} up to {features.rate(error_type):.1f} a session "
        f"from {features.baseline_rate(error_type):.1f}"
    )


#: One line of plain-language evidence per signal, read off the features themselves.
#: The wording stays here, with the arithmetic, so the library stays declarative.
EVIDENCE: Mapping[str, Callable[[Features], str]] = {
    "omissions_up": lambda f: _rate_line("missed steps", f, "omission"),
    "sequence_errors_up": lambda f: _rate_line("steps out of order", f, "sequence"),
    "perseveration_up": lambda f: _rate_line("repeated steps", f, "perseveration"),
    "substitutions_up": lambda f: _rate_line("wrong object used", f, "substitution"),
    "hesitation_up": lambda f: _rate_line("long pauses", f, "hesitation"),
    "errors_up": lambda f: (
        f"{f.total_error_rate:.1f} errors a session against "
        f"{f.baseline_total_error_rate:.1f} normally for this resident"
    ),
    "error_types_broad": lambda f: (
        f"{len(f.risen_error_types())} kinds of error up at once "
        f"({', '.join(f.risen_error_types())})"
    ),
    "steady_rise": lambda f: (
        f"session score rising about {f.drift_slope_per_day:.1f} a day "
        f"over {f.drift_days} days"
    ),
    "evening_concentrated": lambda f: (
        f"late-day sessions average {f.evening_error_rate:.1f} errors against "
        f"{f.morning_error_rate:.1f} in the morning, on {f.evening_worse_days} "
        f"of {f.compared_days} days"
    ),
    "mornings_normal": lambda f: (
        f"mornings unchanged at {f.morning_error_rate:.1f} errors a session"
    ),
    "durations_up": lambda f: (
        f"sessions about {_pct(f.duration_ratio)}% longer than this resident's own average"
    ),
    "gaps_up": lambda f: f"gaps between steps about {_pct(f.gap_ratio)}% longer",
    "movement_slower": lambda f: (
        f"movement about {_pct(f.movement_speed_ratio)}% slower than this resident's own average"
    ),
    "sequencing_intact": lambda f: (
        f"the order of the steps is still right ({f.rate('sequence'):.1f} "
        f"steps out of order a session)"
    ),
    "hand_use_dropped": lambda f: (
        f"one hand doing {round((f.hand_share_drop or 0.0) * 100)}% fewer of the steps "
        f"it normally does"
    ),
    "self_corrected_up": lambda f: (
        f"{f.self_corrected_rate:.1f} self-corrected slips a session against "
        f"{f.baseline_self_corrected_rate:.1f} normally"
    ),
}


def _days(days: float) -> str:
    if days < 1.5:
        return "a day"
    return f"{days:.0f} days"


def _ago(age_h: float) -> str:
    days = int(age_h // 24)
    if days == 0:
        return "today"
    if days == 1:
        return "yesterday"
    return f"{days} days ago"


def _time_line(profile: TimeProfile, features: Features) -> str:
    if features.change_days is None:
        return f"consistent with {profile.note}"
    return f"came on over about {_days(features.change_days)}, consistent with {profile.note}"


def _evidence(pattern: Pattern, features: Features, known: Mapping[str, float]) -> list[str]:
    """The lines a nurse reads under the pattern name, strongest signal first."""
    lines = [_time_line(pattern.time_profile, features)]

    ranked = sorted(known.items(), key=lambda item: (-pattern.signals[item[0]] * item[1], item[0]))
    for name, value in ranked[:MAX_SIGNAL_LINES]:
        if value >= SIGNAL_PRESENT:
            lines.append(EVIDENCE[name](features))

    context = sorted(pattern.context_weights.items(), key=lambda item: (-item[1], item[0]))
    notes = [
        note
        for flag, _ in context
        if flag in features.context and (note := features.context_notes.get(flag))
    ]
    lines += list(dict.fromkeys(notes))[:MAX_CONTEXT_LINES]
    return lines


# ------------------------------------------------------------------- the scorer


def time_fit(profile: TimeProfile, change_days: float | None) -> float:
    """How well the onset matches a pattern's time profile, 0..1.

    Full marks inside the window, fading to nothing over the pattern's tolerance
    outside it: this is what keeps a two-day step change from being read as a drift
    over weeks. An unknown onset is neutral - it contradicts nothing.
    """
    if change_days is None:
        return 1.0
    low, high = profile.onset_days
    if low <= change_days <= high:
        return 1.0
    distance = low - change_days if change_days < low else change_days - high
    return _clamp(1.0 - distance / profile.tolerance_days)


def _match(
    pattern: Pattern, features: Features, values: Mapping[str, float | None]
) -> PatternMatch | None:
    """Score one pattern, or `None` if too much of it is unmeasurable here."""
    weights = pattern.signals
    total = sum(weights.values())
    known = {name: value for name in weights if (value := values.get(name)) is not None}
    covered = sum(weights[name] for name in known)
    if total <= 0.0 or covered < MIN_COVERAGE * total:
        return None
    if any(known.get(name, 0.0) < SIGNAL_PRESENT for name in pattern.requires):
        return None

    signal_score = sum(weights[name] * value for name, value in known.items()) / covered
    context = sum(
        delta for flag, delta in pattern.context_weights.items() if flag in features.context
    )
    fitted = signal_score * time_fit(pattern.time_profile, features.change_days)
    confidence = (fitted * pattern.max_confidence + context) * features.change_strength

    return PatternMatch(
        pattern_id=pattern.pattern_id,
        name=pattern.name,
        confidence=round(_clamp(confidence), 3),
        urgency=pattern.urgency,
        evidence=_evidence(pattern, features, known),
        checks=list(pattern.checks),
    )


def score_patterns(
    features: Features,
    library: tuple[Pattern, ...] = LIBRARY,
    threshold: float = PATTERN_THRESHOLD,
    limit: int = MAX_PATTERNS,
) -> list[PatternMatch]:
    """The patterns this change is consistent with: best first, at most `limit`.

    An empty list is the honest answer when nothing clears the threshold, and the
    dashboard says so: "change detected, no clear pattern" (SPEC §7.5).
    """
    values = signals(features)
    matches = [match for pattern in library if (match := _match(pattern, features, values))]
    scored = [match for match in matches if match.confidence >= threshold]
    scored.sort(key=lambda match: (-match.confidence, match.pattern_id))
    return scored[:limit]


# ----------------------------------------------------------------- the features


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
