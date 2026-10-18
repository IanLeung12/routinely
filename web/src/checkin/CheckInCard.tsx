import { useEffect, useState } from 'react'
import { Button } from '../ui/Button.tsx'
import { Card } from '../ui/Card.tsx'
import { fetchMyCheckin, respondToCheckin } from './api.ts'
import { PinPad } from './PinPad.tsx'
import type { PersonCheckIn } from './types.ts'
import './checkin.css'

type Stage = 'prompt' | 'pin' | 'thanks' | 'closed'

/** How often to look for a check-in that started after this screen opened.
 * Short enough that the question is on screen well inside the shortest window
 * worth answering, long enough not to be a second-by-second poll on a screen
 * the person may leave open all day. */
const ASK_POLL_MS = 1500

function formatCountdown(seconds: number): string {
  const whole = Math.max(0, Math.round(seconds))
  const minutes = Math.floor(whole / 60)
  const remainder = whole % 60
  return `${minutes}:${remainder.toString().padStart(2, '0')}`
}

/** Focuses the panel the moment it mounts - a callback ref fires during React's
 * commit, synchronously, unlike a `useEffect` keyed on async-fetched state, which
 * races the fetch's own promise microtask under a loaded CI runner. */
function focusOnMount(node: HTMLDivElement | null): void {
  node?.focus()
}

/** A calm full-width card for an active check-in (SPEC section 18, T451): a
 * countdown ring, one big "I'm okay" button, and the PIN pad it opens. Whichever
 * PIN matched - safety or duress - `respondToCheckin` answers the same `accepted`
 * either way (T450's `/respond`), so this component is never told which one it
 * was and the "Thanks" screen below can't help but render identically for both.
 *
 * Fetches its own check-in - and keeps looking for one, see below - rendering
 * nothing until there is one to answer, the way `person/routine/RoutineSections.tsx`
 * owns its own data: `MyRoutine.tsx` only ever renders this behind `lazy()`, so
 * nobody's first paint carries the fetch, the PIN pad or the ring unless a
 * check-in is actually active. The question itself (`ask`) comes from the server,
 * so this never hardcodes wording the backend might phrase differently for a
 * person than for a supporter. */
export function CheckInCard({ personId }: { personId: string }) {
  const [checkIn, setCheckIn] = useState<PersonCheckIn | null>(null)
  const [stage, setStage] = useState<Stage>('prompt')
  const [error, setError] = useState('')
  const [remaining, setRemaining] = useState(0)
  const [total, setTotal] = useState(1)

  /** Keeps asking until there is a question to show (T465). Since T461 the live
   * session runs on this very screen, so the SPEC section 18 story - session
   * flagged, person asked to check in - starts while this card is already
   * mounted; a single fetch on mount meant the person only ever saw the question
   * after a reload, by which time the window had run out and their supporters
   * were alarmed. Same shape as the supporter's `AlarmBanner`, except the asking
   * stops the moment a check-in arrives: from then on the card is theirs to
   * answer, the countdown below owns the clock, and no late response can shuffle
   * the question out from under the PIN pad. */
  useEffect(() => {
    let cancelled = false
    let timer: number | undefined
    async function look() {
      let found: PersonCheckIn | null = null
      try {
        found = await fetchMyCheckin(personId)
      } catch {
        // A look that failed is not an answer: keep asking rather than go quiet.
      }
      if (cancelled) return
      if (found) {
        if (found.seconds_left !== null) {
          setTotal(Math.max(1, found.seconds_left))
          setRemaining(found.seconds_left)
        }
        setCheckIn(found)
        return
      }
      timer = window.setTimeout(look, ASK_POLL_MS)
    }
    void look()
    return () => {
      cancelled = true
      window.clearTimeout(timer)
    }
  }, [personId])

  // The countdown is cosmetic here (T450's server owns the real deadline); once
  // checked in there is nothing left to count down to, so the tick stops.
  useEffect(() => {
    if (!checkIn || stage === 'thanks') return
    const interval = window.setInterval(() => setRemaining((seconds) => Math.max(0, seconds - 1)), 1000)
    return () => window.clearInterval(interval)
  }, [checkIn, stage])

  async function handlePin(pin: string) {
    if (!checkIn) return
    try {
      const response = await respondToCheckin(checkIn.checkin_id, pin)
      if (response.accepted) {
        setError('')
        setStage('thanks')
      } else {
        setError('Try again')
      }
    } catch {
      setStage('closed')
    }
  }

  if (!checkIn) return null

  if (stage === 'thanks') {
    return (
      <Card className="check-in-card check-in-card--thanks">
        <div ref={focusOnMount} tabIndex={-1} role="region" aria-label="Check-in" aria-live="polite">
          <h2 className="check-in-card__heading">Thanks, you're checked in</h2>
          <p className="check-in-card__lead">That's everything - nothing else to do.</p>
        </div>
      </Card>
    )
  }

  if (stage === 'closed') {
    return (
      <Card className="check-in-card check-in-card--thanks">
        <div ref={focusOnMount} tabIndex={-1} role="region" aria-label="Check-in" aria-live="polite">
          <h2 className="check-in-card__heading">This check-in has already gone to your supporters</h2>
          <p className="check-in-card__lead">They'll be in touch.</p>
        </div>
      </Card>
    )
  }

  const fraction = Math.min(1, Math.max(0, remaining / total))
  const radius = 54
  const circumference = 2 * Math.PI * radius
  const dashOffset = circumference * (1 - fraction)

  return (
    <Card className="check-in-card">
      <div ref={focusOnMount} tabIndex={-1} role="region" aria-label="Check-in">
        <h2 className="check-in-card__heading">{checkIn.ask}</h2>
        <div className="check-in-card__ring">
          <svg className="check-in-card__ring-svg" viewBox="0 0 120 120" aria-hidden="true">
            <circle className="check-in-card__ring-track" cx="60" cy="60" r={radius} />
            <circle
              className="check-in-card__ring-progress"
              cx="60"
              cy="60"
              r={radius}
              strokeDasharray={circumference}
              strokeDashoffset={dashOffset}
            />
          </svg>
          <p className="check-in-card__ring-time">{formatCountdown(remaining)}</p>
        </div>

        {stage === 'prompt' && (
          <Button variant="primary" className="check-in-card__okay" onClick={() => setStage('pin')}>
            I'm okay
          </Button>
        )}

        {stage === 'pin' && (
          <>
            <p className="check-in-card__pin-lead">Enter your PIN to confirm.</p>
            <PinPad length={4} onSubmit={handlePin} error={error} />
          </>
        )}
      </div>
    </Card>
  )
}

export default CheckInCard
