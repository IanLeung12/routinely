export interface PatternView {
  pattern_id: string
  name: string
  confidence: number /* 0-1 */
  urgency: 'routine' | 'next_round' | 'same_shift' | 'urgent'
  evidence: string[]
  checks: string[]
}

const URGENCY_LABELS: Record<PatternView['urgency'], string> = {
  routine: 'Routine',
  next_round: 'Check next round',
  same_shift: 'Check this shift',
  urgent: 'Urgent',
}

/** Possible patterns a flagged change is consistent with, ranked (SPEC section 9,
 * screen 4). Never diagnostic: always "consistent with", never "has". */
export function PatternList({ patterns }: { patterns: PatternView[] }) {
  if (patterns.length === 0) {
    return <p className="muted">Change detected, no clear pattern.</p>
  }

  return (
    <ul className="pattern-list">
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
              <span className="pattern__confidence">{confidencePct}% confidence</span>
            </div>
            <span className={`pattern__urgency pattern__urgency--${pattern.urgency}`}>
              {URGENCY_LABELS[pattern.urgency]}
            </span>
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
                    <li key={index}>{check}</li>
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
