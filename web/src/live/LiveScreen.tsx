import { useId, useState } from 'react'
import { Button } from '../ui/Button.tsx'
import { LiveSession } from './LiveSession.tsx'
import type { LiveSessionEnded } from './useLiveSession.ts'
import './liveScreen.css'

/** The two recorded tasks a judge can watch. SPEC section 5, Nice to have 4 asks for
 * "a second task, such as getting dressed or taking medication with water, to show it
 * generalises": both options below run the same graph, error, score and flag chain off
 * their own task file, so the only difference between them is the scenario name. */
const TASKS: { scenario: string; label: string }[] = [
  { scenario: 'tea_skip_teabag_pour_twice', label: 'Making tea' },
  { scenario: 'meds_skip_water', label: 'Medication with water' },
]

export type LiveScreenProps = {
  onOpenAlert?: (alertId: string) => void
  onSessionEnd?: (ended: LiveSessionEnded) => void
}

/** Screen 3's task picker (SPEC section 9): the live session, with a switch above it for
 * which routine to watch. Tea is the demo path and stays the default. */
export function LiveScreen({ onOpenAlert, onSessionEnd }: LiveScreenProps) {
  const [scenario, setScenario] = useState(() => {
    const task = new URLSearchParams(window.location.search).get('task')
    return task === 'meds' ? TASKS[1].scenario : TASKS[0].scenario
  })
  const labelId = useId()

  return (
    <div className="live-screen">
      <div className="live-screen__tasks" role="group" aria-labelledby={labelId}>
        <p className="live-screen__label" id={labelId}>
          Routine to watch
        </p>
        {TASKS.map((task) => {
          const active = task.scenario === scenario
          return (
            <Button
              key={task.scenario}
              variant={active ? 'primary' : 'secondary'}
              aria-pressed={active}
              onClick={() => setScenario(task.scenario)}
            >
              {task.label}
            </Button>
          )
        })}
      </div>

      {/* `key` starts the picked routine from scratch: a fresh socket, an empty task map,
          and `onSessionEnd` free to fire again for the second task. */}
      <LiveSession
        key={scenario}
        scenario={scenario}
        onOpenAlert={onOpenAlert}
        onSessionEnd={onSessionEnd}
      />
    </div>
  )
}

export default LiveScreen
