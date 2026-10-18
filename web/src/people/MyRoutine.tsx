import { lazy, Suspense, useState } from 'react'
import { LiveScreen } from '../live/LiveScreen.tsx'
import { PrivacyCard } from '../person/routine/PrivacyCard.tsx'
import { Button } from '../ui/Button.tsx'
import { Card } from '../ui/Card.tsx'
import { EmptyState } from '../ui/EmptyState.tsx'
import { Loading } from '../ui/Loading.tsx'
import { Row } from '../ui/Row.tsx'
import { SectionHeader } from '../ui/SectionHeader.tsx'
import { createInvite, currentPerson, supervisorsOf, unlink } from './api.ts'
import type { Invite, Relationship } from './types.ts'
import './people.css'
import '../person/routine/routine.css'

const RELATIONSHIP: Record<Relationship, string> = {
  family: 'Family',
  carer: 'Carer',
  nurse: 'Nurse',
}

/** Their week, their chart, their sessions and their notes, fetched when a person
 * opens their own screen: a supervisor's first paint is the unit dashboard and
 * shouldn't carry any of it (`web/scripts/check-bundle.mjs`, like App.tsx's
 * off-path screens). The shell below - who can see this, invites, privacy - is
 * eager, so the page has its heading and its off switch straight away. */
const RoutineSections = lazy(() =>
  import('../person/routine/RoutineSections.tsx').then((module) => ({
    default: module.RoutineSections,
  })),
)

/** The countdown ring and PIN pad only matter for the rare person with an active
 * check-in (T450), so they stay out of everyone else's first-load bundle. */
const CheckInCard = lazy(() =>
  import('../checkin/CheckInCard.tsx').then((module) => ({
    default: module.CheckInCard,
  })),
)

/** The person's home screen (SPEC section 17): their own routine and nobody else's.
 *
 * In SPEC's order, which is also the order the questions come in: how this week
 * looked in plain words, their usual against the week, the sessions behind it, a
 * note when something was different, who can see all of this, and the off switch.
 * The pieces live in `person/routine/`; this file is the page they sit on.
 *
 * Calm and plain on purpose. It says what looked different and who is worth
 * mentioning it to. It never says what a difference means. */
export function MyRoutine({
  onChange,
  onOpenAlert,
}: {
  onChange?: () => void
  onOpenAlert?: (alertId: string) => void
}) {
  const person = currentPerson()
  const [supervisors, setSupervisors] = useState(() => supervisorsOf(person.id))
  const [invite, setInvite] = useState<Invite | null>(null)
  const [copyStatus, setCopyStatus] = useState('')
  /** Bumped when a live session ends, so the week behind it refetches without a
   * page reload, the same way the overview's `refreshKey` works (App.tsx). */
  const [sessionRefreshKey, setSessionRefreshKey] = useState(0)
  /** Front-end only: there is no capture device to switch off behind this yet, so
   * pausing says so and stays in this tab (SPEC section 17, mock linking). */
  const [paused, setPaused] = useState(false)
  const supervisorNames = supervisors.map((supervisor) => supervisor.name)

  function removeSupervisor(supervisorId: string) {
    unlink(person.id, supervisorId)
    setSupervisors(supervisorsOf(person.id))
    onChange?.()
  }

  /** One tap to send the invite instead of reading six characters down the phone. */
  async function copyLink(link: string) {
    try {
      if (!navigator.clipboard?.writeText) {
        setCopyStatus('Copy not available')
        return
      }
      await navigator.clipboard.writeText(link)
      setCopyStatus('Link copied')
    } catch {
      setCopyStatus('Copy not available')
    }
  }

  return (
    <section className="my-routine" aria-labelledby="my-routine-heading">
      <h2 id="my-routine-heading">My routine</h2>
      <p className="my-routine__lead">
        Your own routine: how this week went, what looked different, and who can see
        it. Nothing is shared with anyone you have not added yourself.
      </p>

      <Suspense fallback={null}>
        <CheckInCard personId={person.id} />
      </Suspense>

      <Suspense fallback={<Loading label="Loading your week…" />}>
        <RoutineSections key={sessionRefreshKey} personId={person.id} supervisorNames={supervisorNames} />
      </Suspense>

      <Card>
        <SectionHeader title="Your session" />
        <p className="my-routine__session-lead">
          Start making tea when you're ready; only your skeleton is used.
        </p>
        <LiveScreen
          onOpenAlert={onOpenAlert}
          onSessionEnd={() => setSessionRefreshKey((key) => key + 1)}
        />
      </Card>

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
            <Button onClick={() => copyLink(invite.link)}>Copy link</Button>
            <p className="my-routine__copy-status" role="status">{copyStatus}</p>
          </>
        )}
      </Card>

      <PrivacyCard
        paused={paused}
        onTogglePause={() => setPaused((wasPaused) => !wasPaused)}
        supervisorNames={supervisorNames}
      />
    </section>
  )
}

export default MyRoutine
