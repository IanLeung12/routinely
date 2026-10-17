import { cleanup, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { mockResidents } from '../mock/residents.ts'
import { UnitOverview } from './UnitOverview.tsx'
import type { ResidentSummary } from './types.ts'
import { sortResidents } from './ResidentSort.tsx'

afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
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

describe('sortResidents', () => {
  it('defaults to flagged, then watch, then normal, keeping ties in their original order', () => {
    const residents = [
      resident({ id: 'a', status: 'normal' }),
      resident({ id: 'b', status: 'flagged' }),
      resident({ id: 'c', status: 'watch' }),
      resident({ id: 'd', status: 'flagged' }),
      resident({ id: 'e', status: 'normal' }),
    ]

    expect(sortResidents(residents, 'default').map((r) => r.id)).toEqual([
      'b',
      'd',
      'c',
      'a',
      'e',
    ])
  })

  it('orders by most recent change first, newest session timestamp wins', () => {
    const residents = [
      resident({ id: 'a', scores: [{ ts: '2026-01-01T09:00:00+00:00', score: 0.1 }] }),
      resident({
        id: 'b',
        scores: [
          { ts: '2025-12-30T09:00:00+00:00', score: 0.1 },
          { ts: '2026-01-05T09:00:00+00:00', score: 0.2 },
        ],
      }),
      resident({ id: 'c', scores: [{ ts: '2025-12-20T09:00:00+00:00', score: 0.1 }] }),
    ]

    expect(sortResidents(residents, 'recent').map((r) => r.id)).toEqual(['b', 'a', 'c'])
  })

  it('keeps residents with no scores last in recent mode, stable among themselves', () => {
    const residents = [
      resident({ id: 'no-scores-1', scores: [] }),
      resident({ id: 'has-scores', scores: [{ ts: '2026-01-01T09:00:00+00:00', score: 0.1 }] }),
      resident({ id: 'no-scores-2', scores: [] }),
    ]

    expect(sortResidents(residents, 'recent').map((r) => r.id)).toEqual([
      'has-scores',
      'no-scores-1',
      'no-scores-2',
    ])
  })

  it('breaks exact timestamp ties by keeping original order (stable sort)', () => {
    const residents = [
      resident({ id: 'first', scores: [{ ts: '2026-01-01T09:00:00+00:00', score: 0.1 }] }),
      resident({ id: 'second', scores: [{ ts: '2026-01-01T09:00:00+00:00', score: 0.9 }] }),
    ]

    expect(sortResidents(residents, 'recent').map((r) => r.id)).toEqual(['first', 'second'])
  })

  it('does not mutate the input array', () => {
    const residents = [resident({ id: 'a', status: 'normal' }), resident({ id: 'b', status: 'flagged' })]
    const original = [...residents]

    sortResidents(residents, 'default')

    expect(residents).toEqual(original)
  })
})

function residentNames() {
  return screen.getAllByRole('listitem').map((row) => row.querySelector('.resident-name')?.textContent)
}

describe('ResidentSort control in UnitOverview', () => {
  it('switches to most-recent-change order with Tab + Space, keyboard-only', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: true, json: async () => mockResidents }))
    const user = userEvent.setup()

    render(<UnitOverview />)
    await waitFor(() => {
      expect(screen.getAllByRole('listitem')).toHaveLength(mockResidents.length)
    })

    expect(residentNames()).toEqual([
      'Mrs. K',
      'Mr. Chen',
      'Mr. Nguyen',
      'Mrs. Patel',
      'Mrs. Ahmed',
      'Mr. Silva',
    ])

    const recentButton = screen.getByRole('button', { name: 'Most recent change first' })

    for (let i = 0; i < 20 && document.activeElement !== recentButton; i++) {
      await user.tab()
    }
    await waitFor(() => {
      expect(document.activeElement).toBe(recentButton)
    })

    await user.keyboard(' ')

    await waitFor(() => {
      expect(residentNames()).toEqual([
        'Mr. Nguyen',
        'Mrs. K',
        'Mr. Chen',
        'Mrs. Ahmed',
        'Mr. Silva',
        'Mrs. Patel',
      ])
    })
    expect(recentButton.getAttribute('aria-pressed')).toBe('true')

    const defaultButton = screen.getByRole('button', { name: 'Default order' })
    defaultButton.focus()
    await user.keyboard(' ')

    await waitFor(() => {
      expect(residentNames()).toEqual([
        'Mrs. K',
        'Mr. Chen',
        'Mr. Nguyen',
        'Mrs. Patel',
        'Mrs. Ahmed',
        'Mr. Silva',
      ])
    })
    expect(defaultButton.getAttribute('aria-pressed')).toBe('true')
  })
})
