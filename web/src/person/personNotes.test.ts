import { describe, expect, it } from 'vitest'
import type { PatternMatch } from '../contracts'
import { personNote, personStatus } from './personNotes'

const banned = /diagnos|patient|delirium|dementia|stroke|danger|warning|emergency|urgent/i
const patterns = [
  'sudden_change', 'slow_drift', 'evening_worsening', 'motor_slowing',
  'executive_pattern', 'one_sided_change', 'unknown_pattern', 'toString',
]

function match(pattern_id: string): PatternMatch {
  return {
    pattern_id,
    name: 'Clinical delirium warning',
    confidence: 0.8,
    urgency: 'routine',
    evidence: ['Clinical evidence'],
    checks: [],
  }
}

describe('personStatus', () => {
  it.each(['normal', 'watch', 'flagged'] as const)('uses calm personal copy for %s', (state) => {
    expect(personStatus(state)).toBeTruthy()
    expect(personStatus(state)).not.toMatch(banned)
  })

  it('describes the status time windows', () => {
    expect(personStatus('normal')).toContain('this week')
    expect(personStatus('watch')).toContain('lately')
    expect(personStatus('flagged')).toContain('today')
  })
})

describe('personNote', () => {
  describe.each(patterns)('%s', (pattern) => {
    it.each([undefined, 'Alex'])('uses personal wording with supervisor %s', (name) => {
      const note = personNote(match(pattern), name)
      expect(note.title.trim()).not.toBe('')
      expect(note.body.trim()).not.toBe('')
      expect(`${note.title} ${note.body}`).not.toMatch(banned)
      expect(note.body).toMatch(name
        ? /Worth mentioning to Alex or your doctor\.$/
        : /Worth mentioning to your doctor or someone you trust\.$/)
    })
  })

  it('uses the generic closing for an empty supervisor name', () => {
    expect(personNote(match('unknown'), '  ').body)
      .toMatch(/Worth mentioning to your doctor or someone you trust\.$/)
  })

  it('provides distinct descriptions for the known patterns', () => {
    const bodies = patterns.slice(0, 6).map((pattern) => personNote(match(pattern)).body)
    expect(new Set(bodies).size).toBe(6)
  })
})
