import { mockPersonRoutine, mockSteadyRoutine } from './mockRoutine.ts'
import type { PersonRoutine } from './types.ts'

/** Where "My routine" reads one person's own week from (SPEC section 17).
 *
 * There is no per-person route yet - the pipeline's routes are all about a resident
 * a supervisor is looking at - so this is mock-backed, exactly like the linking API
 * next door (`people/api.ts`). The screen only ever calls `routineFor`, so when a
 * real route lands it implements `PersonRoutineApi` and `setPersonRoutineApi` swaps
 * it in without the screen changing.
 *
 * Deliberately synchronous, for the same reason `people/api.ts` is: the person's
 * home screen can then draw their week on the first render instead of flashing a
 * loading state at them. A real backend would cache its answers behind this shape.
 * Nothing to show is a routine with no days and no sessions, which every section
 * below handles, so an empty answer needs no second code path. */
export interface PersonRoutineApi {
  /** This person's own week, their usual, and the patterns behind a change. */
  routineFor(personId: string): PersonRoutine
}

const browserPersonRoutineApi: PersonRoutineApi = {
  routineFor(personId) {
    return personId === mockPersonRoutine.person_id
      ? mockPersonRoutine
      : { ...mockSteadyRoutine, person_id: personId }
  },
}

let api: PersonRoutineApi = browserPersonRoutineApi

/** Replaces the mock with a real per-person API once there is one (null goes back). */
export function setPersonRoutineApi(next: PersonRoutineApi | null): void {
  api = next ?? browserPersonRoutineApi
}

export function routineFor(personId: string): PersonRoutine {
  return api.routineFor(personId)
}
