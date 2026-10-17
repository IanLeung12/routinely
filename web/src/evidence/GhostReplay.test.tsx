import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it } from 'vitest'
import type { CaptureFrame } from '../contracts.ts'
import GhostReplay from './GhostReplay.tsx'

afterEach(cleanup)

function frame(t: number, x = 0.25, people = 1): CaptureFrame {
  return {
    session_id: 'tea', seq: t, t, source: 'synthetic', hands: [], objects: [],
    poses: Array.from({ length: people }, () => ({
      landmarks: Array.from({ length: 33 }, () => ({ x, y: 0.5, z: 0 })),
    })),
  }
}

describe('GhostReplay', () => {
  it('renders grey usual skeletons under blue today skeletons with the specified connections', () => {
    const { container } = render(<GhostReplay today={[frame(0, 0.5, 2)]} normal={[frame(0)]} t={0} />)
    const layers = container.querySelectorAll('[data-layer]')
    expect(layers[0].getAttribute('data-layer')).toBe('normal')
    expect(layers[0].getAttribute('opacity')).toBe('0.4')
    expect(layers[0].getAttribute('fill')).toBe('var(--ghost-usual)')
    expect(layers[0].querySelectorAll('circle')).toHaveLength(33)
    expect(layers[0].querySelectorAll('line')).toHaveLength(8)
    expect(layers[1].getAttribute('fill')).toBe('var(--ghost-today)')
    expect(layers[1].querySelectorAll('circle')).toHaveLength(66)
    expect(layers[1].querySelectorAll('line')).toHaveLength(16)
    expect(screen.getByText('Today')).toBeTruthy()
    expect(screen.getByText('Usual')).toBeTruthy()
  })

  it('selects the nearest frame independently in unsorted lists and scales coordinates', () => {
    const { container } = render(<GhostReplay
      today={[frame(10, 0.8), frame(2, 0.2)]}
      normal={[frame(1, 0.1), frame(8, 0.6)]}
      t={7} width={200} height={100}
    />)
    expect(container.querySelector('[data-layer="today"] circle')?.getAttribute('cx')).toBe('160')
    expect(container.querySelector('[data-layer="normal"] circle')?.getAttribute('cx')).toBe('120')
    expect(container.querySelector('circle')?.getAttribute('cy')).toBe('50')
    expect(container.querySelector('svg')?.getAttribute('viewBox')).toBe('0 0 200 100')
  })

  it.each(['today', 'normal'] as const)('renders only the available %s layer', layer => {
    const { container } = render(<GhostReplay today={layer === 'today' ? [frame(0)] : []} normal={layer === 'normal' ? [frame(0)] : []} t={0} />)
    expect(container.querySelectorAll('[data-layer]')).toHaveLength(1)
    expect(container.querySelector('[data-layer]')?.getAttribute('data-layer')).toBe(layer)
  })

  it.each([
    ['today', "Today's routine, with no usual routine to compare it with, frame 1 of 1 at 0.0 s"],
    ['normal', 'The usual routine, with nothing recorded today to compare it with, frame 1 of 1 at 0.0 s'],
  ] as const)('says there is nothing to compare when only the %s recording has frames', (layer, label) => {
    render(<GhostReplay today={layer === 'today' ? [frame(0)] : []} normal={layer === 'normal' ? [frame(0)] : []} t={0} />)
    expect(screen.getByRole('img', { name: label })).toBeTruthy()
  })

  it('renders a message when neither recording has frames', () => {
    render(<GhostReplay today={[]} normal={[]} t={0} />)
    expect(screen.getByText('No skeleton data')).toBeTruthy()
    expect(screen.queryByRole('img')).toBeNull()
  })

  it('tells a screen reader what is being compared, and moves the label with the frame', () => {
    const today = [frame(0), frame(2), frame(4)]
    const normal = [frame(0), frame(3)]
    const { rerender } = render(<GhostReplay today={today} normal={normal} t={0} />)
    const labelAt = () => screen.getByRole('img').getAttribute('aria-label') ?? ''

    const first = labelAt()
    expect(first).toBe("Today's routine drawn over the usual routine, frame 1 of 3 at 0.0 s")

    rerender(<GhostReplay today={today} normal={normal} t={4} />)
    const last = labelAt()
    expect(last).toBe("Today's routine drawn over the usual routine, frame 3 of 3 at 4.0 s")
    expect(last).not.toBe(first)
  })

  it('never calls the comparison a diagnosis', () => {
    for (const [today, normal] of [[[frame(0)], [frame(0)]], [[frame(1)], []], [[], [frame(1)]]]) {
      const { unmount } = render(<GhostReplay today={today} normal={normal} t={1} />)
      expect(screen.getByRole('img').getAttribute('aria-label')).not.toMatch(/diagnos/i)
      unmount()
    }
  })

  it('warns that the body is a stand-in, not tracked motion', () => {
    render(<GhostReplay today={[frame(0)]} normal={[frame(0)]} t={0} />)
    expect(screen.getByText('Demo recording: the body is drawn as a stand-in; the hand follows the tracked hand box.')).toBeTruthy()
  })
})
