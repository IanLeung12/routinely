import { cleanup, render, screen, within } from '@testing-library/react'
import { afterEach, describe, expect, it } from 'vitest'
import { PrivacyPanel } from './PrivacyPanel.tsx'

afterEach(cleanup)

describe('PrivacyPanel', () => {
  it('labels the section with its heading and renders all seven statements verbatim', () => {
    render(<PrivacyPanel />)

    const section = screen.getByRole('region', { name: 'Privacy and limits' })
    expect(within(section).getByRole('heading', { level: 2, name: 'Privacy and limits' })).toBeTruthy()
    expect(within(section).getAllByRole('listitem').map((item) => item.textContent)).toEqual([
      'Only skeleton points and object boxes leave the camera. No video is stored.',
      'No face recognition. Each camera is linked to a room by configuration.',
      'It flags a change for a nurse to review. It is not a medical assessment.',
      'Low-confidence moments are shown as unclear, never counted as errors.',
      'Pose tracking is less accurate with walkers, wheelchairs and unusual postures.',
      "Residents or their decision-maker opt in; who consented and when is shown on each resident's page.",
      'Monitoring can be paused per room; every pause and resume is logged with who and when.',
    ])
    expect(section.textContent).not.toMatch(/diagnos/i)
  })
})
