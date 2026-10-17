import { cleanup, render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { PatternLibrary } from './PatternLibrary.tsx'
import { mockPatterns } from './mockPatterns.ts'

afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
})

describe('PatternLibrary keyboard access', () => {
  it.each(['{Enter}', ' '])('tabs through every urgency filter and selects with %s', async (key) => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: true, json: async () => mockPatterns }))
    const onBack = vi.fn()
    const user = userEvent.setup()
    render(<PatternLibrary onBack={onBack} />)

    const group = await screen.findByRole('group', { name: 'Filter by urgency' })
    const back = screen.getByRole('button', { name: /Back/ })
    await user.tab()
    await waitFor(() => expect(document.activeElement).toBe(back))
    await user.keyboard('{Enter}')
    expect(onBack).toHaveBeenCalledTimes(1)

    const filters = [
      { label: 'All', urgency: null },
      { label: 'Urgent', urgency: 'urgent' },
      { label: 'Check this shift', urgency: 'same_shift' },
      { label: 'Check next round', urgency: 'next_round' },
      { label: 'Routine', urgency: 'routine' },
    ]
    expect(within(group).getAllByRole('button')).toHaveLength(filters.length)

    for (const { label, urgency } of filters) {
      const button = within(group).getByRole('button', { name: label, exact: true })
      await user.tab()
      await waitFor(() => expect(document.activeElement).toBe(button))
      await user.keyboard(key)

      expect(button.getAttribute('aria-pressed')).toBe('true')
      expect(within(group).getAllByRole('button', { pressed: true })).toEqual([button])
      const expected = mockPatterns.filter((entry) => urgency === null || entry.urgency === urgency)
      expect(screen.getAllByRole('heading', { level: 3 }).map((heading) => heading.textContent))
        .toEqual(expected.map((entry) => entry.name))
    }

    // Return to All using only the keyboard and restore every pattern.
    for (let i = 0; i < filters.length - 1; i++) await user.tab({ shift: true })
    const all = within(group).getByRole('button', { name: 'All', exact: true })
    await waitFor(() => expect(document.activeElement).toBe(all))
    await user.keyboard(key)
    expect(all.getAttribute('aria-pressed')).toBe('true')
    expect(screen.getAllByRole('heading', { level: 3 })).toHaveLength(mockPatterns.length)
  })
})
