import { act, cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import type { CaptureFrame } from '../contracts.ts'
import ReplayPlayer, { type ReplayPlayerMarker } from './ReplayPlayer.tsx'

/** Nine seconds of a kept session, one frame a second (T446: analysing a replay). */
const frames: CaptureFrame[] = Array.from({ length: 9 }, (_, seq) => ({
  session_id: 'replay', seq, t: seq, source: 'synthetic',
  poses: [], hands: [], objects: [],
}))

/** The session's errors, as a supervisor's replay library hands them over. */
const markers: ReplayPlayerMarker[] = [
  { t: 2, label: 'skipped the teabag', kind: 'omission' },
  { t: 5.5, label: 'long pause at pour water', kind: 'hesitation' },
  { t: 7, label: 'stopped partway' },
]

const slider = () => (screen.getByRole('slider') as HTMLInputElement).value

beforeEach(() => vi.useFakeTimers())
afterEach(() => {
  cleanup()
  vi.useRealTimers()
})

describe('ReplayPlayer error markers', () => {
  it('names every marker by what happened and when', () => {
    render(<ReplayPlayer frames={frames} markers={markers} />)

    expect(screen.getAllByRole('button', { name: /^Jump to/ }).map((marker) => marker.getAttribute('aria-label')))
      .toEqual([
        'Jump to skipped the teabag at 0:02',
        'Jump to long pause at pour water at 0:05',
        'Jump to stopped partway at 0:07',
      ])
  })

  it('colours each marker by error type and places it along the timeline', () => {
    render(<ReplayPlayer frames={frames} markers={markers} />)

    const omission = screen.getByRole('button', { name: 'Jump to skipped the teabag at 0:02' })
    expect(omission.className).toBe('replay-player__marker replay-player__marker--omission')
    expect(omission.style.left).toBe('25%')

    const pause = screen.getByRole('button', { name: 'Jump to long pause at pour water at 0:05' })
    expect(pause.className).toBe('replay-player__marker replay-player__marker--hesitation')
    expect(pause.style.left).toBe('68.75%')

    // No kind given: the tick keeps the neutral colour and gains no modifier.
    expect(screen.getByRole('button', { name: 'Jump to stopped partway at 0:07' }).className)
      .toBe('replay-player__marker')
  })

  it('jumps to the first frame at or after the marker and pauses there', () => {
    render(<ReplayPlayer frames={frames} markers={markers} fps={2} autoPlay />)
    act(() => vi.advanceTimersByTime(500))
    expect(slider()).toBe('1')

    fireEvent.click(screen.getByRole('button', { name: 'Jump to long pause at pour water at 0:05' }))

    expect(slider()).toBe('6')
    expect(screen.getByLabelText('Replay time').textContent).toBe('0:06')
    expect(screen.getByRole('button', { name: 'Play' })).toBeTruthy()
    expect(vi.getTimerCount()).toBe(0)
  })

  it('lands on the last kept frame when the error is past the end of the frames', () => {
    render(<ReplayPlayer frames={frames} markers={[{ t: 99, label: 'left the kitchen' }]} />)

    const marker = screen.getByRole('button', { name: 'Jump to left the kitchen at 1:39' })
    expect(marker.style.left).toBe('100%')
    fireEvent.click(marker)

    expect(slider()).toBe('8')
  })

  it('renders no markers when the caller passes none', () => {
    render(<ReplayPlayer frames={frames} />)

    expect(screen.queryAllByRole('button', { name: /^Jump to/ })).toHaveLength(0)
    expect(document.querySelectorAll('.replay-player__marker')).toHaveLength(0)
    expect(screen.getByRole('slider')).toBeTruthy()
  })
})

describe('ReplayPlayer speed', () => {
  /** Frames covered in a second of wall clock, at 2 frames a second and the given speed. */
  const framesInOneSecond = (speed: string) => {
    render(<ReplayPlayer frames={frames} fps={2} />)
    fireEvent.click(screen.getByRole('button', { name: speed }))
    fireEvent.click(screen.getByRole('button', { name: 'Play' }))
    act(() => vi.advanceTimersByTime(1000))
    const position = Number(slider())
    cleanup()
    return position
  }

  it('runs 2x through twice as many frames as 1x over the same time', () => {
    expect(framesInOneSecond('1×')).toBe(2)
    expect(framesInOneSecond('2×')).toBe(4)
    expect(framesInOneSecond('0.5×')).toBe(1)
  })

  it('offers the three speeds in a labelled group and marks the chosen one', () => {
    render(<ReplayPlayer frames={frames} />)
    const speeds = screen.getByRole('toolbar', { name: 'Playback speed' })

    expect(Array.from(speeds.querySelectorAll('button')).map((button) => button.textContent))
      .toEqual(['0.5×', '1×', '2×'])
    expect(screen.getByRole('button', { name: '1×' }).getAttribute('aria-pressed')).toBe('true')

    fireEvent.click(screen.getByRole('button', { name: '0.5×' }))

    expect(screen.getByRole('button', { name: '0.5×' }).getAttribute('aria-pressed')).toBe('true')
    expect(screen.getByRole('button', { name: '1×' }).getAttribute('aria-pressed')).toBe('false')
  })

  it('keeps playing at the new speed when it changes mid-replay', () => {
    render(<ReplayPlayer frames={frames} fps={2} />)
    fireEvent.click(screen.getByRole('button', { name: 'Play' }))
    act(() => vi.advanceTimersByTime(500))
    expect(slider()).toBe('1')

    fireEvent.click(screen.getByRole('button', { name: '2×' }))
    act(() => vi.advanceTimersByTime(500))

    expect(slider()).toBe('3')
    expect(screen.getByRole('button', { name: 'Pause' })).toBeTruthy()
  })
})

describe('ReplayPlayer frame stepping', () => {
  it('steps a frame with the arrow keys and pauses', () => {
    render(<ReplayPlayer frames={frames} fps={2} autoPlay />)
    const player = screen.getByRole('group')
    act(() => vi.advanceTimersByTime(500))
    expect(slider()).toBe('1')

    fireEvent.keyDown(player, { key: 'ArrowRight' })

    expect(slider()).toBe('2')
    expect(screen.getByRole('button', { name: 'Play' })).toBeTruthy()
    expect(vi.getTimerCount()).toBe(0)
    act(() => vi.advanceTimersByTime(2000))
    expect(slider()).toBe('2')

    fireEvent.keyDown(player, { key: 'ArrowLeft' })

    expect(slider()).toBe('1')
    expect(screen.getByLabelText('Replay time').textContent).toBe('0:01')
  })

  it('stops stepping at either end of the replay', () => {
    render(<ReplayPlayer frames={frames} />)
    const player = screen.getByRole('group')

    fireEvent.keyDown(player, { key: 'ArrowLeft' })
    expect(slider()).toBe('0')

    fireEvent.change(screen.getByRole('slider'), { target: { value: '8' } })
    fireEvent.keyDown(player, { key: 'ArrowRight' })
    expect(slider()).toBe('8')
  })

  it('leaves the arrow keys to the scrub bar when that is what has focus', () => {
    render(<ReplayPlayer frames={frames} />)

    fireEvent.keyDown(screen.getByRole('slider'), { key: 'ArrowRight' })

    expect(slider()).toBe('0')
  })

  it('tells the supervisor about the arrow keys in the player name', () => {
    render(<ReplayPlayer frames={frames} />)

    expect(screen.getByRole('group').getAttribute('aria-label')).toMatch(/arrow keys to step one frame/i)
  })
})
