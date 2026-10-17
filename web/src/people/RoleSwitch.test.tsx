import { cleanup, fireEvent, render, screen, within } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { RoleSwitch } from './RoleSwitch.tsx'

afterEach(cleanup)

describe('RoleSwitch', () => {
  it('shows which role is being viewed, in words and not colour alone', () => {
    render(<RoleSwitch role="supervisor" onChange={vi.fn()} />)

    const group = within(screen.getByRole('group', { name: 'Viewing as' }))
    expect(group.getByRole('button', { name: 'Someone I support', pressed: true })).toBeTruthy()
    expect(group.getByRole('button', { name: 'Myself', pressed: false })).toBeTruthy()
  })

  it('switches to the other role', () => {
    const onChange = vi.fn()
    render(<RoleSwitch role="supervisor" onChange={onChange} />)

    fireEvent.click(screen.getByRole('button', { name: 'Myself' }))

    expect(onChange).toHaveBeenCalledWith('person')
  })
})
