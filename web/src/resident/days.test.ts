import { describe, expect, it } from 'vitest'
import { dailyScores } from './days.ts'

describe('dailyScores', () => {
  it('returns no days for empty input or entirely invalid timestamps', () => {
    expect(dailyScores([])).toEqual([])
    expect(dailyScores([{ ts: 'invalid', score: 5 }, { ts: '', score: 1 }])).toEqual([])
  })

  it('sorts days, fills missing days with null, and preserves a zero score', () => {
    expect(dailyScores([
      { ts: '2026-01-03T10:00:00Z', score: 5 },
      { ts: '2026-01-01T10:00:00Z', score: 0 },
    ])).toEqual([
      { date: '2026-01-01', score: 0 },
      { date: '2026-01-02', score: null },
      { date: '2026-01-03', score: 5 },
    ])
  })

  it('uses the worst session score on each UTC day', () => {
    expect(dailyScores([
      { ts: '2026-01-02T00:30:00+02:00', score: 4 },
      { ts: '2026-01-01T18:00:00Z', score: 2 },
      { ts: '2026-01-01T23:30:00-02:00', score: 3 },
      { ts: 'invalid', score: 99 },
    ])).toEqual([{ date: '2026-01-01', score: 4 }, { date: '2026-01-02', score: 3 }])
  })

  it('includes leap days and does not mutate input order', () => {
    const scores = [{ ts: '2024-03-01', score: 2 }, { ts: '2024-02-28', score: 1 }]
    const original = structuredClone(scores)
    expect(dailyScores(scores)).toEqual([
      { date: '2024-02-28', score: 1 },
      { date: '2024-02-29', score: null },
      { date: '2024-03-01', score: 2 },
    ])
    expect(scores).toEqual(original)
  })
})
