import { cleanup, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it } from 'vitest'
import type { CaptureFrame } from '../contracts.ts'
import ReplayPlayer from './ReplayPlayer.tsx'

const frames: CaptureFrame[] = [60, 61, 62].map((t, seq) => ({
  session_id: 'replay', seq, t, source: 'synthetic',
  poses: [], hands: [],
  objects: [],
}))

afterEach(() => {
  cleanup()
})

describe('ReplayPlayer keyboard access', () => {
  it('toggles play/pause on the Play button with Tab + Enter', async () => {
    const user = userEvent.setup()
    render(<ReplayPlayer frames={frames} fps={0.01} />)

    await user.tab()
    await user.tab()
    const playButton = screen.getByRole('button', { name: 'Play' })
    expect(document.activeElement).toBe(playButton)

    await user.keyboard('{Enter}')
    expect(screen.getByRole('button', { name: 'Pause' }).getAttribute('aria-pressed')).toBe('true')
    expect(screen.getByLabelText('Replay time').textContent).toBe('1:00')

    await user.keyboard(' ')
    expect(screen.getByRole('button', { name: 'Play' }).getAttribute('aria-pressed')).toBe('false')
    expect(screen.getByLabelText('Replay time').textContent).toBe('1:00')
  })

  it('tabs to the player and toggles playback with Space', async () => {
    const user = userEvent.setup()
    render(<ReplayPlayer frames={frames} fps={0.01} />)

    await user.tab()
    expect(document.activeElement).toBe(screen.getByRole('group', { name: /Skeleton replay/ }))
    await user.keyboard(' ')
    expect(screen.getByRole('button', { name: 'Pause' })).toBeTruthy()
    await user.keyboard(' ')
    expect(screen.getByRole('button', { name: 'Play' })).toBeTruthy()
  })

  it('tabs to the scrub slider', async () => {
    const user = userEvent.setup()
    render(<ReplayPlayer frames={frames} fps={0.01} />)

    await user.tab()
    await user.tab()
    await user.tab()
    const slider = screen.getByRole('slider') as HTMLInputElement
    expect(document.activeElement).toBe(slider)
    expect(slider.value).toBe('0')
  })

  // jsdom does not implement native arrow-key stepping for <input type="range">
  // (confirmed: even a bare range input ignores ArrowRight via user-event), so this
  // can't be asserted here even though real browsers scrub the slider with arrow keys.
  it.todo('scrubs the slider position with arrow keys — jsdom cannot simulate native range-input key stepping')

  it.todo('toggles the ghost overlay from the keyboard — no ghost toggle control exists on ReplayPlayer yet')
})
