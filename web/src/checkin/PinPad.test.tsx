import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { PinPad } from './PinPad.tsx'

afterEach(cleanup)

describe('PinPad', () => {
  it('has one large key per digit plus delete', () => {
    render(<PinPad onSubmit={vi.fn()} />)
    for (const digit of ['0', '1', '2', '3', '4', '5', '6', '7', '8', '9']) {
      expect(screen.getByRole('button', { name: digit })).toBeTruthy()
    }
    expect(screen.getByRole('button', { name: 'Delete last digit' })).toBeTruthy()
  })

  it('submits once length digits are entered, then resets for the next try', () => {
    const onSubmit = vi.fn()
    render(<PinPad length={4} onSubmit={onSubmit} />)

    for (const digit of ['1', '2', '3', '4']) {
      fireEvent.click(screen.getByRole('button', { name: digit }))
    }
    expect(onSubmit).toHaveBeenCalledTimes(1)
    expect(onSubmit).toHaveBeenCalledWith('1234')

    for (const digit of ['5', '6', '7', '8']) {
      fireEvent.click(screen.getByRole('button', { name: digit }))
    }
    expect(onSubmit).toHaveBeenCalledTimes(2)
    expect(onSubmit).toHaveBeenLastCalledWith('5678')
  })

  it('deletes the last digit typed, by mouse or keyboard', () => {
    const onSubmit = vi.fn()
    render(<PinPad length={4} onSubmit={onSubmit} />)

    fireEvent.click(screen.getByRole('button', { name: '1' }))
    fireEvent.click(screen.getByRole('button', { name: '2' }))
    fireEvent.click(screen.getByRole('button', { name: 'Delete last digit' }))
    fireEvent.click(screen.getByRole('button', { name: '3' }))
    fireEvent.click(screen.getByRole('button', { name: '4' }))
    fireEvent.click(screen.getByRole('button', { name: '5' }))

    expect(onSubmit).toHaveBeenCalledWith('1345')
  })

  it('reads out an error immediately and disables every key while waiting', () => {
    render(<PinPad length={4} onSubmit={vi.fn()} error="Try again" disabled />)

    expect(screen.getByRole('alert').textContent).toBe('Try again')
    expect((screen.getByRole('button', { name: '1' }) as HTMLButtonElement).disabled).toBe(true)
    expect((screen.getByRole('button', { name: 'Delete last digit' }) as HTMLButtonElement).disabled).toBe(true)
  })

  it('starts the delete key disabled and enables it once something is typed', () => {
    render(<PinPad length={4} onSubmit={vi.fn()} />)

    expect((screen.getByRole('button', { name: 'Delete last digit' }) as HTMLButtonElement).disabled).toBe(true)
    fireEvent.click(screen.getByRole('button', { name: '1' }))
    expect((screen.getByRole('button', { name: 'Delete last digit' }) as HTMLButtonElement).disabled).toBe(false)
  })
})
