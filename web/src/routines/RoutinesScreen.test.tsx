import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { RoutinesScreen } from './RoutinesScreen.tsx'

beforeEach(() => {
  vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new Error('offline in tests')))
})

afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
  localStorage.clear()
})

describe('RoutinesScreen', () => {
  it('opens straight into the builder', () => {
    render(<RoutinesScreen onBack={vi.fn()} />)

    expect(screen.getByLabelText('What happens, in order')).toBeTruthy()
  })

  it('calls onBack from the Back button', () => {
    const onBack = vi.fn()
    render(<RoutinesScreen onBack={onBack} />)

    fireEvent.click(screen.getByRole('button', { name: 'Back' }))

    expect(onBack).toHaveBeenCalledTimes(1)
  })

  it('lists the built-in routines', async () => {
    render(<RoutinesScreen onBack={vi.fn()} />)

    fireEvent.click(screen.getByRole('button', { name: 'Routines' }))

    await waitFor(() => expect(screen.getByText('Make tea')).toBeTruthy())
    expect(screen.getByText('Take medication with water')).toBeTruthy()
  })

  it('shows a saved routine in the list after the builder saves it', async () => {
    render(<RoutinesScreen onBack={vi.fn()} />)

    fireEvent.change(screen.getByLabelText('What happens, in order'), {
      target: { value: 'Brush my teeth every morning' },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Draft routine' }))
    await waitFor(() => expect(screen.getByText('Brush teeth')).toBeTruthy())

    fireEvent.click(screen.getByRole('button', { name: 'Save routine' }))

    await waitFor(() => expect(screen.getByText('Saved by you')).toBeTruthy())
    expect(screen.getAllByText('Brush teeth').length).toBeGreaterThan(0)
    expect(screen.getByText('Make tea')).toBeTruthy()
  })
})
