import type { JSX } from 'react'

const STATES = [
  ['pending', 'not yet'],
  ['done', 'done'],
  ['omission', 'missed step'],
  ['repeat', 'repeated step'],
  ['sequence', 'out of order'],
] as const

export function TaskMapLegend(): JSX.Element {
  return (
    <ul
      className="task-map task-map-legend"
      aria-label="Task map legend"
      style={{ flexWrap: 'wrap', listStyle: 'none', margin: 0 }}
    >
      {STATES.map(([state, label]) => (
        <li key={state} style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)' }}>
          <span
            aria-hidden="true"
            className={`step step--${state}`}
            style={{ padding: 'var(--space-2)' }}
          />
          <span>{label}</span>
        </li>
      ))}
    </ul>
  )
}
