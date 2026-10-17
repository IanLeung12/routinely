import { Fragment } from 'react'

type StepState = 'pending' | 'done' | 'omission' | 'repeat' | 'sequence'

type TaskMapProps = {
  steps: { id: string; label: string }[]
  states: Record<string, StepState>
}

export function TaskMap({ steps, states }: TaskMapProps) {
  return (
    <>
      <style>{`
        .task-map { display: flex; align-items: center; gap: 0.75rem; overflow-x: auto; padding: 0.5rem; }
        .task-map .step { flex-shrink: 0; border: 2px solid #64748b; border-radius: 0.5rem; padding: 0.75rem 1rem; background: #f1f5f9; color: #0f172a; }
        .task-map .step--done { background: #dcfce7; border-color: #15803d; }
        .task-map .step--omission { background: #fee2e2; border-color: #b91c1c; animation: task-map-pulse 1s ease-in-out infinite; }
        .task-map .step--repeat, .task-map .step--sequence { background: #fef3c7; border-color: #b45309; }
        @keyframes task-map-pulse { 50% { box-shadow: 0 0 0 4px #ef444466; } }
        @media (prefers-reduced-motion: reduce) { .task-map .step--omission { animation: none; } }
      `}</style>
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
