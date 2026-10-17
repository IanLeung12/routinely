import { afterEach, describe, expect, it } from 'vitest'
import { routineFor, setPersonRoutineApi } from './api.ts'
import { mockPersonRoutine } from './mockRoutine.ts'

afterEach(() => {
  setPersonRoutineApi(null)
})

describe('routineFor', () => {
  it("serves the demo person's own week", () => {
    const routine = routineFor('sam')

    expect(routine.person_id).toBe('sam')
    expect(routine.status).toBe('flagged')
    expect(routine.patterns.map((pattern) => pattern.pattern_id))
      .toEqual(['motor_slowing', 'evening_worsening'])
  })

  it('builds the days from the sessions, oldest first', () => {
    const { days, sessions, usual_minutes } = routineFor('sam')

    expect(days.length).toBe(7)
    expect(days.map((day) => day.date)).toEqual([...days.map((day) => day.date)].sort())
    expect(new Set(days.map((day) => day.usual_minutes))).toEqual(new Set([usual_minutes]))
    // Every charted day is a day the person really had a session.
    const sessionDays = new Set(sessions.map((session) => session.started_at.slice(0, 10)))
    expect(days.every((day) => sessionDays.has(day.date))).toBe(true)
  })

  it('ends the week above their usual, which is what the note is about', () => {
    const { days, usual_minutes } = routineFor('sam')
    const today = days[days.length - 1]

    expect(today.minutes).toBeGreaterThan(usual_minutes)
    expect(days[0].minutes).toBeCloseTo(usual_minutes, 0)
  })

  it('gives anyone else a steady week under their own id', () => {
    const routine = routineFor('mr-d')

    expect(routine.person_id).toBe('mr-d')
    expect(routine.status).toBe('normal')
    expect(routine.patterns).toEqual([])
    expect(routine.sessions.every((session) => Object.keys(session.errors).length === 0))
      .toBe(true)
  })

  it('hands over to a real API and back again', () => {
    const mine = { ...mockPersonRoutine, person_id: 'someone', status: 'watch' as const }
    setPersonRoutineApi({ routineFor: () => mine })

    expect(routineFor('sam')).toBe(mine)

    setPersonRoutineApi(null)
    expect(routineFor('sam').status).toBe('flagged')
  })
})
