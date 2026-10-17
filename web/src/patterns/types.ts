import type { PatternUrgency, SuggestedCheck } from '../contracts.ts'

/** How long a change of this kind takes to show up (SPEC §7.5, "time profile"). */
export type TimeProfile = {
  /** The window the change is expected to have been building for, in days. */
  onset_days: [number, number]
  /** How far outside the onset window still counts (days). */
  tolerance_days: number
  /** The phrase a nurse reads, e.g. "a step change within 1-3 days". */
  note: string
}

/** One entry in the pattern library (`GET /patterns`, SPEC §7.5): what a pattern
 * looks for, where it comes from, and what to rule out - always something a change
 * is "consistent with", never a verdict. */
export type PatternLibraryEntry = {
  pattern_id: string
  name: string
  /** Signal name -> weight: what the rule looks for and how much each signal counts. */
  signals: Record<string, number>
  time_profile: TimeProfile
  checks: (SuggestedCheck | string)[]
  urgency: PatternUrgency
  /** Where the pattern comes from: a SPEC section, a clinical screen, a citation. */
  source: string
}
