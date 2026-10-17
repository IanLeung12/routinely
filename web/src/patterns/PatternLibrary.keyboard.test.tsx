import { cleanup, render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { PatternLibrary } from './PatternLibrary.tsx'
import { mockPatterns } from './mockPatterns.ts'

afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
})

const filters = [
  { label: 'All', urgency: null },
  { label: 'Urgent', urgency: 'urgent' },
  { label: 'Check this shift', urgency: 'same_shift' },
  { label: 'Check next round', urgency: 'next_round' },
  { label: 'Routine', urgency: 'routine' },
]

describe('PatternLibrary keyboard access', () => {
  it.each(['{Enter}', ' '])('tabs through and activates every urgency filter with %j', async (key) => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
      ok: true,
      json: async () => mockPatterns,
    }))
    const onBack = vi.fn()
    const user = userEvent.setup()
    render(<PatternLibrary onBack={onBack} />)
    await screen.findByRole('heading', { name: mockPatterns[0].name, level: 3 })

    await user.tab()
    expect(document.activeElement).toBe(screen.getByRole('button', { name: /Back/ }))
    await user.keyboard('{Enter}')
    expect(onBack).toHaveBeenCalledTimes(1)

    const group = within(screen.getByRole('group', { name: 'Filter by urgency' }))
    expect(group.getAllByRole('button')).toHaveLength(filters.length)
    for (const { label, urgency } of filters) {
      await user.tab()
      const button = group.getByRole('button', { name: label })
      expect(document.activeElement).toBe(button)
      await user.keyboard(key)

      expect(button.getAttribute('aria-pressed')).toBe('true')
      expect(group.getAllByRole('button', { pressed: true })).toEqual([button])
      const expected = mockPatterns.filter((entry) => urgency === null || entry.urgency === urgency)
      expect(screen.getAllByRole('heading', { level: 3 }).map((heading) => heading.textContent))
        .toEqual(expected.map((entry) => entry.name))
    }

    for (let i = 1; i < filters.length; i++) await user.tab({ shift: true })
    const all = group.getByRole('button', { name: 'All' })
    expect(document.activeElement).toBe(all)
    await user.keyboard(key)
    expect(all.getAttribute('aria-pressed')).toBe('true')
    expect(screen.getAllByRole('heading', { level: 3 })).toHaveLength(mockPatterns.length)
  })
})
