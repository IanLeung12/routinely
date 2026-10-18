/** Who is using the app and who they are linked to (SPEC section 3, section 17).
 *
 * Anyone can use Routinely, alone or with someone watching over them, so the shell
 * asks for one of two roles before it shows anything:
 *
 * - `person`: watching their own routine.
 * - `supervisor`: anyone the person linked - a family member, a carer, or a nurse on a
 *   care-home unit. A supervisor can support one person or a whole unit.
 *
 * Field names are snake_case like the rest of the payloads in `contracts.ts`: these
 * stand in for a pairing API that doesn't exist yet (SPEC section 17, "mock linking"). */

export type RoleId = 'person' | 'supervisor'

/** How a supervisor knows the person. Only `nurse` is care-home specific, and only
 * that wording may say "nurse" or "resident" (SPEC section 17). */
export type Relationship = 'family' | 'carer' | 'nurse'

/** Someone whose routine is watched. `id` is the pipeline's `resident_id` where the
 * pipeline knows them, so a supervisor's list opens the detail screen it already has. */
export interface Person {
  id: string
  name: string
  /** One line of context for a list: "Room 204, care home" or "Lives alone". */
  context: string
}

export interface Supervisor {
  id: string
  name: string
  relationship: Relationship
  /** One line for the person's "who can see this" list: "Day shift, care home". */
  context: string
}

/** One person letting one supervisor see their routine. Either side can remove it. */
export interface PersonLink {
  person_id: string
  supervisor_id: string
}

/** What a person hands to someone they want watching over them: a short code to type
 * in, and the same code as a link to send. Mock-backed; no account behind it yet. */
export interface Invite {
  code: string
  link: string
  person_id: string
}
