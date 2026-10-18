import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { ReplayNotes, type ReplayNote } from './ReplayNotes.tsx'

afterEach(cleanup)

const NOTES: ReplayNote[] = [
  { id: 'n2', author: 'Sam', at: '2026-01-05T21:40:00.000Z', text: 'Took longer brushing teeth' },
  { id: 'n1', author: 'Priya', at: '2026-01-05T13:05:00.000Z', text: 'Skipped the kettle step' },
]

describe('ReplayNotes', () => {
  it('lists notes oldest first with author and time', () => {
    render(<ReplayNotes notes={NOTES} canAdd={false} author="Sam" onAdd={vi.fn()} />)

    const items = screen.getAllByText(/·/).map((el) => el.textContent)
    expect(items).toEqual(['Priya · 13:05', 'Sam · 21:40'])
    expect(screen.getByText('Skipped the kettle step')).toBeTruthy()
    expect(screen.getByText('Took longer brushing teeth')).toBeTruthy()
  })

  it('says so when there are no notes', () => {
    render(<ReplayNotes notes={[]} canAdd={false} author="Sam" onAdd={vi.fn()} />)

    expect(screen.getByText('No notes yet.')).toBeTruthy()
  })

  it('hides the add form when canAdd is false', () => {
    render(<ReplayNotes notes={[]} canAdd={false} author="Sam" onAdd={vi.fn()} />)

    expect(screen.queryByLabelText('Add a note')).toBeNull()
    expect(screen.queryByRole('button', { name: 'Add note' })).toBeNull()
  })

  it('disables the button on blank or whitespace-only input', () => {
    render(<ReplayNotes notes={[]} canAdd author="Sam" onAdd={vi.fn()} />)
    const button = screen.getByRole('button', { name: 'Add note' }) as HTMLButtonElement
    const textarea = screen.getByLabelText('Add a note')

    expect(button.disabled).toBe(true)

    fireEvent.change(textarea, { target: { value: '   ' } })
    expect(button.disabled).toBe(true)

    fireEvent.change(textarea, { target: { value: 'Looked steadier today' } })
    expect(button.disabled).toBe(false)
  })

  it('adds a trimmed note under the given author and clears the input', () => {
    const onAdd = vi.fn()
    const now = () => new Date('2026-01-06T17:22:00.000Z')
    render(<ReplayNotes notes={[]} canAdd author="Priya" onAdd={onAdd} now={now} />)
    const textarea = screen.getByLabelText('Add a note') as HTMLTextAreaElement

    fireEvent.change(textarea, { target: { value: '  Paused twice near the stove  ' } })
    fireEvent.click(screen.getByRole('button', { name: 'Add note' }))

    expect(onAdd).toHaveBeenCalledTimes(1)
    const note = onAdd.mock.calls[0][0] as ReplayNote
    expect(note.author).toBe('Priya')
    expect(note.text).toBe('Paused twice near the stove')
    expect(note.at).toBe('2026-01-06T17:22:00.000Z')
    expect(note.id).toBeTruthy()
    expect(textarea.value).toBe('')
  })

  it('does not add a note for whitespace-only input', () => {
    const onAdd = vi.fn()
    render(<ReplayNotes notes={[]} canAdd author="Sam" onAdd={onAdd} />)
    const textarea = screen.getByLabelText('Add a note')

    fireEvent.change(textarea, { target: { value: '   ' } })
    fireEvent.click(screen.getByRole('button', { name: 'Add note' }))

    expect(onAdd).not.toHaveBeenCalled()
  })
})
