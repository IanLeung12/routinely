import { useState } from 'react'
import { SegmentedControl } from '../ui/SegmentedControl.tsx'
import { LiveSession } from './LiveSession.tsx'
import type { LiveSessionEnded } from './useLiveSession.ts'
import './liveScreen.css'

/** The two tasks a judge can watch. SPEC section 5, Nice to have 4 asks for "a second
 * task, such as getting dressed or taking medication with water, to show it
 * generalises": both options below run the same graph, error, score and flag chain off
 * their own task file, so the only difference between them is which recording to play -
 * or, on a camera, which graph to read the kitchen against (`task`). */
const TASKS: { scenario: string; task: string; label: string }[] = [
  { scenario: 'tea_skip_teabag_pour_twice', task: 'tea', label: 'Making tea' },
  { scenario: 'meds_skip_water', task: 'meds', label: 'Medication with water' },
]

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
  const [watching, setWatching] = useState(() => {
    const task = new URLSearchParams(window.location.search).get('task')
    return task === 'meds' ? TASKS[1] : TASKS[0]
  })
  const [cameraIndex] = useState(() => cameraIndexFrom(window.location.search))

  return (
    <div className="live-screen">
      <div className="live-screen__tasks">
        {/* The control's own group label already says this, so the visible copy is
            decoration for sighted readers rather than a second thing to hear. */}
        <p className="live-screen__label" aria-hidden="true">
          Routine to watch
        </p>
        <SegmentedControl
          label="Routine to watch"
          options={TASKS.map((task) => ({ value: task.scenario, label: task.label }))}
          value={watching.scenario}
          onChange={(scenario) => {
            setWatching(TASKS.find((task) => task.scenario === scenario) ?? TASKS[0])
          }}
        />
      </div>

      {/* `key` starts the picked routine from scratch: a fresh socket, an empty task map,
          and `onSessionEnd` free to fire again for the second task. */}
      <LiveSession
        key={watching.scenario}
        scenario={watching.scenario}
        camera={cameraIndex === null ? null : { index: cameraIndex, task: watching.task }}
        onOpenAlert={onOpenAlert}
        onSessionEnd={onSessionEnd}
      />
    </div>
  )
}

export default LiveScreen
