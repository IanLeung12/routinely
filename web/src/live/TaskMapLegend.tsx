import type { JSX } from 'react'
import { STEP_STATUS, type StepState } from './TaskMap.tsx'

const STATES: StepState[] = ['pending', 'done', 'omission', 'repeat', 'sequence']

/** The key to the canvas' node markers: the same swatch a node wears, with the word it
 * stands for, and a line for the two marks the nodes make without a colour - the dashed
 * card and line of an optional step, and the glow on the step that comes next. One
 * quiet block under the map, so the states can be learned once without any of them
 * having to shout from the canvas itself. */
export function TaskMapLegend(): JSX.Element {
  return (
    <>
      <ul className="task-map-legend" aria-label="Task map legend">
        {STATES.map((state) => {
          const { legend, icon } = STEP_STATUS[state]
          return (
            <li key={state} className="task-map-legend__item">
              <span aria-hidden="true" className={`task-map__dot task-map__dot--${state}`} />
              <span>
                {icon && <span aria-hidden="true">{icon} </span>}
                {legend}
              </span>
            </li>
          )
        })}
      </ul>
      <p className="task-map-legend__note">
        Dashed = optional step · glowing = ready next · steps side by side may happen in
        either order
      </p>
    </>
  )
}
