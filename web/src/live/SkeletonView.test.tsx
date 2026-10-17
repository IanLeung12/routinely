import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it } from 'vitest'
import type { CaptureFrame, Landmark } from '../contracts.ts'
import SkeletonView from './SkeletonView.tsx'

afterEach(cleanup)

function makeLandmark(x: number, y: number): Landmark {
  return { x, y, z: 0 }
}

function makeFrame(): CaptureFrame {
  return {
    session_id: 'session-1',
    seq: 0,
    t: 0,
    source: 'synthetic',
    poses: [
      {
        landmarks: Array.from({ length: 33 }, (_, i) => makeLandmark(i / 33, i / 33)),
      },
    ],
    hands: [
      {
        handedness: 'left',
        score: 0.9,
        landmarks: Array.from({ length: 21 }, (_, i) => makeLandmark(i / 21, i / 21)),
      },
    ],
    objects: [
      { label: 'kettle', confidence: 0.95, box: { x1: 0.1, y1: 0.1, x2: 0.3, y2: 0.3 } },
      { label: 'cup', confidence: 0.8, box: { x1: 0.5, y1: 0.5, x2: 0.7, y2: 0.7 } },
    ],
  }
}

describe('SkeletonView', () => {
  it('shows a waiting message when there is no frame', () => {
    render(<SkeletonView frame={null} />)

    expect(screen.getByText('Waiting for camera')).toBeTruthy()
    expect(screen.queryByRole('img')).toBeNull()
  })

  it('renders one rect and label per object', () => {
    const { container } = render(<SkeletonView frame={makeFrame()} />)

    const rects = container.querySelectorAll('rect')
    expect(rects).toHaveLength(2)
    expect(screen.getByText('kettle')).toBeTruthy()
    expect(screen.getByText('cup')).toBeTruthy()
  })

  it('renders circles for pose and hand landmarks', () => {
    const { container } = render(<SkeletonView frame={makeFrame()} />)

    const circles = container.querySelectorAll('circle')
    expect(circles).toHaveLength(33 + 21)
  })

  it('renders lines for the fixed pose connections', () => {
    const { container } = render(<SkeletonView frame={makeFrame()} />)

    const lines = container.querySelectorAll('line')
    expect(lines.length).toBeGreaterThan(0)
  })

  it('never renders video', () => {
    const { container } = render(<SkeletonView frame={makeFrame()} />)

    expect(container.querySelector('video')).toBeNull()
    expect(container.querySelector('img')).toBeNull()
  })

  it('has an accessible name describing who and what is tracked', () => {
    render(<SkeletonView frame={makeFrame()} />)

    const image = screen.getByRole('img')
    expect(image.getAttribute('aria-label')).toBe(
      'Skeleton view: 1 person tracked; 1 hand tracked; objects in view: kettle, cup',
    )
  })
})
