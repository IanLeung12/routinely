import { cleanup, render, screen, waitFor } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { UnitOverview } from './UnitOverview.tsx'
import type { ResidentSummary } from './types.ts'

afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
  sessionStorage.clear()
})

function resident(overrides: Partial<ResidentSummary> & { id: string }): ResidentSummary {
  return {
    id: overrides.id,
    name: overrides.name ?? overrides.id,
    room: overrides.room ?? '100',
    status: overrides.status ?? 'normal',
    top_pattern: overrides.top_pattern ?? null,
    scores: overrides.scores ?? [],
  }
}

const residents: ResidentSummary[] = [
  resident({ id: 'a', name: 'Resident A', room: '101', status: 'flagged' }),
  resident({ id: 'b', name: 'Resident B', room: '102', status: 'watch' }),
  resident({ id: 'c', name: 'Resident C', room: '103', status: 'watch' }),
  resident({ id: 'd', name: 'Resident D', room: '104', status: 'normal' }),
]

function stubFetch(residentsJson: unknown, pausedRooms: string[]) {
  vi.stubGlobal(
    'fetch',
    vi.fn((url: string) => {
      if (String(url).includes('/monitoring')) {
        return Promise.resolve({ ok: true, json: async () => ({ paused_rooms: pausedRooms }) })
      }
      return Promise.resolve({ ok: true, json: async () => residentsJson })
    }),
  )
}

describe('UnitOverview filter button counts', () => {
  it('labels each filter with how many residents it would show, including Paused', async () => {
    stubFetch(residents, ['104'])

    render(<UnitOverview />)
    await waitFor(() => {
      expect(screen.getAllByRole('listitem')).toHaveLength(residents.length)
    })

    expect(screen.getByRole('button', { name: 'All (4)' })).toBeTruthy()
    expect(screen.getByRole('button', { name: 'Flagged (1)' })).toBeTruthy()
    expect(screen.getByRole('button', { name: 'Watch (2)' })).toBeTruthy()
    expect(screen.getByRole('button', { name: 'Paused (1)' })).toBeTruthy()
  })

  it('updates the counts after a refresh', async () => {
    let pausedRooms: string[] = []
    let currentResidents: ResidentSummary[] = residents
    vi.stubGlobal(
      'fetch',
      vi.fn((url: string) => {
        if (String(url).includes('/monitoring')) {
          return Promise.resolve({ ok: true, json: async () => ({ paused_rooms: pausedRooms }) })
        }
        return Promise.resolve({ ok: true, json: async () => currentResidents })
      }),
    )

    const { rerender } = render(<UnitOverview refreshKey={0} />)
    await waitFor(() => {
      expect(screen.getByRole('button', { name: 'Flagged (1)' })).toBeTruthy()
    })

    currentResidents = residents.map((r) => (r.id === 'c' ? { ...r, status: 'flagged' as const } : r))
    pausedRooms = ['104']
    rerender(<UnitOverview refreshKey={1} />)

    await waitFor(() => {
      expect(screen.getByRole('button', { name: 'Flagged (2)' })).toBeTruthy()
    })
    expect(screen.getByRole('button', { name: 'Watch (1)' })).toBeTruthy()
    expect(screen.getByRole('button', { name: 'Paused (1)' })).toBeTruthy()
    expect(screen.getByRole('button', { name: 'All (4)' })).toBeTruthy()
  })
})
