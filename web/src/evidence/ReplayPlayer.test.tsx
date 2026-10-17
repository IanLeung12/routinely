import { act, cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import type { CaptureFrame } from '../contracts.ts'
import evidenceCss from './evidence.css?raw'
import ReplayPlayer from './ReplayPlayer.tsx'

const frames: CaptureFrame[] = [60, 61, 62].map((t, seq) => ({
  session_id: 'replay', seq, t, source: 'synthetic',
  poses: [], hands: [],
  objects: [{ label: 'cup', confidence: 1, box: { x1: seq / 10, y1: 0, x2: 0.5, y2: 0.5 } }],
}))

beforeEach(() => vi.useFakeTimers())
afterEach(() => {
  cleanup()
  vi.useRealTimers()
})

describe('ReplayPlayer', () => {
  it('plays skeleton frames at the supplied fps and pauses', () => {
    render(<ReplayPlayer frames={frames} fps={2} />)
    expect(screen.getByLabelText('Replay time').textContent).toBe('1:00')
    fireEvent.click(screen.getByRole('button', { name: 'Play' }))
    act(() => vi.advanceTimersByTime(500))
    expect((screen.getByRole('slider') as HTMLInputElement).value).toBe('1')
    expect(screen.getByLabelText('Replay time').textContent).toBe('1:01')
    expect(screen.getByRole('img').querySelector('rect')?.getAttribute('x')).toBe('48')
    fireEvent.click(screen.getByRole('button', { name: 'Pause' }))
    act(() => vi.advanceTimersByTime(1000))
    expect((screen.getByRole('slider') as HTMLInputElement).value).toBe('1')
  })

  it('scrubs directly to the selected frame', () => {
    render(<ReplayPlayer frames={frames} />)
    fireEvent.change(screen.getByRole('slider'), { target: { value: '2' } })
    expect(screen.getByLabelText('Replay time').textContent).toBe('1:02')
  })

  it('autoplays at the default rate and stops at the end', () => {
    render(<ReplayPlayer frames={frames} autoPlay />)
    act(() => vi.advanceTimersByTime(200))
    expect((screen.getByRole('slider') as HTMLInputElement).value).toBe('2')
    expect(screen.getByRole('button', { name: 'Play' })).toBeTruthy()
    expect(vi.getTimerCount()).toBe(0)
    act(() => vi.advanceTimersByTime(1000))
    expect(screen.getByLabelText('Replay time').textContent).toBe('1:02')
    fireEvent.click(screen.getByRole('button', { name: 'Play' }))
    expect((screen.getByRole('slider') as HTMLInputElement).value).toBe('0')
    act(() => vi.advanceTimersByTime(100))
    expect((screen.getByRole('slider') as HTMLInputElement).value).toBe('1')
  })

  it('shows the empty state without playback controls', () => {
    render(<ReplayPlayer frames={[]} autoPlay />)
    expect(screen.getByText('No replay available')).toBeTruthy()
    expect(screen.queryByRole('slider')).toBeNull()
    expect(vi.getTimerCount()).toBe(0)
  })

  it('cleans up its timer on unmount', () => {
    const { unmount } = render(<ReplayPlayer frames={frames} autoPlay />)
    expect(vi.getTimerCount()).toBe(1)
    unmount()
    expect(vi.getTimerCount()).toBe(0)
  })

  it('toggles play with Space when the player is focused', () => {
    render(<ReplayPlayer frames={frames} />)
    const player = screen.getByRole('group')
    fireEvent.keyDown(player, { key: ' ' })
    expect(screen.getByRole('button', { name: 'Pause' })).toBeTruthy()
    fireEvent.keyDown(player, { key: ' ' })
    expect(screen.getByRole('button', { name: 'Play' })).toBeTruthy()
  })

  it('ignores Space when it bubbles from a control that already handled it', () => {
    render(<ReplayPlayer frames={frames} />)
    fireEvent.keyDown(screen.getByRole('slider'), { key: ' ' })
    expect(screen.getByRole('button', { name: 'Play' })).toBeTruthy()
  })

  it('exposes accessible names and state on the controls', () => {
    render(<ReplayPlayer frames={frames} />)
    const playButton = screen.getByRole('button', { name: 'Play' })
    expect(playButton.getAttribute('aria-pressed')).toBe('false')
    fireEvent.click(playButton)
    expect(screen.getByRole('button', { name: 'Pause' }).getAttribute('aria-pressed')).toBe('true')
    expect(screen.getByRole('slider').getAttribute('aria-valuetext')).toBe('60.0 s of 62.0 s')
    fireEvent.change(screen.getByRole('slider'), { target: { value: '1' } })
    expect(screen.getByRole('slider').getAttribute('aria-valuetext')).toBe('61.0 s of 62.0 s')
    expect(screen.getByRole('img').getAttribute('aria-label')).toBeTruthy()
  })

  it('does not autoplay when the user prefers reduced motion, but Play still works', () => {
    window.matchMedia = vi.fn().mockReturnValue({ matches: true }) as unknown as typeof window.matchMedia
    render(<ReplayPlayer frames={frames} autoPlay />)
    const playButton = screen.getByRole('button', { name: 'Play' })
    expect(playButton).toBeTruthy()
    expect(vi.getTimerCount()).toBe(0)
    playButton.focus()
    expect(document.activeElement).toBe(playButton)
    fireEvent.click(playButton)
    act(() => vi.advanceTimersByTime(100))
    expect((screen.getByRole('slider') as HTMLInputElement).value).toBe('1')
    delete (window as { matchMedia?: typeof window.matchMedia }).matchMedia
  })
})

/** jsdom doesn't evaluate @media conditions for getComputedStyle, so this checks the
 * stylesheet text directly (same approach as alert.css's and overview.css's phone tests). */
describe('evidence.css phone layout', () => {
  it('scales the skeleton canvas to the container and stacks the controls at 375px', () => {
    const mobileBlock = evidenceCss.match(/@media \(max-width: 375px\) \{([\s\S]*)\}\s*$/)?.[1]
    expect(mobileBlock).toBeTruthy()

    expect(mobileBlock).toMatch(/\.replay-player\s*\{[^}]*flex-direction:\s*column/)
    expect(mobileBlock).toMatch(/\.replay-player \.skeleton-view,\s*\n\s*\.replay-player \.skeleton-view--empty\s*\{[^}]*width:\s*100%/)
    expect(mobileBlock).toMatch(/\.replay-player__controls\s*\{[^}]*flex-wrap:\s*wrap/)
  })

  it('keeps the play button and scrub bar at a 44px tap target', () => {
    const mobileBlock = evidenceCss.match(/@media \(max-width: 375px\) \{([\s\S]*)\}\s*$/)?.[1]

    expect(mobileBlock).toMatch(/\.replay-player__controls \.btn\s*\{[^}]*min-height:\s*2\.75rem/)
    expect(mobileBlock).toMatch(/\.replay-player__controls input\[type='range'\]\s*\{[^}]*min-height:\s*2\.75rem/)
  })
})
