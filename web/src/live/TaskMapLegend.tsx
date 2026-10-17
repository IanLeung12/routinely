import type { JSX } from 'react'
import { STEP_STATUS, type StepState } from './TaskMap.tsx'

const STATES: StepState[] = ['pending', 'done', 'omission', 'repeat', 'sequence']

export function TaskMapLegend(): JSX.Element {
  return (
    <ul className="task-map task-map-legend" aria-label="Task map legend">
      {STATES.map((state) => {
        const { legend, icon } = STEP_STATUS[state]
        return (
          <li key={state} className="task-map-legend__item">
            <span aria-hidden="true" className={`step step--${state}`} />
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
