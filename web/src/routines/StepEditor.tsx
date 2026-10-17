import { useId, useState } from 'react'
import { Button } from '../ui/Button.tsx'
import type { RoutineStep } from './types.ts'

function slugify(label: string): string {
  return label.trim().toLowerCase().replace(/[^a-z0-9]+/g, '_').replace(/^_+|_+$/g, '') || 'step'
}

function uniqueId(base: string, taken: Set<string>): string {
  if (!taken.has(base)) return base
  let suffix = 2
  while (taken.has(`${base}_${suffix}`)) suffix += 1
  return `${base}_${suffix}`
}

/** Keeps every step's `depends_on` pointing only at steps that still come before it
 * (`tasks/graph.py`'s rule), so a reorder or a delete never leaves a dangling or
 * forward-pointing dependency. */
function sanitizeDeps(steps: RoutineStep[]): RoutineStep[] {
  const seen = new Set<string>()
  return steps.map((step) => {
    const depends_on = step.depends_on.filter((id) => seen.has(id))
    seen.add(step.id)
    return { ...step, depends_on }
  })
}

/** The drafted routine's steps, editable (T438): rename, move up/down, change which
 * earlier steps it depends on, toggle optional, delete, add. Every change is reported
 * through `onChange` as a full, sanitised step list, so the caller's task-map preview
 * stays in sync without owning any of this state itself. */
export function StepEditor({
  steps,
  onChange,
}: {
  steps: RoutineStep[]
  onChange: (steps: RoutineStep[]) => void
}) {
  const [newLabel, setNewLabel] = useState('')
  const newStepId = useId()

  function update(index: number, patch: Partial<RoutineStep>) {
    onChange(sanitizeDeps(steps.map((step, i) => (i === index ? { ...step, ...patch } : step))))
  }

  function move(index: number, delta: number) {
    const target = index + delta
    if (target < 0 || target >= steps.length) return
    const next = [...steps]
    const [moved] = next.splice(index, 1)
    next.splice(target, 0, moved)
    onChange(sanitizeDeps(next))
  }

  function remove(index: number) {
    const removedId = steps[index].id
    const next = steps
      .filter((_, i) => i !== index)
      .map((step) => ({ ...step, depends_on: step.depends_on.filter((id) => id !== removedId) }))
    onChange(next)
  }

  function toggleDep(index: number, depId: string) {
    const step = steps[index]
    const depends_on = step.depends_on.includes(depId)
      ? step.depends_on.filter((id) => id !== depId)
      : [...step.depends_on, depId]
    update(index, { depends_on })
  }

  function addStep() {
    const label = newLabel.trim()
    if (!label) return
    const id = uniqueId(slugify(label), new Set(steps.map((step) => step.id)))
    onChange([...steps, { id, label, objects: [], depends_on: [], optional: false, once_only: true }])
    setNewLabel('')
  }

  return (
    <ul className="step-editor">
      {steps.map((step, index) => {
        const earlier = steps.slice(0, index)
        return (
          <li key={step.id} className="step-editor__item">
            <div className="step-editor__row">
              <label className="step-editor__label" htmlFor={`${step.id}-label`}>
                Step {index + 1}
              </label>
              <input
                id={`${step.id}-label`}
                className="step-editor__input"
                value={step.label}
                onChange={(event) => update(index, { label: event.target.value })}
              />
              <Button
                aria-label={`Move ${step.label} up`}
                disabled={index === 0}
                onClick={() => move(index, -1)}
              >
                ↑
              </Button>
              <Button
                aria-label={`Move ${step.label} down`}
                disabled={index === steps.length - 1}
                onClick={() => move(index, 1)}
              >
                ↓
              </Button>
              <Button variant="danger" aria-label={`Delete ${step.label}`} onClick={() => remove(index)}>
                Delete
              </Button>
            </div>

            <label className="step-editor__optional">
              <input
                type="checkbox"
                checked={step.optional}
                onChange={(event) => update(index, { optional: event.target.checked })}
              />
              Optional step
            </label>

            {earlier.length > 0 && (
              <fieldset className="step-editor__deps">
                <legend>{`Depends on, for "${step.label}"`}</legend>
                {earlier.map((candidate) => (
                  <label key={candidate.id} className="step-editor__dep">
                    <input
                      type="checkbox"
                      checked={step.depends_on.includes(candidate.id)}
                      onChange={() => toggleDep(index, candidate.id)}
                    />
                    {candidate.label}
                  </label>
                ))}
              </fieldset>
            )}
          </li>
        )
      })}

      <li className="step-editor__add">
        <label className="step-editor__label" htmlFor={newStepId}>
          Add a step
        </label>
        <input
          id={newStepId}
          className="step-editor__input"
          value={newLabel}
          placeholder="e.g. Rinse the cup"
          onChange={(event) => setNewLabel(event.target.value)}
        />
        <Button variant="primary" onClick={addStep} disabled={newLabel.trim() === ''}>
          Add step
        </Button>
      </li>
    </ul>
  )
}

export default StepEditor
