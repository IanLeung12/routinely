/** The pattern library's shapes (`GET /patterns`, SPEC §7.5): what a pattern looks
 * for, where it comes from, and what to rule out - always something a change is
 * "consistent with", never a verdict.
 *
 * Generated from the pipeline's contracts (`web/src/contracts.ts`) and re-exported
 * under this screen's own names, so a field added to the library on either side alone
 * fails the dashboard's build. */
export type { PatternLibraryEntry, PatternTimeProfile as TimeProfile } from '../contracts.ts'
