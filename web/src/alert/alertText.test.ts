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
})
