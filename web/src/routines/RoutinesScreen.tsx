import { useEffect, useState } from 'react'
import { Button } from '../ui/Button.tsx'
import { Card } from '../ui/Card.tsx'
import { EmptyState } from '../ui/EmptyState.tsx'
import { Row } from '../ui/Row.tsx'
import { SectionHeader } from '../ui/SectionHeader.tsx'
import { SegmentedControl } from '../ui/SegmentedControl.tsx'
import { fetchRoutines } from './api.ts'
import { RoutineBuilder } from './RoutineBuilder.tsx'
import type { SavedRoutine } from './types.ts'
import './routines.css'

type View = 'builder' | 'list'

/** The shell's "New routine" screen (T438): opens straight into the builder, with a
 * "Routines" view alongside it listing the built-ins (tea, meds) plus anything saved,
 * newest last. Saving a draft switches to that list so the new routine is visible
 * right away. */
export function RoutinesScreen({ onBack }: { onBack: () => void }) {
  const [view, setView] = useState<View>('builder')
  const [routines, setRoutines] = useState<SavedRoutine[] | null>(null)

  useEffect(() => {
    let cancelled = false
    fetchRoutines().then((result) => {
      if (!cancelled) setRoutines(result)
    })
    return () => {
      cancelled = true
    }
  }, [])

  function handleSaved(routine: SavedRoutine) {
    setRoutines((previous) => [...(previous ?? []), routine])
    setView('list')
  }

  return (
    <section className="routines" aria-labelledby="routines-heading">
      <div className="routines__header">
        <Button onClick={onBack}>Back</Button>
        <h2 id="routines-heading">Routines</h2>
      </div>

      <SegmentedControl
        label="Routines view"
        options={[
          { value: 'builder', label: 'New routine' },
          { value: 'list', label: 'Routines' },
        ]}
        value={view}
        onChange={setView}
      />

      {view === 'builder' ? (
        <RoutineBuilder onSaved={handleSaved} />
      ) : (
        <Card>
          <SectionHeader
            title="Routines"
            caption="What the detector can watch for"
            action={
              <Button variant="primary" onClick={() => setView('builder')}>
                New routine
              </Button>
            }
          />
          {routines === null ? null : routines.length === 0 ? (
            <EmptyState message="No routines yet." />
          ) : (
            <ul className="routines__list">
              {routines.map((routine) => (
                <li key={routine.id}>
                  <Row
                    title={routine.title}
                    subtitle={routine.built_in ? 'Built in' : 'Saved by you'}
                    value={`${routine.task_graph.steps.length} steps`}
                  />
                </li>
              ))}
            </ul>
          )}
        </Card>
      )}
    </section>
  )
}

export default RoutinesScreen
