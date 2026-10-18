import { useEffect, useState } from 'react'
import { fetchRoutines } from '../routines/api.ts'
import { SegmentedControl } from '../ui/SegmentedControl.tsx'
import { LiveSession } from './LiveSession.tsx'
import type { LiveSessionEnded } from './useLiveSession.ts'
import './liveScreen.css'

/** The two tasks a judge can watch. SPEC section 5, Nice to have 4 asks for "a second
 * task, such as getting dressed or taking medication with water, to show it
 * generalises": both options below run the same graph, error, score and flag chain off
 * their own task file, so the only difference between them is which recording to play -
 * or, on a camera, which graph to read the kitchen against (`task`). */
type Watchable = { scenario: string | null; task: string; label: string }

/** Recorded sessions to play when no camera is attached, by routine id. */
const SCENARIOS: Record<string, string> = {
  tea: 'tea_skip_teabag_pour_twice',
  meds: 'meds_skip_water',
  protein_shake: 'protein_shake_omit_powder',
}

const TASKS: Watchable[] = [
  { scenario: SCENARIOS.tea, task: 'tea', label: 'Making tea' },
  { scenario: SCENARIOS.meds, task: 'meds', label: 'Medication with water' },
  { scenario: SCENARIOS.protein_shake, task: 'protein_shake', label: 'Make a protein shake' },
]

const keyOf = (item: Watchable) => item.task

/** Which camera the Live screen is pointed at, from the dashboard URL: `?source=camera`
 * turns it on and `?camera=N` picks the device, 0 being the laptop's own. `null` - no
 * `?source=camera` - plays the recorded scenario, which is the demo's own path and the
 * fallback for a camera that fails (SPEC section 10). `scripts/camera.sh` starts the
 * stack and prints the URL; `docs/DEMO.md` has the whole run. */
function cameraIndexFrom(search: string): number | null {
  const params = new URLSearchParams(search)
  if (params.get('source') !== 'camera') {
    return null
  }
  const index = Number.parseInt(params.get('camera') ?? '', 10)
  return Number.isNaN(index) || index < 0 ? 0 : index
}

export type LiveScreenProps = {
  onOpenAlert?: (alertId: string) => void
  onSessionEnd?: (ended: LiveSessionEnded) => void
}

/** Screen 3's task picker (SPEC section 9): the live session, with a switch above it for
 * which routine to watch. Tea is the demo path and stays the default. */
export function LiveScreen({ onOpenAlert, onSessionEnd }: LiveScreenProps) {
  const [routines, setRoutines] = useState<Watchable[]>(TASKS)
  const [watchingId, setWatchingId] = useState(
    () => new URLSearchParams(window.location.search).get('task') ?? 'tea',
  )
  const [cameraIndex] = useState(() => cameraIndexFrom(window.location.search))

  useEffect(() => {
    let live = true
    fetchRoutines()
      .then((list) => {
        if (!live || list.length === 0) return
        setRoutines(
          list.map((routine) => ({
            task: routine.id,
            label: TASKS.find((known) => known.task === routine.id)?.label ?? routine.title,
            scenario: SCENARIOS[routine.id] ?? null,
          })),
        )
      })
      .catch(() => {})
    return () => {
      live = false
    }
  }, [])

  const watching = routines.find((item) => keyOf(item) === watchingId) ?? routines[0] ?? TASKS[0]
  const options = routines.map((item) => ({ value: keyOf(item), label: item.label }))

  return (
    <div className="live-screen">
      <div className="live-screen__tasks">
        <p className="live-screen__label" aria-hidden="true">
          Routine to watch
        </p>
        {options.length > 3 ? (
          <select
            aria-label="Routine to watch"
            className="live-screen__select"
            value={keyOf(watching)}
            onChange={(event) => setWatchingId(event.target.value)}
          >
            {options.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        ) : (
          <SegmentedControl
            label="Routine to watch"
            options={options}
            value={keyOf(watching)}
            onChange={(value) => setWatchingId(value)}
          />
        )}
      </div>

      {cameraIndex === null && watching.scenario === null ? (
        <p className="live-screen__hint">
          No recording for this routine yet. Watch it with the camera: run{' '}
          <code>scripts/camera.sh</code> and open the link it prints.
        </p>
      ) : (
        <LiveSession
          key={keyOf(watching)}
          scenario={watching.scenario ?? SCENARIOS.tea}
          camera={cameraIndex === null ? null : { index: cameraIndex, task: watching.task }}
          onOpenAlert={onOpenAlert}
          onSessionEnd={onSessionEnd}
        />
      )}
    </div>
  )
}

export default LiveScreen
