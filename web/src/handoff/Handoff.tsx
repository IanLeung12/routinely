import { useEffect, useState } from 'react'
import type { ReactNode } from 'react'
import { Card } from '../ui/Card.tsx'
import { EmptyState } from '../ui/EmptyState.tsx'
import { ErrorState } from '../ui/ErrorState.tsx'
import { Loading } from '../ui/Loading.tsx'
import { SectionHeader } from '../ui/SectionHeader.tsx'
import { fetchHandoff } from './api.ts'
import type { HandoffResult } from './api.ts'
import type { HandoffResident } from './types.ts'
import './handoff.css'

/** Windows a nurse picks between: an eight or twelve hour shift, a day, a weekend. */
const WINDOWS = [8, 12, 24, 48]

/** A shift, and what `GET /handoff` defaults to. */
const DEFAULT_WINDOW_H = 12

type Chip = {
  key: string
  label: string
  /** `handoff__chip--` modifier: carries the colour, never the meaning. */
  tone: 'flagged' | 'pending' | 'trending' | 'quiet'
  /** Decorative, so the row is scannable without reading; the label says it in words. */
  glyph: string
}

function plural(n: number, noun: string): string {
  return n === 1 ? `${n} ${noun}` : `${n} ${noun}s`
}

function needsReview(resident: HandoffResident): boolean {
  return resident.flags > 0 || resident.pending_review > 0 || resident.trending
}

/** What this resident did with the window, in words. Never empty: a quiet resident
 * says so, so an untouched row can't be mistaken for a row that failed to load. */
function chipsFor(resident: HandoffResident): Chip[] {
  const chips: Chip[] = []
  if (resident.flags > 0) {
    chips.push({
      key: 'flags',
      label: `${plural(resident.flags, 'session')} above baseline`,
      tone: 'flagged',
      glyph: '!',
    })
  }
  if (resident.pending_review > 0) {
    chips.push({
      key: 'pending',
      label: `${plural(resident.pending_review, 'alert')} not reviewed yet`,
      tone: 'pending',
      glyph: '⧗',
    })
  }
  if (resident.trending) {
    chips.push({ key: 'trending', label: 'Error score trending up', tone: 'trending', glyph: '↗' })
  }
  if (chips.length === 0) {
    chips.push({ key: 'quiet', label: 'No change flagged', tone: 'quiet', glyph: '✓' })
  }
  return chips
}

/** The one line a nurse reads first, before any row. */
function headline(residents: HandoffResident[], hours: number): string {
  if (residents.length === 0) return `Nothing to hand over for the last ${hours} hours`
  const review = residents.filter(needsReview).length
  if (review === 0) return `No change flagged for review in the last ${hours} hours`
  return `${review} of ${plural(residents.length, 'resident')} to review in the last ${hours} hours`
}

/** Shift handoff: one view of who changed in the hours this nurse was away, off the
 * main demo path. Rows needing attention come first (the pipeline sorts them), each
 * labelled in words as well as colour, with the plain-language summary above them. */
export function Handoff({ onBack }: { onBack: () => void }) {
  const [hours, setHours] = useState(DEFAULT_WINDOW_H)
  /** Tagged with the window it was fetched for, so switching windows shows the new
   * one loading rather than the last one's rows. */
  const [loaded, setLoaded] = useState<{ hours: number; result: HandoffResult } | null>(null)

  useEffect(() => {
    let cancelled = false
    fetchHandoff(hours).then((result) => {
      if (!cancelled) setLoaded({ hours, result })
    })
    return () => {
      cancelled = true
    }
  }, [hours])

  let body: ReactNode
  if (loaded === null || loaded.hours !== hours) {
    body = <Loading label="Loading handoff…" />
  } else {
    const { handoff, offline } = loaded.result
    body = (
      <>
        {offline && (
          <ErrorState message="Offline: showing demo data, not this unit's last shift." />
        )}
        <p className="handoff__headline" role="status">
          {headline(handoff.residents, handoff.window_hours)}
        </p>
        <Card>
          <SectionHeader title={`Last ${handoff.window_hours} hours`} />
          <p className="handoff__summary">{handoff.summary}</p>
        </Card>
        {handoff.residents.length === 0 ? (
          <EmptyState message="No residents on this unit yet." />
        ) : (
          <ul className="handoff__list">
            {handoff.residents.map((resident) => (
              <li
                key={resident.resident_id}
                className={`handoff__row${needsReview(resident) ? ' handoff__row--review' : ''}`}
              >
                <span className="handoff__name">{resident.name}</span>
                <span className="handoff__chips">
                  {chipsFor(resident).map((chip) => (
                    <span key={chip.key} className={`handoff__chip handoff__chip--${chip.tone}`}>
                      <span aria-hidden="true" className="handoff__glyph">
                        {chip.glyph}
                      </span>
                      {chip.label}
                    </span>
                  ))}
                </span>
              </li>
            ))}
          </ul>
        )}
      </>
    )
  }

  return (
    <section className="handoff" aria-label="Shift handoff">
      <button type="button" className="back-button" onClick={onBack}>
        ← Back
      </button>
      <h2 className="handoff__title">Shift handoff</h2>
      <p className="handoff__lead">
        Who changed while you were away. Everything here is flagged for a nurse to review.
      </p>
      <div className="handoff__controls">
        <label className="handoff__label" htmlFor="handoff-window">
          Window
        </label>
        <select
          id="handoff-window"
          className="handoff__select"
          value={hours}
          onChange={(event) => setHours(Number(event.target.value))}
        >
          {WINDOWS.map((choice) => (
            <option key={choice} value={choice}>
              Last {choice} hours
            </option>
          ))}
        </select>
      </div>
      {body}
    </section>
  )
}

export default Handoff
