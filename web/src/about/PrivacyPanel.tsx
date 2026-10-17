import { useId } from 'react'
import { Card } from '../ui/Card'
import { Row } from '../ui/Row'
import { SectionHeader } from '../ui/SectionHeader'
import './privacyPanel.css'

export function PrivacyPanel() {
  const headingId = useId()

  return (
    <section className="privacy-panel" aria-labelledby={headingId}>
      <Card>
        <div id={headingId}>
          <SectionHeader title="Privacy and limits" />
        </div>
        <ul className="privacy-panel__list">
          <li><Row title="Only skeleton points and object boxes leave the camera. No video is stored." /></li>
          <li><Row title="No face recognition. Each camera is linked to a room by configuration." /></li>
          <li><Row title="It flags a change for a nurse to review. It is not a medical assessment." /></li>
          <li><Row title="Low-confidence moments are shown as unclear, never counted as errors." /></li>
          <li><Row title="Pose tracking is less accurate with walkers, wheelchairs and unusual postures." /></li>
          <li><Row title="Residents or their decision-maker opt in; who consented and when is shown on each resident's page." /></li>
          <li><Row title="Monitoring can be paused per room; every pause and resume is logged with who and when." /></li>
        </ul>
      </Card>
    </section>
  )
}
