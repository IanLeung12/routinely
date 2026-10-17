import { cleanup, render, screen, waitFor } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { mockResidents } from '../mock/residents.ts'
import { UnitOverview } from './UnitOverview.tsx'

afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
  sessionStorage.clear()
})

describe('UnitOverview failure and empty states', () => {
  it('falls back to mock residents (not the shared ErrorState) when the residents API rejects', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new Error('network down')))

    render(<UnitOverview />)

    for (const resident of mockResidents) {
      expect(await screen.findByText(resident.name)).toBeTruthy()
    }
    expect(screen.queryByRole('alert')).toBeNull()
    expect(
      await screen.findByText("Showing demo residents: the Routine Watch service isn't reachable."),
    ).toBeTruthy()
  })

  it('shows the demo notice when the residents API responds non-OK', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: false, status: 500 }))

    render(<UnitOverview />)

    expect(
      await screen.findByText("Showing demo residents: the Routine Watch service isn't reachable."),
    ).toBeTruthy()
  })

  it('shows no demo notice when the residents API responds OK', async () => {
    const residents = [mockResidents[0]]
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: true, json: async () => residents }))

    render(<UnitOverview />)

    expect(await screen.findByText(residents[0].name)).toBeTruthy()
    expect(
      screen.queryByText("Showing demo residents: the Routine Watch service isn't reachable."),
    ).toBeNull()
  })

  it('shows the shared EmptyState with nurse-readable copy when there are no residents', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: true, json: async () => [] }))

    render(<UnitOverview />)

    const message = await screen.findByText('No residents on this unit yet.')
    expect(message.tagName).toBe('P')
    expect(message.className).toBe('empty-state')
    await waitFor(() => {
      expect(screen.queryByRole('list')).toBeNull()
    })
  })
})
