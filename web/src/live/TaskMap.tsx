import { Fragment } from 'react'

type StepState = 'pending' | 'done' | 'omission' | 'repeat' | 'sequence'

type TaskMapProps = {
  steps: { id: string; label: string }[]
  states: Record<string, StepState>
}

export function TaskMap({ steps, states }: TaskMapProps) {
  return (
    <>
      <div className="task-map" role="list" aria-label="Task steps">
        {steps.map((step, index) => {
          const state = states[step.id] ?? 'pending'
          return (
            <Fragment key={step.id}>
              {index > 0 && <span aria-hidden="true">→</span>}
              <div role="listitem" className={`step step--${state}`} data-state={state}>
                {step.label}
              </div>
            </Fragment>
          )
        })}
      </div>
    </>
  )
}

export default TaskMap
