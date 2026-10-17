import { useState, type FormEvent } from 'react'
import { TaskMap } from '../live/TaskMap.tsx'
import { Button } from '../ui/Button.tsx'
import { Card } from '../ui/Card.tsx'
import { ErrorState } from '../ui/ErrorState.tsx'
import { Loading } from '../ui/Loading.tsx'
import { SectionHeader } from '../ui/SectionHeader.tsx'
import { SegmentedControl } from '../ui/SegmentedControl.tsx'
import { draftFromText, draftFromVideo, saveRoutine } from './api.ts'
import { StepEditor } from './StepEditor.tsx'
import type { RoutineStep, SavedRoutine, TaskGraph } from './types.ts'
import './routines.css'

type Tab = 'text' | 'video'
type Status = 'idle' | 'drafting' | 'error'

/** Fills the textarea on click; it does not submit, so a nurse or person can still
 * edit it first. */
const EXAMPLES = [
  { label: 'Brushing teeth', text: 'Get the toothbrush, put toothpaste on it, brush, then rinse and spit.' },
  { label: 'Making toast', text: 'Put a slice of bread in the toaster, get a plate, move the toast to the plate, add butter.' },
  { label: 'Washing hands', text: 'Turn on the tap, add soap, rinse, turn off the tap, dry with a towel.' },
]

const CONSENT_LABEL =
  'This clip is sent once to Google Gemini to draft the steps. It is not stored. Day-to-day monitoring never sends video.'

function previewSteps(steps: RoutineStep[]) {
  return steps.map((step) => ({
    id: step.id,
    label: step.optional ? `${step.label} (optional)` : step.label,
  }))
}

/** "New routine" (T438): describe it in words or upload one setup clip, see the draft
 * as a task map, edit it, then save. Built against T437's API shape with a mock
 * fallback (`mock/routines.ts`) so this works before that backend exists and when
 * it's unreachable. */
export function RoutineBuilder({
  onSaved,
  onCancel,
}: {
  onSaved: (routine: SavedRoutine) => void
  onCancel?: () => void
}) {
  const [tab, setTab] = useState<Tab>('text')
  const [description, setDescription] = useState('')
  const [file, setFile] = useState<File | null>(null)
  const [consent, setConsent] = useState(false)
  const [status, setStatus] = useState<Status>('idle')
  const [error, setError] = useState<string | null>(null)
  const [graph, setGraph] = useState<TaskGraph | null>(null)
  const [needsTraining, setNeedsTraining] = useState<string[]>([])
  const [saving, setSaving] = useState(false)

  async function submitText(event: FormEvent) {
    event.preventDefault()
    if (description.trim() === '') return
    setStatus('drafting')
    setError(null)
    try {
      const result = await draftFromText(description)
      setGraph(result.task_graph)
      setNeedsTraining(result.needs_training)
      setStatus('idle')
    } catch {
      setStatus('error')
      setError("Couldn't draft a routine from that. Try rephrasing it or add more detail.")
    }
  }

  async function submitVideo(event: FormEvent) {
    event.preventDefault()
    if (!file || !consent) return
    setStatus('drafting')
    setError(null)
    try {
      const result = await draftFromVideo(file, consent)
      setGraph(result.task_graph)
      setNeedsTraining(result.needs_training)
      setStatus('idle')
    } catch {
      setStatus('error')
      setError("Couldn't draft a routine from that clip. Try again or describe it in words instead.")
    }
  }

  async function handleSave() {
    if (!graph) return
    setSaving(true)
    const saved = await saveRoutine(graph)
    setSaving(false)
    onSaved(saved)
  }

  function startOver() {
    setGraph(null)
    setNeedsTraining([])
    setStatus('idle')
    setError(null)
  }

  if (graph) {
    return (
      <Card className="routine-builder">
        <SectionHeader title={graph.title} caption="Check the steps before you save" />
        <TaskMap steps={previewSteps(graph.steps)} states={{}} />

        <h4 className="routine-builder__subheading">Edit the steps</h4>
        <StepEditor steps={graph.steps} onChange={(steps) => setGraph({ ...graph, steps })} />

        {needsTraining.length > 0 && (
          <p className="routine-builder__training" role="status">
            {`The detector doesn't know ${needsTraining.join(', ')} yet. Those steps will need a quick training pass before they can be scored.`}
          </p>
        )}

        <div className="routine-builder__actions">
          <Button onClick={startOver}>Start over</Button>
          <Button variant="primary" onClick={handleSave} disabled={saving}>
            {saving ? 'Saving…' : 'Save routine'}
          </Button>
        </div>
      </Card>
    )
  }

  return (
    <Card className="routine-builder">
      <SectionHeader title="New routine" caption="Describe it, or show it once on video" />
      <SegmentedControl
        label="How to create this routine"
        options={[
          { value: 'text', label: 'Describe it' },
          { value: 'video', label: 'From a video' },
        ]}
        value={tab}
        onChange={setTab}
      />

      {tab === 'text' ? (
        <form className="routine-builder__form" onSubmit={submitText}>
          <label className="routine-builder__field-label" htmlFor="routine-description">
            What happens, in order
          </label>
          <textarea
            id="routine-description"
            className="routine-builder__textarea"
            value={description}
            onChange={(event) => setDescription(event.target.value)}
            disabled={status === 'drafting'}
          />
          <div className="routine-builder__examples">
            <span className="routine-builder__examples-label">Examples:</span>
            {EXAMPLES.map((example) => (
              <button
                key={example.label}
                type="button"
                className="routine-builder__example"
                onClick={() => setDescription(example.text)}
                disabled={status === 'drafting'}
              >
                {example.label}
              </button>
            ))}
          </div>
          <Button
            type="submit"
            variant="primary"
            disabled={description.trim() === '' || status === 'drafting'}
          >
            Draft routine
          </Button>
        </form>
      ) : (
        <form className="routine-builder__form" onSubmit={submitVideo}>
          <label className="routine-builder__field-label" htmlFor="routine-video">
            A clip of the routine, up to about 60 seconds
          </label>
          <input
            id="routine-video"
            type="file"
            accept="video/*"
            className="routine-builder__file"
            onChange={(event) => setFile(event.target.files?.[0] ?? null)}
            disabled={status === 'drafting'}
          />
          <label className="routine-builder__consent">
            <input
              type="checkbox"
              checked={consent}
              onChange={(event) => setConsent(event.target.checked)}
              disabled={status === 'drafting'}
            />
            {CONSENT_LABEL}
          </label>
          <Button type="submit" variant="primary" disabled={!file || !consent || status === 'drafting'}>
            Draft routine
          </Button>
        </form>
      )}

      {status === 'drafting' && <Loading label="Drafting the steps…" />}
      {status === 'error' && error && <ErrorState message={error} />}
      {onCancel && (
        <Button className="routine-builder__cancel" onClick={onCancel}>
          Cancel
        </Button>
      )}
    </Card>
  )
}

export default RoutineBuilder
