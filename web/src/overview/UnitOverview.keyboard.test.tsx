import { cleanup, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { mockResidents } from '../mock/residents.ts'
import { UnitOverview } from './UnitOverview.tsx'

afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
})

describe('UnitOverview keyboard access', () => {
  it('tabs through every resident card in DOM order and opens one with Enter', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({ ok: true, json: async () => mockResidents }),
    )
    const onSelect = vi.fn()
    const user = userEvent.setup()

    render(<UnitOverview onSelect={onSelect} />)
    await waitFor(() => {
      expect(screen.getAllByRole('listitem')).toHaveLength(mockResidents.length)
    })

    const rows = screen.getAllByRole('listitem')
    const openButtons = rows.map((row) => row.querySelector('button.resident-open') as HTMLElement)

    // Every resident card has an accessible name.
    for (const button of openButtons) {
      expect(button.getAttribute('aria-label')).toBeTruthy()
    }

    for (const button of openButtons) {
      for (let i = 0; i < 20 && document.activeElement !== button; i++) {
        await user.tab()
      }
      await waitFor(() => {
        expect(document.activeElement).toBe(button)
      })
    }

    const mrsKOpen = openButtons.find((button) => button.getAttribute('aria-label')?.startsWith('Open Mrs. K'))!
    mrsKOpen.focus()
    await user.keyboard('{Enter}')

    expect(onSelect).toHaveBeenCalledWith('mrs-k')
  })
})
