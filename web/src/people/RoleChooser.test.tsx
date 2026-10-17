import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { RoleChooser } from './RoleChooser.tsx'

afterEach(cleanup)

describe('RoleChooser', () => {
  it('offers both roles and says what each one shows', () => {
    render(<RoleChooser onChoose={vi.fn()} />)

    expect(screen.getByRole('heading', { name: 'Who is this for?' })).toBeTruthy()
    const mine = screen.getByRole('button', { name: /setting this up for myself/i })
    const theirs = screen.getByRole('button', { name: /supporting someone/i })
    expect(mine.textContent).toContain('your own routine')
    expect(theirs.textContent).toContain('shared their routine with you')
  })

  it('answers with the role that was picked', () => {
    const onChoose = vi.fn()
    render(<RoleChooser onChoose={onChoose} />)

    fireEvent.click(screen.getByRole('button', { name: /setting this up for myself/i }))
    expect(onChoose).toHaveBeenCalledWith('person')

    fireEvent.click(screen.getByRole('button', { name: /supporting someone/i }))
    expect(onChoose).toHaveBeenLastCalledWith('supervisor')
  })

  it('says the choice can be changed later, so nobody has to get it right first time', () => {
    render(<RoleChooser onChoose={vi.fn()} />)

    expect(screen.getByText(/change it at the top of any screen/i)).toBeTruthy()
  })
})
