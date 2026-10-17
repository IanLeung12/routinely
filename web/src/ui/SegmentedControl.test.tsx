import { cleanup, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { SegmentedControl } from './SegmentedControl.tsx'

afterEach(() => {
  cleanup()
})

const RANGES = [
  { value: '7d', label: '7 days' },
  { value: '14d', label: '14 days' },
  { value: '30d', label: '30 days' },
] as const

describe('SegmentedControl', () => {
  it('labels the group and shows every option', () => {
    render(
      <SegmentedControl label="Time range" options={RANGES} value="14d" onChange={() => {}} />,
    )
    const group = screen.getByRole('group', { name: 'Time range' })
    expect(group).toBeTruthy()
    for (const range of RANGES) {
      expect(screen.getByRole('button', { name: range.label })).toBeTruthy()
    }
  })

  it('marks the chosen option as pressed, not by colour alone', () => {
    render(
      <SegmentedControl label="Time range" options={RANGES} value="14d" onChange={() => {}} />,
    )
    expect(screen.getByRole('button', { name: '14 days' }).getAttribute('aria-pressed')).toBe(
      'true',
    )
    expect(screen.getByRole('button', { name: '7 days' }).getAttribute('aria-pressed')).toBe(
      'false',
    )
  })

  it('reports the option the user picked', async () => {
    const onChange = vi.fn()
    const user = userEvent.setup()
    render(<SegmentedControl label="Time range" options={RANGES} value="14d" onChange={onChange} />)
    await user.click(screen.getByRole('button', { name: '30 days' }))
    expect(onChange).toHaveBeenCalledWith('30d')
  })

  it('can be reached and chosen from the keyboard', async () => {
    const onChange = vi.fn()
    const user = userEvent.setup()
    render(<SegmentedControl label="Time range" options={RANGES} value="14d" onChange={onChange} />)
    await user.tab()
    expect(document.activeElement).toBe(screen.getByRole('button', { name: '7 days' }))
    await user.keyboard('{Enter}')
    expect(onChange).toHaveBeenCalledWith('7d')
  })
})
