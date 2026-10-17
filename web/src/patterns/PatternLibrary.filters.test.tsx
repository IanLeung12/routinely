import { act, cleanup, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { PatternLibrary } from './PatternLibrary.tsx'
import { mockPatterns } from './mockPatterns.ts'

afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
})

function serve(patterns = mockPatterns) {
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: true, json: async () => patterns }))
}

function namesByUrgency(urgency: string) {
  return mockPatterns.filter((p) => p.urgency === urgency).map((p) => p.name)
}

function namesNotUrgency(urgency: string) {
  return mockPatterns.filter((p) => p.urgency !== urgency).map((p) => p.name)
}

async function renderLibrary() {
  await act(async () => { render(<PatternLibrary onBack={() => {}} />) })
  await screen.findByRole('heading', { name: mockPatterns[0].name, level: 3 })
}

async function expectExactlyOnePressed(label: string) {
  const buttons = screen.getAllByRole('button', { name: /./ }).filter(
    (b) => b.hasAttribute('aria-pressed'),
  )
  const pressed = buttons.filter((b) => b.getAttribute('aria-pressed') === 'true')
  expect(pressed).toHaveLength(1)
  expect(pressed[0]).toBe(screen.getByRole('button', { name: label }))
}

describe('PatternLibrary urgency filter', () => {
  const filters: { label: string; urgency: string }[] = [
    { label: 'Urgent', urgency: 'urgent' },
    { label: 'Check this shift', urgency: 'same_shift' },
    { label: 'Check next round', urgency: 'next_round' },
    { label: 'Routine', urgency: 'routine' },
  ]

  for (const { label, urgency } of filters) {
    it(`narrows the list to patterns matching "${label}"`, async () => {
      serve()
      const user = userEvent.setup()
      await renderLibrary()

      await user.click(screen.getByRole('button', { name: label }))

      await expectExactlyOnePressed(label)
      for (const name of namesByUrgency(urgency)) {
        expect(screen.getByRole('heading', { name, level: 3 })).toBeTruthy()
      }
      for (const name of namesNotUrgency(urgency)) {
        expect(screen.queryByRole('heading', { name, level: 3 })).toBeNull()
      }
    })
  }

  it('restores the full list when "All" is picked after a filter', async () => {
    serve()
    const user = userEvent.setup()
    await renderLibrary()

    await user.click(screen.getByRole('button', { name: 'Routine' }))
    await expectExactlyOnePressed('Routine')

    await user.click(screen.getByRole('button', { name: 'All' }))

    await expectExactlyOnePressed('All')
    for (const entry of mockPatterns) {
      expect(screen.getByRole('heading', { name: entry.name, level: 3 })).toBeTruthy()
    }
  })

  it('shows the empty state for an urgency with no matching patterns', async () => {
    const noUrgent = mockPatterns.filter((p) => p.urgency !== 'urgent')
    serve(noUrgent)
    const user = userEvent.setup()
    await act(async () => { render(<PatternLibrary onBack={() => {}} />) })
    await screen.findByRole('heading', { name: noUrgent[0].name, level: 3 })

    await user.click(screen.getByRole('button', { name: 'Urgent' }))

    expect(await screen.findByText('No patterns at this level.')).toBeTruthy()
    expect(screen.queryByText(/No patterns in the library\./)).toBeNull()
  })

  it('operates the filter by keyboard: Tab to the button, then Enter to select it', async () => {
    serve()
    const user = userEvent.setup()
    await renderLibrary()

    const allButton = screen.getByRole('button', { name: 'All' })
    allButton.focus()

    await user.tab()
    const urgentButton = screen.getByRole('button', { name: 'Urgent' })
    expect(document.activeElement).toBe(urgentButton)

    await user.keyboard('{Enter}')

    await expectExactlyOnePressed('Urgent')
    for (const name of namesByUrgency('urgent')) {
      expect(screen.getByRole('heading', { name, level: 3 })).toBeTruthy()
    }
    for (const name of namesNotUrgency('urgent')) {
      expect(screen.queryByRole('heading', { name, level: 3 })).toBeNull()
    }
  })

  it('operates the filter by keyboard: Space also selects the focused button', async () => {
    serve()
    const user = userEvent.setup()
    await renderLibrary()

    const sameShiftButton = screen.getByRole('button', { name: 'Check this shift' })
    sameShiftButton.focus()

    await user.keyboard(' ')

    await expectExactlyOnePressed('Check this shift')
  })
})
