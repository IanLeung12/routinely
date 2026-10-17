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
