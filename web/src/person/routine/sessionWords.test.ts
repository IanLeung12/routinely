import { describe, expect, it } from 'vitest'
import {
  dayLabel,
  describeSession,
  formatMinutes,
  joinWords,
  whenLabel,
} from './sessionWords.ts'
import type { RoutineSession } from './types.ts'

const NOW = '2026-01-01T20:10:00+00:00'

/** Nothing the person reads may name a condition or raise an alarm (SPEC section 17). */
const banned = /diagnos|patient|resident|delirium|dementia|stroke|danger|warning|emergency|urgent|alarm/i

function session(overrides: Partial<RoutineSession> = {}): RoutineSession {
  return {
    session_id: 's1',
    started_at: '2026-01-01T08:10:00+00:00',
    task: 'Making tea',
    duration_s: 180,
    errors: {},
    ...overrides,
  }
}

describe('whenLabel', () => {
  it('names the part of today a session happened in', () => {
    expect(whenLabel('2026-01-01T08:10:00+00:00', NOW)).toBe('This morning')
    expect(whenLabel('2026-01-01T13:00:00+00:00', NOW)).toBe('This afternoon')
    expect(whenLabel('2026-01-01T18:40:00+00:00', NOW)).toBe('This evening')
  })

  it('says yesterday, then falls back to the weekday', () => {
    expect(whenLabel('2025-12-31T18:25:00+00:00', NOW)).toBe('Yesterday evening')
    expect(whenLabel('2025-12-30T08:08:00+00:00', NOW)).toBe('Tuesday morning')
  })

  it('reads the clock in UTC, so the words do not depend on the machine', () => {
    // 23:30 UTC is the evening everywhere this runs, not "tomorrow morning" east of it.
    expect(whenLabel('2026-01-01T23:30:00+00:00', NOW)).toBe('This evening')
  })

  it('leaves an unreadable timestamp alone and still names a weekday without a clock', () => {
    expect(whenLabel('not a date', NOW)).toBe('not a date')
    expect(whenLabel('2026-01-01T08:10:00+00:00', 'not a date')).toBe('Thursday morning')
  })
})

describe('dayLabel', () => {
  it('shortens a day to its weekday', () => {
    expect(dayLabel('2026-01-01')).toBe('Thu')
    expect(dayLabel('2025-12-28')).toBe('Sun')
  })

  it('leaves an unreadable date alone', () => {
    expect(dayLabel('whenever')).toBe('whenever')
  })
})

describe('formatMinutes', () => {
  it('rounds to whole minutes, never to none', () => {
    expect(formatMinutes(180)).toBe('3 min')
    expect(formatMinutes(318)).toBe('5 min')
    expect(formatMinutes(20)).toBe('1 min')
  })
})

describe('joinWords', () => {
  it.each([
    [[], ''],
    [['one'], 'one'],
    [['one', 'two'], 'one and two'],
    [['one', 'two', 'three'], 'one, two and three'],
  ])('joins %j naturally', (parts, expected) => {
    expect(joinWords(parts)).toBe(expected)
  })
})

describe('describeSession', () => {
  it('says the whole routine went the usual way when nothing differed', () => {
    const words = describeSession(session(), 3, NOW)

    expect(words.when).toBe('This morning')
    expect(words.took).toBe('3 min')
    expect(words.different).toBe('')
    expect(words.smooth).toBe('The whole routine went the way it usually does.')
  })

  it('names what was different in plain words, and what was not', () => {
    const words = describeSession(
      session({ errors: { omission: 1, hesitation: 2 } }),
      3,
      NOW,
    )

    expect(words.different).toBe(
      'A step was missed and there were a few longer pauses.',
    )
    expect(words.smooth).toBe('The rest went the way it usually does.')
  })

  it('mentions a routine that ran long against their own usual', () => {
    const words = describeSession(session({ duration_s: 318 }), 3, NOW)

    expect(words.different).toBe(
      'It took about 5 min instead of your usual 3 min.',
    )
  })

  it('leaves a slightly slower morning alone', () => {
    const words = describeSession(session({ duration_s: 200 }), 3, NOW)

    expect(words.different).toBe('')
  })

  it('credits a slip the person put right themselves', () => {
    expect(describeSession(session({ self_corrected: 1 }), 3, NOW).smooth).toBe(
      'You put one step right yourself and the whole routine went the way it usually does.',
    )
    expect(describeSession(session({ self_corrected: 2 }), 3, NOW).smooth).toBe(
      'You put 2 steps right yourself and the whole routine went the way it usually does.',
    )
  })

  it('never names a condition or raises an alarm', () => {
    const words = describeSession(
      session({
        duration_s: 400,
        self_corrected: 1,
        errors: {
          omission: 2, sequence: 1, perseveration: 2, substitution: 1,
          hesitation: 1, abandonment: 2,
        },
      }),
      3,
      NOW,
    )

    expect(`${words.when} ${words.took} ${words.different} ${words.smooth}`)
      .not.toMatch(banned)
  })
})
