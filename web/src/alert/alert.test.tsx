import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import alertCss from './alert.css?raw'
import { FeedbackButtons } from './FeedbackButtons.tsx'
import { SuggestedChecks } from './SuggestedChecks.tsx'

afterEach(() => {
  cleanup()
})

describe('SuggestedChecks', () => {
  it('renders the four labels in the given order', () => {
    render(
      <SuggestedChecks
        checks={['infection_or_uti', 'hydration', 'medication_review', 'cam_screen']}
      />,
    )

    expect(screen.getAllByRole('listitem').map((item) => item.textContent)).toEqual([
      'Check for infection / UTI',
      'Check hydration',
      'Review recent medication changes',
      'Run a CAM delirium screen',
    ])
  })

  it('renders nothing for an empty list', () => {
    const { container } = render(<SuggestedChecks checks={[]} />)

    expect(container.innerHTML).toBe('')
  })
})

describe('FeedbackButtons', () => {
  it('calls onChange with "confirmed" when Confirmed is clicked', () => {
    const onChange = vi.fn()
    render(<FeedbackButtons onChange={onChange} />)

    screen.getByRole('button', { name: 'Confirmed' }).click()

    expect(onChange).toHaveBeenCalledWith('confirmed')
  })

  it('calls onChange with "false_alarm" when False alarm is clicked', () => {
    const onChange = vi.fn()
    render(<FeedbackButtons onChange={onChange} />)

    screen.getByRole('button', { name: 'False alarm' }).click()

    expect(onChange).toHaveBeenCalledWith('false_alarm')
  })

  it('marks the selected button aria-pressed, the other not', () => {
    render(<FeedbackButtons value="confirmed" onChange={vi.fn()} />)

    expect(screen.getByRole('button', { name: 'Confirmed' }).getAttribute('aria-pressed')).toBe(
      'true',
    )
    expect(
      screen.getByRole('button', { name: 'False alarm' }).getAttribute('aria-pressed'),
    ).toBe('false')
  })

  it('marks neither button aria-pressed when value is null or unset', () => {
    render(<FeedbackButtons value={null} onChange={vi.fn()} />)

    expect(screen.getByRole('button', { name: 'Confirmed' }).getAttribute('aria-pressed')).toBe(
      'false',
    )
    expect(
      screen.getByRole('button', { name: 'False alarm' }).getAttribute('aria-pressed'),
    ).toBe('false')
  })
})

/** jsdom doesn't evaluate @media conditions for getComputedStyle, so this checks the
 * stylesheet text directly (T238, same approach as T234's overview.css test). */
describe('alert.css phone layout', () => {
  it('stacks error rows, evidence and the alert context full-width below 480px', () => {
    const mobileBlock = alertCss.match(/@media \(max-width: 480px\) \{([\s\S]*)\}\s*$/)?.[1]
    expect(mobileBlock).toBeTruthy()

    expect(mobileBlock).toMatch(/\.error-list__open\s*\{[^}]*flex-wrap:\s*wrap/)
    expect(mobileBlock).toMatch(/\.error-list__phrase\s*\{[^}]*flex-basis:\s*100%/)
    expect(mobileBlock).toMatch(/\.alert-view__evidence\s*\{[^}]*flex-direction:\s*column/)
    expect(mobileBlock).toMatch(/\.alert-context__record\s*\{[^}]*flex-wrap:\s*wrap/)
  })

  it('keeps feedback buttons at a 44px tap target and stacks them full-width', () => {
    const mobileBlock = alertCss.match(/@media \(max-width: 480px\) \{([\s\S]*)\}\s*$/)?.[1]

    expect(mobileBlock).toMatch(/\.feedback-buttons > \[role='group'\]\s*\{[^}]*flex-direction:\s*column/)
    expect(mobileBlock).toMatch(/\.feedback-button\s*\{[^}]*min-height:\s*2\.75rem[^}]*width:\s*100%/)
  })
})
