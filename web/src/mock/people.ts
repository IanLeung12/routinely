import type { Person, PersonLink, Supervisor } from '../people/types.ts'
import { mockResidents } from './residents.ts'

/** The demo's people and who watches over them (SPEC section 17). Stands in for a
 * pairing backend that doesn't exist yet: `people/api.ts` seeds localStorage from this
 * and every link made or removed in the UI is written back there.
 *
 * SPEC section 17 asks for three cases, and they are the three the demo flips between:
 * Mrs. K in a care home with Nurse Ana watching, Mr. D at home with his daughter Lena
 * watching, and Sam watching their own routine with nobody else linked.
 *
 * The rest of the care-home unit comes from `mockResidents` rather than a second copy
 * of the same names, so Nurse Ana supports the unit the dashboard already shows: the
 * original nurse view is simply the supervisor-with-many case. */

/** The care-home unit, as people rather than rows of a nurse's list. */
const unit: Person[] = mockResidents.map((resident) => ({
  id: resident.id,
  name: resident.name,
  context: `Room ${resident.room}, care home`,
}))

/** Lives alone; his daughter is the only one watching (SPEC section 17). */
const mrD: Person = { id: 'mr-d', name: 'Mr. D', context: 'Lives alone' }

/** Watching their own routine, nobody linked. The demo's "me" in the person role. */
const sam: Person = { id: 'sam', name: 'Sam', context: 'Watching their own routine' }

export const mockPeople: Person[] = [...unit, mrD, sam]

export const mockSupervisors: Supervisor[] = [
  { id: 'nurse-ana', name: 'Nurse Ana', relationship: 'nurse', context: 'Day shift, care home' },
  { id: 'lena', name: 'Lena', relationship: 'family', context: "Mr. D's daughter" },
]

/** Who can see whose routine before anyone changes anything in the UI. Sam is in
 * nobody's list: self-monitoring is a supported state, not a setup step left undone. */
export const mockLinks: PersonLink[] = [
  ...unit.map((person) => ({ person_id: person.id, supervisor_id: 'nurse-ana' })),
  { person_id: mrD.id, supervisor_id: 'lena' },
]

/** Who the demo is when the person role is picked: Sam, with nobody watching yet, so
 * "invite someone" has something to do. */
export const MOCK_CURRENT_PERSON_ID = sam.id

/** Who the demo is when the supervisor role is picked: the care-home nurse, so the
 * existing unit dashboard is what the supervisor role opens on. */
export const MOCK_CURRENT_SUPERVISOR_ID = 'nurse-ana'
