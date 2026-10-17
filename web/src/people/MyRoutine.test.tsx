import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { acceptInvite, createInvite, currentPerson, setPeopleApi, supervisorsOf } from './api.ts'
import { MyRoutine } from './MyRoutine.tsx'

beforeEach(() => {
  localStorage.clear()
  setPeopleApi(null)
})

afterEach(cleanup)

/** Links the demo's supervisor to the person using the app, the way the invite flow does. */
function linkASupervisor() {
  acceptInvite(createInvite(currentPerson().id).code)
}

describe('MyRoutine', () => {
  it('says nobody else can see this when the person is watching themselves', () => {
    render(<MyRoutine />)

    expect(screen.getByRole('heading', { name: 'My routine' })).toBeTruthy()
    expect(screen.getByText(/Nobody else can see this/)).toBeTruthy()
  })

  it('lists who can see this, and takes one off again', () => {
    linkASupervisor()
    const onChange = vi.fn()
    render(<MyRoutine onChange={onChange} />)

    expect(screen.getByText('Nurse Ana')).toBeTruthy()

    fireEvent.click(screen.getByRole('button', { name: 'Remove Nurse Ana' }))

    expect(screen.queryByText('Nurse Ana')).toBeNull()
    expect(screen.getByText(/Nobody else can see this/)).toBeTruthy()
    expect(supervisorsOf(currentPerson().id)).toEqual([])
    expect(onChange).toHaveBeenCalled()
  })

  it('hands out a code and a link for someone to watch over them', () => {
    render(<MyRoutine />)

    fireEvent.click(screen.getByRole('button', { name: 'Invite someone' }))

    const { code } = createInvite(currentPerson().id)
    expect(screen.getByText(code)).toBeTruthy()
    expect(screen.getByText(/Or send them this link/).textContent).toContain(code)
  })

  it('tells the person nothing is shared with anyone they have not added', () => {
    render(<MyRoutine />)

    expect(screen.getByText(/Nothing is shared with anyone you have not added yourself/)).toBeTruthy()
  })
})
