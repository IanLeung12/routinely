import { useState } from 'react'
import type { PatternMatch } from '../../contracts.ts'
import { Button } from '../../ui/Button.tsx'
import { Card } from '../../ui/Card.tsx'
import { SectionHeader } from '../../ui/SectionHeader.tsx'
import { personNote } from '../personNotes.ts'
import { joinWords } from './sessionWords.ts'
import './routine.css'

/** The notes behind a flagged change, written for the person whose routine it is
 * (SPEC section 17): the same patterns their supervisors see, rephrased by
 * `person/personNotes.ts` as what looked different and who is worth mentioning it
 * to. No confidence, no ranking, nothing to rule out - that is the supervisor's
 * screen, and this one is a nudge, not a verdict.
 *
 * "Tell my supervisor" is a mock: there is no messaging backend yet (SPEC section
 * 17, mock linking), so it confirms on the spot and calls `onTell`. */
export function RoutineNotes({
  patterns,
  supervisorNames,
  onTell,
}: {
  patterns: PatternMatch[]
  supervisorNames: string[]
  onTell?: (patternId: string) => void
}) {
  const [told, setTold] = useState<string[]>([])
  const [shared, setShared] = useState('')

  if (patterns.length === 0) return null

  const names = joinWords(supervisorNames)
  const verb = supervisorNames.length === 1 ? 'sees' : 'see'

  function tell(patternId: string) {
    setTold((ids) => (ids.includes(patternId) ? ids : [...ids, patternId]))
    setShared(`Shared with ${names}.`)
    onTell?.(patternId)
  }

  return (
    <Card>
      <SectionHeader title="Worth a mention" caption="What looked different this week" />
      {supervisorNames.length === 0 && (
        <p className="routine-note__alone">
          Nobody else can see your routine yet. You can invite someone further down
          this page, or bring this up at your next appointment.
        </p>
      )}
      <ul className="routine-notes">
        {patterns.map((pattern) => {
          const note = personNote(pattern, supervisorNames[0])
          return (
            <li key={pattern.pattern_id} className="routine-note">
              <h4 className="routine-note__title">{note.title}</h4>
              <p className="routine-note__body">{note.body}</p>
              {supervisorNames.length > 0 && (
                told.includes(pattern.pattern_id) ? (
                  <p className="routine-note__told">
                    {`${names} ${verb} this the next time they open Routinely.`}
                  </p>
                ) : (
                  <Button
                    variant="primary"
                    className="routine-note__tell"
                    onClick={() => tell(pattern.pattern_id)}
                  >
                    {supervisorNames.length === 1 ? `Tell ${names}` : 'Tell my supervisors'}
                  </Button>
                )
              )}
            </li>
          )
        })}
      </ul>
      <p className="routine-note__shared" role="status">{shared}</p>
    </Card>
  )
}

export default RoutineNotes
