import { cleanup, render, screen, within } from '@testing-library/react'
import { afterEach, describe, expect, it } from 'vitest'
import { PrivacyPanel } from './PrivacyPanel.tsx'

afterEach(cleanup)

describe('PrivacyPanel', () => {
  it('labels the section with its heading and renders all six statements verbatim', () => {
    render(<PrivacyPanel />)

    const section = screen.getByRole('region', { name: 'Privacy and limits' })
    expect(within(section).getByRole('heading', { level: 2, name: 'Privacy and limits' })).toBeTruthy()
    expect(within(section).getAllByRole('listitem').map((item) => item.textContent)).toEqual([
      'Only skeleton points and object boxes leave the camera. No video is stored.',
      'No face recognition. Each camera is linked to a room by configuration.',
      'It flags a change for a nurse to review. It is not a medical assessment.',
      'Low-confidence moments are shown as unclear, never counted as errors.',
      'Pose tracking is less accurate with walkers, wheelchairs and unusual postures.',
      'Residents or their decision-maker opt in, and monitoring can be turned off per room.',
    ])
    expect(section.textContent).not.toMatch(/diagnos/i)
  })
})
