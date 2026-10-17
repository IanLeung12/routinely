import { cleanup, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, expect, it, vi } from 'vitest'
import { RangeSelector } from './RangeSelector'

afterEach(cleanup)

it('shows three ranges, exposes selection and reports a new range', async () => {
  const onChange = vi.fn()
  const user = userEvent.setup()
  const { rerender } = render(<RangeSelector value="14D" onChange={onChange} />)
  expect(screen.getByRole('group', { name: 'Chart time range' })).toBeTruthy()
  expect(screen.getAllByRole('button').map((button) => button.textContent)).toEqual(['7D', '14D', '30D'])
  expect(screen.getByRole('button', { name: '14D' }).getAttribute('aria-pressed')).toBe('true')
  await user.click(screen.getByRole('button', { name: '30D' }))
  expect(onChange).toHaveBeenCalledWith('30D')
  rerender(<RangeSelector label="Score range" value="30D" onChange={onChange} />)
  expect(screen.getByRole('group', { name: 'Score range' })).toBeTruthy()
  expect(screen.getByRole('button', { name: '30D' }).getAttribute('aria-pressed')).toBe('true')
})

it('can select a range with the keyboard', async () => {
  const onChange = vi.fn()
  const user = userEvent.setup()
  render(<RangeSelector value="14D" onChange={onChange} />)
  await user.tab()
  await user.keyboard('{Enter}')
  expect(onChange).toHaveBeenCalledWith('7D')
})
