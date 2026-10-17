import { beforeEach, describe, expect, it } from 'vitest'
import {
  acceptInvite,
  createInvite,
  currentPerson,
  currentSupervisor,
  getRole,
  peopleISupport,
  resetPeople,
  setPeopleApi,
  setRole,
  supervisorsOf,
  unlink,
} from './api.ts'
import type { PeopleApi } from './api.ts'

beforeEach(() => {
  localStorage.clear()
  setPeopleApi(null)
})

describe('the chosen role', () => {
  it('is unanswered until someone picks, then remembered', () => {
    expect(getRole()).toBeNull()

    setRole('person')
    expect(getRole()).toBe('person')

    setRole('supervisor')
    expect(getRole()).toBe('supervisor')
  })

  it('ignores a stored value that is not a role', () => {
    localStorage.setItem('rw.people.role', 'nurse')

    expect(getRole()).toBeNull()
  })
})

describe('the demo people', () => {
  it('ship the three cases SPEC section 17 asks for', () => {
    // Mrs. K is in a care home, with Nurse Ana watching.
    expect(supervisorsOf('mrs-k').map((supervisor) => supervisor.name)).toEqual(['Nurse Ana'])
    // Mr. D lives alone, with his daughter watching.
    expect(supervisorsOf('mr-d').map((supervisor) => supervisor.name)).toEqual(['Lena'])
    // Sam watches their own routine: nobody else is linked, and that is a finished setup.
    expect(supervisorsOf('sam')).toEqual([])
    expect(currentPerson().id).toBe('sam')
  })

  it('give the care-home nurse a whole unit, so the nurse view is one supervisor with many', () => {
    const ids = peopleISupport().map((person) => person.id)

    expect(ids.length).toBeGreaterThan(1)
    expect(ids).toContain('mrs-k')
    // Mr. D is his daughter's, not the unit's.
    expect(ids).not.toContain('mr-d')
  })

  it('falls back to the seeded links when the stored ones are corrupt', () => {
    localStorage.setItem('rw.people.links', '{"not": "a list"}')

    expect(peopleISupport().map((person) => person.id)).toContain('mrs-k')
  })
})

describe('inviting a supervisor', () => {
  it('round-trips create, accept and unlink through the mock', () => {
    const person = currentPerson()
    expect(supervisorsOf(person.id)).toEqual([])

    const invite = createInvite(person.id)
    expect(invite.code).toMatch(/^[A-Z2-9]{6}$/)
    expect(invite.link).toContain(invite.code)
    expect(invite.person_id).toBe(person.id)

    expect(acceptInvite(invite.code)?.id).toBe(person.id)
    expect(peopleISupport().map((supported) => supported.id)).toContain(person.id)
    expect(supervisorsOf(person.id).map((supervisor) => supervisor.id)).toEqual([
      currentSupervisor().id,
    ])

    unlink(person.id, currentSupervisor().id)
    expect(peopleISupport().map((supported) => supported.id)).not.toContain(person.id)
    expect(supervisorsOf(person.id)).toEqual([])
  })

  it('shows the same code again rather than issuing a new one', () => {
    expect(createInvite('sam').code).toBe(createInvite('sam').code)
  })

  it('reads a code back however it was typed, and refuses one nobody issued', () => {
    const { code } = createInvite('sam')
    const asTyped = ` ${code.slice(0, 3)}-${code.slice(3).toLowerCase()} `

    expect(acceptInvite(asTyped)?.id).toBe('sam')
    expect(acceptInvite('NOPE23')).toBeNull()
  })

  it('links a person once however often the code is used', () => {
    const { code } = createInvite('sam')

    acceptInvite(code)
    acceptInvite(code)

    expect(peopleISupport().filter((person) => person.id === 'sam')).toHaveLength(1)
  })
})

describe('reset', () => {
  it('forgets the role, every link made since, and the codes', () => {
    setRole('supervisor')
    const { code } = createInvite('sam')
    acceptInvite(code)
    unlink('mrs-k', currentSupervisor().id)

    resetPeople()

    expect(getRole()).toBeNull()
    expect(peopleISupport().map((person) => person.id)).toContain('mrs-k')
    expect(supervisorsOf('sam')).toEqual([])
    expect(acceptInvite(code)).toBeNull()
  })
})

describe('the interface', () => {
  it('can be swapped for a real pairing API without touching a screen', () => {
    const fake: PeopleApi = {
      getRole: () => 'person',
      setRole: () => {},
      currentPerson: () => ({ id: 'api-person', name: 'From the API', context: '' }),
      currentSupervisor: () => ({
        id: 'api-supervisor', name: 'From the API', relationship: 'carer', context: '',
      }),
      supervisorsOf: () => [],
      peopleISupport: () => [],
      createInvite: () => ({ code: 'FROMAPI', link: 'https://example.test/FROMAPI', person_id: 'api-person' }),
      acceptInvite: () => null,
      unlink: () => {},
      reset: () => {},
    }

    setPeopleApi(fake)
    expect(getRole()).toBe('person')
    expect(currentPerson().name).toBe('From the API')
    expect(peopleISupport()).toEqual([])

    setPeopleApi(null)
    expect(getRole()).toBeNull()
  })
})
