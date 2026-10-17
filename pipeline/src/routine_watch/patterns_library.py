"""The pattern library, held as data (SPEC §7.5).

A flag says *something changed*. These patterns say what kind of change it looks
like, so the care team knows what to rule out first. The table below is the whole
library: signals and their weights, which of them a change has to show at all, the
time profile a change of this kind follows, the care-record context that raises or
lowers it, what to rule out, how urgent it is and where the pattern comes from.
`routine_watch.patterns` owns every bit of arithmetic, so a new pattern is a new entry
here and nothing else.

Nothing here is a claim about a resident. A pattern is only ever something a change
is **consistent with**, next to the checks that would rule it out.

Signal names must exist in `routine_watch.patterns.SIGNALS`, and context names in
`CONTEXT_FLAGS`; both are asserted when that module is imported, so a typo in this
table fails at import rather than quietly scoring zero.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field

from .contracts import PatternUrgency, SuggestedCheck

#: Care-record context a pattern may weigh (`routine_watch.patterns` sets these from
#: the resident's records). Raising and lowering flags both live here: normal
#: observations make a pattern less likely, never impossible (SPEC §7.5).
CONTEXT_FLAGS: tuple[str, ...] = (
    "new_medication",
    "new_sedating_medication",
    "recent_medication_change",
    "fever",
    "low_fluids",
    "normal_temperature",
    "normal_fluids",
)

#: Substances whose main everyday effect is sedation or anticholinergic load, matched
#: case-insensitively against a care record's value and note. Short and
#: care-home-flavoured on purpose: enough for the demo residents, extended as real
#: records arrive.
SEDATING_MEDICATIONS: tuple[str, ...] = (
    "amitriptyline",
    "chlorphenamine",
    "codeine",
    "cyclizine",
    "diazepam",
    "diphenhydramine",
    "gabapentin",
    "haloperidol",
    "hydroxyzine",
    "lorazepam",
    "mirtazapine",
    "morphine",
    "olanzapine",
    "oxybutynin",
    "oxycodone",
    "promethazine",
    "quetiapine",
    "risperidone",
    "trazodone",
    "zopiclone",
    # Written in a note rather than named, e.g. "new sedating medication started".
    "sedating",
    "sedative",
    "antihistamine",
)


@dataclass(frozen=True)
class TimeProfile:
    """How long a change of this kind takes to show up (SPEC §7.5, "time profile").

    `onset_days` is the window the change is expected to have been building for, and
    `tolerance_days` how far outside it still counts for anything: a step change two
    days old is not a drift over weeks, and vice versa. `note` is the phrase a nurse
    reads, so it stays next to the numbers it describes.
    """

    onset_days: tuple[float, float]
    tolerance_days: float
    note: str


@dataclass(frozen=True)
class Pattern:
    """One pattern a change can be consistent with."""

    pattern_id: str
    name: str
    signals: Mapping[str, float]
    time_profile: TimeProfile
    checks: tuple[SuggestedCheck | str, ...]
    urgency: PatternUrgency
    source: str
    #: Signals this pattern is defined by: unless every one of them is actually up,
    #: the pattern does not score at all. Without this a pattern can coast on the
    #: signals that are normal by default ("mornings fine", "order still right"),
    #: which are only worth anything next to the signal that does distinguish it.
    requires: tuple[str, ...] = ()
    context_weights: Mapping[str, float] = field(default_factory=dict)
    #: Ceiling on this pattern's confidence. Below 1.0 for the patterns whose signals
    #: the pipeline cannot measure well yet, so they can appear without outranking a
    #: pattern that is fully evidenced (SPEC §7.5: sudden change and slow drift are
    #: the two the MVP scores on).
    max_confidence: float = 1.0


#: The six patterns in SPEC §7.5, best-understood first.
LIBRARY: tuple[Pattern, ...] = (
    Pattern(
        pattern_id="sudden_change",
        name="Sudden change (delirium pattern)",
        signals={
            "omissions_up": 3.0,
            "sequence_errors_up": 2.0,
            "perseveration_up": 2.0,
            "error_types_broad": 2.0,
            "errors_up": 1.0,
        },
        time_profile=TimeProfile(
            onset_days=(0.0, 3.0),
            tolerance_days=2.0,
            note="a step change within 1-3 days",
        ),
        checks=(
            SuggestedCheck.INFECTION_OR_UTI,
            SuggestedCheck.HYDRATION,
            SuggestedCheck.MEDICATION_REVIEW,
            SuggestedCheck.CAM_SCREEN,
        ),
        urgency=PatternUrgency.SAME_SHIFT,
        context_weights={
            "new_medication": 0.10,
            "fever": 0.08,
            "low_fluids": 0.05,
            "normal_temperature": -0.05,
            "normal_fluids": -0.03,
        },
        source="SPEC §7.5; CAM delirium screen (Inouye et al., 1990): acute onset, "
        "fluctuating course, several kinds of error at once.",
    ),
    Pattern(
        pattern_id="slow_drift",
        name="Slow drift (cognitive decline pattern)",
        signals={
            "steady_rise": 3.0,
            "hesitation_up": 2.0,
            "errors_up": 1.0,
        },
        time_profile=TimeProfile(
            onset_days=(7.0, 60.0),
            tolerance_days=4.0,
            note="a steady rise over weeks",
        ),
        checks=("Cognitive reassessment", "Care-plan review"),
        urgency=PatternUrgency.ROUTINE,
        requires=("steady_rise",),
        source="SPEC §7.5; gradual loss of instrumental activities of daily living, "
        "measured in weeks rather than days.",
    ),
    Pattern(
        pattern_id="evening_worsening",
        name="Evening-only worsening (sundowning pattern)",
        signals={
            "evening_concentrated": 3.0,
            "mornings_normal": 2.0,
            "errors_up": 1.0,
        },
        time_profile=TimeProfile(
            onset_days=(0.0, 60.0),
            tolerance_days=10.0,
            note="late-day sessions only, recurring daily",
        ),
        checks=(
            "Review sleep, lighting and the evening routine",
            "Rule out pain",
            "Review evening medication",
        ),
        urgency=PatternUrgency.ROUTINE,
        requires=("evening_concentrated",),
        max_confidence=0.7,
        source="SPEC §7.5; late-day worsening ('sundowning') described in dementia "
        "care guidance.",
    ),
    Pattern(
        pattern_id="motor_slowing",
        name="Motor slowing / medication effect",
        signals={
            "durations_up": 3.0,
            "gaps_up": 2.0,
            "movement_slower": 2.0,
            "hesitation_up": 1.0,
            "sequencing_intact": 1.0,
        },
        time_profile=TimeProfile(
            onset_days=(0.0, 21.0),
            tolerance_days=7.0,
            note="slowing after a medication change, or gradual",
        ),
        checks=(
            SuggestedCheck.MEDICATION_REVIEW,
            "Rule out sedation or anticholinergic burden",
            "Mobility check",
        ),
        urgency=PatternUrgency.NEXT_ROUND,
        requires=("durations_up",),
        context_weights={
            "new_sedating_medication": 0.15,
            "recent_medication_change": 0.05,
        },
        max_confidence=0.8,
        source="SPEC §7.5; sedative and anticholinergic burden slows everyday-action "
        "performance without disordering it.",
    ),
    Pattern(
        pattern_id="executive_pattern",
        name="Executive pattern",
        signals={
            "perseveration_up": 3.0,
            "sequencing_intact": 2.0,
            "errors_up": 1.0,
        },
        time_profile=TimeProfile(
            onset_days=(2.0, 21.0),
            tolerance_days=3.0,
            note="days to weeks, with the order of steps otherwise intact",
        ),
        checks=("Cognitive screen", "Review recent changes in routine or medication"),
        urgency=PatternUrgency.ROUTINE,
        requires=("perseveration_up",),
        max_confidence=0.7,
        source="SPEC §7.5; perseveration in the everyday-action error taxonomy "
        "(Schwartz et al., Naturalistic Action Test).",
    ),
    Pattern(
        pattern_id="one_sided_change",
        name="One-sided change (possible stroke)",
        signals={
            "hand_use_dropped": 5.0,
            "errors_up": 1.0,
        },
        time_profile=TimeProfile(
            onset_days=(0.0, 1.0),
            tolerance_days=1.0,
            note="one hand dropping out of its usual steps within hours",
        ),
        checks=("Escalate now per facility stroke protocol",),
        urgency=PatternUrgency.URGENT,
        requires=("hand_use_dropped",),
        max_confidence=0.9,
        source="SPEC §7.5; sudden one-sided weakness, FAST stroke recognition. Needs "
        "per-hand step shares, which capture records carry but the store does not keep "
        "yet, so it scores only where that feature is supplied.",
    ),
)

#: The library by id, for callers that want one pattern.
BY_ID: Mapping[str, Pattern] = {pattern.pattern_id: pattern for pattern in LIBRARY}

assert len(BY_ID) == len(LIBRARY), "pattern ids must be unique"
assert all(
    flag in CONTEXT_FLAGS for pattern in LIBRARY for flag in pattern.context_weights
), "unknown context flag in the pattern library"
assert all(
    name in pattern.signals for pattern in LIBRARY for name in pattern.requires
), "a pattern requires a signal it does not weigh"
