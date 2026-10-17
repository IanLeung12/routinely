import { Button } from '../../ui/Button.tsx'
import { Card } from '../../ui/Card.tsx'
import { SectionHeader } from '../../ui/SectionHeader.tsx'
import './routine.css'

/** Its own three lines rather than `sessionWords.joinWords`: this card is the one
 * piece of the person's screen that loads with the shell, so it imports nothing
 * that would drag the rest of the week's wording along with it. */
function joinNames(names: string[]): string {
  if (names.length <= 1) return names[0] ?? ''
  return `${names.slice(0, -1).join(', ')} and ${names[names.length - 1]}`
}

/** Who can see this, in one sentence. */
function seenBy(supervisorNames: string[]): string {
  if (supervisorNames.length === 0) return 'Only you can see this.'
  const verb = supervisorNames.length === 1 ? 'sees' : 'see'
  return `${joinNames(supervisorNames)} ${verb} exactly what you see here.`
}

/** The person's off switch and the privacy story in their own words (SPEC sections
 * 8 and 17): pause watching, what is kept (skeletons and timings, never video), and
 * that their supervisors see this screen's data and nothing more.
 *
 * The interface is T429's, which builds the same card as its own piece; when that
 * lands, "My routine" swaps the import and this file goes. */
export function PrivacyCard({
  paused,
  onTogglePause,
  supervisorNames,
}: {
  paused: boolean
  onTogglePause: () => void
  supervisorNames: string[]
}) {
  return (
    <Card>
      <SectionHeader title="Your privacy" />
      <Button
        variant={paused ? 'primary' : 'secondary'}
        className="privacy-card__pause"
        aria-pressed={paused}
        onClick={onTogglePause}
      >
        {paused ? 'Resume watching' : 'Pause watching'}
      </Button>
      <p className="privacy-card__paused" role="status">
        {paused ? 'Watching is paused. Nothing is recorded until you resume.' : ''}
      </p>
      <dl className="privacy-card__facts">
        <dt className="privacy-card__term">{`What's stored`}</dt>
        <dd className="privacy-card__detail">
          Body outlines (skeletons) and timings only. No video or photos ever leave
          this device or get saved.
        </dd>
        <dt className="privacy-card__term">Who sees it</dt>
        <dd className="privacy-card__detail">{seenBy(supervisorNames)}</dd>
      </dl>
    </Card>
  )
}

export default PrivacyCard
