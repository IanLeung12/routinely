import { act, cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import type { CaptureFrame } from '../contracts.ts'
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
})
