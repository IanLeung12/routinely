import { RecentSessions } from './RecentSessions.tsx'
import { RoutineChart } from './RoutineChart.tsx'
import { RoutineNotes } from './RoutineNotes.tsx'
import { RoutineStatus } from './RoutineStatus.tsx'
import { routineFor } from './api.ts'

/** The reading half of "My routine" (SPEC section 17), in the order the questions
 * come in: how the week looked, their usual against it, the sessions behind it, and
 * a note when something was different.
 *
 * One module so `people/MyRoutine.tsx` can load it on demand: a supervisor opening
 * the unit dashboard never renders any of this, and the first-load budget
 * (`web/scripts/check-bundle.mjs`) is the nurse's first paint. The person's own
 * week is one small fetch behind their heading instead. */
export function RoutineSections({
  personId,
  supervisorNames,
}: {
  personId: string
  supervisorNames: string[]
}) {
  const routine = routineFor(personId)

  return (
    <>
      <RoutineStatus routine={routine} />
      <RoutineChart routine={routine} />
      <RecentSessions routine={routine} />
      <RoutineNotes patterns={routine.patterns} supervisorNames={supervisorNames} />
    </>
  )
}

export default RoutineSections
