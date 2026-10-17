import {
  MOCK_CURRENT_PERSON_ID,
  MOCK_CURRENT_SUPERVISOR_ID,
  mockLinks,
  mockPeople,
  mockSupervisors,
} from '../mock/people.ts'
import type { Invite, Person, PersonLink, RoleId, Supervisor } from './types.ts'

/** Roles, people and who can see whose routine (SPEC section 17).
 *
 * There is no pairing backend yet, so this is the whole thing: the chosen role, the
 * links and the invite codes live in `localStorage`, seeded from `mock/people.ts`. The
 * screens only ever call the functions at the bottom of this file, so when a real API
 * lands it implements `PeopleApi` and `setPeopleApi` swaps it in - no screen changes.
 *
 * Deliberately synchronous: `localStorage` is, so the shell can decide on the first
 * render whether to show the role chooser instead of flashing a loading state. A real
 * backend would cache its answers behind the same shape. */
export interface PeopleApi {
  /** The role this browser picked, or null before anyone picked one. */
  getRole(): RoleId | null
  setRole(role: RoleId): void
  /** Who the demo is in the person role. */
  currentPerson(): Person
  /** Who the demo is in the supervisor role. */
  currentSupervisor(): Supervisor
  /** Everyone who can see this person's routine, in the order they were linked. */
  supervisorsOf(personId: string): Supervisor[]
  /** The people the current supervisor can see. */
  peopleISupport(): Person[]
  /** A code (and the same code as a link) for someone this person wants watching over
   * them. Calling it twice for the same person gives back the same invite. */
  createInvite(personId: string): Invite
  /** Links the current supervisor to the invite's person. Null when no invite has that
   * code; already linked is not an error. */
  acceptInvite(code: string): Person | null
  unlink(personId: string, supervisorId: string): void
  /** Forgets the role, the links and the invites: "Reset demo" starts from the chooser
   * with the seeded links again. */
  reset(): void
}

const ROLE_KEY = 'rw.people.role'
const LINKS_KEY = 'rw.people.links'
const INVITES_KEY = 'rw.people.invites'

const ROLES: RoleId[] = ['person', 'supervisor']

/** No look-alike characters (0/O, 1/I): an invite code gets read out over the phone. */
const CODE_ALPHABET = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789'
const CODE_LENGTH = 6

function readStored<T>(key: string, isValid: (value: unknown) => value is T): T | null {
  try {
    const raw = localStorage.getItem(key)
    if (raw === null) return null
    const parsed: unknown = JSON.parse(raw)
    return isValid(parsed) ? parsed : null
  } catch {
    // Storage unavailable (private mode, quota) or a corrupt value: fall back to the seed.
    return null
  }
}

function writeStored(key: string, value: unknown): void {
  try {
    localStorage.setItem(key, JSON.stringify(value))
  } catch {
    // Storage unavailable: the change just won't outlive this tab.
  }
}

function isLinks(value: unknown): value is PersonLink[] {
  return (
    Array.isArray(value) &&
    value.every((link) =>
      !!link &&
      typeof (link as PersonLink).person_id === 'string' &&
      typeof (link as PersonLink).supervisor_id === 'string')
  )
}

function isInvites(value: unknown): value is Invite[] {
  return (
    Array.isArray(value) &&
    value.every((invite) =>
      !!invite &&
      typeof (invite as Invite).code === 'string' &&
      typeof (invite as Invite).link === 'string' &&
      typeof (invite as Invite).person_id === 'string')
  )
}

/** The seeded links until something in the UI changes them, the stored ones after. */
function readLinks(): PersonLink[] {
  return readStored(LINKS_KEY, isLinks) ?? mockLinks
}

function writeLinks(links: PersonLink[]): void {
  writeStored(LINKS_KEY, links)
}

function readInvites(): Invite[] {
  return readStored(INVITES_KEY, isInvites) ?? []
}

function personById(personId: string): Person | null {
  return mockPeople.find((person) => person.id === personId) ?? null
}

function supervisorById(supervisorId: string): Supervisor | null {
  return mockSupervisors.find((supervisor) => supervisor.id === supervisorId) ?? null
}

/** Who the demo is in the supervisor role: the care-home nurse, so the supervisor role
 * opens on the unit dashboard that already exists. */
function me(): Supervisor {
  return (
    supervisorById(MOCK_CURRENT_SUPERVISOR_ID) ??
    { id: MOCK_CURRENT_SUPERVISOR_ID, name: 'You', relationship: 'family', context: '' }
  )
}

/** Typed-in codes arrive with spaces, dashes and any case; stored codes are bare. */
function normaliseCode(code: string): string {
  return code.replace(/[\s-]/g, '').toUpperCase()
}

function randomCode(taken: Set<string>): string {
  for (let attempt = 0; attempt < 50; attempt += 1) {
    let code = ''
    for (let index = 0; index < CODE_LENGTH; index += 1) {
      code += CODE_ALPHABET[Math.floor(Math.random() * CODE_ALPHABET.length)]
    }
    if (!taken.has(code)) return code
  }
  // Vanishingly unlikely with a 32^6 space; a longer code is better than a clash.
  return `${CODE_ALPHABET[0]}${taken.size}${CODE_LENGTH}`
}

/** The link that carries a code to whoever is going to watch over this person. The
 * dashboard reads `?invite=` back and offers it to the supervisor (`PeopleISupport`). */
function inviteLink(code: string): string {
  return `${window.location.origin}/?invite=${code}`
}

const browserPeopleApi: PeopleApi = {
  getRole() {
    try {
      const stored = localStorage.getItem(ROLE_KEY)
      return ROLES.includes(stored as RoleId) ? (stored as RoleId) : null
    } catch {
      return null
    }
  },

  setRole(role: RoleId) {
    try {
      localStorage.setItem(ROLE_KEY, role)
    } catch {
      // Storage unavailable: the chooser will ask again next time.
    }
  },

  currentPerson() {
    return (
      personById(MOCK_CURRENT_PERSON_ID) ??
      { id: MOCK_CURRENT_PERSON_ID, name: 'You', context: 'Watching your own routine' }
    )
  },

  currentSupervisor() {
    return me()
  },

  supervisorsOf(personId: string) {
    return readLinks()
      .filter((link) => link.person_id === personId)
      .map((link) => supervisorById(link.supervisor_id))
      .filter((supervisor): supervisor is Supervisor => supervisor !== null)
  },

  peopleISupport() {
    const supervisorId = me().id
    return readLinks()
      .filter((link) => link.supervisor_id === supervisorId)
      .map((link) => personById(link.person_id))
      .filter((person): person is Person => person !== null)
  },

  createInvite(personId: string) {
    const invites = readInvites()
    const existing = invites.find((invite) => invite.person_id === personId)
    if (existing) return existing

    const code = randomCode(new Set(invites.map((invite) => invite.code)))
    const invite: Invite = { code, link: inviteLink(code), person_id: personId }
    writeStored(INVITES_KEY, [...invites, invite])
    return invite
  },

  acceptInvite(code: string) {
    const wanted = normaliseCode(code)
    const invite = readInvites().find((candidate) => candidate.code === wanted)
    if (!invite) return null

    const person = personById(invite.person_id)
    if (person === null) return null

    const supervisorId = me().id
    const links = readLinks()
    const linked = links.some(
      (link) => link.person_id === person.id && link.supervisor_id === supervisorId,
    )
    if (!linked) {
      writeLinks([...links, { person_id: person.id, supervisor_id: supervisorId }])
    }
    return person
  },

  unlink(personId: string, supervisorId: string) {
    writeLinks(
      readLinks().filter(
        (link) => !(link.person_id === personId && link.supervisor_id === supervisorId),
      ),
    )
  },

  reset() {
    try {
      localStorage.removeItem(ROLE_KEY)
      localStorage.removeItem(LINKS_KEY)
      localStorage.removeItem(INVITES_KEY)
    } catch {
      // Storage unavailable: there was nothing stored to forget.
    }
  },
}

/** The implementation every screen below delegates to. */
let api: PeopleApi = browserPeopleApi

/** Replaces the mock with a real pairing API once there is one (pass null to go back). */
export function setPeopleApi(next: PeopleApi | null): void {
  api = next ?? browserPeopleApi
}

export function getRole(): RoleId | null {
  return api.getRole()
}

export function setRole(role: RoleId): void {
  api.setRole(role)
}

export function currentPerson(): Person {
  return api.currentPerson()
}

export function currentSupervisor(): Supervisor {
  return api.currentSupervisor()
}

export function supervisorsOf(personId: string): Supervisor[] {
  return api.supervisorsOf(personId)
}

export function peopleISupport(): Person[] {
  return api.peopleISupport()
}

export function createInvite(personId: string): Invite {
  return api.createInvite(personId)
}

export function acceptInvite(code: string): Person | null {
  return api.acceptInvite(code)
}

export function unlink(personId: string, supervisorId: string): void {
  api.unlink(personId, supervisorId)
}

export function resetPeople(): void {
  api.reset()
}
