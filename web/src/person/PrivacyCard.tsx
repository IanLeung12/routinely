import { Button } from '../ui/Button'
import { Card } from '../ui/Card'
import { SectionHeader } from '../ui/SectionHeader'
import './privacyCard.css'

export function PrivacyCard({
  paused,
  onTogglePause,
  supervisorNames,
}: {
  paused: boolean
  onTogglePause: () => void
  supervisorNames: string[]
}) {
  const names = supervisorNames.length < 3
    ? supervisorNames.join(' and ')
    : `${supervisorNames.slice(0, -1).join(', ')}, and ${supervisorNames.at(-1)}`

  return (
    <Card className="privacy-card">
      <SectionHeader title="Your privacy" />
      <Button aria-pressed={paused} onClick={onTogglePause}>
        {paused ? 'Resume watching' : 'Pause watching'}
      </Button>
      <div aria-live="polite">
        {paused && <p className="privacy-card__paused">Watching is paused. Nothing is recorded until you resume.</p>}
      </div>
      <div className="privacy-card__detail">
        <h4 className="privacy-card__label">What's stored</h4>
        <p className="privacy-card__copy">Body outlines (skeletons) and timings only. No video or photos ever leave this device or get saved.</p>
      </div>
      <div className="privacy-card__detail">
        <h4 className="privacy-card__label">Who sees it</h4>
        <p className="privacy-card__copy">
          {supervisorNames.length === 0
            ? 'Only you can see this.'
            : `${names} ${supervisorNames.length === 1 ? 'sees' : 'see'} exactly what you see here.`}
        </p>
      </div>
    </Card>
  )
}
