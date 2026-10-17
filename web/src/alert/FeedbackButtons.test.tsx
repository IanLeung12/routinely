import { cleanup, fireEvent, render, screen, within } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { FeedbackButtons } from './FeedbackButtons.tsx'

afterEach(cleanup)

describe('FeedbackButtons', () => {
  it('groups the choices and leaves the status empty without a value', () => {
    render(<FeedbackButtons onChange={() => {}} />)

    const group = screen.getByRole('group', { name: 'Nurse feedback' })
    expect(within(group).getAllByRole('button')).toHaveLength(2)
    expect(within(group).getByRole('status').textContent).toBe('')
    expect(screen.getByRole('status').getAttribute('aria-live')).toBe('polite')
  })

  it.each([
    ['confirmed', 'Marked as confirmed', 'Confirmed'],
    ['false_alarm', 'Marked as false alarm', 'False alarm'],
  ] as const)('announces %s and keeps the selected button pressed', (value, message, label) => {
    render(<FeedbackButtons value={value} onChange={() => {}} />)

    expect(screen.getByRole('status').textContent).toBe(message)
    expect(screen.getByRole('button', { name: label }).getAttribute('aria-pressed')).toBe('true')
    expect(screen.getAllByRole('button').filter((button) => button.getAttribute('aria-pressed') === 'false')).toHaveLength(1)
  })

  it('calls onChange with the clicked verdict', () => {
    const onChange = vi.fn()
    render(<FeedbackButtons onChange={onChange} />)

    fireEvent.click(screen.getByRole('button', { name: 'Confirmed' }))
    fireEvent.click(screen.getByRole('button', { name: 'False alarm' }))
    expect(onChange.mock.calls).toEqual([['confirmed'], ['false_alarm']])
  })

  const CAUSE_OPTIONS = [
    { id: 'uti', label: 'UTI' },
    { id: 'fatigue', label: 'Fatigue' },
  ]

  it('hides the cause picker before confirming, even with causeOptions given', () => {
    render(<FeedbackButtons onChange={() => {}} causeOptions={CAUSE_OPTIONS} />)

    expect(screen.queryByRole('group', { name: 'What was it? (optional)' })).toBeNull()
  })

  it('hides the cause picker after confirming when causeOptions is absent', () => {
    render(<FeedbackButtons value="confirmed" onChange={() => {}} />)

    expect(screen.queryByRole('group', { name: 'What was it? (optional)' })).toBeNull()
  })

  it('shows the cause picker with an Other option once confirmed', () => {
    render(<FeedbackButtons value="confirmed" onChange={() => {}} causeOptions={CAUSE_OPTIONS} />)

    const group = screen.getByRole('group', { name: 'What was it? (optional)' })
    // The question is on the screen, not only in the group's accessible name.
    expect(within(group).getByText('What was it? (optional)')).toBeTruthy()
    expect(within(group).getAllByRole('button').map((button) => button.textContent)).toEqual([
      'UTI',
      'Fatigue',
      'Other',
    ])
  })

  it('marks the selected cause as pressed and calls onCauseChange when another is clicked', () => {
    const onCauseChange = vi.fn()
    render(
      <FeedbackButtons
        value="confirmed"
        onChange={() => {}}
        causeOptions={CAUSE_OPTIONS}
        cause="uti"
        onCauseChange={onCauseChange}
      />,
    )

    expect(screen.getByRole('button', { name: 'UTI' }).getAttribute('aria-pressed')).toBe('true')
    fireEvent.click(screen.getByRole('button', { name: 'Other' }))
    expect(onCauseChange).toHaveBeenCalledWith('other')
  })
})
