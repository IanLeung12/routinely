import type { JSX } from 'react'
import { STEP_STATUS, type StepState } from './TaskMap.tsx'

const STATES: StepState[] = ['pending', 'done', 'omission', 'repeat', 'sequence']

export function TaskMapLegend(): JSX.Element {
  return (
    <ul
      className="task-map task-map-legend"
      aria-label="Task map legend"
      style={{ flexWrap: 'wrap', listStyle: 'none', margin: 0 }}
    >
      {STATES.map((state) => {
        const { legend, icon } = STEP_STATUS[state]
        return (
          <li key={state} style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)' }}>
            <span
              aria-hidden="true"
              className={`step step--${state}`}
              style={{ padding: 'var(--space-2)' }}
            />
            <span>
              {icon && <span aria-hidden="true">{icon} </span>}
              {legend}
            </span>
          </li>
        )
      })}
    </ul>
  )
}
