"""From a flag to likely patterns (SPEC §7.5).

A flag says *something changed*. This module says what kind of change it is
consistent with, so a nurse knows what to rule out first::

    features = extract_features(resident["sessions"], baseline, resident["care_records"])
    patterns = score_patterns(features)   # top 3 above the threshold, best first

Two stages, both pure:

* `pattern_features.extract_features` turns a resident's own session history and care
  records into the feature list in SPEC §7.5 - error counts by type, durations and
  gaps against their own baseline, onset in days or weeks, time of day, movement
  speed, which hand, self-corrected slips, care-record context. Re-exported here as
  `extract_features` (with `Features`) so callers only need this module.
* `score_patterns` scores every pattern in `routine_watch.patterns_library` against
  those features. Each pattern's confidence is the weighted mean of its signals,
  narrowed by how well the onset matches its time profile, nudged by care-record
  context, scaled by how far the resident has moved past their own threshold, and
  finally multiplied by this resident's nurse-feedback weight for that pattern, if
  her nurses have answered "what was it?" before (`weights`, SPEC Nice to have 8).

It is rules over features, never a guess: the same features and the same past nurse
answers always give the same patterns, and the library is data, so the LLM summariser
never adds a pattern. An empty result is a real answer - "a change was detected, with
no clear pattern" - and the wording is always "consistent with ... - rule out ...".

Features the pipeline does not record yet (gaps between steps, movement speed from
the skeleton, per-hand step shares) are left as `None` rather than guessed. A pattern
whose signals are mostly unmeasurable is not scored at all, which is why the one-sided
change pattern stays out of the demo until per-hand shares are stored: callers that do
have those numbers can pass them to `Features` and it scores immediately.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping

from .contracts import PatternMatch
from .pattern_features import Features, extract_features  # noqa: F401 - re-exported
from .patterns_library import LIBRARY, Pattern, TimeProfile

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

# Normalisation: what counts as a signal at full strength. All signals are 0..1, so
# the weights in the library are the only thing that says which signal matters more.

#: One extra error of a given type per session.
RATE_FULL = 1.0

#: One and a half extra errors per session, counting every type.
TOTAL_RATE_FULL = 1.5

#: Error types up at once for "across error types" to be at full strength
#: (`pattern_features.BREADTH_MIN` is how far above baseline a type has to be
#: before it counts as one of them).
BREADTH_FULL = 3

#: 40 % longer, slower, or more time between steps.
RATIO_FULL = 0.4

#: Session score rising this much a day, on top of `drift.drift` calling it a trend.
SLOPE_FULL = 0.3

#: Half of the steps a hand normally does moving to the other hand.
HAND_DROP_FULL = 0.5

#: How far up a signal has to be to count as present at all: the bar a pattern's
#: `requires` signals have to clear, and the bar for a signal to be worth a line of
#: evidence.
SIGNAL_PRESENT = 0.25

#: At most this many signal lines and context lines per pattern, on top of the line
#: about its time course: a nurse reads the pattern in seconds (SPEC §9).
MAX_SIGNAL_LINES = 3
MAX_CONTEXT_LINES = 2


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


def _weight_line(weight: float, answers: int) -> str:
    """Why this pattern sits higher or lower than the rules alone put it.

    Shown whenever nurse feedback moved the pattern for this resident, so the
    ranking is never quietly re-ordered behind her back (SPEC Nice to have 8).
    """
    return (
        f"weighted by {answers} past nurse {'answer' if answers == 1 else 'answers'} "
        f"for this resident: confidence {'up' if weight > 1.0 else 'down'} {_pct(weight)}%"
    )


def _evidence(
    pattern: Pattern,
    features: Features,
    known: Mapping[str, float],
    weight: float = 1.0,
    answers: int = 0,
) -> list[str]:
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
    if weight != 1.0 and answers > 0:
        lines.append(_weight_line(weight, answers))
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
    pattern: Pattern,
    features: Features,
    values: Mapping[str, float | None],
    weight: float = 1.0,
    answers: int = 0,
) -> PatternMatch | None:
    """Score one pattern, or `None` if too much of it is unmeasurable here.

    `weight` is this resident's nurse-feedback multiplier for this pattern
    (`feedback.FeedbackStore.pattern_weights`), applied to the finished confidence so
    it moves the pattern's place in the ranking and nothing else: a pattern that does
    not match at all still scores zero however often it was confirmed before.
    """
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
        confidence=round(_clamp(_clamp(confidence) * weight), 3),
        urgency=pattern.urgency,
        evidence=_evidence(pattern, features, known, weight, answers),
        checks=list(pattern.checks),
    )


def score_patterns(
    features: Features,
    library: tuple[Pattern, ...] = LIBRARY,
    threshold: float = PATTERN_THRESHOLD,
    limit: int = MAX_PATTERNS,
    weights: Mapping[str, float] | None = None,
    answers: Mapping[str, int] | None = None,
) -> list[PatternMatch]:
    """The patterns this change is consistent with: best first, at most `limit`.

    An empty list is the honest answer when nothing clears the threshold, and the
    dashboard says so: "change detected, no clear pattern" (SPEC §7.5).

    `weights` is one resident's nurse-feedback multiplier per pattern id
    (`feedback.FeedbackStore.pattern_weights`), missing entries meaning 1.0: it
    multiplies each confidence before the threshold and the sort, so what her nurses
    confirmed before ranks higher and what they dismissed ranks lower on her next
    alerts (SPEC Nice to have 8). `answers` is how many answers each weight is read
    from (`pattern_answers`), for the evidence line that says so. With no weights
    this is the pattern library against the features and nothing else.
    """
    weights = weights or {}
    answers = answers or {}
    values = signals(features)
    matches = [
        match
        for pattern in library
        if (
            match := _match(
                pattern,
                features,
                values,
                weights.get(pattern.pattern_id, 1.0),
                answers.get(pattern.pattern_id, 0),
            )
        )
    ]
    scored = [match for match in matches if match.confidence >= threshold]
    scored.sort(key=lambda match: (-match.confidence, match.pattern_id))
    return scored[:limit]
