import { act, cleanup, fireEvent, render, screen } from '@testing-library/react'
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
    expect(screen.getByText('Urgent')).toBeTruthy()
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
})
