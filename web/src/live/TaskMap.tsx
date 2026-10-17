import { Fragment } from 'react'
import './taskMap.css'

export type StepState = 'pending' | 'done' | 'omission' | 'repeat' | 'sequence'

type TaskMapProps = {
  steps: { id: string; label: string }[]
  states: Record<string, StepState>
}

/** Icon and accessible status word per state, shared with `TaskMapLegend`, so a step's
 * state never relies on colour alone (SPEC section 9 accessibility rule). `pending` has
 * no icon or suffix: nothing has happened yet, so the step's own label already says it all. */
export const STEP_STATUS: Record<StepState, { legend: string; icon: string; accessible: string }> = {
  pending: { legend: 'not yet', icon: '', accessible: '' },
  done: { legend: 'done', icon: '✓', accessible: 'done' },
  omission: { legend: 'missed step', icon: '✕', accessible: 'missed' },
  repeat: { legend: 'repeated step', icon: '↻', accessible: 'repeated' },
  sequence: { legend: 'out of order', icon: '⇄', accessible: 'out of order' },
}

function stepAccessibleName(label: string, state: StepState): string {
  const { accessible } = STEP_STATUS[state]
  return accessible ? `${label} — ${accessible}` : label
}

/** Steps flow in wrapping rows (see `taskMap.css`), so all of them stay inside the
 * card and a step that turns red or amber is never scrolled out of sight. */
export function TaskMap({ steps, states }: TaskMapProps) {
  return (
    <div className="task-map" role="list" aria-label="Task steps">
      {steps.map((step, index) => {
        const state = states[step.id] ?? 'pending'
        const { icon } = STEP_STATUS[state]
        return (
          <Fragment key={step.id}>
            {index > 0 && (
              <span className="task-map__arrow" aria-hidden="true">
                →
              </span>
            )}
            <div
              role="listitem"
              className={`step step--${state}`}
              data-state={state}
              aria-label={stepAccessibleName(step.label, state)}
            >
              {icon && <span aria-hidden="true">{icon} </span>}
              {step.label}
            </div>
          </Fragment>
        )
      })}
    </div>
  )
}

export default TaskMap
