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
    expect(screen.getByText('9 steps')).toBeTruthy()
    expect(screen.getByText('6 steps')).toBeTruthy()
  })

  it('lists what the live API sends, which carries a step count and no task graph', async () => {
    // Exactly one `Routine.summary()` row each (routine_builder.py): the screen used to
    // read `task_graph.steps.length` and threw on this (T443).
    const rows = [
      {
        id: 'tea',
        title: 'Make tea',
        task_id: 'make_tea',
        built_in: true,
        source: 'built_in',
        step_count: 9,
        needs_training: [],
      },
      {
        id: 'wash_hands',
        title: 'Wash hands',
        task_id: 'wash_hands',
        built_in: false,
        source: 'text',
        step_count: 5,
        needs_training: ['towel'],
      },
    ]
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: true, json: async () => rows }))
    render(<RoutinesScreen onBack={vi.fn()} />)

    fireEvent.click(screen.getByRole('button', { name: 'Routines' }))

    await waitFor(() => expect(screen.getByText('Wash hands')).toBeTruthy())
    expect(screen.getByText('9 steps')).toBeTruthy()
    expect(screen.getByText('5 steps')).toBeTruthy()
    expect(screen.getByText('Built in')).toBeTruthy()
    expect(screen.getByText('Saved by you')).toBeTruthy()
  })

  it('says "1 step" for a one-step routine', async () => {
    const rows = [
      {
        id: 'water',
        title: 'Drink a glass of water',
        task_id: 'water',
        built_in: false,
        source: 'text',
        step_count: 1,
        needs_training: [],
      },
    ]
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: true, json: async () => rows }))
    render(<RoutinesScreen onBack={vi.fn()} />)

    fireEvent.click(screen.getByRole('button', { name: 'Routines' }))

    await waitFor(() => expect(screen.getByText('1 step')).toBeTruthy())
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
    expect(screen.getByText('5 steps')).toBeTruthy()
    expect(screen.getByText('Make tea')).toBeTruthy()
  })
})
