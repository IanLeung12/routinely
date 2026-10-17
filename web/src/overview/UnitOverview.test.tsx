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
    expect(names).toEqual(['Mrs. K', 'Mr. Chen', 'Mrs. Ahmed', 'Mr. Silva'])

    expect(rows[0].querySelector('.status-chip')?.textContent).toBe('Flagged')
    expect(rows[1].querySelector('.status-chip')?.textContent).toBe('Watch')
    for (const row of rows.slice(2)) {
      expect(row.querySelector('.status-chip')?.textContent).toBe('Normal')
    }
  })

  it('colours the status chip per status', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({ ok: true, json: async () => mockResidents }),
    )

    render(<UnitOverview />)

    const flagged = await screen.findByText('Flagged')
    expect(flagged.className).toContain('status-chip--flagged')
    const watch = await screen.findByText('Watch')
    expect(watch.className).toContain('status-chip--watch')
    const [normal] = await screen.findAllByText('Normal')
    expect(normal.className).toContain('status-chip--normal')
  })
})
