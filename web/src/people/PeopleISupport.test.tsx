import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { createInvite, peopleISupport, setPeopleApi } from './api.ts'
import { PeopleISupport } from './PeopleISupport.tsx'
import type { Person } from './types.ts'

const MRS_K: Person = { id: 'mrs-k', name: 'Mrs. K', context: 'Room 204, care home' }
const MR_D: Person = { id: 'mr-d', name: 'Mr. D', context: 'Lives alone' }

beforeEach(() => {
  localStorage.clear()
  setPeopleApi(null)
})

afterEach(cleanup)

function typeCode(code: string) {
  fireEvent.change(screen.getByLabelText('Invite code'), { target: { value: code } })
}

describe('PeopleISupport', () => {
  it('says how to start when nobody has shared their routine yet', () => {
    render(<PeopleISupport people={[]} />)

    expect(screen.getByText(/Nobody has shared their routine with you yet/)).toBeTruthy()
  })

  it('lists each person with their context and opens one', () => {
    const onOpen = vi.fn()
    render(<PeopleISupport people={[MRS_K]} onOpen={onOpen} />)

    expect(screen.getByText('Room 204, care home')).toBeTruthy()
    fireEvent.click(screen.getByRole('button', { name: 'Open Mrs. K' }))

    expect(onOpen).toHaveBeenCalledWith('mrs-k')
  })

  it('lists several people, each with their own context', () => {
    const onOpen = vi.fn()
    render(<PeopleISupport people={[MRS_K, MR_D]} onOpen={onOpen} />)

    expect(screen.getByText('Mrs. K')).toBeTruthy()
    expect(screen.getByText('Room 204, care home')).toBeTruthy()
    expect(screen.getByText('Mr. D')).toBeTruthy()
    expect(screen.getByText('Lives alone')).toBeTruthy()

    fireEvent.click(screen.getByRole('button', { name: 'Open Mr. D' }))
    expect(onOpen).toHaveBeenCalledWith('mr-d')
  })

  it('adds a person from their invite code', () => {
    const onChange = vi.fn()
    const { code } = createInvite('sam')
    render(<PeopleISupport people={[]} onChange={onChange} />)

    typeCode(code)
    fireEvent.click(screen.getByRole('button', { name: 'Add person' }))

    expect(screen.getByRole('status').textContent).toContain('Sam shared their routine with you.')
    expect(peopleISupport().map((person) => person.id)).toContain('sam')
    expect(onChange).toHaveBeenCalled()
  })

  it('says so when the code matches nothing, without losing what was typed', () => {
    const onChange = vi.fn()
    render(<PeopleISupport people={[]} onChange={onChange} />)

    typeCode('NOPE23')
    fireEvent.click(screen.getByRole('button', { name: 'Add person' }))

    expect(screen.getByRole('alert').textContent).toContain("That code doesn't match an invite")
    expect((screen.getByLabelText('Invite code') as HTMLInputElement).value).toBe('NOPE23')
    expect(onChange).not.toHaveBeenCalled()
  })

  it('fills in a code that arrived as a link', () => {
    render(<PeopleISupport people={[]} initialCode="ABC234" />)

    expect((screen.getByLabelText('Invite code') as HTMLInputElement).value).toBe('ABC234')
  })

  it('stops supporting someone', () => {
    const onChange = vi.fn()
    render(<PeopleISupport people={[MRS_K]} onChange={onChange} />)

    fireEvent.click(screen.getByRole('button', { name: 'Stop supporting Mrs. K' }))

    expect(peopleISupport().map((person) => person.id)).not.toContain('mrs-k')
    expect(onChange).toHaveBeenCalled()
  })
})
