import { useId, useState } from 'react'
import { Button } from '../ui/Button.tsx'
import { Card } from '../ui/Card.tsx'
import { EmptyState } from '../ui/EmptyState.tsx'
import { SectionHeader } from '../ui/SectionHeader.tsx'
import './replayNotes.css'

/** A short note a supervisor leaves on a replay. Local state only (T431): the
 * person sees exactly the same notes their supervisors do (SPEC section 17), so
 * there is no author-only view to build. */
export type ReplayNote = { id: string; author: string; at: string; text: string }

/** 'HH:MM' in the reader's own clock, matching how `Handoff.tsx` reads a timestamp
 * a person on this shift wrote, not a pipeline one (T281). */
function formatTime(at: string): string {
  const date = new Date(at)
  const hours = String(date.getHours()).padStart(2, '0')
  const minutes = String(date.getMinutes()).padStart(2, '0')
  return `${hours}:${minutes}`
}

/** Notes on a replay, oldest first, with who left them and when. When `canAdd`
 * (a supervisor viewing it, SPEC section 17), a labelled textarea and an "Add
 * note" button let them leave another; the person viewing the same replay sees
 * only the list, never the form. `onAdd` owns storing the note - this component
 * only builds it, from `author` and `now` (defaulting to the real clock, overridable
 * in tests). */
export function ReplayNotes({
  notes,
  canAdd,
  author,
  onAdd,
  now = () => new Date(),
}: {
  notes: ReplayNote[]
  canAdd: boolean
  author: string
  onAdd: (note: ReplayNote) => void
  now?: () => Date
}) {
  const [text, setText] = useState('')
  const textareaId = useId()
  const ordered = [...notes].sort((a, b) => a.at.localeCompare(b.at))

  function addNote() {
    const trimmed = text.trim()
    if (!trimmed) return
    onAdd({ id: crypto.randomUUID(), author, at: now().toISOString(), text: trimmed })
    setText('')
  }

  return (
    <Card className="replay-notes">
      <SectionHeader title="Notes" />
      {ordered.length === 0 ? (
        <EmptyState message="No notes yet." />
      ) : (
        <ul className="replay-notes__list">
          {ordered.map((note) => (
            <li key={note.id} className="replay-notes__item">
              <span className="replay-notes__meta">
                {note.author} · {formatTime(note.at)}
              </span>
              <p className="replay-notes__text">{note.text}</p>
            </li>
          ))}
        </ul>
      )}
      {canAdd ? (
        <form
          className="replay-notes__form"
          onSubmit={(event) => {
            event.preventDefault()
            addNote()
          }}
        >
          <label className="replay-notes__label" htmlFor={textareaId}>
            Add a note
          </label>
          <textarea
            id={textareaId}
            className="replay-notes__input"
            value={text}
            onChange={(event) => setText(event.target.value)}
          />
          <Button type="submit" variant="primary" disabled={text.trim() === ''}>
            Add note
          </Button>
        </form>
      ) : null}
    </Card>
  )
}

export default ReplayNotes
