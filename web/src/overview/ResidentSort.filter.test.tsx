import { cleanup, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
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
  resident({
    id: 'a',
    name: 'Resident A',
    status: 'normal',
    scores: [{ ts: '2026-01-01T09:00:00+00:00', score: 0.1 }],
  }),
  resident({
    id: 'b',
    name: 'Resident B',
    status: 'watch',
    scores: [{ ts: '2026-01-05T09:00:00+00:00', score: 0.2 }],
  }),
  resident({
    id: 'c',
    name: 'Resident C',
    status: 'flagged',
    scores: [{ ts: '2026-01-02T09:00:00+00:00', score: 0.3 }],
  }),
  resident({
    id: 'd',
    name: 'Resident D',
    status: 'watch',
    scores: [],
  }),
]

function residentNames() {
  return screen.getAllByRole('listitem').map((row) => row.querySelector('.resident-name')?.textContent)
}

describe('ResidentSort combined with filters in UnitOverview', () => {
  it('composes the Watch filter with recent sort, and restores default order', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: true, json: async () => residents }))
    const user = userEvent.setup()

    render(<UnitOverview />)
    await waitFor(() => {
      expect(screen.getAllByRole('listitem')).toHaveLength(residents.length)
    })

    await user.click(screen.getByRole('button', { name: 'Watch (2)' }))
    await user.click(screen.getByRole('button', { name: 'Most recent change first' }))

    await waitFor(() => {
      expect(residentNames()).toEqual(['Resident B', 'Resident D'])
    })

    await user.click(screen.getByRole('button', { name: 'Default order' }))
    await waitFor(() => {
      expect(residentNames()).toEqual(['Resident B', 'Resident D'])
    })

    await user.click(screen.getByRole('button', { name: 'All (4)' }))
    await waitFor(() => {
      expect(residentNames()).toEqual(['Resident C', 'Resident B', 'Resident D', 'Resident A'])
    })
  })

  it('shows all residents newest-first under All filter + recent sort, scores-less resident last', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: true, json: async () => residents }))
    const user = userEvent.setup()

    render(<UnitOverview />)
    await waitFor(() => {
      expect(screen.getAllByRole('listitem')).toHaveLength(residents.length)
    })

    await user.click(screen.getByRole('button', { name: 'Most recent change first' }))

    await waitFor(() => {
      expect(residentNames()).toEqual(['Resident B', 'Resident C', 'Resident A', 'Resident D'])
    })
  })
})
