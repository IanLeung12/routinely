import { cleanup, fireEvent, render, screen, within } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { StepEditor } from './StepEditor.tsx'
import type { RoutineStep } from './types.ts'

afterEach(cleanup)

const STEPS: RoutineStep[] = [
  { id: 'get_cup', label: 'Get a cup', objects: ['cup'], depends_on: [], optional: false, once_only: true },
  { id: 'pour', label: 'Pour the water', objects: ['kettle'], depends_on: ['get_cup'], optional: false, once_only: true },
  { id: 'milk', label: 'Add milk', objects: ['milk'], depends_on: ['pour'], optional: true, once_only: true },
]

describe('StepEditor', () => {
  it('renames a step', () => {
    const onChange = vi.fn()
    render(<StepEditor steps={STEPS} onChange={onChange} />)

    fireEvent.change(screen.getByDisplayValue('Get a cup'), { target: { value: 'Grab a mug' } })

    expect(onChange).toHaveBeenCalledTimes(1)
    expect(onChange.mock.calls[0][0][0].label).toBe('Grab a mug')
  })

  it('toggles a step optional', () => {
    const onChange = vi.fn()
    render(<StepEditor steps={STEPS} onChange={onChange} />)

    const getCupItem = screen.getByDisplayValue('Get a cup').closest('li') as HTMLElement
    fireEvent.click(within(getCupItem).getByRole('checkbox', { name: 'Optional step' }))

    expect(onChange.mock.calls[0][0][0].optional).toBe(true)
  })

  it('moves a step up, keeping every dependency pointing earlier', () => {
    const onChange = vi.fn()
    render(<StepEditor steps={STEPS} onChange={onChange} />)

    fireEvent.click(screen.getByRole('button', { name: 'Move Add milk up' }))

    const next = onChange.mock.calls[0][0] as RoutineStep[]
    expect(next.map((step) => step.id)).toEqual(['get_cup', 'milk', 'pour'])
    // "milk" depended on "pour", which now comes after it, so that dependency is dropped.
    expect(next.find((step) => step.id === 'milk')?.depends_on).toEqual([])
  })

  it('deletes a step and drops it from any dependency list', () => {
    const onChange = vi.fn()
    render(<StepEditor steps={STEPS} onChange={onChange} />)

    fireEvent.click(screen.getByRole('button', { name: 'Delete Pour the water' }))

    const next = onChange.mock.calls[0][0] as RoutineStep[]
    expect(next.map((step) => step.id)).toEqual(['get_cup', 'milk'])
    expect(next.find((step) => step.id === 'milk')?.depends_on).toEqual([])
  })

  it('adds a new step from the label field', () => {
    const onChange = vi.fn()
    render(<StepEditor steps={STEPS} onChange={onChange} />)

    fireEvent.change(screen.getByLabelText('Add a step'), { target: { value: 'Stir' } })
    fireEvent.click(screen.getByRole('button', { name: 'Add step' }))

    const next = onChange.mock.calls[0][0] as RoutineStep[]
    expect(next).toHaveLength(4)
    expect(next[3]).toMatchObject({ id: 'stir', label: 'Stir', depends_on: [], optional: false })
  })

  it('toggles a dependency on an earlier step', () => {
    const onChange = vi.fn()
    render(<StepEditor steps={STEPS} onChange={onChange} />)

    const milkItem = screen.getByDisplayValue('Add milk').closest('li') as HTMLElement
    fireEvent.click(within(milkItem).getByRole('checkbox', { name: 'Get a cup' }))

    const next = onChange.mock.calls[0][0] as RoutineStep[]
    expect(next.find((step) => step.id === 'milk')?.depends_on).toEqual(['pour', 'get_cup'])
  })
})
