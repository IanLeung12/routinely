import { useEffect, useState } from 'react'
import type { PatternUrgency, SuggestedCheck } from '../contracts.ts'
import { SUGGESTED_CHECK_LABELS } from '../alert/SuggestedChecks.tsx'
import { Button } from '../ui/Button.tsx'
import { EmptyState } from '../ui/EmptyState.tsx'
import { ErrorState } from '../ui/ErrorState.tsx'
import { Loading } from '../ui/Loading.tsx'
import { fetchPatterns } from './api.ts'
import type { PatternLibraryEntry } from './types.ts'
import './PatternLibrary.css'
import './urgencyFilter.css'

const URGENCY_LABELS: Record<PatternUrgency, string> = {
  routine: 'Routine',
  next_round: 'Check next round',
  same_shift: 'Check this shift',
  urgent: 'Urgent',
}

type UrgencyFilter = 'all' | PatternUrgency

const URGENCY_FILTERS: { id: UrgencyFilter; label: string }[] = [
  { id: 'all', label: 'All' },
  { id: 'urgent', label: URGENCY_LABELS.urgent },
  { id: 'same_shift', label: URGENCY_LABELS.same_shift },
  { id: 'next_round', label: URGENCY_LABELS.next_round },
  { id: 'routine', label: URGENCY_LABELS.routine },
]

function checkLabel(check: SuggestedCheck | string): string {
  return (SUGGESTED_CHECK_LABELS as Record<string, string>)[check] ?? check
}

function signalLabel(signal: string): string {
  return signal.replace(/_/g, ' ')
}

function timeProfileLabel(entry: PatternLibraryEntry): string {
  return entry.time_profile.note
}

/** Read-only library of every pattern the pipeline can flag a change as consistent
 * with (SPEC §7.5): what it looks for, how long it takes to show up, what to rule
 * out and where it comes from. Separate from the demo path, so a judge can see the
 * whole cited rules library, not a model guess, without touching live data. */
export function PatternLibrary({ onBack }: { onBack: () => void }) {
  const [patterns, setPatterns] = useState<PatternLibraryEntry[] | null>(null)
  const [filter, setFilter] = useState<UrgencyFilter>('all')

  useEffect(() => {
    let cancelled = false
    fetchPatterns().then((result) => {
      if (!cancelled) setPatterns(result)
    })
    return () => {
      cancelled = true
    }
  }, [])

  let body
  let filterBar
  if (patterns === null) {
    body = <Loading label="Loading pattern library…" />
  } else if (patterns.length === 0) {
    body = <ErrorState message="No patterns in the library." />
  } else {
    filterBar = (
      <div className="urgency-filter" role="group" aria-label="Filter by urgency">
        {URGENCY_FILTERS.map(({ id, label }) => (
          <Button
            key={id}
            variant="secondary"
            className="urgency-filter__button"
            aria-pressed={filter === id}
            onClick={() => setFilter(id)}
          >
            {label}
          </Button>
        ))}
      </div>
    )

    const filtered = filter === 'all' ? patterns : patterns.filter((entry) => entry.urgency === filter)

    body = filtered.length === 0 ? (
      <EmptyState message="No patterns at this level." />
    ) : (
      <ul className="pattern-library__list" aria-label="Pattern library">
        {filtered.map((entry) => {
          const urgent = entry.urgency === 'urgent'
          return (
            <li
              key={entry.pattern_id}
              className={`pattern-library__entry${urgent ? ' pattern-library__entry--urgent' : ''}`}
            >
              <div className="pattern-library__header">
                <h3 className="pattern-library__name">{entry.name}</h3>
                <span
                  className={`pattern-library__urgency pattern-library__urgency--${entry.urgency}`}
                >
                  {URGENCY_LABELS[entry.urgency]}
                </span>
              </div>

              <p className="pattern-library__time-profile">{timeProfileLabel(entry)}</p>

              <p className="pattern-library__section-label">Signals it looks for</p>
              <ul className="pattern-library__signals">
                {Object.entries(entry.signals).map(([signal, weight]) => (
                  <li key={signal}>
                    {signalLabel(signal)} <span className="muted">(weight {weight})</span>
                  </li>
                ))}
              </ul>

              <p className="pattern-library__section-label">Consider ruling out</p>
              <ul className="pattern-library__checks">
                {entry.checks.map((check, index) => (
                  <li key={index}>{checkLabel(check)}</li>
                ))}
              </ul>

              <p className="pattern-library__source">Source: {entry.source}</p>
            </li>
          )
        })}
      </ul>
    )
  }

  return (
    <section className="pattern-library" aria-label="Pattern library">
      <button type="button" className="back-button" onClick={onBack}>
        ← Back
      </button>
      <h2 className="pattern-library__title">Pattern library</h2>
      <p className="pattern-library__lead">
        What each pattern a flagged change can be consistent with looks for, and where it
        comes from. Reference only - never a verdict on a specific resident.
      </p>
      {filterBar}
      {body}
    </section>
  )
}

export default PatternLibrary
