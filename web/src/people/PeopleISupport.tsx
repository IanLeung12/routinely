import { useId, useState } from 'react'
import { Button } from '../ui/Button.tsx'
import { EmptyState } from '../ui/EmptyState.tsx'
import { acceptInvite, currentSupervisor, unlink } from './api.ts'
import type { Person } from './types.ts'
import './people.css'

/** "People I support" (SPEC section 17): everyone who shared their routine with this
 * supervisor, plus the invite code box that adds another. One person or a whole unit
 * reads the same here; what changes is the home screen behind it, which the shell
 * picks (one person opens straight into their detail).
 *
 * Linking is mock-backed for now: codes and links live in the browser, not an account. */
export function PeopleISupport({
  people,
  initialCode,
  onOpen,
  onChange,
}: {
  people: Person[]
  /** An `?invite=` code from a link someone was sent, filled in ready to add. */
  initialCode?: string | null
  onOpen?: (personId: string) => void
  /** Called after a link is added or removed, so the shell re-reads who I support. */
  onChange?: () => void
}) {
  const [code, setCode] = useState(initialCode ?? '')
  const [added, setAdded] = useState<string | null>(null)
  const [failed, setFailed] = useState(false)
  const codeId = useId()

  function addPerson() {
    const person = acceptInvite(code)
    if (person === null) {
      setAdded(null)
      setFailed(true)
      return
    }
    setAdded(person.name)
    setFailed(false)
    setCode('')
    onChange?.()
  }

  function removePerson(person: Person) {
    unlink(person.id, currentSupervisor().id)
    setAdded(null)
    setFailed(false)
    onChange?.()
  }

  return (
    <div className="people">
      {people.length === 0 ? (
        <EmptyState message="Nobody has shared their routine with you yet. Ask them for their invite code." />
      ) : (
        <ul className="people-list">
          {people.map((person) => (
            <li key={person.id} className="people-list__row">
              <button
                type="button"
                className="people-list__open"
                aria-label={`Open ${person.name}, ${person.context}`}
                onClick={() => onOpen?.(person.id)}
              >
                <span className="people-list__name">{person.name}</span>
                <span className="people-list__context">{person.context}</span>
              </button>
              <Button
                aria-label={`Stop supporting ${person.name}`}
                onClick={() => removePerson(person)}
              >
                Stop supporting
              </Button>
            </li>
          ))}
        </ul>
      )}

      <form
        className="people__add"
        onSubmit={(event) => {
          event.preventDefault()
          addPerson()
        }}
      >
        <label className="people__add-label" htmlFor={codeId}>Invite code</label>
        <input
          id={codeId}
          className="people__add-input"
          value={code}
          placeholder="ABC123"
          autoComplete="off"
          onChange={(event) => setCode(event.target.value)}
        />
        <Button type="submit" variant="primary" disabled={code.trim() === ''}>Add person</Button>
      </form>
      <p className="people__hint">
        {'Ask the person you support for the code on their "Invite someone" screen.'}
      </p>
      {added !== null && (
        <p className="people__message" role="status">{`${added} shared their routine with you.`}</p>
      )}
      {failed && (
        <p className="people__message people__message--failed" role="alert">
          {"That code doesn't match an invite. Check it and try again."}
        </p>
      )}
    </div>
  )
}

export default PeopleISupport
