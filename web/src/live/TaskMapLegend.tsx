import type { JSX } from 'react'
import { STEP_STATUS, type StepState } from './TaskMap.tsx'

const STATES: StepState[] = ['pending', 'done', 'omission', 'repeat', 'sequence']

/** The key to the step list's nodes: the same swatch a step wears, with the word it
 * stands for. One quiet line under the map, so the five states can be learned once
 * without any of them having to shout from the list itself. */
export function TaskMapLegend(): JSX.Element {
  return (
    <ul className="task-map-legend" aria-label="Task map legend">
      {STATES.map((state) => {
        const { legend, icon } = STEP_STATUS[state]
        return (
          <li key={state} className="task-map-legend__item">
            <span aria-hidden="true" className={`step__node step__node--${state}`} />
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
