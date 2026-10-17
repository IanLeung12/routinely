import type { CSSProperties } from 'react'
import type { PatternMatch, PatternUrgency, SuggestedCheck } from '../contracts.ts'
import { SUGGESTED_CHECK_LABELS } from './SuggestedChecks.tsx'
import './PatternList.css'

function checkLabel(check: SuggestedCheck | string): string {
  return (SUGGESTED_CHECK_LABELS as Record<string, string>)[check] ?? check
}

const URGENCY_LABELS: Record<PatternUrgency, string> = {
  routine: 'Routine',
  next_round: 'Check next round',
  same_shift: 'Check this shift',
  urgent: 'Urgent',
}

/** Possible patterns a flagged change is consistent with, ranked (SPEC section 9,
 * screen 4): one card each, with the confidence as a number and a bar, the evidence
 * lines behind it and the checks that would rule it out. Never diagnostic: always
 * "consistent with", never "has". */
export function PatternList({ patterns }: { patterns: PatternMatch[] }) {
  if (patterns.length === 0) {
    return <p className="muted">Change detected, no clear pattern.</p>
  }

  return (
    <ul className="pattern-list" aria-label="Possible patterns">
      {patterns.map((pattern) => {
        const urgent = pattern.urgency === 'urgent'
        const confidencePct = Math.round(pattern.confidence * 100)
        return (
          <li
            key={pattern.pattern_id}
            className={`pattern${urgent ? ' pattern--urgent' : ''}`}
          >
            <div className="pattern__header">
              <h3 className="pattern__name">Consistent with: {pattern.name}</h3>
              <span className={`pattern__urgency pattern__urgency--${pattern.urgency}`}>
                {URGENCY_LABELS[pattern.urgency]}
              </span>
            </div>
            {/* The number carries the meaning; the bar only makes two patterns
                comparable at a glance, so it is hidden from screen readers. */}
            <div className="pattern__confidence-row">
              <p className="pattern__confidence">
                <span className="pattern__confidence-value tabular-nums">{confidencePct}%</span>{' '}
                confidence
              </p>
              <span className="pattern__meter" aria-hidden="true">
                <span
                  className="pattern__meter-fill"
                  style={{ '--confidence': pattern.confidence } as CSSProperties}
                />
              </span>
            </div>
            {pattern.evidence.length > 0 && (
              <ul className="pattern__evidence">
                {pattern.evidence.map((line, index) => (
                  <li key={index}>{line}</li>
                ))}
              </ul>
            )}
            {pattern.checks.length > 0 && (
              <>
                <p className="pattern__checks-label">Consider ruling out:</p>
                <ul className="pattern__checks">
                  {pattern.checks.map((check, index) => (
                    <li key={index}>{checkLabel(check)}</li>
                  ))}
                </ul>
              </>
            )}
          </li>
        )
      })}
    </ul>
  )
}

export default PatternList
