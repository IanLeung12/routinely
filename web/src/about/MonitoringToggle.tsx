import { Button } from '../ui/Button'

export function MonitoringToggle({ room, on, onChange }: {
  room: string
  on: boolean
  onChange: (on: boolean) => void
}) {
  return (
    <div>
      <Button
        role="switch"
        aria-checked={on}
        aria-label={`Monitoring in room ${room}`}
        onClick={() => onChange(!on)}
      >
        {on ? 'On' : 'Paused'}
      </Button>
      {!on && <p>No camera data is processed while paused.</p>}
    </div>
  )
}
