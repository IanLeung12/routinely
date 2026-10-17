import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
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
