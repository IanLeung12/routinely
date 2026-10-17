import { describe, expect, it } from 'vitest'
import { formatDay, formatDayTime, formatDuration, formatErrors, formatScore, utcDate } from './format.ts'

describe('resident formatting', () => {
  it('gets UTC dates across offset and year boundaries', () => {
    expect(utcDate('2026-01-01T00:30:00+02:00')).toBe('2025-12-31')
    expect(utcDate('2026-12-31T23:30:00-02:00')).toBe('2027-01-01')
  })

  it.each(['not-a-date', ''])('handles invalid timestamps: %j', timestamp => {
    expect(utcDate(timestamp)).toBeNull()
    expect(formatDay(timestamp)).toBe(timestamp)
    expect(formatDayTime(timestamp)).toBe(timestamp)
  })

  it('formats days using UTC and unpadded day numbers', () => {
    expect(formatDay('2026-01-01T23:00:00-02:00')).toBe('2 Jan')
    expect(formatDay('2024-02-29T12:00:00Z')).toBe('29 Feb')
  })

  it('pads UTC hours and minutes', () => {
    expect(formatDayTime('2026-01-01T08:02:59Z')).toBe('1 Jan, 08:02')
    expect(formatDayTime('2026-01-01T23:30:00-02:00')).toBe('2 Jan, 01:30')
  })

  it.each([[0, '0m 00s'], [226, '3m 46s'], [59.6, '1m 00s'], [60.4, '1m 00s'], [3600, '60m 00s']])(
    'formats duration %s seconds as %s', (seconds, expected) => {
      expect(formatDuration(Number(seconds))).toBe(expected)
    },
  )

  it.each([[0, '0.0'], [4, '4.0'], [4.56, '4.6'], [0.04, '0.0']])(
    'formats score %s to one decimal', (score, expected) => {
      expect(formatScore(Number(score))).toBe(expected)
    },
  )

  it('formats every error type in supplied order', () => {
    expect(formatErrors({
      omission: 1, sequence: 2, perseveration: 3,
      substitution: 4, hesitation: 5, abandonment: 6,
    })).toBe('skipped step ×1 · out of order ×2 · repeated step ×3 · wrong object ×4 · long pause ×5 · stopped partway ×6')
  })

  it('omits nonpositive and absent errors', () => {
    expect(formatErrors({})).toBe('')
    expect(formatErrors({ omission: 0, sequence: -1, hesitation: undefined })).toBe('')
    expect(formatErrors({ omission: 0, perseveration: 2 })).toBe('repeated step ×2')
  })
})
