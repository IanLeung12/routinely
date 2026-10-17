import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { RoutineBuilder } from './RoutineBuilder.tsx'

beforeEach(() => {
  // Offline in every test: the mock draft responds instantly and deterministically,
  // same as the demo running with no keys.
  vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new Error('offline in tests')))
})

afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
  localStorage.clear()
})

describe('Describe it', () => {
  it('fills the textarea from an example', () => {
    render(<RoutineBuilder onSaved={vi.fn()} />)

    fireEvent.click(screen.getByRole('button', { name: 'Brushing teeth' }))

    const textarea = screen.getByLabelText('What happens, in order') as HTMLTextAreaElement
    expect(textarea.value).toBe('Get the toothbrush, put toothpaste on it, brush, then rinse and spit.')
  })

  it('disables submit until there is a description, then drafts a routine', async () => {
    render(<RoutineBuilder onSaved={vi.fn()} />)

    const submit = screen.getByRole('button', { name: 'Draft routine' }) as HTMLButtonElement
    expect(submit.disabled).toBe(true)

    fireEvent.change(screen.getByLabelText('What happens, in order'), {
      target: { value: 'Brush my teeth every morning' },
    })
    expect(submit.disabled).toBe(false)
    fireEvent.click(submit)

    await waitFor(() => expect(screen.getByText('Brush teeth')).toBeTruthy())
    expect(screen.getByRole('list', { name: 'Task steps' })).toBeTruthy()
    expect(screen.getByText(/doesn't know/)).toBeTruthy()
  })
})

describe('From a video', () => {
  function openVideoTab() {
    render(<RoutineBuilder onSaved={vi.fn()} />)
    fireEvent.click(screen.getByRole('button', { name: 'From a video' }))
  }

  it('keeps submit disabled until a clip is chosen and consent is ticked', () => {
    openVideoTab()
    const submit = screen.getByRole('button', { name: 'Draft routine' }) as HTMLButtonElement
    const file = new File(['clip'], 'setup.mp4', { type: 'video/mp4' })

    expect(submit.disabled).toBe(true)

    fireEvent.change(screen.getByLabelText(/A clip of the routine/), { target: { files: [file] } })
    expect(submit.disabled).toBe(true)

    fireEvent.click(screen.getByLabelText(/sent once to Google Gemini/))
    expect(submit.disabled).toBe(false)
  })

  it('drafts a routine once a clip and consent are both given', async () => {
    openVideoTab()
    const file = new File(['clip'], 'setup.mp4', { type: 'video/mp4' })
    fireEvent.change(screen.getByLabelText(/A clip of the routine/), { target: { files: [file] } })
    fireEvent.click(screen.getByLabelText(/sent once to Google Gemini/))

    fireEvent.click(screen.getByRole('button', { name: 'Draft routine' }))

    await waitFor(() => expect(screen.getByText('Brush teeth')).toBeTruthy())
  })
})

describe('editing and saving the draft', () => {
  async function draftBrushTeeth(onSaved = vi.fn()) {
    render(<RoutineBuilder onSaved={onSaved} />)
    fireEvent.change(screen.getByLabelText('What happens, in order'), {
      target: { value: 'Brush my teeth every morning' },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Draft routine' }))
    await waitFor(() => expect(screen.getByText('Brush teeth')).toBeTruthy())
    return onSaved
  }

  it('renaming a step updates the task map preview live', async () => {
    await draftBrushTeeth()

    fireEvent.change(screen.getByDisplayValue('Get the toothbrush'), {
      target: { value: 'Pick up the toothbrush' },
    })

    expect(screen.queryByText('Get the toothbrush')).toBeNull()
    const steps = screen.getByRole('list', { name: 'Task steps' })
    expect(steps.textContent).toContain('Pick up the toothbrush')
  })

  it('deleting a step removes it from the task map preview', async () => {
    await draftBrushTeeth()

    fireEvent.click(screen.getByRole('button', { name: 'Delete Get the toothbrush' }))

    const steps = screen.getByRole('list', { name: 'Task steps' })
    expect(steps.textContent).not.toContain('Get the toothbrush')
  })

  it('saves the edited routine', async () => {
    const onSaved = await draftBrushTeeth()

    fireEvent.change(screen.getByDisplayValue('Get the toothbrush'), {
      target: { value: 'Pick up the toothbrush' },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Save routine' }))

    await waitFor(() => expect(onSaved).toHaveBeenCalledTimes(1))
    const saved = onSaved.mock.calls[0][0]
    expect(saved.title).toBe('Brush teeth')
    expect(saved.task_graph.steps[0].label).toBe('Pick up the toothbrush')
  })

  it('starting over returns to the tabs', async () => {
    await draftBrushTeeth()

    fireEvent.click(screen.getByRole('button', { name: 'Start over' }))

    expect(screen.getByLabelText('What happens, in order')).toBeTruthy()
    expect(screen.queryByText('Brush teeth')).toBeNull()
  })
})
