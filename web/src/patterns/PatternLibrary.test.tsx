import { act, cleanup, fireEvent, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { PatternLibrary } from './PatternLibrary.tsx'
import { mockPatterns } from './mockPatterns.ts'

afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
})

function serve() {
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: true, json: async () => mockPatterns }))
}

describe('PatternLibrary', () => {
  it('renders every pattern with its signals, checks and source', async () => {
    serve()
    await act(async () => { render(<PatternLibrary onBack={() => {}} />) })

    for (const entry of mockPatterns) {
      expect(await screen.findByRole('heading', { name: entry.name, level: 3 })).toBeTruthy()
    }
    // Signals are shown by name, not just internal keys.
    expect(screen.getByText(/omissions up/)).toBeTruthy()
    // Every entry's source is on screen, since that is what makes it a cited library.
    for (const entry of mockPatterns) {
      expect(screen.getByText(new RegExp(entry.source.slice(0, 20)))).toBeTruthy()
    }
  })

  it('marks the urgent pattern as visually distinct from the rest', async () => {
    serve()
    await act(async () => { render(<PatternLibrary onBack={() => {}} />) })

    const urgentHeading = await screen.findByRole('heading', { name: /one-sided change/i })
    const urgentEntry = urgentHeading.closest('li')
    const routineHeading = screen.getByRole('heading', { name: /slow drift/i })
    const routineEntry = routineHeading.closest('li')

    expect(urgentEntry?.className).toContain('pattern-library__entry--urgent')
    expect(routineEntry?.className).not.toContain('pattern-library__entry--urgent')
    expect(urgentEntry?.textContent).toContain('Urgent')
  })

  it('never uses diagnostic wording', async () => {
    serve()
    const { container } = render(<PatternLibrary onBack={() => {}} />)
    await act(async () => {})

    expect(container.textContent?.toLowerCase()).not.toContain('diagnos')
  })

  it('calls onBack when the back button is clicked', async () => {
    serve()
    const onBack = vi.fn()
    await act(async () => { render(<PatternLibrary onBack={onBack} />) })

    fireEvent.click(screen.getByRole('button', { name: /back/i }))
    expect(onBack).toHaveBeenCalledTimes(1)
  })

  it('shows a loading state before the library arrives', async () => {
    serve()
    render(<PatternLibrary onBack={() => {}} />)

    expect(screen.getByText('Loading pattern library…')).toBeTruthy()
    await screen.findByRole('heading', { name: mockPatterns[0].name, level: 3 })
  })

  it('falls back to the mock library when the API is unreachable', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new TypeError('network down')))
    await act(async () => { render(<PatternLibrary onBack={() => {}} />) })

    expect(await screen.findByRole('heading', { name: mockPatterns[0].name, level: 3 })).toBeTruthy()
  })

  it('lets a keyboard-only nurse go back', async () => {
    serve()
    const user = userEvent.setup()
    const onBack = vi.fn()
    await act(async () => { render(<PatternLibrary onBack={onBack} />) })
    await screen.findByRole('heading', { name: mockPatterns[0].name, level: 3 })

    await user.tab()
    expect(document.activeElement).toBe(screen.getByRole('button', { name: /back/i }))

    await user.keyboard('{Enter}')
    expect(onBack).toHaveBeenCalledTimes(1)
  })

  it('keeps every pattern name as an h3 under the page heading', async () => {
    serve()
    await act(async () => { render(<PatternLibrary onBack={() => {}} />) })

    expect(screen.getByRole('heading', { name: 'Pattern library', level: 2 })).toBeTruthy()
    for (const entry of mockPatterns) {
      expect(await screen.findByRole('heading', { name: entry.name, level: 3 })).toBeTruthy()
    }
  })

  it('defaults to showing every pattern with the All filter pressed', async () => {
    serve()
    await act(async () => { render(<PatternLibrary onBack={() => {}} />) })
    await screen.findByRole('heading', { name: mockPatterns[0].name, level: 3 })

    expect(screen.getByRole('button', { name: 'All' }).getAttribute('aria-pressed')).toBe('true')
    for (const entry of mockPatterns) {
      expect(screen.getByRole('heading', { name: entry.name, level: 3 })).toBeTruthy()
    }
  })

  it('filters the list to one urgency level when its button is picked', async () => {
    serve()
    const user = userEvent.setup()
    await act(async () => { render(<PatternLibrary onBack={() => {}} />) })
    await screen.findByRole('heading', { name: mockPatterns[0].name, level: 3 })

    await user.click(screen.getByRole('button', { name: 'Urgent' }))

    expect(screen.getByRole('button', { name: 'Urgent' }).getAttribute('aria-pressed')).toBe('true')
    expect(screen.getByRole('button', { name: 'All' }).getAttribute('aria-pressed')).toBe('false')

    const urgentEntries = mockPatterns.filter((p) => p.urgency === 'urgent')
    const routineEntries = mockPatterns.filter((p) => p.urgency !== 'urgent')
    for (const entry of urgentEntries) {
      expect(screen.getByRole('heading', { name: entry.name, level: 3 })).toBeTruthy()
    }
    for (const entry of routineEntries) {
      expect(screen.queryByRole('heading', { name: entry.name, level: 3 })).toBeNull()
    }
  })

  it('shows an empty state, not an error, when a level has no patterns', async () => {
    const noNextRound = mockPatterns.filter((p) => p.urgency !== 'next_round')
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: true, json: async () => noNextRound }))
    const user = userEvent.setup()
    await act(async () => { render(<PatternLibrary onBack={() => {}} />) })
    await screen.findByRole('heading', { name: noNextRound[0].name, level: 3 })

    await user.click(screen.getByRole('button', { name: 'Check next round' }))

    expect(await screen.findByText('No patterns at this level.')).toBeTruthy()
    expect(screen.queryByText(/No patterns in the library\./)).toBeNull()
  })

  it('lets a keyboard-only nurse toggle the urgency filter', async () => {
    serve()
    const user = userEvent.setup()
    await act(async () => { render(<PatternLibrary onBack={() => {}} />) })
    await screen.findByRole('heading', { name: mockPatterns[0].name, level: 3 })

    const urgentButton = screen.getByRole('button', { name: 'Urgent' })
    urgentButton.focus()
    expect(document.activeElement).toBe(urgentButton)

    await user.keyboard('{Enter}')
    expect(urgentButton.getAttribute('aria-pressed')).toBe('true')

    const allButton = screen.getByRole('button', { name: 'All' })
    allButton.focus()
    await user.keyboard('{Enter}')
    expect(allButton.getAttribute('aria-pressed')).toBe('true')
    expect(urgentButton.getAttribute('aria-pressed')).toBe('false')
  })
})
