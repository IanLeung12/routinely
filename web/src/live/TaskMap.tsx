import { Pill, type PillTone } from '../ui/Pill.tsx'
import './taskMap.css'

export type StepState = 'pending' | 'done' | 'omission' | 'repeat' | 'sequence'

type TaskMapProps = {
  steps: { id: string; label: string }[]
  states: Record<string, StepState>
}

/** Icon, accessible status word and pill per state, shared with `TaskMapLegend`, so a
 * step's state never relies on colour alone (SPEC section 9 accessibility rule).
 * `pending` has no icon, suffix or pill: nothing has happened yet, so the step keeps
 * its number and its label says it all. */
export const STEP_STATUS: Record<
  StepState,
  { legend: string; icon: string; accessible: string; pill: { label: string; tone: PillTone } | null }
> = {
  pending: { legend: 'not yet', icon: '', accessible: '', pill: null },
  done: { legend: 'done', icon: '✓', accessible: 'done', pill: { label: 'Done', tone: 'positive' } },
  omission: {
    legend: 'missed step',
    icon: '✕',
    accessible: 'missed',
    pill: { label: 'Missed', tone: 'negative' },
  },
  repeat: {
    legend: 'repeated step',
    icon: '↻',
    accessible: 'repeated',
    pill: { label: 'Repeated', tone: 'watch' },
  },
  sequence: {
    legend: 'out of order',
    icon: '⇄',
    accessible: 'out of order',
    pill: { label: 'Out of order', tone: 'watch' },
  },
}

function stepAccessibleName(label: string, state: StepState): string {
  const { accessible } = STEP_STATUS[state]
  return accessible ? `${label} — ${accessible}` : label
}

/** Screen 3's task graph (SPEC section 9), as a vertical step list: one dense row per
 * step down a single rail, the node carrying the step number until something happens
 * to it, then its icon. The state's own word rides on the right in a pill, so a step
 * that goes green, red or amber says which in text as well as colour.
 *
 * One column, not the wrapping rows this used to be: the card sits beside the skeleton
 * view in about a 400 px column, and a reader follows "what has happened so far" down a
 * list far faster than across a grid - which is the whole point of the demo's "the task
 * map flashes red and amber in real time" moment (SPEC section 10 step 3). */
export function TaskMap({ steps, states }: TaskMapProps) {
  const done = steps.filter((step) => (states[step.id] ?? 'pending') === 'done').length
  const percent = steps.length > 0 ? Math.round((done / steps.length) * 100) : 0

  return (
    <>
      {steps.length > 0 && (
        <div className="task-map__progress">
          <p className="task-map__progress-label">
            <span className="task-map__progress-count tabular-nums">
              {done} of {steps.length}
            </span>{' '}
            steps done
          </p>
          {/* A slim track rather than a number alone: how far through the routine
              someone is reads off the fill before anyone reads the count. */}
          <div
            className="task-map__track"
            role="progressbar"
            aria-label="Steps done"
            aria-valuemin={0}
            aria-valuemax={steps.length}
            aria-valuenow={done}
            aria-valuetext={`${done} of ${steps.length} steps done`}
          >
            <span className="task-map__track-fill" style={{ width: `${percent}%` }} />
          </div>
        </div>
      )}

      <div className="task-map" role="list" aria-label="Task steps">
        {steps.map((step, index) => {
          const state = states[step.id] ?? 'pending'
          const { icon, pill } = STEP_STATUS[state]
          return (
            <div
              role="listitem"
              key={step.id}
              className={`step step--${state}`}
              data-state={state}
              aria-label={stepAccessibleName(step.label, state)}
            >
              <span className={`step__node step__node--${state}`} aria-hidden="true">
                {icon || index + 1}
              </span>
              <span className="step__label">{step.label}</span>
              {pill && (
                <Pill className="step__pill" tone={pill.tone}>
                  {pill.label}
                </Pill>
              )}
            </div>
          )
        })}
      </div>
    </>
  )
}

export default TaskMap
