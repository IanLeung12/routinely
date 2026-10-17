import { Button } from '../ui/Button'
import './privacyPanel.css'

export function MonitoringToggle({ room, on, onChange }: {
  room: string
  on: boolean
  onChange: (on: boolean) => void
}) {
  return (
    <div className="monitoring-toggle">
      <Button
        role="switch"
        aria-checked={on}
        aria-label={`Monitoring in room ${room}`}
        onClick={() => onChange(!on)}
      >
        {on ? 'On' : 'Paused'}
      </Button>
      {!on && <p className="monitoring-toggle__note">No camera data is processed while paused.</p>}
    </div>
  )
}
