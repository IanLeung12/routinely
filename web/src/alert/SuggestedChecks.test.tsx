import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it } from 'vitest'
import type { SuggestedCheck } from '../contracts.ts'
import { SuggestedChecks } from './SuggestedChecks.tsx'

afterEach(cleanup)

describe('SuggestedChecks', () => {
  it('renders one labelled item per suggested check in order', () => {
    const checks: SuggestedCheck[] = ['infection_or_uti', 'hydration', 'medication_review', 'cam_screen']
    render(<SuggestedChecks checks={checks} />)

    expect(screen.getAllByRole('listitem').map((item) => item.textContent)).toEqual([
      'Check for infection / UTI', 'Check hydration',
      'Review recent medication changes', 'Run a CAM delirium screen',
    ])
  })

  it('renders nothing when there are no suggested checks', () => {
    const { container } = render(<SuggestedChecks checks={[]} />)
    expect(container.textContent).toBe('')
    expect(screen.queryByRole('list')).toBeNull()
  })
})
