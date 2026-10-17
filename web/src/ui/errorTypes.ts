import type { ErrorType } from '../contracts.ts'

/** Plain-language names for the error types in SPEC section 7, used wherever a type
 * needs to read on its own (no step name to hand). */
export const ERROR_TYPE_LABEL: Record<ErrorType, string> = {
  omission: 'skipped step',
  sequence: 'out of order',
  perseveration: 'repeated step',
  substitution: 'wrong object',
  hesitation: 'long pause',
  abandonment: 'stopped partway',
}

/** SPEC section 9: red = omission/substitution, amber = sequence/repeat,
 * grey = everything else (a pause or a stop is uncertain, not a clear mistake). */
export const ERROR_TYPE_TONE: Record<ErrorType, 'red' | 'amber' | 'grey'> = {
  omission: 'red',
  substitution: 'red',
  sequence: 'amber',
  perseveration: 'amber',
  hesitation: 'grey',
  abandonment: 'grey',
}

/** Same wording as `pipeline/src/routine_watch/explain.py`'s `_PHRASES`, so the
 * dashboard reads exactly like the plain-language summary it is built from. */
const PHRASES: Record<ErrorType, (step: string) => string> = {
  omission: (step) => `skipped ${step}`,
  perseveration: (step) => `repeated ${step}`,
  sequence: (step) => `${step} out of order`,
  substitution: (step) => `wrong object for ${step}`,
  hesitation: (step) => `long pause at ${step}`,
  abandonment: (step) => `stopped before ${step}`,
}

/** One error, named with the step it happened at, e.g. "skipped put the teabag in the cup". */
export function describeError(type: ErrorType, stepLabel: string): string {
  return PHRASES[type](stepLabel)
}
