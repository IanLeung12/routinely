import { describe, expect, it } from 'vitest'
import { mockAlerts } from '../mock/alerts.ts'
import { alertText } from './alertText.ts'

describe('alertText', () => {
  it('reads the summary, errors, patterns and checks behind the mock alert', () => {
    const text = alertText(mockAlerts[0])

    expect(text).toContain('Change flagged for review')
    expect(text).toContain(mockAlerts[0].summary)
    expect(text).toContain('skipped teabag in cup at 0:42')
    expect(text).toContain('repeated pour at 1:15')
    expect(text).toContain('Consistent with: Sudden change')
    expect(text).toContain('Check for infection / UTI')
    expect(text).not.toMatch(/diagnos/i)
  })

  it('always says "consistent with" for patterns, never "has <pattern>"', () => {
    const text = alertText(mockAlerts[0])

    expect(text).toContain('Consistent with: Sudden change')
    expect(text).not.toMatch(/has sudden change/i)
  })

  it('includes each error\'s time', () => {
    const text = alertText(mockAlerts[0])

    for (const error of mockAlerts[0].errors) {
      const minutes = Math.floor(error.t_start / 60)
      const seconds = Math.floor(error.t_start % 60).toString().padStart(2, '0')
      expect(text).toContain(`${minutes}:${seconds}`)
    }
  })

  it('names the resident by the name it is given, not one guessed from the id', () => {
    const text = alertText(mockAlerts[0], 'Mrs. Kowalski')

    expect(text).toContain('Resident: Mrs. Kowalski')
    expect(text).not.toMatch(/Resident: mrs-k/)
  })

  it('falls back to the raw id when no resident name is given', () => {
    const text = alertText(mockAlerts[0])

    expect(text).toContain(`Resident: ${mockAlerts[0].resident_id}`)
  })

  it('works with zero patterns', () => {
    const noPatterns = { ...mockAlerts[0], patterns: [] }
    const text = alertText(noPatterns)

    expect(text).not.toContain('Consistent with:')
    expect(text).toContain('Change flagged for review')
  })
})
