import { useEffect, useRef, useState } from 'react'
import { Button } from '../ui/Button.tsx'
import { Card } from '../ui/Card.tsx'
import { activeCheckIn, respondToCheckIn } from './api.ts'
import { PinPad } from './PinPad.tsx'
import type { CheckIn } from './types.ts'
import './checkin.css'

type Stage = 'prompt' | 'pin' | 'thanks'

function secondsLeft(deadline: string): number {
  return Math.max(0, Math.round((new Date(deadline).getTime() - Date.now()) / 1000))
}

function formatCountdown(seconds: number): string {
  const minutes = Math.floor(seconds / 60)
  const remainder = seconds % 60
  return `${minutes}:${remainder.toString().padStart(2, '0')}`
}

/** A calm full-width card for an active check-in (SPEC section 18, T451): a
 * countdown ring, one big "I'm okay" button, and the PIN pad it opens. Whichever
 * PIN matched - safety or duress - `respondToCheckIn` answers the same `accepted`
 * either way (T450), so this component is never told which one it was and the
 * "Thanks" screen below can't help but render identically for both.
 *
 * Fetches its own check-in and renders nothing when there isn't one, the way
 * `person/routine/RoutineSections.tsx` owns its own data: `MyRoutine.tsx` only
 * ever renders this behind `lazy()`, so nobody's first paint carries the fetch,
 * the PIN pad or the ring unless a check-in is actually active. */
export function CheckInCard({ personId }: { personId: string }) {
  const [checkIn, setCheckIn] = useState<CheckIn | null>(null)
  const [stage, setStage] = useState<Stage>('prompt')
  const [error, setError] = useState('')
  const [remaining, setRemaining] = useState(0)
  const [total, setTotal] = useState(1)
  const panelRef = useRef<HTMLDivElement>(null)
  const focusedRef = useRef(false)

  useEffect(() => {
    let cancelled = false
    activeCheckIn(personId).then((result) => {
      if (cancelled) return
      if (result) {
        const seconds = secondsLeft(result.deadline)
        setTotal(Math.max(1, seconds))
        setRemaining(seconds)
      }
      setCheckIn(result)
    })
    return () => {
      cancelled = true
    }
  }, [personId])

  useEffect(() => {
    if (checkIn && !focusedRef.current) {
      focusedRef.current = true
      panelRef.current?.focus()
    }
  }, [checkIn])

  // The countdown is cosmetic here (T450's server owns the real deadline); once
  // checked in there is nothing left to count down to, so the tick stops.
  useEffect(() => {
    if (!checkIn || stage === 'thanks') return
    const interval = window.setInterval(() => setRemaining(secondsLeft(checkIn.deadline)), 1000)
    return () => window.clearInterval(interval)
  }, [checkIn, stage])

  async function handlePin(pin: string) {
    if (!checkIn) return
    const response = await respondToCheckIn(checkIn.id, pin)
    if (response.accepted) {
      setError('')
      setStage('thanks')
    } else {
      setError('Try again')
    }
  }

  if (!checkIn) return null

  if (stage === 'thanks') {
    return (
      <Card className="check-in-card check-in-card--thanks">
        <div ref={panelRef} tabIndex={-1} role="region" aria-label="Check-in" aria-live="polite">
          <h2 className="check-in-card__heading">Thanks, you're checked in</h2>
          <p className="check-in-card__lead">That's everything - nothing else to do.</p>
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
      <div ref={panelRef} tabIndex={-1} role="region" aria-label="Check-in">
        <h2 className="check-in-card__heading">Quick check-in: are you okay?</h2>
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
