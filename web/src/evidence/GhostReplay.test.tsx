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
    expect(layers[0].getAttribute('fill')).toBe('grey')
    expect(layers[0].querySelectorAll('circle')).toHaveLength(33)
    expect(layers[0].querySelectorAll('line')).toHaveLength(8)
    expect(layers[1].getAttribute('fill')).toBe('blue')
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

  it('renders a message when neither recording has frames', () => {
    render(<GhostReplay today={[]} normal={[]} t={0} />)
    expect(screen.getByText('No skeleton data')).toBeTruthy()
    expect(screen.queryByRole('img')).toBeNull()
  })
})
