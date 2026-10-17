import { cleanup, render, screen, waitFor } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { mockResidents } from '../mock/residents.ts'
import { UnitOverview } from './UnitOverview.tsx'

afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
  sessionStorage.clear()
})

describe('UnitOverview remembers filter and sort for the session', () => {
  it('keeps Flagged + most-recent-change selected across unmount/remount', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({ ok: true, json: async () => mockResidents }),
    )

    const { unmount } = render(<UnitOverview />)
    await waitFor(() => {
      expect(screen.getAllByRole('listitem')).toHaveLength(mockResidents.length)
    })

    screen.getByRole('button', { name: 'Flagged (1)' }).click()
    await waitFor(() => {
      expect(
        screen.getByRole('button', { name: 'Flagged (1)' }).getAttribute('aria-pressed'),
      ).toBe('true')
    })

    screen.getByRole('button', { name: 'Most recent change first' }).click()
    await waitFor(() => {
      expect(
        screen.getByRole('button', { name: 'Most recent change first' }).getAttribute('aria-pressed'),
      ).toBe('true')
    })

    unmount()
    render(<UnitOverview />)
    await waitFor(() => {
      expect(screen.getAllByRole('listitem').length).toBeGreaterThan(0)
    })

    expect(screen.getByRole('button', { name: 'Flagged (1)' }).getAttribute('aria-pressed')).toBe(
      'true',
    )
    expect(
      screen.getByRole('button', { name: 'Most recent change first' }).getAttribute('aria-pressed'),
    ).toBe('true')
    expect(screen.getByRole('button', { name: 'All (6)' }).getAttribute('aria-pressed')).toBe(
      'false',
    )
    expect(screen.getByRole('button', { name: 'Default order' }).getAttribute('aria-pressed')).toBe(
      'false',
    )
  })

  it('starts from stored prefs instead of the hardcoded defaults', async () => {
    sessionStorage.setItem('rw.overview.prefs', JSON.stringify({ filter: 'watch', sort: 'recent' }))
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({ ok: true, json: async () => mockResidents }),
    )

    render(<UnitOverview />)
    await waitFor(() => {
      expect(screen.getAllByRole('listitem').length).toBeGreaterThan(0)
    })

    expect(screen.getByRole('button', { name: 'Watch (3)' }).getAttribute('aria-pressed')).toBe(
      'true',
    )
    expect(
      screen.getByRole('button', { name: 'Most recent change first' }).getAttribute('aria-pressed'),
    ).toBe('true')
  })
})
