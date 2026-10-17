import { describe, expect, it } from 'vitest'
import { ERROR_TYPE_VALUES } from '../contracts.ts'
import { describeError, ERROR_TYPE_LABEL, ERROR_TYPE_TONE } from './errorTypes.ts'

describe('errorTypes', () => {
  it.each(ERROR_TYPE_VALUES)('has a label and a tone for %s', (type) => {
    expect(ERROR_TYPE_LABEL[type]).toBeTruthy()
    expect(['red', 'amber', 'grey']).toContain(ERROR_TYPE_TONE[type])
  })

  it.each([
    ['omission', 'skipped pour water'],
    ['perseveration', 'repeated pour water'],
    ['sequence', 'pour water out of order'],
    ['substitution', 'wrong object for pour water'],
    ['hesitation', 'long pause at pour water'],
    ['abandonment', 'stopped before pour water'],
  ] as const)('describes %s with its step', (type, phrase) => {
    expect(describeError(type, 'pour water')).toBe(phrase)
  })

  it('gives omission and substitution the red tone, the colours that mean a clear mistake', () => {
    expect(ERROR_TYPE_TONE.omission).toBe('red')
    expect(ERROR_TYPE_TONE.substitution).toBe('red')
  })

  it('gives sequence and perseveration the amber tone', () => {
    expect(ERROR_TYPE_TONE.sequence).toBe('amber')
    expect(ERROR_TYPE_TONE.perseveration).toBe('amber')
  })

  it('gives hesitation and abandonment the grey tone', () => {
    expect(ERROR_TYPE_TONE.hesitation).toBe('grey')
    expect(ERROR_TYPE_TONE.abandonment).toBe('grey')
  })
})
