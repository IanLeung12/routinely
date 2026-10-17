import { useState } from 'react'
import { Button } from '../ui/Button.tsx'
import { Card } from '../ui/Card.tsx'
import { EmptyState } from '../ui/EmptyState.tsx'
import { Row } from '../ui/Row.tsx'
import { SectionHeader } from '../ui/SectionHeader.tsx'
import { createInvite, currentPerson, supervisorsOf, unlink } from './api.ts'
import type { Invite, Relationship } from './types.ts'
import './people.css'

const RELATIONSHIP: Record<Relationship, string> = {
  family: 'Family',
  carer: 'Carer',
  nurse: 'Nurse',
}

/** The person's home screen (SPEC section 17). A placeholder until T409 fills it with
 * their status in plain words, their usual week against today, recent sessions and the
 * notes behind a change: what is here is the part the linking API already answers, so
 * someone can invite a supervisor and take them off again.
 *
 * Calm and plain on purpose. Never alarming, never a conclusion about health. */
export function MyRoutine({ onChange }: { onChange?: () => void }) {
  const person = currentPerson()
  const [supervisors, setSupervisors] = useState(() => supervisorsOf(person.id))
  const [invite, setInvite] = useState<Invite | null>(null)

  function removeSupervisor(supervisorId: string) {
    unlink(person.id, supervisorId)
    setSupervisors(supervisorsOf(person.id))
    onChange?.()
  }

  return (
    <section className="my-routine" aria-labelledby="my-routine-heading">
      <h2 id="my-routine-heading">My routine</h2>
      <p className="my-routine__lead">
        Your usual week, how today went and a gentle note when something looked different
        all land here. Nothing is shared with anyone you have not added yourself.
      </p>

      <Card>
        <SectionHeader title="Who can see this" />
        {supervisors.length === 0 ? (
          <EmptyState message="Nobody else can see this. You are watching your own routine." />
        ) : (
          <ul className="people-list">
            {supervisors.map((supervisor) => (
              <li key={supervisor.id}>
                <Row
                  title={supervisor.name}
                  subtitle={`${RELATIONSHIP[supervisor.relationship]} · ${supervisor.context}`}
                  trailing={
                    <Button
                      aria-label={`Remove ${supervisor.name}`}
                      onClick={() => removeSupervisor(supervisor.id)}
                    >
                      Remove
                    </Button>
                  }
                />
              </li>
            ))}
          </ul>
        )}
      </Card>

      <Card>
        <SectionHeader title="Invite someone" />
        {invite === null ? (
          <>
            <p className="my-routine__invite-lead">
              Give someone a code and they can see the same routine you see. You can take
              it back at any time.
            </p>
            <Button variant="primary" onClick={() => setInvite(createInvite(person.id))}>
              Invite someone
            </Button>
          </>
        ) : (
          <>
            <p className="my-routine__invite-lead">
              {`They choose "I'm supporting someone" and type this code:`}
            </p>
            <p className="my-routine__code">{invite.code}</p>
            <p className="my-routine__link">
              Or send them this link: <span className="my-routine__link-url">{invite.link}</span>
            </p>
          </>
        )}
      </Card>
    </section>
  )
}

export default MyRoutine
