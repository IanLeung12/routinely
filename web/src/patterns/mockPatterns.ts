import type { PatternLibraryEntry } from './types.ts'

/** Mirrors `pipeline/src/routine_watch/patterns_library.py`'s `LIBRARY`, for the
 * screen to fall back to while offline (SPEC §13). */
export const mockPatterns: PatternLibraryEntry[] = [
  {
    pattern_id: 'sudden_change',
    name: 'Sudden change (delirium pattern)',
    signals: {
      omissions_up: 3.0,
      sequence_errors_up: 2.0,
      perseveration_up: 2.0,
      error_types_broad: 2.0,
      errors_up: 1.0,
    },
    time_profile: { onset_days: [0.0, 3.0], tolerance_days: 2.0, note: 'a step change within 1-3 days' },
    checks: ['infection_or_uti', 'hydration', 'medication_review', 'cam_screen'],
    urgency: 'same_shift',
    source: 'SPEC §7.5; CAM delirium screen (Inouye et al., 1990): acute onset, fluctuating '
      + 'course, several kinds of error at once.',
  },
  {
    pattern_id: 'slow_drift',
    name: 'Slow drift (cognitive decline pattern)',
    signals: { steady_rise: 3.0, hesitation_up: 2.0, errors_up: 1.0 },
    time_profile: { onset_days: [7.0, 60.0], tolerance_days: 4.0, note: 'a steady rise over weeks' },
    checks: ['Cognitive reassessment', 'Care-plan review'],
    urgency: 'routine',
    source: 'SPEC §7.5; gradual loss of instrumental activities of daily living, measured in '
      + 'weeks rather than days.',
  },
  {
    pattern_id: 'evening_worsening',
    name: 'Evening-only worsening (sundowning pattern)',
    signals: { evening_concentrated: 3.0, mornings_normal: 2.0, errors_up: 1.0 },
    time_profile: {
      onset_days: [0.0, 60.0], tolerance_days: 10.0, note: 'late-day sessions only, recurring daily',
    },
    checks: ['Review sleep, lighting and the evening routine', 'Rule out pain', 'Review evening medication'],
    urgency: 'routine',
    source: "SPEC §7.5; late-day worsening ('sundowning') described in dementia care guidance.",
  },
  {
    pattern_id: 'motor_slowing',
    name: 'Motor slowing / medication effect',
    signals: {
      durations_up: 3.0, gaps_up: 2.0, movement_slower: 2.0, hesitation_up: 1.0, sequencing_intact: 1.0,
    },
    time_profile: {
      onset_days: [0.0, 21.0], tolerance_days: 7.0, note: 'slowing after a medication change, or gradual',
    },
    checks: ['medication_review', 'Rule out sedation or anticholinergic burden', 'Mobility check'],
    urgency: 'next_round',
    source: 'SPEC §7.5; sedative and anticholinergic burden slows everyday-action performance '
      + 'without disordering it.',
  },
  {
    pattern_id: 'executive_pattern',
    name: 'Executive pattern',
    signals: { perseveration_up: 3.0, sequencing_intact: 2.0, errors_up: 1.0 },
    time_profile: {
      onset_days: [2.0, 21.0], tolerance_days: 3.0, note: 'days to weeks, with the order of steps otherwise intact',
    },
    checks: ['Cognitive screen', 'Review recent changes in routine or medication'],
    urgency: 'routine',
    source: 'SPEC §7.5; perseveration in the everyday-action error taxonomy (Schwartz et al., '
      + 'Naturalistic Action Test).',
  },
  {
    pattern_id: 'one_sided_change',
    name: 'One-sided change (possible stroke)',
    signals: { hand_use_dropped: 5.0, errors_up: 1.0 },
    time_profile: {
      onset_days: [0.0, 1.0], tolerance_days: 1.0, note: 'one hand dropping out of its usual steps within hours',
    },
    checks: ['Escalate now per facility stroke protocol'],
    urgency: 'urgent',
    source: 'SPEC §7.5; sudden one-sided weakness, FAST stroke recognition. Needs per-hand step '
      + 'shares, which capture records carry but the store does not keep yet, so it scores only '
      + 'where that feature is supplied.',
  },
]
