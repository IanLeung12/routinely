import { cleanup, render, screen, waitFor } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { mockResidents } from '../mock/residents.ts'
import { UnitOverview } from './UnitOverview.tsx'

afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
})

describe('UnitOverview', () => {
  it('falls back to the mock residents when the API is unreachable', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new Error('network down')))

    render(<UnitOverview />)

    for (const resident of mockResidents) {
      expect(await screen.findByText(resident.name)).toBeTruthy()
    }
  })

  it('renders every resident with their status chip, flagged residents first', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({ ok: true, json: async () => mockResidents }),
    )

    render(<UnitOverview />)

    await waitFor(() => {
      expect(screen.getAllByRole('listitem')).toHaveLength(mockResidents.length)
    })

    const rows = screen.getAllByRole('listitem')
    const names = rows.map((row) => row.querySelector('.resident-name')?.textContent)
    expect(names).toEqual(['Mrs. K', 'Mr. Chen', 'Mr. Nguyen', 'Mrs. Patel', 'Mrs. Ahmed', 'Mr. Silva'])

    expect(rows[0].querySelector('.status-chip')?.textContent).toBe('Flagged')
    expect(rows[1].querySelector('.status-chip')?.textContent).toBe('Watch')
    for (const row of rows.slice(1, 4)) {
      expect(row.querySelector('.status-chip')?.textContent).toBe('Watch')
    }
    for (const row of rows.slice(4)) {
      expect(row.querySelector('.status-chip')?.textContent).toBe('Normal')
    }
  })

  it('summarizes mixed statuses in a status line', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({ ok: true, json: async () => mockResidents }),
    )

    render(<UnitOverview />)

    const status = await screen.findByText('1 flagged for review · 3 on watch · 2 normal')
    expect(status.getAttribute('role')).toBe('status')
  })

  it('shows "All residents normal" when nothing is flagged or on watch', async () => {
    const allNormal = mockResidents.map((resident) => ({ ...resident, status: 'normal' as const }))
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: true, json: async () => allNormal }))

    render(<UnitOverview />)

    const status = await screen.findByText('All residents normal')
    expect(status.getAttribute('role')).toBe('status')
  })

  it('shows the top pattern for flagged and watch residents, nothing for normal', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({ ok: true, json: async () => mockResidents }),
    )

    render(<UnitOverview />)

    await waitFor(() => {
      expect(screen.getAllByRole('listitem')).toHaveLength(mockResidents.length)
    })

    const rows = screen.getAllByRole('listitem')
    const byName = new Map(rows.map((row) => [row.querySelector('.resident-name')?.textContent, row]))

    expect(byName.get('Mrs. K')?.querySelector('.resident-pattern')?.textContent).toBe(
      'Sudden change (delirium pattern)',
    )
    expect(byName.get('Mr. Chen')?.querySelector('.resident-pattern')?.textContent).toBe(
      'Slow drift (cognitive decline pattern)',
    )
    expect(byName.get('Mrs. Ahmed')?.querySelector('.resident-pattern')).toBeNull()
    expect(byName.get('Mr. Silva')?.querySelector('.resident-pattern')).toBeNull()
  })

  it('refetches residents when refreshKey changes', async () => {
    const fetchMock = vi.fn().mockResolvedValue({ ok: true, json: async () => mockResidents })
    vi.stubGlobal('fetch', fetchMock)

    const { rerender } = render(<UnitOverview refreshKey={0} />)
    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(1))

    rerender(<UnitOverview refreshKey={1} />)
    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(2))
  })

  it('shows an empty state when there are no residents', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: true, json: async () => [] }))

    render(<UnitOverview />)

    expect(await screen.findByText('No residents on this unit yet.')).toBeTruthy()
    expect(screen.queryByRole('list')).toBeNull()
  })

  it('colours the status chip per status', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({ ok: true, json: async () => mockResidents }),
    )

    render(<UnitOverview />)

    const flagged = await screen.findByText('Flagged')
    expect(flagged.className).toContain('status-chip--flagged')
    const [watch] = await screen.findAllByText('Watch')
    expect(watch.className).toContain('status-chip--watch')
    const [normal] = await screen.findAllByText('Normal')
    expect(normal.className).toContain('status-chip--normal')
  })
})
