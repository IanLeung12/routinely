import type { PatternMatch } from '../contracts'

export function personStatus(state: 'normal' | 'watch' | 'flagged'): string {
  const statuses = {
    normal: 'Your routine looks like your usual this week',
    watch: 'A few things looked a little different lately',
    flagged: 'A few things looked different today',
  }
  return statuses[state]
}

const notes: Record<string, { title: string; body: string }> = {
  sudden_change: {
    title: 'A change in your routine',
    body: 'Some parts of your routine looked different from your usual over the past few days.',
  },
  slow_drift: {
    title: 'Small changes over time',
    body: 'Some parts of your routine have gradually looked different over recent weeks.',
  },
  evening_worsening: {
    title: 'A difference in the evening',
    body: 'Some steps looked harder to complete as usual, mostly in the evening.',
  },
  motor_slowing: {
    title: 'Taking a little longer',
    body: 'Some movements and steps took longer than usual.',
  },
  executive_pattern: {
    title: 'A change in the steps',
    body: 'Some steps were missed, repeated, or done in a different order from your usual.',
  },
  one_sided_change: {
    title: 'A difference in movement',
    body: 'Movement on one side of your body looked different from your usual.',
  },
}

export function personNote(
  match: PatternMatch,
  supervisorName?: string,
): { title: string; body: string } {
  const note = Object.hasOwn(notes, match.pattern_id) ? notes[match.pattern_id] : {
    title: 'Something looked a little different',
    body: 'Some parts of your routine looked different from your usual.',
  }
  const name = supervisorName?.trim()
  const closing = name
    ? `Worth mentioning to ${name} or your doctor.`
    : 'Worth mentioning to your doctor or someone you trust.'
  return { title: note.title, body: `${note.body} ${closing}` }
}
