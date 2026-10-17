import { describe, expect, it } from 'vitest'
import { mockResidentDetail } from './residentDetail.ts'
import { mockResidents } from './residents.ts'

describe('offline demo residents', () => {
  it('includes the API demo resident ids', () => {
    // Keep in sync with _RESIDENTS in pipeline/src/routine_watch/demo.py.
    expect(mockResidents.map((resident) => resident.id)).toEqual([
      'mrs-k',
      'mr-chen',
      'mrs-ahmed',
      'mr-silva',
      'mr-nguyen',
      'mrs-patel',
    ])
  })

  it.each([
    ['mr-nguyen', 'Mr. Nguyen', '126'],
    ['mrs-patel', 'Mrs. Patel', '132'],
  ])('provides offline detail for %s', (id, name, room) => {
    const detail = mockResidentDetail(id)
    expect(detail).toMatchObject({ id, name, room, status: 'watch' })
    expect(detail?.sessions.length).toBeGreaterThan(0)
    expect(detail?.scores).toEqual(mockResidents.find((resident) => resident.id === id)?.scores)
  })
})
